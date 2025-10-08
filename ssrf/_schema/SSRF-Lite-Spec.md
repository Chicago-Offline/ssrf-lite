# SSRF-Lite YAML Specification  
*A pragmatic spectrum data model for codeplug generation*  

Version: **0.4.0**  
Last updated: 2025-10-06  

---

## 1. Purpose
SSRF-Lite is a trimmed-down profile of the [Standard Spectrum Resource Format (SSRF)](https://www.ntia.gov/publications/2023/standard-spectrum-resource-format-ssrf) designed for:  

- Representing radio channels, repeaters, and channel plans in **YAML**.  
- Driving automated codeplug generators ex. OpenGD77, qdmr, OpenRTX, & OEM imports.
- Remaining close enough to SSRF that future expansion or exchange is straightforward.  

---

## 2. Entities

### 2.1 Organization
Represents an owning or operating body.  
```yaml
organizations:
  - id: org_ns9rc
    name: "North Shore Radio Club"
```

Fields:  
- `id` (string, unique)  
- `name` (string)  

---

### 2.2 Location
Geographic site.  
```yaml
locations:
  - id: loc_chicago_lsd
    name: "Chicago – North Lake Shore Dr"
    lat: 41.9804506
    lon: -87.6546484
```
Fields:  
- `id`, `name`  
- `lat`, `lon` (decimal degrees)  

> **Note:** See Antenna for height fields (AGL/AMSL).

---

### 2.3 Station
Logical station at a location, often tied to an organization.  
```yaml
stations:
  - id: stn_ns9rc_440
    call_sign: "NS9RC"
    organization_id: org_ns9rc
    location_id: loc_chicago_lsd
    service: "amateur"
```

Fields:  
- `id`, `call_sign`  
- `organization_id` (ref → Organization)  
- `location_id` (ref → Location)  
- `service` (e.g. `"amateur"`, `"gmrs"`, `"marine"`)  

---

### 2.4 Antenna
Basic antenna info with explicit height references.  
```yaml
antennas:
  - id: ant_ns9rc_440
    station_id: stn_ns9rc_440
    name: "Offset Pattern Antenna"
    gain_dbi: null
    height_agl_m: 156.4       # 513 feet ≈ 156.4 m
    height_amsl_m: null
```
Fields:  
- `id`, `station_id`, `name`  
- `gain_dbi` (optional)  
- `height_agl_m` (optional, meters AGL)  
- `height_amsl_m` (optional, meters AMSL)  

> Populate whichever height(s) you know. If both are present, they need not be mathematically linked (site elevation is not modeled in SSRF-Lite).

---

### 2.5 RF Chain
Bundled **Transmitter + Receiver + Mode**.  
```yaml
rf_chains:
  - id: chain_ns9rc_440_fm
    station_id: stn_ns9rc_440
    antenna_id: ant_ns9rc_440
    tx:
      freq_mhz: 447.725       # uplink (ERP, repeater output +5 MHz)
      power_w: 80             # ERP approx
      emission: "16K0F3E"     # FM voice, wideband (25 kHz)
      bandwidth_khz: 25
    rx:
      freq_mhz: 442.725       # repeater input
    mode:
      type: "FM"
      ctcss_tx_hz: 114.8
      ctcss_rx_hz: 114.8
      dcs_tx_code: 023        # DCS transmit code (optional)
      dcs_rx_code: 023        # DCS receive code (optional)

  - id: chain_n9kd_444_dmr
    station_id: stn_n9kd
    antenna_id: ant_n9kd
    tx:
      freq_mhz: 449.000
      emission: "7K60FXE"     # DMR voice/data
    rx:
      freq_mhz: 444.000
    mode:
      type: "DMR"
      color_code: 0
      timeslots: [1, 2]
```

Fields:  

- `id`, `station_id`, `antenna_id`  
- `tx`: `freq_mhz`, `power_w?`, `emission`, `bandwidth_khz?`  
- `rx`: `freq_mhz`, `sensitivity_dbm?`  
- `mode`:  
  - `type` (`"FM"`, `"DMR"`, etc.)  
  - Mode-specific fields:
    - `ctcss_tx_hz`, `ctcss_rx_hz` (optional, Hz)
    - `dcs_tx_code`, `dcs_rx_code` (optional, DCS code as string or integer, e.g. "023", "205")
    - `color_code`, `timeslots` (for DMR repeaters — talkgroup slot priorities live in `contacts`)

For multi-site DMR systems, capture each repeater as an `rf_chain` and centralize talkgroup metadata in `contacts`. See `chicagoland_dmr_system.yml` for a working example.



### 2.6 Channel Plan

Reusable collections (NOAA, Marine, GMRS interstitials).  

```yaml
channel_plans:
  - id: chplan_noaa
    name: "NOAA WX"
    channels:
      - name: "WX1"
        freq_mhz: 162.550
      - name: "WX2"
        freq_mhz: 162.400
```

---

### 2.7 Authorization

License or permission required.  

```yaml
authorizations:
  - id: auth_fcc_amateur_t
    authority: "FCC"
    service: "Amateur Radio"
    class: "Technician or higher"
    identifier: null
    notes: "TX requires US amateur license."
  - id: auth_rx_only_public
    authority: "N/A"
    service: "Receive-only"
    class: null
    identifier: null
    notes: "Listening only (e.g., NOAA); no license required."
```

Fields:  

- `id`  
- `authority` (e.g. `"FCC"`)  
- `service` (Amateur, GMRS, Marine, etc.)  
- `class` (optional, license class)  
- `identifier` (e.g. license number)  
- `notes`  

---

### 2.8 Contacts

Directory for DMR talkgroups or similar.  

```yaml
contacts:
  - id: tg_310
    name: "TAC-310"
    kind: "Group"
```

Expanded DMR example with slot hints and talkgroup numbers:  

```yaml
contacts:
  - id: tg_9
    name: "Site Local"
    kind: "Group"
    number: 9
    default_timeslot: 1
    notes: "Local traffic, always-on."
```

Fields:  

- `id`, `name`, `kind` (`"Group"`, `"Private"`, or `"AllCall"`)  
- `number` (integer talkgroup ID, optional for analog contacts)  
- `default_timeslot` (1 or 2, optional)  
- `notes` (usage guidance, optional)  
- Future extensions may add `dtmf_id`, `call_type`, etc.  

---

### 2.9 Assignment

The “workhorse” — links RF chain or channel plan to an operational use (codeplug row).  

```yaml
assignments:
  - id: asgn_ns9rc_440
    rf_chain_id: chain_ns9rc_440_fm
    usage: "repeater"
    zones: ["Ham-Repeaters"]
    codeplug:
      name: "NS9RC 440"
      rx_only: false
      all_skip: false  # Optional: if true, sets Channels.csv "All Skip" = Yes
      preferred_contacts: [tg_9, tg_3181, tg_3166]
    authorization_id: auth_fcc_amateur_t
    comment: |
      Motorola + S-Com 7330 controller, ~80 W ERP.
      Offset pattern antenna at 513 ft (156 m).
      Coverage: Cook & Lake Counties; one of the most active repeaters in Chicago.
      Mobile access: S to Merrillville IN, N to Kenosha WI, W to Crystal Lake.

  - id: asgn_noaa_wx1
    channel_plan_id: chplan_noaa
    channel_name: "WX1"
    usage: "receive-only"
    zones: ["NOAA"]
    codeplug:
      name: "WX1-Chicago"
      rx_only: true
      all_skip: true
    authorization_id: auth_rx_only_public
```

Within `assignments[].codeplug` the following helper flags are recognized:  

- `rx_only`: mark receive-only channels.  
- `all_skip`: map to CPS "All Skip" or scan lockouts.  
- `preferred_contacts`: ordered list of contact IDs (typically DMR talkgroups) a generator should populate for that channel.  

---

## 3. Mapping to SSRF

| SSRF Entity | SSRF-Lite Equivalent | Notes |
|---|---|---|
| Organization | `organizations[]` | same name, pared fields |
| Location | `locations[]` | same (no site elevation) |
| Station | `stations[]` | same |
| Antenna | `antennas[]` | same, + `height_agl_m` / `height_amsl_m` |
| Equipment / Tx / Rx / TxMode / RxMode | `rf_chains[]` | consolidated |
| ChannelPlan / ChannelFreq | `channel_plans[]` | same |
| Authorization | `authorizations[]` | same |
| Assignment | `assignments[]` | same, plus codeplug extras |
| Contacts (not in SSRF) | `contacts[]` | **added** for DMR convenience |
| Codeplug / Zones | `assignments[].codeplug`, `zones` | **added** for generator use; `codeplug.all_skip` maps to Channels.csv "All Skip" |

---

## 4. Example Summary

This spec now demonstrates:

- **Analog FM repeater**: NS9RC 440 MHz with ERP, offset, tones, and coverage notes.  
- **Receive-only channel plan**: NOAA WX frequencies.  
- **Authorization linkage**: Amateur TX license vs. public RX-only.  
- **DMR repeater support**: ChicagoLand control center example with color codes, timeslots, and talkgroup guidance.  
- **Codeplug guidance**: `codeplug` helpers surface skip flags and ordered talkgroup lists (`preferred_contacts`).  
- **Extensibility**: Ready to add other digital modes.  

---

## 5. Design Principles

- **Stay SSRF-shaped**: reuse names and relationships where possible.  
- **Trim fat**: omit coordination, workflows, and technical minutiae not needed for codeplugs.  
- **Add only what’s practical**: `zones`, `codeplug`, `contacts`.  
- **Interoperable**: keep ITU emission designators, MHz/kHz/Hz units consistent.  
- **Extensible**: can grow into full SSRF without breaking the schema.  

---

## 6. DMR & Codeplug Enhancements (v0.4.0)

- **RF chains**: Capture `color_code` and `timeslots` to pin repeater color codes and slot availability. See `chicagoland_dmr_system.yml` for a multi-site example.
- **Talkgroup catalog**: `contacts` entries may include `number`, `default_timeslot`, and descriptive `notes`, providing enough metadata to build CPS contact lists.
- **Channel programming hints**: `codeplug.preferred_contacts` expresses the talkgroups a generator should populate first, while existing flags (`rx_only`, `all_skip`) continue to drive receive-only or scan skip behavior.
- **Backwards compatible**: All new fields are optional; analog-focused data remains valid without changes.
