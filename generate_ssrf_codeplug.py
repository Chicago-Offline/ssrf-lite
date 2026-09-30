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
        "name": str,                # human-readable channel name
        "short_name": str           # <=6 char label for narrow displays
    }

Frequencies in the SSRF-Lite library belong to the *station* being described:
an rf_chain's ``tx`` is what that station radiates (a repeater's output) and
its ``rx`` is what that station listens for (a repeater's input). The records
emitted here are the mirror image, because a codeplug describes the operator's
radio: ``rx_mhz`` is what the radio listens to (the station's tx) and
``tx_mhz`` is what the radio transmits (the station's rx). For simplex
channels the two are equal.

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
from ssrf.emissions import bandwidth_khz as _emission_bandwidth_khz
from ssrf.emissions import mode_from_emission as _mode_from_emission
from ssrf.models.pydantic_models import SHORT_NAME_MAX_LEN

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"
SITE_DIR = BASE / "site"


def _round(value: Optional[float], digits: int = 6) -> Optional[float]:
    return round(value, digits) if value is not None else None


def _assignment_display_name(a: Any) -> str:
    if a.channel_name:
        return a.channel_name
    name = a.id
    for prefix in ("asg_", "asgn_", "assign_", "chan_", "ch_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("_", " ")


_WORD_RE = re.compile(r"[A-Za-z]+|\d+")


def _abbreviate(name: Optional[str], limit: int = SHORT_NAME_MAX_LEN) -> str:
    """Squeeze a channel name into ``limit`` characters, deterministically.

    A last resort for records that never authored a ``short_name``. What
    distinguishes sibling channels sits in a different place in every naming
    convention this library carries -- the tail ("Sparta BOE" / "Sparta DPW"),
    the head ("KORD ASOS" / "KDPA ASOS"), or the middle ("CB 30 USB" / "CB 31
    USB") -- so no fixed truncation can work. Instead every word keeps at
    least one character and the longest words give up the most, which
    preserves a little of each part rather than all of one and none of another.

    Numbers surrender their high-order digits and words their trailing
    letters, because that is the end each one repeats across siblings:
    ``160230`` and ``160320`` differ late, ``UNICOM`` and ``UNICOM`` not at all.
    """
    tokens = [t.upper() for t in _WORD_RE.findall(name or "")]
    if not tokens:
        return ""

    compact = "".join(tokens)
    if len(compact) <= limit:
        return compact

    # An acronym only reads as one when there are enough words to make it:
    # "Tampa Amateur Radio Club" -> TARC, but "SuxCo EMS Link" -> SEL is noise.
    alpha = [t for t in tokens if not t.isdigit()]
    if len(alpha) >= 3:
        initials = "".join(t if t.isdigit() else t[0] for t in tokens)
        if 4 <= len(initials) <= limit:
            return initials

    parts = list(tokens)
    total = len(compact)
    while total > limit:
        longest = max(range(len(parts)), key=lambda i: (len(parts[i]), -i))
        if len(parts[longest]) <= 1:
            break
        token = parts[longest]
        parts[longest] = token[1:] if token.isdigit() else token[:-1]
        total -= 1
    return "".join(parts)[:limit]


def _short_name(
    authored: Optional[str], display_name: str, callsign: Optional[str] = None
) -> str:
    """Authored short name, else the callsign if it fits, else an abbreviation.

    The callsign is only worth borrowing when the name says nothing more than
    the callsign already does. One licensee routinely holds a dozen channels
    ("KORD APP", "KORD ASOS"), and collapsing them all to the callsign loses
    the only thing that tells them apart.

    Collision handling is deliberately absent: uniqueness is a property of a
    particular codeplug's zone, which this library cannot see. Consumers
    disambiguate once they know which subset of channels they are loading.
    """
    if authored:
        return authored
    if callsign:
        call = "".join(_WORD_RE.findall(callsign.upper()))
        name = "".join(_WORD_RE.findall((display_name or "").upper()))
        if call and len(call) <= SHORT_NAME_MAX_LEN and name in ("", call):
            return call
    return _abbreviate(display_name)


def _encode_tone(tx_tone: Optional[float], rx_tone: Optional[float]) -> Optional[float]:
    """Tone the radio must transmit to access the far end (repeater input)."""
    return rx_tone if rx_tone is not None else tx_tone


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
    callsign = station.call_sign if station else None
    display_name = _assignment_display_name(a)
    return {
        "callsign": callsign,
        # Mirrored: the radio hears what the station sends, and vice versa.
        "rx_mhz": chain.tx.freq_mhz or chain.rx.freq_mhz,
        "tx_mhz": chain.rx.freq_mhz or chain.tx.freq_mhz,
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
        "name": display_name,
        "short_name": _short_name(a.short_name, display_name, callsign),
    }


def _record_from_plan_channel(
    a: Any,
    plan: Any,
    ch: Any,
    *,
    name_override: Optional[str] = None,
    short_name_override: Optional[str] = None,
    emission: Any = None,
) -> Dict[str, Any]:
    name = name_override or ch.name
    designator = emission.emission if emission else ch.emission
    return {
        "callsign": None,
        # Mirrored: the radio hears what the channel's station sends.
        "rx_mhz": ch.freq_mhz,
        "tx_mhz": ch.rx_freq_mhz or ch.freq_mhz,
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
        "mode": (emission.mode if emission and emission.mode else None)
        or _mode_from_emission(designator),
        "bandwidth_khz": (emission.bandwidth_khz if emission else ch.bandwidth_khz)
        or _emission_bandwidth_khz(designator),
        # Plan channels carry the canonical national name ("Ch 06"). A local
        # assignment may prefer its own label ("M06 SAFETY") -- see
        # `display_name` handling in build_records(). Falls back to the plan
        # name so existing documents are unaffected.
        "name": name,
        "short_name": _short_name(short_name_override or ch.short_name, name),
    }


def _records_from_plan_channel(
    a: Any,
    plan: Any,
    ch: Any,
    *,
    name_override: Optional[str] = None,
    short_name_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """One record per permitted emission.

    A channel that allows several incompatible modulations on one frequency --
    US CB runs AM, SSB, and FM on all 40 -- is several channels as far as a
    radio is concerned, so each gets its own record with the mode appended to
    the name.
    """

    permitted = ch.permitted_emissions()
    if len(permitted) <= 1:
        return [
            _record_from_plan_channel(
                a,
                plan,
                ch,
                name_override=name_override,
                short_name_override=short_name_override,
                emission=permitted[0] if permitted else None,
            )
        ]

    records: List[Dict[str, Any]] = []
    for spec in permitted:
        record = _record_from_plan_channel(
            a,
            plan,
            ch,
            name_override=name_override,
            short_name_override=short_name_override,
            emission=spec,
        )
        suffix = spec.mode or _mode_from_emission(spec.emission)
        if suffix:
            record["name"] = f"{record['name']} {suffix}"
            record["short_name"] = _short_name(None, record["name"])
        records.append(record)
    return records


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
                short_name_override = None
                if len(plan_channels) == 1:
                    name_override = getattr(a, "display_name", None)
                    short_name_override = getattr(a, "short_name", None)
                for ch in plan_channels:
                    records.extend(
                        _records_from_plan_channel(
                            a,
                            plan,
                            ch,
                            name_override=name_override,
                            short_name_override=short_name_override,
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
