# Contributing to SSRF-Lite

Thanks for helping grow the reference library! Contributions of new RF systems,
channel plans, and corrections to existing data are all welcome.

**Don't want to write YAML?** Open a
[Submit a system](../../issues/new?template=submit_system.yml) issue with the
system details and sources, and a maintainer will draft the file.

## What belongs here

SSRF-Lite is a **reference layer**: authoritative RF facts — who owns a system,
where it lives, how it transmits, what authorizations exist. Consumer opinions
(zones, scan lists, transmit enablement, channel ordering) belong in downstream
policy layers, not in this repo. See the
[SSRF-Lite spec](ssrf/_schema/SSRF-Lite-Spec.md) for the data model.

Every entry must be verifiable from a cited source. Data without provenance
will not be merged.

## Repo layout

| Path | Contents |
| --- | --- |
| `ssrf/systems/<CC>/<State>/<County>/<City>/<service>/` | RF systems by geography (e.g. `US/IL/Cook/Chicago/amateur/`) |
| `ssrf/systems/<CC>/<State>/_Statewide/` | Systems spanning a whole state or crossing borders |
| `ssrf/plans/` | Reusable channel plans (GMRS, MURS, marine, band plans, ...) |
| `ssrf/_taxonomies/services.yaml` | Allowed `service` ids |

## Adding or updating a system

1. **Start from a similar file.** For a single analog repeater,
   [kc8brs_four_flags.yml](ssrf/systems/US/MI/Berrien/Niles/amateur/kc8brs_four_flags.yml)
   is a good minimal template.
2. **Place it by geography and service** following the layout above.
3. **Cite your sources.** Every file needs a `ssrf_lite.sources` block with
   `name`, `url`, and the `accessed` date you verified the data:

   ```yaml
   ssrf_lite:
     sources:
       - name: "Club repeater page"
         url: "https://example.org/repeaters"
         accessed: "2026-09-08"
   ```

4. **Use stable, prefixed snake_case ids** (`org_`, `loc_`, `stn_`, `ant_`,
   `chain_`, `auth_`, `asgn_`) that are unique within the file. Ids are patch
   targets for private overlays, so avoid renaming existing ones.
5. **Use a `service` id from the taxonomy**
   ([services.yaml](ssrf/_taxonomies/services.yaml)) on stations, plans, or
   assignments.
6. **Stamp the schema headers** so editors and CI can validate the file:

   ```bash
   make stamp-headers
   ```

7. **Regenerate the docs** (generated markdown in `docs/ssrf/` is committed):

   ```bash
   make docs
   ```

## Validating your change

```bash
make install          # once: sync dependencies with uv
make validate-schema  # schema + header freshness
make test             # full suite, including semantic data checks
```

### Whose station is this? (tx/rx perspective)

**Every record is written from the perspective of the station it describes.**
`tx` is what that station *transmits*; `rx` is what that station *receives*.

For a repeater that means `tx` is the output you listen to, and `rx` is the
input you key up on:

```yaml
tx:
  freq_mhz: 462.550   # repeater output
rx:
  freq_mhz: 467.550   # repeater input
mode:
  ctcss_tx_hz: 141.3  # tone the repeater sends on its output
  ctcss_rx_hz: 225.7  # tone the repeater requires on its input
```

The same rule covers the other cases:

- **Simplex** — set `tx.freq_mhz` and omit `rx.freq_mhz`.
- **Monitored only** — if you have logged a station's output but never
  confirmed its input, set `tx.freq_mhz` and leave `rx.freq_mhz` unset rather
  than guessing a standard offset.
- **Receive-only sites** (voting receivers, remote RX) — set `rx.freq_mhz`
  and omit `tx.freq_mhz`.

A chain must carry at least one of the two.

Consumers that build codeplugs mirror this for you: `codeplug.json` reports
`rx_mhz` as what the *operator's radio* listens to and `tx_mhz` as what it
transmits. Don't pre-mirror the reference data by hand.

### Channels permitting more than one emission

Where a service allows several incompatible modulations on one frequency —
US CB runs AM, SSB, and FM on all 40 channels — list them under `emissions`
rather than the single `emission` key, most typical first. If the rule covers
the whole plan, declare it once on the plan and every channel inherits it:

```yaml
channel_plans:
  - id: chplan_us_cb
    emissions:
      - emission: "8K00A3E"
        mode: "AM"
        bandwidth_khz: 8
        power_w: 4
      - emission: "4K00J3E"
        mode: "USB"   # J3E alone can't distinguish USB from LSB
        bandwidth_khz: 4
        power_w: 12
    channels:
      - name: "CB 01"
        freq_mhz: 26.9650
```

Setting both `emission` and `emissions` on one channel is an error.

### Channels whose definition includes a tone or colour code

Some plan channels have squelch or digital parameters baked into the rule
that creates them — NIFOG channels are 156.7 Hz nationwide, the GMRS travel
convention is 141.3 Hz, a club's shared DMR simplex plan has a fixed colour
code. Put those in a `mode` block on the channel (or once on the plan as the
default), not in `notes`, so codeplug generators can see them. It is the same
`mode` an `rf_chain` carries, written from the channel's transmitting
station: `ctcss_tx_hz` is what it sends, `ctcss_rx_hz` what keys it.

```yaml
channel_plans:
  - id: chplan_nifog_nonfederal
    mode: { type: "FM", ctcss_tx_hz: 156.7, ctcss_rx_hz: 156.7 }
    channels:
      - name: "VCALL10"
        freq_mhz: 155.7525
        emission: "11K0F3E"
      - name: "VTAC36"
        freq_mhz: 151.1375
        rx_freq_mhz: 159.4725
        emission: "11K0F3E"
        mode: { type: "FM", ctcss_tx_hz: 156.7, ctcss_rx_hz: 136.5 }
```

Do **not** model a nationally defined channel+tone as a bespoke system with
`rf_chains` just to carry the tone. Systems describe actual deployments; where
one exists on a plan frequency, the system's `rf_chain` is authoritative for
that deployment and the plan `mode` is the regulatory default.

The test suite validates every YAML file against the schema **and** runs
semantic checks: frequencies must sit inside the declared service's
allocation, CTCSS/DCS values must be standard, repeater splits must be
conventional for the band, and coordinates must fall inside the file's
region. If a check fails on data you know is correct (e.g. a genuinely
unusual repeater split), say so in the PR and we'll extend the check.

## Pull requests

- Fork, branch, and open a PR against `main`.
- CI must pass (the `test` check is required to merge).
- Keep PRs focused: one system or one logical change per PR.
- Corrections are as valuable as additions — if a repeater went off the air
  or changed tones, a PR updating the file (and its `accessed` date) is the
  ideal fix.
