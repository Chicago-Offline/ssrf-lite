#!/usr/bin/env python3
"""
Generate the static data payload for the SSRF-Lite GitHub Pages site.

Walks every SSRF-Lite YAML document, flattens assignments into browsable
channel rows (joined with stations, locations, organizations, and RF chains),
and writes ``site/data.json`` for the frontend in ``site/``.
"""

import argparse
import json
import pathlib
from datetime import date
from typing import Any, Dict, List, Optional

import yaml

from ssrf import load_ssrf_document

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"
SITE_DIR = BASE / "site"

REPO_URL = "https://github.com/Chicago-Offline/ssrf-lite"


def _category(rel: pathlib.Path) -> str:
    parts = rel.parts
    if "plans" in parts:
        return "plan"
    if "custom" in parts:
        return "custom"
    if "systems" in parts:
        return "system"
    return "other"


def _region(rel: pathlib.Path) -> str:
    """Human-readable geographic scope derived from the file path."""
    parts = list(rel.parts[:-1])  # drop filename
    for root in ("plans", "systems"):
        if root in parts:
            parts = parts[parts.index(root) + 1 :]
            break
    # Drop trailing service-category folder (amateur, gmrs, ...) if present
    cleaned = [p.lstrip("_") for p in parts if p not in ("custom",)]
    return " / ".join(cleaned) if cleaned else "Global"


def _mode_summary(mode: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"type": mode.type}
    details: List[str] = []
    if mode.ctcss_tx_hz:
        if mode.ctcss_rx_hz and mode.ctcss_rx_hz != mode.ctcss_tx_hz:
            details.append(f"CTCSS {mode.ctcss_tx_hz:g}/{mode.ctcss_rx_hz:g} Hz")
        else:
            details.append(f"CTCSS {mode.ctcss_tx_hz:g} Hz")
    elif mode.ctcss_rx_hz:
        details.append(f"CTCSS rx {mode.ctcss_rx_hz:g} Hz")
    if mode.dcs_tx_code:
        details.append(f"DCS {mode.dcs_tx_code}")
    if mode.color_code is not None:
        cc = f"CC{mode.color_code}"
        if mode.timeslots:
            cc += " TS" + ",".join(str(t) for t in mode.timeslots)
        details.append(cc)
    if mode.nac is not None:
        details.append(f"NAC ${mode.nac:03X}")
    if mode.nxdn_ran is not None:
        details.append(f"RAN {mode.nxdn_ran}")
    out["detail"] = " · ".join(details)
    return out


def _round(value: Optional[float], digits: int = 6) -> Optional[float]:
    return round(value, digits) if value is not None else None


def _doc_sources(path: pathlib.Path) -> List[Dict[str, str]]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    block = raw.get("ssrf_lite")
    if not isinstance(block, dict):
        return []
    sources = block.get("sources")
    out: List[Dict[str, str]] = []
    if isinstance(sources, list):
        for src in sources:
            if isinstance(src, dict) and src.get("name"):
                out.append(
                    {"name": str(src["name"]), "url": str(src.get("url") or "")}
                )
    return out


def _prettify(stem: str) -> str:
    return stem.replace("_", " ").title()


def _assignment_display_name(a: Any) -> str:
    if a.channel_name:
        return a.channel_name
    name = a.id
    for prefix in ("asgn_", "assign_", "chan_", "ch_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("_", " ")


def build_payload() -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    channels: List[Dict[str, Any]] = []
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
        except Exception as exc:  # keep the site build resilient
            errors.append(f"{rel}: {exc}")
            continue

        orgs = {o.id: o for o in ref.organizations}
        locs = {l.id: l for l in ref.locations}
        stations = {s.id: s for s in ref.stations}
        chains = {c.id: c for c in ref.rf_chains}
        plans = {p.id: p for p in ref.channel_plans}

        file_id = str(rel)
        category = _category(rel)
        if category == "plan" and len(ref.channel_plans) == 1:
            title = ref.channel_plans[0].name
        elif len(ref.organizations) == 1:
            title = ref.organizations[0].name
        else:
            title = _prettify(path.stem)
        file_entry = {
            "id": file_id,
            "title": title,
            "category": category,
            "region": _region(rel),
            "services": sorted(
                {
                    s
                    for s in (
                        [st.service for st in ref.stations]
                        + [a.service for a in ref.assignments]
                        + [pl.service for pl in ref.channel_plans]
                        + [au.service for au in ref.authorizations]
                    )
                    if s
                }
            ),
            "counts": {
                "assignments": len(ref.assignments),
                "stations": len(ref.stations),
                "locations": len(ref.locations),
            },
            "sources": _doc_sources(path),
            "url": f"{REPO_URL}/blob/main/ssrf/{rel}",
        }
        files.append(file_entry)

        for a in ref.assignments:
            row: Dict[str, Any] = {
                "file": file_id,
                "name": _assignment_display_name(a),
                "usage": a.usage,
                "service": a.service,
                "notes": a.notes or "",
            }

            if a.rf_chain_id and a.rf_chain_id in chains:
                chain = chains[a.rf_chain_id]
                station = stations.get(chain.station_id)
                loc = locs.get(station.location_id) if station and station.location_id else None
                org = orgs.get(station.organization_id) if station and station.organization_id else None
                mode = _mode_summary(chain.mode)
                row.update(
                    {
                        # tx = repeater transmit = user receive frequency
                        "freq_mhz": chain.tx.freq_mhz or chain.rx.freq_mhz,
                        "input_mhz": (
                            chain.rx.freq_mhz
                            if chain.tx.freq_mhz and chain.rx.freq_mhz != chain.tx.freq_mhz
                            else None
                        ),
                        "mode": mode["type"],
                        "mode_detail": mode["detail"],
                        "call_sign": station.call_sign if station else None,
                        "org": org.name if org else None,
                        "loc_name": loc.name if loc else None,
                        "lat": _round(loc.lat) if loc else None,
                        "lon": _round(loc.lon) if loc else None,
                    }
                )
                if not row["service"] and station and station.service:
                    row["service"] = station.service
                channels.append(row)
            elif a.channel_plan_id and a.channel_plan_id in plans:
                plan = plans[a.channel_plan_id]
                plan_channels = plan.channels
                if a.channel_name:
                    plan_channels = [
                        c for c in plan.channels if c.name == a.channel_name
                    ] or plan.channels
                for ch in plan_channels:
                    ch_row = dict(row)
                    ch_row.update(
                        {
                            "name": ch.name,
                            "freq_mhz": ch.freq_mhz,
                            "input_mhz": None,
                            "mode": None,
                            "mode_detail": "",
                            "notes": ch.notes or row["notes"],
                        }
                    )
                    if not ch_row["service"]:
                        ch_row["service"] = plan.service
                    channels.append(ch_row)
            else:
                channels.append(row)

    payload = {
        "generated": date.today().isoformat(),
        "repo": REPO_URL,
        "files": files,
        "channels": channels,
    }
    if errors:
        payload["errors"] = errors
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=SITE_DIR / "data.json",
        help="Output path for the site data JSON (default: site/data.json)",
    )
    args = parser.parse_args()

    payload = build_payload()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=None, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    n_mapped = len({(c["lat"], c["lon"]) for c in payload["channels"] if c.get("lat")})
    print(
        f"✅ Wrote {args.output} — {len(payload['files'])} files, "
        f"{len(payload['channels'])} channels, {n_mapped} mapped sites"
    )
    for err in payload.get("errors", []):
        print(f"⚠️  {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
