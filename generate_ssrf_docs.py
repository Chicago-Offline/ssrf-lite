#!/usr/bin/env python3
"""
Generate markdown documentation for SSRF-Lite files describing RF systems and channel plans.

This script analyzes all SSRF-Lite YAML files and generates comprehensive documentation showing:
- SSRF file overview and structure
- Channel plans (portable frequency sets)
- Systems (location-based RF infrastructure)
- Organizations and locations
- Service coverage by region
- Frequency allocations and usage patterns
"""

import argparse
import pathlib
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, Counter
import yaml

# Import from the existing generator
from ssrf import load_ssrf_document, SSRFReference

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"
DEFAULT_DOCS_DIR = BASE / "docs" / "ssrf"


def categorize_ssrf_files(ssrf_root: pathlib.Path) -> Dict[str, List[pathlib.Path]]:
    """Categorize SSRF files by type and location."""

    categories = {"plans": [], "systems": [], "custom": [], "other": []}

    for yml_file in ssrf_root.rglob("*.yml"):
        relative_path = yml_file.relative_to(ssrf_root)
        parts = relative_path.parts

        if "plans" in parts:
            categories["plans"].append(yml_file)
        elif "systems" in parts:
            if "custom" in parts:
                categories["custom"].append(yml_file)
            else:
                categories["systems"].append(yml_file)
        elif yml_file.name.startswith("_"):
            continue  # Skip _defaults.yml and _schema files
        else:
            categories["other"].append(yml_file)

    return categories


def analyze_ssrf_file(file_path: pathlib.Path) -> Dict[str, Any]:
    """Analyze a single SSRF file and extract metadata."""

    try:
        reference = load_ssrf_document(file_path)
        relative_path = file_path.relative_to(SSRF_ROOT)

        # Basic file info
        file_info = {
            "path": file_path,
            "relative_path": str(relative_path),
            "name": file_path.stem,
            "category": determine_category(relative_path),
            "geographic_scope": extract_geographic_info(relative_path),
            "services": set(),
            "modes": Counter(),
            "usage_types": Counter(),
            "frequency_bands": Counter(),
            "organizations": len(reference.organizations),
            "locations": len(reference.locations),
            "stations": len(reference.stations),
            "rf_chains": len(reference.rf_chains),
            "channel_plans": len(reference.channel_plans),
            "assignments": len(reference.assignments),
            "contacts": len(reference.contacts),
            "authorizations": len(reference.authorizations),
            "reference": reference,
        }

        # Analyze services and modes
        for station in reference.stations:
            if station.service:
                file_info["services"].add(station.service)

        for auth in reference.authorizations:
            if auth.service:
                file_info["services"].add(auth.service)

        for assignment in reference.assignments:
            if assignment.service:
                file_info["services"].add(assignment.service)

            # Analyze RF chains for modes and frequencies
            if assignment.rf_chain_id:
                rf_chain = next(
                    (
                        rc
                        for rc in reference.rf_chains
                        if rc.id == assignment.rf_chain_id
                    ),
                    None,
                )
                if rf_chain and rf_chain.mode:
                    mode = rf_chain.mode.type
                    file_info["modes"][mode] += 1

                    # Categorize frequency
                    rx_freq = rf_chain.rx.freq_mhz if rf_chain.rx else None
                    if rx_freq:
                        if rx_freq < 30:
                            file_info["frequency_bands"]["HF (<30 MHz)"] += 1
                        elif 136 <= rx_freq <= 174:
                            file_info["frequency_bands"]["VHF (136-174 MHz)"] += 1
                        elif 400 <= rx_freq <= 480:
                            file_info["frequency_bands"]["UHF (400-480 MHz)"] += 1
                        elif rx_freq > 1000:
                            file_info["frequency_bands"]["Microwave (>1 GHz)"] += 1
                        else:
                            file_info["frequency_bands"]["Other"] += 1

            # Analyze channel plans
            elif assignment.channel_plan_id:
                channel_plan = next(
                    (
                        cp
                        for cp in reference.channel_plans
                        if cp.id == assignment.channel_plan_id
                    ),
                    None,
                )
                if channel_plan:
                    for channel in channel_plan.channels:
                        if channel.freq_mhz:
                            if channel.freq_mhz < 30:
                                file_info["frequency_bands"]["HF (<30 MHz)"] += 1
                            elif 136 <= channel.freq_mhz <= 174:
                                file_info["frequency_bands"]["VHF (136-174 MHz)"] += 1
                            elif 400 <= channel.freq_mhz <= 480:
                                file_info["frequency_bands"]["UHF (400-480 MHz)"] += 1
                            elif channel.freq_mhz > 1000:
                                file_info["frequency_bands"]["Microwave (>1 GHz)"] += 1
                            else:
                                file_info["frequency_bands"]["Other"] += 1

                        # Assume FM for channel plans unless otherwise specified
                        file_info["modes"]["FM"] += 1

            if assignment.usage:
                file_info["usage_types"][assignment.usage] += 1

        return file_info

    except Exception as e:
        return {
            "path": file_path,
            "relative_path": str(file_path.relative_to(SSRF_ROOT)),
            "name": file_path.stem,
            "error": str(e),
            "services": set(),
            "modes": Counter(),
            "usage_types": Counter(),
            "frequency_bands": Counter(),
        }


def determine_category(relative_path: pathlib.Path) -> str:
    """Determine the category of an SSRF file from its path."""
    parts = relative_path.parts

    if "plans" in parts:
        return "Channel Plan"
    elif "systems" in parts:
        if "custom" in parts:
            return "Custom System"
        else:
            return "Geographic System"
    else:
        return "Other"


def extract_geographic_info(relative_path: pathlib.Path) -> Dict[str, Optional[str]]:
    """Extract geographic information from the file path."""
    parts = relative_path.parts

    geo_info: Dict[str, Optional[str]] = {
        "country": None,
        "region": None,
        "state": None,
        "county": None,
        "city": None,
        "service": None,
    }

    if "plans" in parts:
        # plans/US/amateur/ham_vhf_simplex.yml
        plan_idx = parts.index("plans")
        if len(parts) > plan_idx + 1:
            geo_info["country"] = parts[plan_idx + 1]
        if len(parts) > plan_idx + 2:
            geo_info["service"] = parts[plan_idx + 2]

    elif "systems" in parts:
        # systems/US/IL/Cook/Chicago/amateur/ns9rc_repeaters.yml
        sys_idx = parts.index("systems")
        if len(parts) > sys_idx + 1:
            geo_info["country"] = parts[sys_idx + 1]
        if len(parts) > sys_idx + 2:
            geo_info["state"] = parts[sys_idx + 2]
        if len(parts) > sys_idx + 3:
            geo_info["county"] = parts[sys_idx + 3]
        if len(parts) > sys_idx + 4:
            geo_info["city"] = parts[sys_idx + 4]
        if len(parts) > sys_idx + 5:
            geo_info["service"] = parts[sys_idx + 5]

    return geo_info


def generate_file_documentation(file_info: Dict[str, Any]) -> str:
    """Generate markdown documentation for a single SSRF file."""

    if "error" in file_info:
        return (
            f"# {file_info['name']}\n\n**Error loading file:** {file_info['error']}\n"
        )

    reference = file_info["reference"]
    md = []

    # Header
    md.append(f"# {file_info['name']}")
    md.append("")
    md.append(f"**Path:** `{file_info['relative_path']}`  ")
    md.append(f"**Category:** {file_info['category']}  ")

    # Geographic info
    geo = file_info["geographic_scope"]
    geo_parts = []
    for key in ["country", "state", "county", "city"]:
        if geo[key]:
            geo_parts.append(geo[key])
    if geo_parts:
        md.append(f"**Geographic Scope:** {' / '.join(geo_parts)}  ")

    if geo["service"]:
        md.append(f"**Primary Service:** {geo['service']}  ")

    md.append("")

    # Quick stats
    md.append("## Overview")
    md.append("")
    md.append(f"- **Assignments:** {file_info['assignments']}")
    if file_info["services"]:
        md.append(f"- **Services:** {', '.join(sorted(file_info['services']))}")
    md.append(f"- **Organizations:** {file_info['organizations']}")
    md.append(f"- **Locations:** {file_info['locations']}")
    md.append(f"- **RF Chains:** {file_info['rf_chains']}")
    md.append(f"- **Channel Plans:** {file_info['channel_plans']}")
    md.append(f"- **Contacts:** {file_info['contacts']}")
    md.append("")

    # Statistics
    if file_info["modes"]:
        md.append("### Modes")
        for mode, count in file_info["modes"].most_common():
            md.append(f"- **{mode}:** {count}")
        md.append("")

    if file_info["usage_types"]:
        md.append("### Usage Types")
        for usage, count in file_info["usage_types"].most_common():
            md.append(f"- **{usage.title()}:** {count}")
        md.append("")

    if file_info["frequency_bands"]:
        md.append("### Frequency Bands")
        for band, count in file_info["frequency_bands"].most_common():
            md.append(f"- **{band}:** {count}")
        md.append("")

    # Organizations
    if reference.organizations:
        md.append("## Organizations")
        md.append("")
        for org in reference.organizations:
            md.append(f"- **{org.name}** (`{org.id}`)")
        md.append("")

    # Locations
    if reference.locations:
        md.append("## Locations")
        md.append("")
        for loc in reference.locations:
            md.append(f"### {loc.name}")
            if loc.lat and loc.lon:
                md.append(f"**Coordinates:** {loc.lat:.4f}, {loc.lon:.4f}")
            md.append("")

    # Channel Plans
    if reference.channel_plans:
        md.append("## Channel Plans")
        md.append("")
        for plan in reference.channel_plans:
            md.append(f"### {plan.name} (`{plan.id}`)")
            md.append("")
            md.append("| Channel | Frequency | Emission |")
            md.append("|---------|-----------|----------|")
            for channel in plan.channels:
                freq = f"{channel.freq_mhz:.4f} MHz" if channel.freq_mhz else "N/A"
                emission = channel.emission or "N/A"
                md.append(f"| {channel.name} | {freq} | {emission} |")
            md.append("")

    # Assignments Summary
    if reference.assignments:
        md.append("## Assignments")
        md.append("")

        # Group by service
        by_service = defaultdict(list)
        for assignment in reference.assignments:
            service = assignment.service or "unknown"
            by_service[service].append(assignment)

        for service in sorted(by_service.keys()):
            assignments = by_service[service]
            md.append(f"### {service.title()} ({len(assignments)} assignments)")
            md.append("")

            for assignment in assignments:
                md.append(
                    f"- **{assignment.id}** - {assignment.usage or 'Unknown usage'}"
                )
                if assignment.notes:
                    md.append(f"  - *{assignment.notes}*")
            md.append("")

    # Authorizations
    if reference.authorizations:
        md.append("## Authorization Requirements")
        md.append("")
        for auth in reference.authorizations:
            md.append(f"### {auth.service or 'Unknown Service'}")
            md.append(f"- **Authority:** {auth.authority}")
            if auth.class_:
                md.append(f"- **Class:** {auth.class_}")
            if auth.notes:
                md.append(f"- **Notes:** {auth.notes}")
            md.append("")

    return "\n".join(md)


def generate_index_documentation(file_analyses: List[Dict[str, Any]]) -> str:
    """Generate the main SSRF documentation index."""

    md = []

    # Header
    md.append("# SSRF-Lite Documentation")
    md.append("")
    md.append(
        "This directory contains automatically generated documentation for all SSRF-Lite YAML files in the project."
    )
    md.append("")

    # Quick stats
    total_files = len(file_analyses)
    total_assignments = sum(f.get("assignments", 0) for f in file_analyses)
    all_services = set()
    all_modes = Counter()
    all_bands = Counter()

    for f in file_analyses:
        all_services.update(f.get("services", set()))
        all_modes.update(f.get("modes", {}))
        all_bands.update(f.get("frequency_bands", {}))

    md.append("## Quick Statistics")
    md.append("")
    md.append(f"- **Total SSRF Files:** {total_files}")
    md.append(f"- **Total Assignments:** {total_assignments:,}")
    md.append(f"- **Services Covered:** {len(all_services)}")
    md.append(f"- **Modes:** {', '.join(sorted(all_modes.keys()))}")
    md.append(f"- **Frequency Bands:** {len(all_bands)}")
    md.append("")

    # File categories
    by_category = defaultdict(list)
    for f in file_analyses:
        category = f.get("category", "Other")
        by_category[category].append(f)

    md.append("## File Categories")
    md.append("")

    for category in sorted(by_category.keys()):
        files = by_category[category]
        md.append(f"### {category} ({len(files)} files)")
        md.append("")

        # Create table for this category
        md.append("| File | Services | Assignments | Modes | Geographic Scope |")
        md.append("|------|----------|-------------|-------|------------------|")

        for f in sorted(files, key=lambda x: x.get("relative_path", "")):
            name = f.get("name", "Unknown")
            name_link = f"[{name}]({name}.md)"

            services = ", ".join(sorted(f.get("services", set())))[:30]
            if len(services) == 30:
                services += "..."

            assignments = f.get("assignments", 0)
            modes = ", ".join(f.get("modes", {}).keys())[:20]
            if len(modes) == 20:
                modes += "..."

            geo = f.get("geographic_scope", {})
            geo_parts = []
            for key in ["country", "state", "county", "city"]:
                if geo.get(key):
                    geo_parts.append(geo[key])
            geographic = " / ".join(geo_parts) if geo_parts else "N/A"

            md.append(
                f"| {name_link} | {services} | {assignments} | {modes} | {geographic} |"
            )

        md.append("")

    # Geographic coverage
    md.append("## Geographic Coverage")
    md.append("")

    by_country = defaultdict(lambda: defaultdict(list))
    for f in file_analyses:
        geo = f.get("geographic_scope", {})
        country = geo.get("country") or "Unknown"
        state = geo.get("state") or "N/A"
        by_country[country][state].append(f)

    for country in sorted(by_country.keys()):
        states = by_country[country]
        md.append(f"### {country}")

        for state in sorted(states.keys()):
            files = states[state]
            if state != "N/A":
                md.append(f"- **{state}:** {len(files)} files")
            else:
                md.append(f"- **National/Regional:** {len(files)} files")
        md.append("")

    # Service breakdown
    md.append("## Service Coverage")
    md.append("")

    service_stats = Counter()
    for f in file_analyses:
        for service in f.get("services", set()):
            service_stats[service] += f.get("assignments", 0)

    md.append("| Service | Total Assignments | Files |")
    md.append("|---------|------------------|-------|")

    service_files = defaultdict(int)
    for f in file_analyses:
        for service in f.get("services", set()):
            service_files[service] += 1

    for service in sorted(service_stats.keys()):
        assignments = service_stats[service]
        files = service_files[service]
        md.append(f"| {service} | {assignments} | {files} |")

    md.append("")

    # Usage instructions
    md.append("## Using SSRF Files")
    md.append("")
    md.append(
        "SSRF-Lite files contain reference data about RF systems and channel plans. They are used by:"
    )
    md.append("")
    md.append("### Profiles")
    md.append("Profiles select which SSRF files to include in a build:")
    md.append("```yaml")
    md.append("profile:")
    md.append("  include:")
    md.append("    paths:")
    md.append('      - "ssrf/plans/US/amateur/*.yml"')
    md.append('      - "ssrf/systems/US/IL/Cook/Chicago/amateur/*.yml"')
    md.append("```")
    md.append("")

    md.append("### Code Generation")
    md.append("```bash")
    md.append("# Generate codeplug using profile that includes SSRF files")
    md.append("uv run python generate_opengd_import.py --profile chicago_amateur")
    md.append("")
    md.append("# Preview which SSRF files a profile would use")
    md.append(
        "uv run python generate_opengd_import.py --profile chicago_amateur --dry-run"
    )
    md.append("```")
    md.append("")

    # File structure explanation
    md.append("## File Organization")
    md.append("")
    md.append("```")
    md.append("ssrf/")
    md.append("  plans/          # Portable channel plans (GMRS, Marine, etc.)")
    md.append("    US/")
    md.append("      amateur/")
    md.append("      gmrs/")
    md.append("      marine/")
    md.append("  systems/        # Location-based systems")
    md.append("    US/")
    md.append("      IL/Cook/Chicago/amateur/")
    md.append("      FL/_Regional/gmrs/")
    md.append("  custom/         # Special-purpose systems")
    md.append("```")
    md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Generate markdown documentation for SSRF-Lite files"
    )
    parser.add_argument(
        "--ssrf-dir",
        type=pathlib.Path,
        default=SSRF_ROOT,
        help="Directory containing SSRF YAML files",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=DEFAULT_DOCS_DIR,
        help="Directory for generated markdown files",
    )
    parser.add_argument(
        "--file", help="Generate documentation for specific SSRF file only"
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="List all available SSRF files and exit",
    )

    args = parser.parse_args()

    # Find all SSRF files
    ssrf_files = []
    for yml_file in args.ssrf_dir.rglob("*.yml"):
        if yml_file.name.startswith("_"):
            continue  # Skip _defaults.yml etc.
        ssrf_files.append(yml_file)

    if args.list_files:
        # List all available SSRF files
        print(f"Available SSRF files ({len(ssrf_files)} total):")
        print()

        # Group by category for better organization
        plans = [f for f in ssrf_files if "/plans/" in str(f)]
        systems = [f for f in ssrf_files if "/systems/" in str(f)]
        custom = [f for f in ssrf_files if "/custom/" in str(f)]

        if plans:
            print("📋 Channel Plans:")
            for file in sorted(plans):
                rel_path = file.relative_to(args.ssrf_dir)
                print(f"   {rel_path}")
            print()

        if systems:
            print("🌍 Geographic Systems:")
            for file in sorted(systems):
                rel_path = file.relative_to(args.ssrf_dir)
                print(f"   {rel_path}")
            print()

        if custom:
            print("⚙️ Custom Systems:")
            for file in sorted(custom):
                rel_path = file.relative_to(args.ssrf_dir)
                print(f"   {rel_path}")
            print()

        return

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        # Generate documentation for specific file
        target_file = pathlib.Path(args.file)
        if not target_file.is_absolute():
            target_file = args.ssrf_dir.parent / args.file

        if not target_file.exists():
            # Try with .yml extension
            if not args.file.endswith(".yml"):
                target_file = target_file.with_suffix(".yml")

        if not target_file.exists():
            print(f"SSRF file not found: {args.file}")
            print(f"Tried: {target_file}")
            return

        ssrf_files = [target_file]

    if not ssrf_files:
        print(f"No SSRF files found in {args.ssrf_dir}")
        return

    print(f"Analyzing {len(ssrf_files)} SSRF files...")

    # Analyze all files
    file_analyses = []
    for ssrf_file in ssrf_files:
        print(f"  Analyzing {ssrf_file.relative_to(args.ssrf_dir)}")
        analysis = analyze_ssrf_file(ssrf_file)
        file_analyses.append(analysis)

        # Generate individual file documentation
        doc = generate_file_documentation(analysis)
        doc_file = args.output_dir / f"{analysis['name']}.md"

        with doc_file.open("w") as f:
            f.write(doc)

        print(f"    → {doc_file}")

    # Generate index documentation
    if len(file_analyses) > 1:
        index_doc = generate_index_documentation(file_analyses)
        index_file = args.output_dir / "README.md"

        with index_file.open("w") as f:
            f.write(index_doc)

        print(f"  → {index_file}")

    print(f"\nSSRF documentation generated in: {args.output_dir}")


if __name__ == "__main__":
    main()
