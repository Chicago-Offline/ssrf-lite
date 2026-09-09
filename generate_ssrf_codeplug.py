#!/usr/bin/env python3
"""
Generate a compiled, browser-ready codeplug JSON from the SSRF-Lite library.

Walks every SSRF-Lite YAML document and flattens each channel-bearing
assignment (``assignments`` → ``rf_chains`` → ``stations`` → ``locations``, or
``assignments`` → ``channel_plans``) into a single flat array of radio-centric
channel records:

    {
        "callsign": str | null,     # station call sign, if any
        "rx_mhz": float,            # frequency the radio RECEIVES on
        "tx_mhz": float,            # frequency the radio TRANSMITS on
        "ctcss": float | null,      # CTCSS tone the radio must encode (Hz)
        "dcs": str | int | null,    # DCS code the radio must encode
        "dcs_polarity": str | null, # DCS polarity (N or I)
        "color_code": int | null,   # DMR color code
        "timeslots": [int] | null,  # DMR timeslots
        "lat": float | null,        # site latitude
        "lon": float | null,        # site longitude
        "service": str | null,      # SSRF service taxonomy id
        "mode": str | null,         # modulation/mode (FM, DMR, ...)
        "bandwidth_khz": float | null, # channel bandwidth (kHz)
        "name": str                 # human-readable channel name
    }

Frequencies are radio-centric: ``rx_mhz`` is what the operator's radio listens
to (the repeater's transmit / output), and ``tx_mhz`` is what the radio
transmits (the repeater's receive / input). For simplex channels the two are
equal.

CTCSS/DCS values are the tones the radio must *encode* to key a repeater, i.e.
the repeater's receive (input) tone, falling back to the transmit tone when only
one is defined. This keeps downstream consumers (e.g. NeonPlug) thin: they can
fetch this file and filter by distance without joining any relational data.

The output is a top-level JSON array written to ``site/codeplug.json`` so it is
published alongside the GitHub Pages site.
"""

import argparse
import json
import pathlib
import re
from typing import Any, Dict, List, Optional

from ssrf import resolve_ssrf_roots

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"
SITE_DIR = BASE / "site"


def _round(value: Optional[float], digits: int = 6) -> Optional[float]:
    return round(value, digits) if value is not None else None


def _assignment_display_name(a: Any) -> str:
    if a.channel_name:
        return a.channel_name
    name = a.id
    for prefix in ("asgn_", "assign_", "chan_", "ch_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("_", " ")


def _encode_tone(tx_tone: Optional[float], rx_tone: Optional[float]) -> Optional[float]:
    """Tone the radio must transmit to access the far end (repeater input)."""
    return rx_tone if rx_tone is not None else tx_tone


# ITU necessary-bandwidth prefix: digits around a decimal-point letter
# (H = Hz, K = kHz, M = MHz), e.g. 16K0 -> 16.0 kHz, 11K2 -> 11.2 kHz.
_EMISSION_BANDWIDTH_RE = re.compile(r"^(\d{0,3})([HKM])(\d{0,2})")


def _emission_bandwidth_khz(emission: Optional[str]) -> Optional[float]:
    """Necessary bandwidth in kHz from an ITU emission designator."""
    if not emission:
        return None
    m = _EMISSION_BANDWIDTH_RE.match(emission.strip().upper())
    if not m or not m.group(1):
        return None
    value = float(f"{m.group(1)}.{m.group(3) or 0}")
    scale = {"H": 0.001, "K": 1.0, "M": 1000.0}[m.group(2)]
    khz = value * scale
    return khz or None


def _encode_dcs(mode: Any) -> tuple[str | int | None, str | None]:
    """DCS code and polarity the radio must transmit to access the far end."""
    if mode.dcs_rx_code is not None:
        return mode.dcs_rx_code, mode.dcs_rx_polarity
    if mode.dcs_tx_code is not None:
        return mode.dcs_tx_code, mode.dcs_tx_polarity
    return None, None


def _record_from_rf_chain(a: Any, chain: Any, station: Any, loc: Any) -> Dict[str, Any]:
    mode = chain.mode
    dcs, dcs_polarity = _encode_dcs(mode)
    return {
        "callsign": station.call_sign if station else None,
        # radio rx = repeater tx (output); radio tx = repeater rx (input)
        "rx_mhz": chain.tx.freq_mhz or chain.rx.freq_mhz,
        "tx_mhz": chain.rx.freq_mhz,
        "ctcss": _encode_tone(mode.ctcss_tx_hz, mode.ctcss_rx_hz),
        "dcs": dcs,
        "dcs_polarity": dcs_polarity,
        "color_code": mode.color_code,
        "timeslots": list(mode.timeslots) if mode.timeslots else None,
        "lat": _round(loc.lat) if loc else None,
        "lon": _round(loc.lon) if loc else None,
        "service": a.service or (station.service if station else None),
        "mode": mode.type,
        "bandwidth_khz": chain.tx.bandwidth_khz
        or _emission_bandwidth_khz(chain.tx.emission),
        "name": _assignment_display_name(a),
    }


# ITU emission-designator (5th symbol = type of modulation) -> SSRF mode.
# Only unambiguous analog-voice designators are mapped; digital/data emissions
# stay None because the designator alone can't distinguish DMR/P25/NXDN/etc.
_EMISSION_MODE_BY_DESIGNATOR = {
    "F3E": "FM",   # angle-modulated telephony (FM voice) -> 16K0F3E, 11K0F3E, ...
    "A3E": "AM",   # double-sideband AM telephony (aircraft band) -> 6K00A3E
    "J3E": "USB",  # single-sideband, suppressed carrier (upper by convention)
}


def _mode_from_emission(emission: Optional[str]) -> Optional[str]:
    """Infer an SSRF mode from an ITU emission designator.

    The designator's 3-char modulation code is its final three characters
    (e.g. ``16K0F3E`` -> ``F3E``). Returns None for digital/data or unknown
    emissions, which downstream consumers treat as untyped.
    """
    if not emission:
        return None
    code = emission.strip().upper()[-3:]
    return _EMISSION_MODE_BY_DESIGNATOR.get(code)


def _record_from_plan_channel(
    a: Any, plan: Any, ch: Any, *, name_override: Optional[str] = None
) -> Dict[str, Any]:
    return {
        "callsign": None,
        "rx_mhz": ch.freq_mhz,
        "tx_mhz": ch.tx_freq_mhz or ch.freq_mhz,
        "ctcss": None,
        "dcs": None,
        "dcs_polarity": None,
        "color_code": None,
        "timeslots": None,
        "lat": None,
        "lon": None,
        "service": a.service or plan.service,
        # Plan channels carry an ITU emission designator instead of a full Mode
        # object; infer analog-voice mode from it so downstream radio zone
        # filters (which match on mode: FM) can pick up simplex/calling
        # channels. Was hardcoded None, which silently dropped every plan
        # channel from mode-filtered zones.
        "mode": _mode_from_emission(ch.emission),
        "bandwidth_khz": ch.bandwidth_khz or _emission_bandwidth_khz(ch.emission),
        # Plan channels carry the canonical national name ("Ch 06"). A local
        # assignment may prefer its own label ("M06 SAFETY") -- see
        # `display_name` handling in build_records(). Falls back to the plan
        # name so existing documents are unaffected.
        "name": name_override or ch.name,
    }


def build_records(ssrf_roots: Optional[List[pathlib.Path]] = None) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    roots = ssrf_roots or [SSRF_ROOT]

    for document in resolve_ssrf_roots(roots):
        root = document.root
        path = document.path
        rel = path.relative_to(root)
        ref = document.reference

        locs = {l.id: l for l in ref.locations}
        stations = {s.id: s for s in ref.stations}
        chains = {c.id: c for c in ref.rf_chains}
        plans = {p.id: p for p in ref.channel_plans}

        for a in ref.assignments:
            if a.rf_chain_id and a.rf_chain_id in chains:
                chain = chains[a.rf_chain_id]
                station = stations.get(chain.station_id)
                loc = (
                    locs.get(station.location_id)
                    if station and station.location_id
                    else None
                )
                records.append(_record_from_rf_chain(a, chain, station, loc))
            elif a.channel_plan_id and a.channel_plan_id in plans:
                plan = plans[a.channel_plan_id]
                plan_channels = plan.channels
                if a.channel_name:
                    plan_channels = [
                        c for c in plan.channels if c.name == a.channel_name
                    ] or plan.channels
                # `display_name` renames a plan channel locally without
                # forking the plan. Only honoured when the assignment selects
                # exactly ONE channel -- otherwise a single override would
                # collapse every channel in the plan to the same name.
                name_override = None
                if getattr(a, "display_name", None) and len(plan_channels) == 1:
                    name_override = a.display_name
                for ch in plan_channels:
                    records.append(
                        _record_from_plan_channel(
                            a, plan, ch, name_override=name_override
                        )
                    )
            # assignments without RF data carry no channel; skip them.

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ssrf-root",
        type=pathlib.Path,
        default=SSRF_ROOT,
        help="Primary SSRF root to scan (default: ./ssrf)",
    )
    parser.add_argument(
        "--extra-ssrf-root",
        type=pathlib.Path,
        action="append",
        default=[],
        help="Additional SSRF root to include, such as a private repo's ssrf/ directory. May be repeated.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=SITE_DIR / "codeplug.json",
        help="Output path for the flat codeplug JSON (default: site/codeplug.json)",
    )
    args = parser.parse_args()

    roots = [args.ssrf_root, *args.extra_ssrf_root]
    for root in roots:
        if not root.exists():
            parser.error(f"SSRF root does not exist: {root}")
        if not root.is_dir():
            parser.error(f"SSRF root is not a directory: {root}")
    records = build_records(roots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(records, indent=None, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    n_mapped = sum(1 for r in records if r.get("lat") is not None)
    print(
        f"✅ Wrote {args.output} — {len(records)} channels, {n_mapped} with coordinates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
