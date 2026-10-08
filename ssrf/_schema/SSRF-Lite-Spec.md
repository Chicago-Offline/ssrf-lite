# SSRF-Lite YAML Specification  

*A pragmatic spectrum data model for codeplug generation*  

Version: **0.10.0**  
Last updated: 2026-09-29  

---

## 1. Purpose

SSRF-Lite is a trimmed-down profile of the [Standard Spectrum Resource Format (SSRF)](https://www.ntia.gov/publications/2023/standard-spectrum-resource-format-ssrf) designed for:  

- Representing radio channels, repeaters, and channel plans in **YAML** as reference data.  
- Remaining close enough to SSRF that future expansion or exchange is straightforward.  
- Powering downstream tooling (codeplug generators, planners, etc.) **without** embedding per-consumer policy choices inside the reference layer.  

### Layered architecture (Reference ➜ Selection ➜ Policy)

```text
┌────────────────┐   ┌────────────────────┐   ┌────────────────────┐
│ SSRF-Lite data │ → │ Profiles (selection│ → │ Policies (opinions │
│ Reference-only │   │ & scoping)         │   │ & rendering rules) │
└────────────────┘   └────────────────────┘   └────────────────────┘
```

- **SSRF-Lite** captures authoritative RF facts: who owns a system, where it lives, how it transmits, what authorizations exist.  
- **Profiles** choose which SSRF assignments apply to a requested configuration (e.g., "Chicago GMRS" vs. "Emergency-only").  
- **Policies** express consumer-specific opinions such as transmit enablement, scan skip defaults, zone membership, ordering, and naming conventions.  

Keeping these concerns separated makes SSRF-Lite reusable across radios, services, and policy stacks.  

---

## 1.1 File headers & validation

Every SSRF-Lite YAML document carries two schema-association headers so that
editors and CI can validate it **without importing the Python models**:

```yaml
# yaml-language-server: $schema=../../../_schema/ssrf-lite-0.10.0.schema.json
$schema: "../../../_schema/ssrf-lite-0.10.0.schema.json"
ssrf_lite_version: "0.10.0"
```

- The `# yaml-language-server:` modeline enables live validation in editors such
  as VS Code (Red Hat YAML extension). The relative path is resolved from the
  file's own location.
- The top-level `$schema` key lets CI tools (e.g. `check-jsonschema`) discover the
  schema. Its value is a path relative to the file.
- `ssrf_lite_version` pins the spec revision the file targets and must match the
  shipped schema (`0.10.0`).

The versioned JSON Schema lives beside this document at
[`ssrf-lite-0.10.0.schema.json`](./ssrf-lite-0.10.0.schema.json) and is generated
from the Pydantic models via `generate_ssrf_schema.py`. Optional, non-normative
metadata keys (`ssrf_lite.sources`, `comments`) and the normative `overrides`
block are permitted alongside the reference entities.

> Regenerate the schema and re-stamp headers with `make schema stamp-headers`
> (or `make docs`), and verify freshness in CI with `make validate-schema`.

## 1.2 Overlay field patches

Additional SSRF roots may add entities with unique IDs and may patch entities
loaded from earlier roots. Patches are explicit and grouped by entity
collection:

```yaml
overrides:
  assignments:
    - id: asg_example
      patch:
        channel_name: "LOCAL NAME"
  rf_chains:
    - id: chain_example
      patch:
        mode:
          ctcss_tx_hz: null
```

Patch mappings merge recursively. Lists replace rather than append, and `null`
explicitly clears an optional field. The selector ID is immutable and cannot
appear inside `patch`. A target must identify exactly one entity in its
collection across roots processed so far; missing and ambiguous targets are
errors. The complete owning document is validated after patching, so clearing
a required field or introducing an unknown field is also an error.

### Root precedence

By default roots are processed in the order they are supplied, with later
roots patching earlier ones. A root may instead declare its own precedence in
a top-level `_root.yml` (files whose names start with `_` are skipped by the
data scan):

```yaml
ssrf_root:
  id: "my_private_overlay"
  precedence: 100   # integer; higher loads later and wins on conflict
```

Roots without a declaration fall back to their positional index (0, 1, 2, …).
Two roots declaring the same `precedence` is an error. An override may only
target entities from roots that load *before* it.

## 1.3 Legacy field handling

When loading, the reference layer silently drops the deprecated policy-era
assignment keys `codeplug`, `zones`, and `scan`, and maps a legacy `comment`
key to `notes` when `notes` is absent. Any other unknown key on any entity is
an error (`additionalProperties: false`).

---

## 2. Entities (Reference layer)

### 2.0 Shared value constraints

- **`service`** (wherever it appears) is a closed vocabulary drawn from
  `ssrf/_taxonomies/services.yaml`. Values are matched case-insensitively and
  normalized to lowercase. Current IDs: `amateur`, `gmrs`, `frs`, `murs`,
  `pmr446`, `noaa_weather_radio`, `marine`, `aviation`, `railroad_aar`,
  `public_safety_part90`, `business_itinerant_part90`.
- **`mode.type`** is a closed vocabulary, normalized to uppercase (`DSTAR` →
  `D-STAR`): `AM`, `APRS`, `C4FM`, `CW`, `DMR`, `D-STAR`, `DSD`, `FM`, `LSB`,
  `NFM`, `NXDN`, `PACKET`, `P25`, `USB`.
- Every entity forbids unknown keys.

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
- `lat`, `lon` (optional, decimal degrees; `lat` in [-90, 90], `lon` in [-180, 180])  

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

- `id`  
- `call_sign` (optional string; omit or set `null` if unknown; blank strings become `null`)  
- `organization_id` (optional ref → Organization)  
- `location_id` (optional ref → Location)  
- `service` (optional; see §2.0)  

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

- `id`, `station_id`  
- `name` (optional)  
- `gain_dbi` (optional)  
- `height_agl_m` (optional, meters AGL, ≥ 0)  
- `height_amsl_m` (optional, meters AMSL, ≥ 0)  

> Populate whichever height(s) you know. If both are present, they need not be mathematically linked (site elevation is not modeled in SSRF-Lite).

---

### 2.5 RF Chain

Bundled **Transmitter + Receiver + Mode**. Reference-only facts (frequencies, emissions, and modulation metadata) live here; codeplug behaviors are defined elsewhere.  

> **Perspective.** Every RF chain is written from the point of view of the
> station it belongs to, matching SSRF, where a `Transmitter` describes what a
> piece of equipment radiates and a `Receiver` what it tunes. `tx` is therefore
> a repeater's **output** and `rx` its **input** — never the other way round.
> The same applies to the tones: `ctcss_tx_hz` is what the station sends,
> `ctcss_rx_hz` what it requires to be keyed up.

```yaml
rf_chains:
  - id: chain_ns9rc_440_fm
    station_id: stn_ns9rc_440
    antenna_id: ant_ns9rc_440
    tx:
      freq_mhz: 442.725       # repeater output
      power_w: 80             # ERP approx
      emission: "16K0F3E"     # FM voice, wideband (25 kHz)
      bandwidth_khz: 25
    rx:
      freq_mhz: 447.725       # repeater input (+5 MHz above output)
    mode:
      type: "FM"
      ctcss_tx_hz: 114.8      # tone sent on the output
      ctcss_rx_hz: 114.8      # tone required on the input
      dcs_tx_code: "023"      # DCS code sent on the output (optional)
      dcs_tx_polarity: "N"   # N (normal, default) or I (inverted)
      dcs_rx_code: "023"      # DCS code required on the input (optional)
      dcs_rx_polarity: "N"   # N (normal, default) or I (inverted)

  - id: chain_n9kd_444_dmr
    station_id: stn_n9kd
    antenna_id: ant_n9kd
    tx:
      freq_mhz: 444.000
      emission: "7K60FXE"     # DMR voice/data
    rx:
      freq_mhz: 449.000
    mode:
      type: "DMR"
      color_code: 0
      timeslots: [1, 2]
      notes: "Optional freeform notes about the repeater's digital behavior."
```

Fields:  

- `id`, `station_id`  
- `antenna_id` (optional ref → Antenna)  
- `tx`: `freq_mhz?`, `power_w?`, `emission?`, `bandwidth_khz?` (all positive when present)  
- `rx`: `freq_mhz?`, `sensitivity_dbm?`  
- `mode`:  
  - `type` (closed vocabulary; see §2.0)  
  - `notes?` (optional descriptive string)  
  - Mode-specific fields:
    - `ctcss_tx_hz`, `ctcss_rx_hz` (optional, Hz, > 0)
    - `dcs_tx_code`, `dcs_rx_code` (optional) — a **quoted three-digit octal**
      DCS code drawn from the standard 104-code set in
      `ssrf/_taxonomies/dcs_codes.yaml`, e.g. `"023"`, `"205"`, `"624"`.
      Integers are rejected: DCS codes are octal, so `624` is ambiguous (octal
      624 is 404 decimal), and YAML 1.1 reads an unquoted leading zero as octal,
      silently turning `032` into `26`. Codes outside the standard set are
      rejected — add to the taxonomy rather than loosening the type.
    - `dcs_tx_polarity`, `dcs_rx_polarity` (`"N"` or `"I"`; optional, defaults to `"N"`)
    - `color_code` (optional, 0–15), `timeslots` (optional list of ints) — for DMR repeaters; talkgroup slot priorities live in `contacts`
    - `nac` (optional, 0–4095) — P25 network access code
    - `nxdn_ran` (optional, 0–63) — NXDN radio access number

For multi-site DMR systems, capture each repeater as an `rf_chain` and centralize talkgroup metadata in `contacts`. See `chicagoland_dmr_system.yml` for a working example.

A chain must set at least one of `tx.freq_mhz` / `rx.freq_mhz`:

| Case | `tx.freq_mhz` | `rx.freq_mhz` |
|---|---|---|
| Duplex repeater | output | input |
| Simplex | frequency | *omit* |
| Output logged, input unconfirmed | output | *omit* — don't guess an offset |
| Receive-only site (voting RX) | *omit* | frequency |



### 2.6 Channel Plan

Reusable collections (NOAA, Marine, GMRS interstitials). Channel plans remain purely descriptive references—no profile or scan behavior is defined here.  

`freq_mhz` is the frequency the channel's **transmitting station** radiates on — the coast station, repeater output, or broadcaster. Duplex channels add `rx_freq_mhz` for the frequency that same station receives on. Simplex channels omit it.

Where a service permits several incompatible modulations on one frequency, list them under `emissions` (most typical first) instead of the single `emission` key. A plan-level `emissions` block applies to every channel that does not declare its own. Setting both `emission` and `emissions` on one channel is an error.

```yaml
channel_plans:
  - id: chplan_marine
    name: "Marine VHF"
    service: "marine"
    channels:
      - name: "Ch 06"
        freq_mhz: 156.300
        emission: "16K0F3E"
        bandwidth_khz: 25
        notes: "Intership safety"
      - name: "Ch 20"
        freq_mhz: 161.600     # coast station transmit
        rx_freq_mhz: 157.000  # coast station receive

  - id: chplan_us_cb
    name: "US CB (Citizens Band)"
    service: "cb"
    emissions:                # applies to every channel below
      - emission: "8K00A3E"
        mode: "AM"
        bandwidth_khz: 8
        power_w: 4
      - emission: "4K00J3E"
        mode: "USB"           # J3E alone can't distinguish USB from LSB
        bandwidth_khz: 4
        power_w: 12
    channels:
      - name: "CB 01"
        freq_mhz: 26.9650
```

Fields:  

- `id`, `name`  
- `service` (optional; see §2.0)  
- `emissions[]` (optional; default for every channel in the plan)  
- `channels[]`:  
  - `name` (string)  
  - `short_name` (optional)  
  - `freq_mhz` (> 0)  
  - `rx_freq_mhz` (optional, > 0)  
  - `emission` (optional ITU designator)  
  - `bandwidth_khz` (optional, > 0)  
  - `emissions[]` (optional; mutually exclusive with `emission`)  
  - `mode` (optional; squelch and digital parameters the convention specifies)  
  - `notes` (optional)  

Each `emissions[]` entry carries `emission` (required ITU designator), plus optional `mode`, `bandwidth_khz`, `power_w`, and `notes`. Set `mode` where the designator is ambiguous — `J3E` covers both `USB` and `LSB`.  

#### Channel plans vs. deployed chains

A channel plan records a **convention**: the agreed definition of a channel,
whether that agreement comes from a regulator (NOAA, marine, GMRS) or from
community practice (amateur simplex calling frequencies, NIFOG interop
channels). An `rf_chain` records what one **specific station actually does**.

The same frequency routinely appears in both. They answer different questions,
and neither replaces the other:

- The plan entry is the **convention baseline** — what a radio should use to
  participate, absent any local knowledge.
- The `rf_chain` is **authoritative for that station**. Where the two differ,
  the chain wins *for that station only*.

A consumer resolving a channel for a given station takes the chain's value for
every field the chain sets, and falls back to the plan for fields it does not.
That fallback covers `emission`, `bandwidth_khz`, and `mode`.

**A plan that disagrees with a local deployment is not a data error, and the
plan must not be edited to match one site.** NIFOG defines VTAC11 nationally;
an individual licensee may be authorized with different parameters. Both
records are correct at their own scope, and flattening one into the other
destroys the distinction.

A channel's `mode` carries the squelch and digital parameters the convention
specifies — CTCSS/DCS tones, DMR color code and timeslots, P25 NAC — using the
same `Mode` shape as `rf_chains[].mode` (§2.5). Use it for values that are part
of the agreed channel definition: the CTCSS a NIFOG interop channel expects, or
the color code and timeslot an agreed DMR simplex channel runs. Do **not** use
it for one station's local choices; those belong on that station's chain.

Where a channel declares both `mode` and multiple `emissions[]`, `mode.type`
states the channel's primary modulation; per-emission `mode` strings refine
individual entries and win for those entries.

---

### 2.7 Authorization

License or permission required.  

```yaml
authorizations:
  - id: auth_fcc_amateur_t
    authority: "FCC"
    service: "amateur"
    class: "Technician or higher"
    identifier: null
    notes: "TX requires US amateur license."
  - id: auth_rx_only_noaa
    authority: "N/A"
    service: "noaa_weather_radio"
    class: null
    identifier: null
    notes: "Listening only; no license required."
```

Fields:  

- `id`  
- `authority` (e.g. `"FCC"`)  
- `service` (required; see §2.0)  
- `class` (optional, license class)  
- `identifier` (optional, e.g. license number)  
- `notes` (optional)  

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

- `id`, `name`, `kind` (string; by convention `"Group"`, `"Private"`, or `"AllCall"` — not enforced)  
- `number` (integer talkgroup ID, ≥ 0, optional for analog contacts)  
- `default_timeslot` (optional integer; by convention 1 or 2 — not enforced)  
- `notes` (usage guidance, optional)  
- Future extensions may add `dtmf_id`, `call_type`, etc.  

---

### 2.9 Assignment

The “workhorse” — links RF chains or channel plans to an operational RF use **without** prescribing how any consumer should render it.  

```yaml
assignments:
  - id: asgn_ns9rc_440
    rf_chain_id: chain_ns9rc_440_fm
    usage: "repeater"
    service: "amateur"
    authorization_id: auth_fcc_amateur_t
    notes: |
      Motorola + S-Com 7330 controller, ~80 W ERP.
      Offset pattern antenna at 513 ft (156 m).
      Coverage: Cook & Lake Counties; one of the most active repeaters in Chicago.

  - id: asgn_noaa_wx1
    channel_plan_id: chplan_noaa
    channel_name: "WX1"
    usage: "receive-only"
    service: "noaa_weather_radio"
    authorization_id: auth_rx_only_noaa
    notes: "NOAA WX channel for Chicago core service area."

  - id: asgn_marine_06_local
    channel_plan_id: chplan_marine
    channel_name: "Ch 06"
    display_name: "M06 SAFETY"
    usage: "simplex"
    service: "marine"
```

Fields:  

- `id` (string, unique)  
- Either `rf_chain_id` (reference to RF chain) **or** `channel_plan_id` + `channel_name` (reference to plan entry)  
- `display_name` (optional; local label for a plan channel so a document can reuse a shared plan without forking it to rename entries. Honoured only when `channel_name` selects exactly one channel; ignored for `rf_chain_id` assignments)  
- `usage` (string; repeater, simplex, receive-only, data link, etc.)  
- `service` (optional; see §2.0 — supports downstream filtering without dictating policy)  
- `authorization_id` (optional)  
- `notes` (optional freeform description)  
- `verified` (optional; freshness marker — see §2.10)  

> **Deprecated fields:** prior versions allowed `zones`, `codeplug.*`, and `preferred_contacts`. These are now owned by the policy layer. Generators should migrate those concerns to policy definitions (see §3.2).  

---

### 2.10 Verification (v0.7.0; extended to `rf_chains[]` in v0.8.0)

Reference data goes stale quietly. `verified` records the most recent positive confirmation that an entry still reflects on-the-air reality, so consumers can distinguish *"checked last week"* from *"transcribed from a club page in 2019 and never touched since."*

It is a provenance claim about the **record**, not an operational fact about the RF resource. A repeater does not stop existing because nobody verified it; the claim simply ages.

The block is accepted on both **`assignments[]`** and **`rf_chains[]`**, and the two are deliberately independent:

| Host | The claim being made |
|---|---|
| `assignments[]` | *This operational use is still current* — the org still runs this channel for this purpose |
| `rf_chains[]` | *These radio parameters still work* — frequency, offset, tone, and mode still produce a usable contact |

A CTCSS tone can be re-confirmed without re-confirming who is using the channel, and an assignment can be confirmed current by someone who never checked the tone. Recording them separately keeps an old tone from being laundered as fresh by a recent assignment check.

```yaml
assignments:
  - id: asgn_nsea_675
    rf_chain_id: chain_nsea_675
    usage: "repeater"
    service: "gmrs"
    verified:
      date: "2026-09-27"
      method: "on-air"
      by: "WRXC682"
      note: "Checked into the Sunday evening net; full quieting from Edgewater."
```

Fields:  

- `date` (**required**; ISO 8601 calendar date, `YYYY-MM-DD`)  
- `method` (**required**; one of the values below)  
- `by` (optional; call sign, unit ID, or handle of whoever confirmed it)  
- `note` (optional; detail about the confirmation)  

| `method` | Meaning |
|---|---|
| `on-air` | An operator transmitted through or worked the resource |
| `monitor` | Received on a receiver or SDR without transmitting — attended or unattended |
| `licensee` | Owner, trustee, or coordinator confirmed it directly |
| `published` | Authoritative document or database (FCC ULS, coordinator list) |
| `survey` | Deliberate RF survey or measurement |

On an RF chain the block sits alongside the radio parameters it vouches for:

```yaml
rf_chains:
  - id: ch_cdot_towing_parking
    station_id: stn_muni
    rx: {freq_mhz: 453.775}
    tx: {emission: "11K2F3E"}
    mode: {type: "FM", ctcss_rx_hz: 107.2, ctcss_tx_hz: 107.2}
    verified:
      date: "2026-09-27"
      method: "monitor"
      by: "WRXC682"
      note: "Received several times over several days; most recent copy ~2300 local."
```

> **Absence is not staleness.** A missing `verified` block means *never verified*, which is a different (and weaker) claim than an old date. Tooling should treat the two distinctly.

> **Only claim what was actually checked.** `method: monitor` on an RF chain confirms that the receive frequency carries the expected traffic. It does **not** by itself confirm a listed CTCSS/DCS tone, an input frequency, or an emission designator, since a receiver with squelch open will hear the carrier regardless. Say in `note` what was genuinely observed.  

> `verified` describes a single assignment. Document-wide provenance stays in the `ssrf_lite.sources[]` header block (§1.1), and the two are complementary: cite the source, then record who last confirmed it on the air.  

---

## 3. Layer boundaries & SSRF mapping

### 3.1 Reference ➜ SSRF alignment

| SSRF Entity | SSRF-Lite Equivalent | Notes |
|---|---|---|
| Organization | `organizations[]` | same name, pared fields |
| Location | `locations[]` | same (no site elevation) |
| Station | `stations[]` | same |
| Antenna | `antennas[]` | same, + `height_agl_m` / `height_amsl_m` |
| Equipment / Tx / Rx / TxMode / RxMode | `rf_chains[]` | consolidated; same station-centric perspective |
| ChannelPlan / ChannelFreq | `channel_plans[]` | same |
| Authorization | `authorizations[]` | same |
| Assignment | `assignments[]` | same intent, policy fields removed |
| Contacts (not in SSRF) | `contacts[]` | **added** for DMR convenience |
| Codeplug / Zones | *(policy layer)* | handled via policy documents |

SSRF describes spectrum from the equipment outward: a `Transmitter`'s
frequencies are what that transmitter emits, a `Receiver`'s are what it tunes,
and `StationConfig.Type` labels a station `Transmit Only` / `Receive Only` /
`Transmit-Receive` from its own point of view. SSRF-Lite keeps that rule, which
is why a repeater's `tx` is its output. Mirroring into the operator's frame of
reference is a consumer concern, handled once in `codeplug.json`.

### 3.2 Profiles & Policies interface

- **Profiles** (outside the SSRF-Lite schema) collect assignments by ID/path and expose them to a given build. They answer “*which* RF resources participate?” without mutating those resources.  
- **Policies** describe how a consumer should render the selected assignments: naming, transmit enablement, zone placement, scan skip defaults, ordering, talkgroup bundling, etc. Policies may reference assignments by ID but **must not** redefine the RF facts contained in SSRF-Lite.  
- **Generators** merge SSRF reference data + profile selection + policy opinions to produce device-specific outputs.  

---

## 4. Example Summary

This spec now demonstrates:

- **Analog FM repeater**: NS9RC 440 MHz with ERP, offset, tones, and coverage notes.  
- **Receive-only channel plan**: NOAA WX frequencies.  
- **Authorization linkage**: Amateur TX license vs. public RX-only.  
- **DMR repeater support**: ChicagoLand control center example with color codes and timeslot availability.  
- **Separation of concerns**: RF truths remain in SSRF-Lite; rendering logic moves to policies.  

---

## 5. Design Principles

- **Stay SSRF-shaped**: reuse names and relationships where possible.  
- **Trim fat**: omit coordination, workflows, and technical minutiae not needed for RF description.  
- **Reference-only**: do not embed codeplug or scan behavior—policies own those choices.  
- **Interoperable**: keep ITU emission designators, MHz/kHz/Hz units consistent.  
- **Extensible**: can grow into full SSRF without breaking the schema.  

---

## 6. Digital Metadata Enhancements (v0.5.0)

- **RF chains**: continue to capture `color_code` and `timeslots` for DMR repeaters; this data remains reference-worthy.  
- **Talkgroup catalog**: `contacts` entries may include `number`, `default_timeslot`, and descriptive `notes`, enabling policy layers to build CPS contact lists without re-sourcing IDs.  
- **Policy migration**: The previous `codeplug.*`, `zones`, and other rendering hints have been promoted to policy documents. Generators should consult policies when deciding transmit enablement, scan skip behavior, zone membership, or talkgroup ordering.  

---

## 7. Migration Notes

- **Channel plan modes (v0.10.0)**: new optional `mode` on channel plan
  channels, carrying the same `Mode` block as `rf_chains[].mode` — CTCSS/DCS
  tones, DMR color code and timeslots, P25 NAC. Purely additive, but the
  `ssrf_lite_version` const and `$schema` path move to `0.10.0`, so headers must
  be restamped (`make stamp-headers`). Validators pinned to the 0.9.0 schema
  will reject documents carrying it, since channel plan channels are
  `additionalProperties: false`. Lets conventions that are defined by their
  tones or color codes be recorded as plans instead of synthetic systems; see
  §2.6 for precedence against a deployed chain.
- **Station perspective (v0.9.0)**: **breaking.** RF chains and channel plans
  are now written from the perspective of the station being described, matching
  SSRF (§3.1). A repeater's `tx` is its **output** and its `rx` is its
  **input** — the reverse of 0.8.0, which recorded both from the operator
  radio's side. The mode tones moved with them: `ctcss_tx_hz` / `dcs_tx_code`
  are what the station sends, `ctcss_rx_hz` / `dcs_rx_code` what it requires to
  be keyed up. `rx.freq_mhz` is no longer required, and a chain must now set at
  least one of `tx.freq_mhz` / `rx.freq_mhz`. On channel plans `tx_freq_mhz` is
  renamed `rx_freq_mhz` and keeps its value; loading a document that still uses
  `tx_freq_mhz` is an error rather than a silent drop. Run
  `python migrate_0_8_to_0_9.py [ROOT ...]` to convert a tree, including private
  overlays — it verifies that the swap is the only change it made.
- **Multi-emission channels (v0.9.0)**: new optional `emissions[]` on channel
  plans and their channels, for services permitting several incompatible
  modulations on one frequency (US CB allows AM, SSB, and FM on all 40).
  Additive. A plan-level block applies to every channel that does not declare
  its own; `emission` and `emissions` are mutually exclusive on a channel.
- **`verified` (v0.7.0)**: new optional block on `assignments[]`. Purely additive — existing documents remain valid in content, but the `ssrf_lite_version` const and `$schema` path both move to `0.7.0`, so headers must be restamped (`make stamp-headers`). Validators pinned to the 0.6.0 schema will reject documents carrying `verified`, since assignments are `additionalProperties: false`.
- **`verified` on `rf_chains[]` (v0.8.0)**: the same block is now accepted on RF chains, so radio parameters can be confirmed independently of the operational use that references them. Additive; headers move to `0.8.0` and must be restamped. The `monitor` method was also widened to cover **attended** receive-only observation, not just unattended captures — no data change, but the old wording excluded "I heard it on my scanner", which is the most common way a receive-only channel gets confirmed.

- **Legacy fields**: `assignments.zones`, `assignments.codeplug.*`, and `assignments.codeplug.preferred_contacts` are deprecated as of v0.5.0. The loader drops them (and `scan`) on read and maps `comment` → `notes`; see §1.3. New data should omit them.  
- **Profiles** should continue to use path-based include/exclude semantics while adding the ability to pull in explicit assignment IDs as needed.  
- **Policies** may be expressed in YAML/TOML/JSON (format-agnostic) so long as they reference assignments by ID and avoid redefining RF facts.  
