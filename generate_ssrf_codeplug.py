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
        "color_code": int | null,   # DMR color code
        "timeslots": [int] | null,  # DMR timeslots
        "lat": float | null,        # site latitude
        "lon": float | null,        # site longitude
        "service": str | null,      # SSRF service taxonomy id
        "mode": str | null,         # modulation/mode (FM, DMR, ...)
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
from typing import Any, Dict, List, Optional

from ssrf import load_ssrf_document

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


def _record_from_rf_chain(a: Any, chain: Any, station: Any, loc: Any) -> Dict[str, Any]:
    mode = chain.mode
    return {
        "callsign": station.call_sign if station else None,
        # radio rx = repeater tx (output); radio tx = repeater rx (input)
        "rx_mhz": chain.tx.freq_mhz or chain.rx.freq_mhz,
        "tx_mhz": chain.rx.freq_mhz,
        "ctcss": _encode_tone(mode.ctcss_tx_hz, mode.ctcss_rx_hz),
        "dcs": _encode_tone(mode.dcs_tx_code, mode.dcs_rx_code),
        "color_code": mode.color_code,
        "timeslots": list(mode.timeslots) if mode.timeslots else None,
        "lat": _round(loc.lat) if loc else None,
        "lon": _round(loc.lon) if loc else None,
        "service": a.service or (station.service if station else None),
        "mode": mode.type,
        "name": _assignment_display_name(a),
    }


def _record_from_plan_channel(a: Any, plan: Any, ch: Any) -> Dict[str, Any]:
    return {
        "callsign": None,
        "rx_mhz": ch.freq_mhz,
        "tx_mhz": ch.freq_mhz,
        "ctcss": None,
        "dcs": None,
        "color_code": None,
        "timeslots": None,
        "lat": None,
        "lon": None,
        "service": a.service or plan.service,
        "mode": None,
        "name": ch.name,
    }


def build_records() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    errors: List[str] = []

    yml_files = sorted(
        p
        for p in SSRF_ROOT.rglob("*.yml")
        if not p.name.startswith("_") and "_schema" not in p.parts
    )

    for path in yml_files:
        rel = path.relative_to(SSRF_ROOT)
        try:
            ref = load_ssrf_document(path)
        except Exception as exc:  # keep the build resilient
            errors.append(f"{rel}: {exc}")
            continue

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
                for ch in plan_channels:
                    records.append(_record_from_plan_channel(a, plan, ch))
            # assignments without RF data carry no channel; skip them.

    if errors:
        for err in errors:
            print(f"⚠️  {err}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=SITE_DIR / "codeplug.json",
        help="Output path for the flat codeplug JSON (default: site/codeplug.json)",
    )
    args = parser.parse_args()

    records = build_records()
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
