#!/usr/bin/env python3
"""Migrate SSRF-Lite YAML from 0.8.0 to 0.9.0: frequencies move to the station.

Under 0.8.0 an rf_chain's ``tx``/``rx`` were written from the *radio's* point of
view, so a repeater's ``tx`` held its input. Under 0.9.0 every rf_chain
describes its own station, so ``tx`` holds the output. Each chain therefore
swaps its two ``freq_mhz`` scalars -- which for the common "monitored output
only" chains means the frequency moves from ``rx`` to ``tx`` and ``rx`` is
dropped. The same flip applies to ``mode``: a repeater's ``ctcss_rx_hz`` is now
the tone it demands on its input, and ``ctcss_tx_hz`` the tone it sends on its
output. Channel plans get the matching rename, ``tx_freq_mhz`` ->
``rx_freq_mhz``.

Point it at a private overlay root to migrate that too::

    python migrate_0_8_to_0_9.py ../my-ssrf-private/ssrf

The rewrite is textual, to preserve comments and layout, then verified by
re-parsing and checking that the swap is the *only* difference. Files that fail
verification are left untouched and reported.
"""

from __future__ import annotations

import argparse
import copy
import pathlib
import re
import sys
from typing import Any

import yaml

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"

# Block style: tx: / rx: on their own lines, each with a freq_mhz scalar and
# possibly other keys (power_w, emission, ...) in between.
BLOCK_BOTH_RE = re.compile(
    r"""
    ^(?P<indent>[ ]*)tx:[ ]*\n
    (?P<tx_key>(?P=indent)[ ]+freq_mhz:[ ]*)(?P<tx_val>\S+)(?P<tx_tail>[^\n]*)\n
    (?P<tx_rest>(?:(?P=indent)[ ]+(?!freq_mhz:)[^\n]*\n)*?)
    (?P=indent)rx:[ ]*\n
    (?P<rx_key>(?P=indent)[ ]+freq_mhz:[ ]*)(?P<rx_val>\S+)(?P<rx_tail>[^\n]*)\n
    """,
    re.MULTILINE | re.VERBOSE,
)

# Block style: rx: before tx:, both carrying a frequency.
BLOCK_RX_FIRST_BOTH_RE = re.compile(
    r"""
    ^(?P<indent>[ ]*)rx:[ ]*\n
    (?P<rx_key>(?P=indent)[ ]+freq_mhz:[ ]*)(?P<rx_val>\S+)(?P<rx_tail>[^\n]*)\n
    (?P<rx_rest>(?:(?P=indent)[ ]+(?!freq_mhz:)[^\n]*\n)*?)
    (?P=indent)tx:[ ]*\n
    (?P<tx_key>(?P=indent)[ ]+freq_mhz:[ ]*)(?P<tx_val>\S+)(?P<tx_tail>[^\n]*)\n
    """,
    re.MULTILINE | re.VERBOSE,
)

# Block style: rx: holds the only frequency and tx: carries just the emission
# metadata, i.e. a monitored output recorded from the listener's side.
BLOCK_RX_THEN_TX_RE = re.compile(
    r"""
    ^(?P<indent>[ ]*)rx:[ ]*\n
    (?P<key>(?P=indent)[ ]+freq_mhz:[ ]*)(?P<val>\S+)(?P<tail>[^\n]*)\n
    (?P=indent)tx:[ ]*\n
    (?!(?P=indent)[ ]+freq_mhz:)
    (?P<tx_body>(?:(?P=indent)[ ]+[^\n]*\n)*)
    """,
    re.MULTILINE | re.VERBOSE,
)

# Flow style, e.g. rx: { freq_mhz: N }, tx: { freq_mhz: M, emission: ... }.
# Whitespace-tolerant because some files wrap these mappings across lines.
FLOW_BOTH_RE = re.compile(
    r"""
    rx:\s*\{\s*freq_mhz:\s*(?P<rx_val>[^,}\s]+)\s*\}(?P<sep>\s*,?\s*)
    tx:\s*\{\s*freq_mhz:\s*(?P<tx_val>[^,}\s]+)\s*(?P<tx_rest>(?:,[^}]*)?)\}
    """,
    re.VERBOSE,
)

# Flow style where rx: holds the only frequency and tx: carries just metadata.
FLOW_RX_ONLY_RE = re.compile(
    r"""
    rx:\s*\{\s*freq_mhz:\s*(?P<val>[^,}\s]+)\s*\}\s*,?\s*
    tx:\s*\{(?!\s*freq_mhz)\s*(?P<body>[^}]*?)\s*\}
    """,
    re.VERBOSE,
)


def _swap_block(match: re.Match[str]) -> str:
    g = match.groupdict()
    return (
        f"{g['indent']}tx:\n"
        f"{g['tx_key']}{g['rx_val']}{g['rx_tail']}\n"
        f"{g['tx_rest']}"
        f"{g['indent']}rx:\n"
        f"{g['rx_key']}{g['tx_val']}{g['tx_tail']}\n"
    )


def _swap_flow_both(match: re.Match[str]) -> str:
    g = match.groupdict()
    return (
        f"rx: {{ freq_mhz: {g['tx_val']} }}{g['sep']}"
        f"tx: {{ freq_mhz: {g['rx_val']}{g['tx_rest']} }}"
    )


def _fold_flow_rx_into_tx(match: re.Match[str]) -> str:
    g = match.groupdict()
    body = f"freq_mhz: {g['val']}"
    if g["body"]:
        body += f", {g['body']}"
    return f"tx: {{ {body} }}"


def _fold_rx_into_tx(match: re.Match[str]) -> str:
    g = match.groupdict()
    return f"{g['indent']}tx:\n{g['key']}{g['val']}{g['tail']}\n{g['tx_body']}"


def _swap_rx_first(match: re.Match[str]) -> str:
    g = match.groupdict()
    return (
        f"{g['indent']}rx:\n"
        f"{g['rx_key']}{g['tx_val']}{g['tx_tail']}\n"
        f"{g['rx_rest']}"
        f"{g['indent']}tx:\n"
        f"{g['tx_key']}{g['rx_val']}{g['rx_tail']}\n"
    )


#: Mode keys that change sides with the frequencies. Swapping the key names
#: rather than the values keeps values, quoting, and comments untouched.
MODE_KEY_PAIRS = (
    ("ctcss_tx_hz", "ctcss_rx_hz"),
    ("dcs_tx_code", "dcs_rx_code"),
    ("dcs_tx_polarity", "dcs_rx_polarity"),
)


def _swap_mode_keys(text: str) -> tuple[str, int]:
    count = 0
    for index, (tx_key, rx_key) in enumerate(MODE_KEY_PAIRS):
        placeholder = f"__SSRF_SWAP_{index}__"
        # Only rename actual mapping keys; prose in `comments` and `notes`
        # mentions these names too and must be reworded by hand.
        text, a = re.subn(rf"\b{tx_key}(?=\s*:)", placeholder, text)
        text, b = re.subn(rf"\b{rx_key}(?=\s*:)", tx_key, text)
        text, _ = re.subn(rf"\b{placeholder}\b", rx_key, text)
        count += a + b
    return text, count


def _freqs(doc: Any) -> dict[Any, tuple[Any, Any]]:
    out: dict[Any, tuple[Any, Any]] = {}
    for chain in (doc or {}).get("rf_chains") or []:
        tx = chain.get("tx") or {}
        rx = chain.get("rx") or {}
        out[chain.get("id")] = (tx.get("freq_mhz"), rx.get("freq_mhz"))
    return out


def _unswapped(doc: Any) -> Any:
    """Copy of the migrated doc with the swap undone, so that any *other*
    accidental edit shows up as a difference."""

    doc = copy.deepcopy(doc) or {}
    for chain in doc.get("rf_chains") or []:
        tx = chain.get("tx") or {}
        rx = chain.get("rx") or {}
        tx["freq_mhz"], rx["freq_mhz"] = rx.get("freq_mhz"), tx.get("freq_mhz")
        chain["tx"], chain["rx"] = tx, rx
        mode = chain.get("mode")
        if isinstance(mode, dict):
            for tx_key, rx_key in MODE_KEY_PAIRS:
                if tx_key in mode or rx_key in mode:
                    mode[tx_key], mode[rx_key] = mode.get(rx_key), mode.get(tx_key)
    for plan in doc.get("channel_plans") or []:
        for ch in plan.get("channels") or []:
            if "rx_freq_mhz" in ch:
                ch["tx_freq_mhz"] = ch.pop("rx_freq_mhz")
    return doc


def _baseline(doc: Any) -> Any:
    """The pre-migration doc reshaped so the two are comparable."""

    doc = copy.deepcopy(doc) or {}
    for chain in doc.get("rf_chains") or []:
        tx = chain.get("tx") or {}
        rx = chain.get("rx") or {}
        tx.setdefault("freq_mhz", None)
        rx.setdefault("freq_mhz", None)
        chain["tx"], chain["rx"] = tx, rx
        mode = chain.get("mode")
        if isinstance(mode, dict):
            for tx_key, rx_key in MODE_KEY_PAIRS:
                if tx_key in mode or rx_key in mode:
                    mode.setdefault(tx_key, None)
                    mode.setdefault(rx_key, None)
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=pathlib.Path,
        default=[SSRF_ROOT],
        help="SSRF roots to migrate (default: this repository's ssrf/).",
    )
    args = parser.parse_args()

    files = 0
    chains = 0
    renames = 0
    failures: list[str] = []

    for root in args.roots:
        for path in sorted(root.rglob("*.yml")):
            original = path.read_text(encoding="utf-8")
            before = yaml.safe_load(original) or {}
            if not (before.get("rf_chains") or before.get("channel_plans")):
                continue

            migrated, n_block = BLOCK_BOTH_RE.subn(_swap_block, original)
            migrated, n_rxfirst = BLOCK_RX_FIRST_BOTH_RE.subn(_swap_rx_first, migrated)
            migrated, n_fold = BLOCK_RX_THEN_TX_RE.subn(_fold_rx_into_tx, migrated)
            migrated, n_flow_both = FLOW_BOTH_RE.subn(_swap_flow_both, migrated)
            migrated, n_flow = FLOW_RX_ONLY_RE.subn(_fold_flow_rx_into_tx, migrated)
            migrated, n_mode = _swap_mode_keys(migrated)
            migrated, n_plan = re.subn(
                r"^(\s*)tx_freq_mhz:", r"\1rx_freq_mhz:", migrated, flags=re.MULTILINE
            )
            if migrated == original:
                continue

            after = yaml.safe_load(migrated) or {}

            expected = {cid: (rx, tx) for cid, (tx, rx) in _freqs(before).items()}
            if _freqs(after) != expected:
                failures.append(f"{path}: frequency swap incorrect")
                continue
            if _unswapped(after) != _baseline(before):
                failures.append(f"{path}: unrelated content changed")
                continue

            path.write_text(migrated, encoding="utf-8")
            files += 1
            chains += n_block + n_rxfirst + n_fold + n_flow_both + n_flow
            renames += n_plan

    print(f"{files} files, {chains} rf_chains swapped, {renames} plan keys renamed")
    for failure in failures:
        print(f"  FAILED {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
