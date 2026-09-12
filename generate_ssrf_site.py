#!/usr/bin/env python3
"""
Generate the static data payload for the SSRF-Lite GitHub Pages site.

Walks every SSRF-Lite YAML document, flattens assignments into browsable
channel rows (joined with stations, locations, organizations, and RF chains),
and writes ``site/data.json`` for the frontend in ``site/``.
"""

import argparse
import html
import json
import pathlib
import subprocess
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ssrf import resolve_ssrf_roots

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"
SITE_DIR = BASE / "site"
DETAIL_DIR_NAME = "files"

REPO_URL = "https://github.com/Chicago-Offline/ssrf-lite"
RAW_REPO_URL = "https://raw.githubusercontent.com/Chicago-Offline/ssrf-lite/main"
SITE_URL = "https://chicago-offline.github.io/ssrf-lite/"


def _category(rel: pathlib.Path) -> str:
    parts = rel.parts
    if "plans" in parts:
        return "plan"
    if "custom" in parts:
        return "custom"
    if "systems" in parts:
        return "system"
    return "other"


def _region(rel: pathlib.Path) -> Tuple[str, str, Optional[str]]:
    """Geographic scope derived from the file path.

    Returns ``(region, region_group, topic)``: the full place path
    (``US / IL / Cook / Chicago``), the coarse grouping used by the library
    view (country, plus state for systems), and the trailing service folder
    (``amateur``, ``gmrs``, ...) if the path has one.
    """
    parts = list(rel.parts[:-1])  # drop filename
    is_plan = "plans" in parts
    for root in ("plans", "systems"):
        if root in parts:
            parts = parts[parts.index(root) + 1 :]
            break
    parts = [p for p in parts if p != "custom"]
    topic: Optional[str] = None
    # Place folders are capitalized (Cook, _Regional); service folders are lowercase.
    if len(parts) > 1 and parts[-1] == parts[-1].lower():
        topic = parts.pop()
    geo = [p.lstrip("_") for p in parts]
    region = " / ".join(geo) if geo else "Global"
    group = " / ".join(geo[:1] if is_plan else geo[:2]) if geo else "Global"
    return region, group, topic


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
    if mode.dcs_tx_code is not None:
        dcs = f"DCS {mode.dcs_tx_code} {mode.dcs_tx_polarity}"
        if mode.dcs_rx_code is not None and (
            mode.dcs_rx_code != mode.dcs_tx_code
            or mode.dcs_rx_polarity != mode.dcs_tx_polarity
        ):
            dcs += f"/{mode.dcs_rx_code} {mode.dcs_rx_polarity}"
        details.append(dcs)
    elif mode.dcs_rx_code is not None:
        details.append(f"DCS rx {mode.dcs_rx_code} {mode.dcs_rx_polarity}")
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
                entry = {"name": str(src["name"]), "url": str(src.get("url") or "")}
                if src.get("accessed"):
                    entry["accessed"] = str(src["accessed"])
                out.append(entry)
    return out


def _prettify(stem: str) -> str:
    return stem.replace("_", " ").title()


def _git_lastmod(path: pathlib.Path) -> Optional[str]:
    """Last git commit date (YYYY-MM-DD) for path, or None if untracked/no repo."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _assignment_display_name(a: Any) -> Tuple[str, bool]:
    """Return ``(label, derived)``; derived labels come from the record ID."""
    if a.channel_name:
        return a.channel_name, False
    name = a.id
    for prefix in ("asg_", "asgn_", "assign_", "chan_", "ch_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("_", " ").upper(), True


def build_payload(ssrf_roots: Optional[List[pathlib.Path]] = None) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    channels: List[Dict[str, Any]] = []
    # Per-file record detail for the static detail pages; not written to data.json.
    details: Dict[str, Dict[str, Any]] = {}

    roots = ssrf_roots or [SSRF_ROOT]

    for document in resolve_ssrf_roots(roots):
        root = document.root
        path = document.path
        rel = path.relative_to(root)
        is_overlay = document.is_overlay
        ref = document.reference

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
        region, region_group, topic = _region(rel)
        file_entry = {
            "id": file_id,
            "title": title,
            "category": category,
            "region": region,
            "region_group": region_group,
            "topic": topic,
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
        }
        if is_overlay:
            # Private overlay file: it is not published in the public repo, so
            # emit no public GitHub links (they would 404). Flag it as local
            # so the site UI can label/handle it accordingly.
            file_entry["local"] = True
        else:
            file_entry["url"] = f"{REPO_URL}/blob/main/ssrf/{rel}"
            file_entry["doc_url"] = f"{DETAIL_DIR_NAME}/{path.stem}.html"
            file_entry["download_url"] = f"{RAW_REPO_URL}/ssrf/{rel}"
            file_entry["lastmod"] = _git_lastmod(path)
        files.append(file_entry)

        details[file_id] = {
            "organizations": [
                {
                    "id": o.id,
                    "name": o.name,
                    "call_signs": sorted(
                        {s.call_sign for s in ref.stations if s.organization_id == o.id and s.call_sign}
                    ),
                }
                for o in ref.organizations
            ],
            "locations": [
                {"id": l.id, "name": l.name, "lat": _round(l.lat), "lon": _round(l.lon)}
                for l in ref.locations
            ],
            "authorizations": [
                {
                    "service": au.service,
                    "authority": au.authority,
                    "class": au.class_field,
                    "identifier": au.identifier,
                    "notes": au.notes or "",
                }
                for au in ref.authorizations
            ],
            "contacts": [
                {"name": c.name, "kind": c.kind, "number": c.number, "notes": c.notes or ""}
                for c in ref.contacts
            ],
        }

        for a in ref.assignments:
            name, name_derived = _assignment_display_name(a)
            row: Dict[str, Any] = {
                "file": file_id,
                "name": name,
                "name_derived": name_derived,
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
                            "name_derived": False,
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
        "details": details,
    }
    return payload


# --------------------------------------------------------------------------
# Static detail pages (site/files/<stem>.html)
# --------------------------------------------------------------------------

SERVICE_LABELS = {
    "amateur": "Amateur",
    "gmrs": "GMRS",
    "frs": "FRS",
    "murs": "MURS",
    "pmr446": "PMR446",
    "noaa_weather_radio": "NOAA Weather",
    "marine": "Marine VHF",
    "aviation": "Aviation",
    "railroad_aar": "Railroad (AAR)",
    "public_safety_part90": "Public safety",
    "business_itinerant_part90": "Business / itinerant",
}
CATEGORY_LABELS = {
    "system": "Systems",
    "plan": "Channel plans",
    "custom": "Custom systems",
    "other": "Other",
}

LEAFLET_CSS = (
    '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" '
    'integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />'
)
LEAFLET_JS = (
    '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" '
    'integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>'
)


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _service_label(service: Optional[str]) -> str:
    if not service:
        return ""
    return SERVICE_LABELS.get(service, service.replace("_", " ").title())


def _fmt_freq(value: Optional[float]) -> str:
    return f"{value:.4f}" if value is not None else ""


def _render_channels_table(channels: List[Dict[str, Any]]) -> str:
    if not channels:
        return '<div class="empty">This file defines no channel assignments.</div>'
    rows = []
    for c in sorted(channels, key=lambda c: (c.get("freq_mhz") is None, c.get("freq_mhz") or 0, c.get("name") or "")):
        service = c.get("service")
        service_html = (
            f'<span class="badge">{_e(_service_label(service))}</span>' if service else ""
        )
        name_cls = "name derived" if c.get("name_derived") else "name"
        name_title = (
            ' title="No channel name in the data; label derived from the record ID"'
            if c.get("name_derived")
            else ""
        )
        rows.append(
            "<tr>"
            f'<td class="num">{_fmt_freq(c.get("freq_mhz"))}</td>'
            f'<td class="num">{_fmt_freq(c.get("input_mhz"))}</td>'
            f"<td>{_e(c.get('mode') or '')}</td>"
            f'<td class="muted">{_e(c.get("mode_detail") or "")}</td>'
            f'<td class="{name_cls}"{name_title}>{_e(c.get("name"))}</td>'
            f"<td>{_e(c.get('usage') or '')}</td>"
            f'<td class="mono">{_e(c.get("call_sign") or "")}</td>'
            f'<td class="muted">{_e(c.get("loc_name") or "")}</td>'
            f"<td>{service_html}</td>"
            f'<td class="notes">{_e(c.get("notes") or "")}</td>'
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="data"><thead><tr>'
        "<th class=\"num\">Freq (MHz)</th><th class=\"num\">Input (MHz)</th>"
        "<th>Mode</th><th>Tone / CC</th><th>Name</th><th>Usage</th><th>Callsign</th>"
        "<th>Location</th><th>Service</th><th class=\"notes\">Notes</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def _render_sites(locations: List[Dict[str, Any]]) -> str:
    if not locations:
        return ""
    cards = []
    for loc in locations:
        if loc.get("lat") is not None and loc.get("lon") is not None:
            coords = (
                f'<a href="https://www.openstreetmap.org/?mlat={loc["lat"]}&amp;mlon={loc["lon"]}#map=13/{loc["lat"]}/{loc["lon"]}" '
                f'target="_blank" rel="noopener" class="mono">{loc["lat"]:.4f}, {loc["lon"]:.4f}</a>'
            )
        else:
            coords = '<span class="muted">No coordinates</span>'
        cards.append(
            f'<article><h3>{_e(loc["name"])}</h3><p>{coords}</p>'
            f'<p class="mono muted">{_e(loc["id"])}</p></article>'
        )
    mapped = [l for l in locations if l.get("lat") is not None and l.get("lon") is not None]
    map_html = '<div id="map"></div>' if mapped else ""
    return (
        '<section id="sites"><div class="wrap">'
        f"<h2>Sites</h2><p class=\"sub\">{len(locations)} location{'s' if len(locations) != 1 else ''}"
        f"{f', {len(mapped)} with coordinates' if mapped and len(mapped) != len(locations) else ''}.</p>"
        f'{map_html}<div class="kv" style="margin-top:1rem">{"".join(cards)}</div>'
        "</div></section>"
    )


def _render_orgs(orgs: List[Dict[str, Any]]) -> str:
    if not orgs:
        return ""
    cards = []
    for o in orgs:
        calls = ", ".join(o.get("call_signs") or [])
        calls_html = f'Callsigns: <span class="mono">{_e(calls)}</span>' if calls else ""
        cards.append(
            f'<article><h3>{_e(o["name"])}</h3>'
            f"<p>{calls_html}</p>"
            f'<p class="mono muted">{_e(o["id"])}</p></article>'
        )
    return (
        '<section id="organizations"><div class="wrap"><h2>Organizations</h2>'
        f'<div class="kv">{"".join(cards)}</div></div></section>'
    )


def _render_authorizations(auths: List[Dict[str, Any]]) -> str:
    if not auths:
        return ""
    cards = []
    for a in auths:
        bits = [f"<strong>{_e(a['authority'])}</strong>"]
        if a.get("class"):
            bits.append(f"Class: {_e(a['class'])}")
        if a.get("identifier"):
            bits.append(f'<span class="mono">{_e(a["identifier"])}</span>')
        notes = f"<p>{_e(a['notes'])}</p>" if a.get("notes") else ""
        cards.append(
            f'<article><h3>{_e(_service_label(a["service"]))}</h3>'
            f'<p>{" · ".join(bits)}</p>{notes}</article>'
        )
    return (
        '<section id="authorizations"><div class="wrap"><h2>Authorization</h2>'
        '<p class="sub">What it takes to transmit on these channels.</p>'
        f'<div class="kv">{"".join(cards)}</div></div></section>'
    )


def _render_contacts(contacts: List[Dict[str, Any]]) -> str:
    if not contacts:
        return ""
    rows = "".join(
        "<tr>"
        f'<td class="name">{_e(c["name"])}</td>'
        f"<td>{_e(c['kind'])}</td>"
        f'<td class="num">{_e(c["number"]) if c.get("number") is not None else ""}</td>'
        f'<td class="notes">{_e(c.get("notes") or "")}</td>'
        "</tr>"
        for c in contacts
    )
    return (
        '<section id="contacts"><div class="wrap"><h2>Talkgroups &amp; contacts</h2>'
        '<div class="table-wrap"><table class="data"><thead><tr>'
        '<th>Name</th><th>Kind</th><th class="num">ID</th><th class="notes">Notes</th>'
        f"</tr></thead><tbody>{rows}</tbody></table></div></div></section>"
    )


def render_detail_page(
    file_entry: Dict[str, Any],
    channels: List[Dict[str, Any]],
    detail: Dict[str, Any],
    generated: str,
) -> str:
    title = file_entry["title"]
    category = CATEGORY_LABELS.get(file_entry["category"], file_entry["category"].title())
    services = [_service_label(s) for s in file_entry.get("services", [])]
    region = file_entry.get("region") or "Global"
    topic = _service_label(file_entry.get("topic"))
    n_ch = len(channels)
    n_sites = len(detail.get("locations", []))
    stem = pathlib.Path(file_entry["id"]).stem

    desc_bits = [f"{n_ch} channel{'s' if n_ch != 1 else ''}"]
    if n_sites:
        desc_bits.append(f"{n_sites} site{'s' if n_sites != 1 else ''}")
    if services:
        desc_bits.append(", ".join(services))
    description = f"{title}: {' · '.join(desc_bits)}. SSRF-Lite reference data for {region}."
    page_url = f"{SITE_URL}{file_entry['doc_url']}"

    badges = "".join(f'<span class="badge">{_e(s)}</span>' for s in services)
    if file_entry.get("category") == "plan":
        badges += '<span class="badge dim">Channel plan</span>'

    meta_bits = [category, region]
    if topic:
        meta_bits.append(topic)
    if file_entry.get("lastmod"):
        meta_bits.append(f"Updated {file_entry['lastmod']}")

    sources = file_entry.get("sources") or []
    sources_html = ""
    if sources:
        items = []
        for s in sources:
            label = (
                f'<a href="{_e(s["url"])}" target="_blank" rel="noopener">{_e(s["name"])}</a>'
                if s.get("url")
                else _e(s["name"])
            )
            if s.get("accessed"):
                label += f' <span class="muted">· accessed {_e(s["accessed"])}</span>'
            items.append(f"<li>{label}</li>")
        sources_html = (
            '<section id="sources"><div class="wrap"><h2>Sources</h2>'
            '<p class="sub">Where this data came from. Verify on the air before relying on it.</p>'
            f'<ul class="sources">{"".join(items)}</ul></div></section>'
        )

    mapped = [
        l for l in detail.get("locations", []) if l.get("lat") is not None and l.get("lon") is not None
    ]
    map_script = ""
    if mapped:
        sites_json = json.dumps(
            [{"name": l["name"], "lat": l["lat"], "lon": l["lon"]} for l in mapped]
        ).replace("</", "<\\/")
        map_script = f"""{LEAFLET_JS}
  <script>
    (function () {{
      var sites = {sites_json};
      var map = L.map("map", {{ scrollWheelZoom: false }});
      L.tileLayer("https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 19
      }}).addTo(map);
      var bounds = [];
      sites.forEach(function (s) {{
        bounds.push([s.lat, s.lon]);
        L.circleMarker([s.lat, s.lon], {{ radius: 7, color: "#4fb3ff", weight: 2, fillColor: "#4fb3ff", fillOpacity: 0.35 }})
          .bindPopup('<div class="popup-title">' + s.name.replace(/[<>&]/g, "") + "</div>").addTo(map);
      }});
      map.fitBounds(L.latLngBounds(bounds).pad(0.2), {{ maxZoom: 12 }});
    }})();
  </script>"""

    browse_url = f"../#browse?file={_e(file_entry['id'].replace('/', '%2F'))}"
    actions = [f'<a class="button primary" href="{browse_url}">Browse in the channel table</a>']
    if file_entry.get("url"):
        actions.append(
            f'<a class="button" href="{_e(file_entry["url"])}" target="_blank" rel="noopener">View YAML on GitHub</a>'
        )
    if file_entry.get("download_url"):
        actions.append(
            f'<a class="button" href="{_e(file_entry["download_url"])}" download="{_e(stem)}.yml">Download YAML</a>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{_e(description)}" />
  <link rel="canonical" href="{_e(page_url)}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{_e(title)} — SSRF-Lite" />
  <meta property="og:description" content="{_e(description)}" />
  <meta property="og:url" content="{_e(page_url)}" />
  <meta property="og:image" content="{SITE_URL}logo.svg" />
  <meta name="twitter:card" content="summary" />
  <title>{_e(title)} — SSRF-Lite</title>
  <link rel="icon" type="image/svg+xml" href="../favicon.svg" />
  {LEAFLET_CSS if mapped else ""}
  <link rel="stylesheet" href="../style.css" />
</head>
<body class="detail">
  <header class="site">
    <div class="wrap">
      <a class="brand" href="../"><img src="../logo.svg" alt="" /> SSRF-Lite</a>
      <nav>
        <a href="../#browse">Browse</a>
        <a href="../#library">Library</a>
        <a href="../#about">About</a>
        <a href="../#ecosystem">Ecosystem</a>
        <a href="../#start">Use the data</a>
      </nav>
      <a class="repo-link" href="{REPO_URL}" target="_blank" rel="noopener">GitHub ↗</a>
    </div>
  </header>

  <main>
    <div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../#library">Library</a><span>›</span>
        <span>{_e(category)}</span><span>›</span>
        <span>{_e(region)}</span>
      </nav>
      <div class="detail-hero">
        <p class="eyebrow">SSRF-Lite reference data</p>
        <h1>{_e(title)}</h1>
        <p class="meta">{" · ".join(_e(b) for b in meta_bits)} · <span class="mono">{_e(file_entry["id"])}</span></p>
        <div class="badges">{badges}</div>
        <div class="actions">{"".join(actions)}</div>
      </div>
    </div>

    <section id="channels">
      <div class="wrap wide">
        <h2>Channels</h2>
        <p class="sub">{n_ch} assignment{'s' if n_ch != 1 else ''}, sorted by frequency. Frequency is what your radio receives; input is what it transmits on for repeaters.</p>
        {_render_channels_table(channels)}
      </div>
    </section>
    {_render_sites(detail.get("locations", []))}
    {_render_orgs(detail.get("organizations", []))}
    {_render_authorizations(detail.get("authorizations", []))}
    {_render_contacts(detail.get("contacts", []))}
    {sources_html}
  </main>

  <footer class="site">
    <div class="wrap">
      <span>© 2026 Eric Muehlstein · Apache-2.0 · a <a href="https://chicagooffline.com">Chicago Offline</a> project</span>
      <span>Data generated {_e(generated)} · <a href="{REPO_URL}">Source</a> · <a href="{REPO_URL}/blob/main/ssrf/_schema/SSRF-Lite-Spec.md">Spec</a> · <a href="{REPO_URL}/issues">Issues</a></span>
    </div>
  </footer>
  {map_script}
</body>
</html>
"""


def write_detail_pages(output_dir: pathlib.Path, payload: Dict[str, Any]) -> int:
    """Write one static HTML page per public file. Returns the number written."""
    detail_dir = output_dir / DETAIL_DIR_NAME
    detail_dir.mkdir(parents=True, exist_ok=True)
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for c in payload["channels"]:
        by_file.setdefault(c["file"], []).append(c)
    written = 0
    for f in payload["files"]:
        if not f.get("doc_url"):
            continue  # private overlays get no public page
        page = render_detail_page(
            f, by_file.get(f["id"], []), payload["details"].get(f["id"], {}), payload["generated"]
        )
        (output_dir / f["doc_url"]).write_text(page, encoding="utf-8")
        written += 1
    return written


def write_sitemap(
    output_dir: pathlib.Path, generated: str, files: List[Dict[str, Any]]
) -> None:
    # Per-file git commit dates keep lastmod stable across rebuilds; the
    # homepage reflects the newest content change.
    lastmods = [f["lastmod"] for f in files if f.get("lastmod")]
    home_lastmod = max(lastmods) if lastmods else generated
    detail_urls = "\n".join(
        f"""  <url>
    <loc>{SITE_URL}{file['doc_url']}</loc>
    <lastmod>{file.get('lastmod') or generated}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>"""
        # Private overlay files have no public doc page; skip them.
        for file in files
        if file.get("doc_url")
    )
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE_URL}</loc>
    <lastmod>{home_lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
{detail_urls}
</urlset>
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def write_robots(output_dir: pathlib.Path) -> None:
    robots = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}sitemap.xml
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "robots.txt").write_text(robots, encoding="utf-8")


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
        default=SITE_DIR / "data.json",
        help="Output path for the site data JSON (default: site/data.json)",
    )
    args = parser.parse_args()

    roots = [args.ssrf_root, *args.extra_ssrf_root]
    for root in roots:
        if not root.exists():
            parser.error(f"SSRF root does not exist: {root}")
        if not root.is_dir():
            parser.error(f"SSRF root is not a directory: {root}")

    payload = build_payload(roots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    public_payload = {k: v for k, v in payload.items() if k != "details"}
    args.output.write_text(
        json.dumps(public_payload, indent=None, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    n_pages = write_detail_pages(args.output.parent, payload)
    write_sitemap(args.output.parent, payload["generated"], payload["files"])
    write_robots(args.output.parent)

    n_mapped = len({(c["lat"], c["lon"]) for c in payload["channels"] if c.get("lat")})
    print(
        f"✅ Wrote {args.output} — {len(payload['files'])} files, "
        f"{len(payload['channels'])} channels, {n_mapped} mapped sites, "
        f"{n_pages} detail pages"
    )
    for err in payload.get("errors", []):
        print(f"⚠️  {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
