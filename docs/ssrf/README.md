# SSRF-Lite Documentation

This directory contains automatically generated documentation for all SSRF-Lite YAML files in the project.

## Quick Statistics

- **Total SSRF Files:** 36
- **Total Assignments:** 532
- **Services Covered:** 9
- **Modes:** APRS, C4FM, CW, D-STAR, DMR, FM, NXDN, P25, PACKET
- **Frequency Bands:** 5

## File Categories

### Channel Plan (10 files)

| File | Services | Assignments | Modes | Geographic Scope |
|------|----------|-------------|-------|------------------|
| [pmr446_analog](pmr446_analog.md) | pmr446 | 16 | FM | EU |
| [ham_dmr_simplex](ham_dmr_simplex.md) | amateur | 14 | DMR | US |
| [ham_uhf_simplex](ham_uhf_simplex.md) |  | 20 | FM | US |
| [ham_vhf_simplex](ham_vhf_simplex.md) |  | 20 | FM | US |
| [itinerant_business](itinerant_business.md) | business_itinerant_part90 | 27 | FM | US |
| [gmrs_channels](gmrs_channels.md) | gmrs | 30 | FM | US |
| [marine_vhf_channels](marine_vhf_channels.md) | marine | 52 | FM | US |
| [murs_channels](murs_channels.md) | murs | 5 | FM | US |
| [rail_aar_scan](rail_aar_scan.md) | railroad_aar | 24 | FM | US |
| [noaa_weather](noaa_weather.md) | noaa_weather_radio | 7 | FM | US |

### Custom System (1 files)

| File | Services | Assignments | Modes | Geographic Scope |
|------|----------|-------------|-------|------------------|
| [mmdvm_duplex_hotspot](mmdvm_duplex_hotspot.md) | amateur | 2 | DMR | custom / mmdvm_duplex_hotspot.yml |

### Geographic System (25 files)

| File | Services | Assignments | Modes | Geographic Scope |
|------|----------|-------------|-------|------------------|
| [tarc_repeaters](tarc_repeaters.md) | amateur | 3 | FM | US / FL / Hillsborough / Tampa |
| [florida_simulcast_group](florida_simulcast_group.md) | amateur, gmrs | 15 | FM, P25, DMR, NXDN, ... | US / FL / _Regional / florida_simulcast_group.yml |
| [st_pete_gmrs_repeaters](st_pete_gmrs_repeaters.md) | gmrs | 7 | FM | US / FL / _Regional / gmrs |
| [cfmc_repeaters](cfmc_repeaters.md) | amateur | 7 | FM, D-STAR, C4FM | US / IL / Cook / Chicago |
| [chicagoland_dmr_system](chicagoland_dmr_system.md) | amateur | 2 | DMR | US / IL / Cook / Chicago |
| [ns9rc_repeaters](ns9rc_repeaters.md) | amateur | 13 | FM, C4FM, D-STAR, AP... | US / IL / Cook / Chicago |
| [sara_repeaters](sara_repeaters.md) | amateur | 3 | FM, C4FM | US / IL / Cook / Chicago |
| [chicago_businesses_northside](chicago_businesses_northside.md) | business_itinerant_part90 | 50 | DMR, FM | US / IL / Cook / Chicago |
| [venues_chicago](venues_chicago.md) | business_itinerant_part90 | 15 | DMR, FM | US / IL / Cook / Chicago |
| [chicago_gmrs_repeaters](chicago_gmrs_repeaters.md) | gmrs | 9 | FM | US / IL / Cook / Chicago |
| [family_channels](family_channels.md) | amateur, gmrs | 17 | FM, DMR | US / IL / Cook / Chicago |
| [chicago_ems_services](chicago_ems_services.md) | public_safety_part90 | 41 | FM | US / IL / Cook / Chicago |
| [chicago_fire_ems_northside](chicago_fire_ems_northside.md) | public_safety_part90 | 18 | FM | US / IL / Cook / Chicago |
| [chicago_police_department](chicago_police_department.md) | public_safety_part90 | 8 | FM | US / IL / Cook / Chicago |
| [public_works_parks](public_works_parks.md) | public_safety_part90 | 17 | FM, DMR | US / IL / Cook / Chicago |
| [transit_transport](transit_transport.md) | public_safety_part90 | 7 | FM, DMR | US / IL / Cook / Chicago |
| [cook_county_interop](cook_county_interop.md) | public_safety_part90 | 9 | FM | US / IL / Cook / _Countywide |
| [tri_state_dmr](tri_state_dmr.md) | amateur | 16 | DMR | US / IL / _Statewide / amateur |
| [il_statewide_interop](il_statewide_interop.md) | public_safety_part90 | 14 | FM | US / IL / _Statewide / public_safety |
| [laporte_county_amateur_radio_club](laporte_county_amateur_radio_club.md) | amateur | 6 | FM, C4FM | US / IN / LaPorte / LaPorte |
| [laporte_county_public_safety](laporte_county_public_safety.md) | public_safety_part90 | 15 | FM | US / IN / LaPorte / LaPorte |
| [n9iaa_aresc_network](n9iaa_aresc_network.md) | amateur | 4 | FM, DMR | US / IN / Northwest / Regional |
| [kc8brs_four_flags](kc8brs_four_flags.md) | amateur | 1 | FM | US / MI / Berrien / Niles |
| [berrien_county_amateur](berrien_county_amateur.md) | amateur | 5 | FM, D-STAR | US / MI / Berrien / _Countywide |
| [berrien_county_public_safety](berrien_county_public_safety.md) | public_safety_part90 | 13 | FM | US / MI / Berrien / _Countywide |

## Geographic Coverage

### EU
- **National/Regional:** 1 files

### US
- **FL:** 3 files
- **IL:** 16 files
- **IN:** 3 files
- **MI:** 3 files
- **National/Regional:** 9 files

### custom
- **mmdvm_duplex_hotspot.yml:** 1 files

## Service Coverage

| Service | Total Assignments | Files |
|---------|------------------|-------|
| amateur | 108 | 14 |
| business_itinerant_part90 | 92 | 3 |
| gmrs | 78 | 5 |
| marine | 52 | 1 |
| murs | 5 | 1 |
| noaa_weather_radio | 7 | 1 |
| pmr446 | 16 | 1 |
| public_safety_part90 | 142 | 9 |
| railroad_aar | 24 | 1 |

## Using SSRF Files

SSRF-Lite files contain reference data about RF systems and channel plans. They are used by:

### Profiles
Profiles select which SSRF files to include in a build:
```yaml
profile:
  include:
    paths:
      - "ssrf/plans/US/amateur/*.yml"
      - "ssrf/systems/US/IL/Cook/Chicago/amateur/*.yml"
```

### Code Generation
```bash
# Generate codeplug using profile that includes SSRF files
uv run python generate_opengd_import.py --profile chicago_amateur

# Preview which SSRF files a profile would use
uv run python generate_opengd_import.py --profile chicago_amateur --dry-run
```

## File Organization

```
ssrf/
  plans/          # Portable channel plans (GMRS, Marine, etc.)
    US/
      amateur/
      gmrs/
      marine/
  systems/        # Location-based systems
    US/
      IL/Cook/Chicago/amateur/
      FL/_Regional/gmrs/
  custom/         # Special-purpose systems
```
