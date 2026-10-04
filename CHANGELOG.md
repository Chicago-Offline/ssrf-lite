# Changelog

All notable changes to the SSRF-Lite **specification and data model** are
recorded here. The version is the `ssrf_lite_version` every data file carries
and the `SPEC_VERSION` in `generate_ssrf_schema.py`; the Python package tracks
it. Data additions (new systems, plans, corrections) are not listed — see the
git log for those.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries marked **breaking** change the meaning or validity of existing
documents; everything else is additive and only requires restamping headers
(`make stamp-headers`).

## [Unreleased]

## [0.10.1] - 2026-10-03

Package-only release; the specification stays at 0.10.0 and data files keep
their `ssrf_lite_version: "0.10.0"` headers.

### Fixed
- `plans/US/amateur/ham_dmr_simplex.yml`: the plan-level `mode` now declares
  `timeslots: [1, 2]` as its header already claimed, so DMR simplex channels
  can be built by consumers that refuse to invent a slot. (#50)

## [0.10.0] - 2026-10-01

### Added
- `mode` on channel-plan channels and on the plan itself — the same `Mode`
  object an `rf_chain` carries, so regulator-defined tones (NIFOG 156.7 Hz,
  GMRS travel 141.3 Hz) and shared DMR colour codes are structured data
  instead of free text. Plan-level `mode` is a default for channels that
  declare none. A plan `mode` is the regulatory/conventional default; a
  system's `rf_chain` is authoritative for an actual deployment. (#45, #47)
- `codeplug.json` emits `ctcss` / `dcs` / `dcs_polarity` / `color_code` /
  `timeslots` for plan channels.
- `ssrf/modes.py` — shared human-readable `Mode` summary for the generators.

### Changed
- **breaking** for pre-0.5.0 documents: the loader no longer silently drops
  the policy-era assignment keys `codeplug`, `zones`, `scan`, nor remaps
  `comment` → `notes`, and no longer whitelists channel-plan channel keys.
  Every unknown key on every entity is an error. (#47)

### Data
- NIFOG 2.02 federal and non-federal interoperability plans, with tones as
  structured `mode` data. (#46)
- `ham_dmr_simplex.yml` rebuilt as a real channel plan instead of a stand-in
  station with 14 `rf_chains`. (#48)

## [0.9.0] - 2026-09-29

### Changed
- **breaking**: station perspective. RF chains and channel plans are written
  from the station being described, matching NTIA SSRF. A repeater's `tx` is
  its output and `rx` its input — the reverse of 0.8.0. `ctcss_tx_hz` /
  `dcs_tx_code` are what the station sends; `ctcss_rx_hz` / `dcs_rx_code`
  what keys it. `rx.freq_mhz` is optional; a chain must set at least one of
  `tx.freq_mhz` / `rx.freq_mhz`. Channel-plan `tx_freq_mhz` is renamed
  `rx_freq_mhz` (value unchanged) and the old key is a load error.
  `migrate_0_8_to_0_9.py` converts a tree, including private overlays. (#43)
- `codeplug.json` is the radio-centric mirror (`rx_mhz` = station `tx`).

### Added
- `emissions[]` on channel-plan channels and plans for services permitting
  several modulations on one frequency (US CB: AM, SSB, FM), with per-emission
  `mode`, `bandwidth_khz`, `power_w`. `emission` and `emissions` are mutually
  exclusive on a channel. (#40, #43)
- `short_name` (≤ 6 uppercase characters) on assignments and plan channels for
  radios with narrow displays; `codeplug.json` falls back to a deterministic
  abbreviation. (#44)
- `cb` service and the US CB channel plan. (#39)

## [0.8.0] - 2026-09-27

### Added
- `verified` accepted on `rf_chains[]`, so radio parameters can be confirmed
  independently of the assignment that uses them. (#36)

### Changed
- `verified.method: monitor` widened to cover attended receive-only
  observation ("heard it on my scanner"), not only unattended captures.

## [0.7.0] - 2026-09-27

### Added
- `verified` freshness block on `assignments[]`: `date`, `method`
  (`on-air` / `monitor` / `licensee` / `published` / `survey`), `by`, `note`.
  (#35)

## [0.6.0] - 2026-09-17

### Changed
- **breaking**: `dcs_tx_code` / `dcs_rx_code` are a closed set of the 104
  standard three-digit octal codes (`ssrf/_taxonomies/dcs_codes.yaml`),
  written as quoted strings. Integers are rejected — DCS is octal and YAML 1.1
  reads an unquoted leading zero as octal, so `032` silently loaded as 26.
  (#16)
- `dcs_tx_polarity` / `dcs_rx_polarity` (`N` | `I`) added alongside. (#7)

## [0.5.3] - 2026-07-11

### Added
- Versioned JSON Schema (Draft 2020-12) generated from the Pydantic models,
  with `# yaml-language-server:` modeline, `$schema`, and `ssrf_lite_version`
  headers on every file; `make schema` / `make stamp-headers` /
  `make validate-schema`.
- Private overlay roots: extra roots add entities or patch existing ones via a
  top-level `overrides` block; `_root.yml` declares load precedence.

## [0.5.0] - 2025-10

### Changed
- Policy-layer fields (`codeplug.*`, `zones`, `scan`) removed from the
  reference model and moved to downstream policy documents; `comment`
  renamed `notes`. Deprecated keys were dropped on read until 0.10.0.

[Unreleased]: https://github.com/Chicago-Offline/ssrf-lite/compare/v0.10.1...HEAD
[0.10.1]: https://github.com/Chicago-Offline/ssrf-lite/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/Chicago-Offline/ssrf-lite/compare/85d3a07...v0.10.0
[0.9.0]: https://github.com/Chicago-Offline/ssrf-lite/compare/88360f8...85d3a07
[0.8.0]: https://github.com/Chicago-Offline/ssrf-lite/compare/a814212...88360f8
[0.7.0]: https://github.com/Chicago-Offline/ssrf-lite/compare/a0fb971...a814212
[0.6.0]: https://github.com/Chicago-Offline/ssrf-lite/compare/2f9be5a...a0fb971
[0.5.3]: https://github.com/Chicago-Offline/ssrf-lite/commit/2f9be5a
[0.5.0]: https://github.com/Chicago-Offline/ssrf-lite/commit/b6b35dc
