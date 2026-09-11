# SSRF-Lite

**🌐 [Browse the data online](https://chicago-offline.github.io/ssrf-lite/)**

A simplified, YAML-based format for sharing information about RF systems, inspired by the
[NTIA Standard Spectrum Resource Format (SSRF)](https://www.ntia.gov/publications/2023/standard-spectrum-resource-format-ssrf).

SSRF-Lite captures authoritative RF facts — who owns a system, where it lives, how it
transmits, and what authorizations exist — independent of any particular radio,
programming tool, or presentation layer. The same reference data can feed codeplug
generators (OpenGD77, CHIRP, dmrconfig, qdmr, OEM CPS), monitoring tools, and
documentation pipelines.

## What's in this repo

| Path | Contents |
| --- | --- |
| [ssrf/_schema/SSRF-Lite-Spec.md](ssrf/_schema/SSRF-Lite-Spec.md) | The SSRF-Lite specification |
| [ssrf/_schema/](ssrf/_schema/) | Versioned JSON Schema (Draft 2020-12) for editor/CI validation without Python |
| [ssrf/models/](ssrf/models/) | Pydantic models — the source of truth for the schema |
| [ssrf/systems/](ssrf/systems/) | Reference data library: RF systems by geography |
| [ssrf/plans/](ssrf/plans/) | Channel plans (GMRS, MURS, marine VHF, amateur band plans, ...) |
| [ssrf/talkgroups/](ssrf/talkgroups/) | DMR talkgroup references |
| [ssrf/_taxonomies/](ssrf/_taxonomies/) | Controlled vocabularies (services, ...) |
| [docs/ssrf/](docs/ssrf/) | Generated documentation for the data library |
| [site/](site/) | Static web browser for the data library (GitHub Pages) |

## Browse the data

A searchable web frontend (channel table, map of repeater sites, and file index) is
published via GitHub Pages from [site/](site/). Run it locally with:

```bash
make serve-site   # builds site/data.json and serves http://localhost:8000
```

The site build also emits `site/sitemap.xml` and `site/robots.txt` for search
engines. After GitHub Pages deploys, submit
`https://chicago-offline.github.io/ssrf-lite/sitemap.xml` in Google Search Console
for faster discovery.

## Compiled data feed

For downstream consumers (e.g. codeplug generators like NeonPlug), the repo
publishes a compiled, browser-ready `site/codeplug.json` — a single flat array of
radio-centric channel records with the relational data already joined. A client
can simply fetch it and filter by distance; no schema knowledge required.

```bash
make codeplug   # writes site/codeplug.json
```

Each record has the shape:

```json
{
  "callsign": "W9CR",   // station call sign, or null
  "rx_mhz": 449.75,      // frequency the radio receives on (repeater output)
  "tx_mhz": 444.75,      // frequency the radio transmits on (repeater input)
  "ctcss": 146.2,        // CTCSS tone to encode (Hz), or null
  "dcs": "023",          // DCS code to encode, or null
  "dcs_polarity": "N",   // DCS polarity (N or I), or null
  "color_code": 1,        // DMR color code, or null
  "timeslots": [1, 2],    // DMR timeslots, or null
  "lat": 27.983104,       // site latitude, or null
  "lon": -82.490542,      // site longitude, or null
  "service": "amateur",  // SSRF service taxonomy id, or null
  "mode": "FM",          // modulation/mode, or null
  "bandwidth_khz": 16.0,  // channel bandwidth (kHz), or null
  "name": "tarc uhf1"    // human-readable channel name
}
```

Frequencies are radio-centric (`rx_mhz`/`tx_mhz` are what the operator's radio
listens to and transmits on); for simplex channels the two are equal. CTCSS/DCS
values are the tones the radio must encode to key the far end.

## Private SSRF overlays

Recommended mechanism: keep private or local-only SSRF-Lite data in a separate
private GitHub repository that mirrors the public `ssrf/` layout, then pass that
repository's `ssrf/` directory as an extra root when building local outputs.

Example private repo layout:

```text
my-ssrf-private/
  ssrf/
    plans/
      US/custom/family_channels.yml
    systems/
      custom/home_hotspot.yml
      US/IL/Cook/Chicago/gmrs/my_repeaters.yml
```

Build an official-plus-private feed without copying private YAML into this
repo. Both the flat codeplug feed and the site `data.json` accept
`--extra-ssrf-root` (repeatable):

```bash
# Flat codeplug.json (rx_mhz/tx_mhz/ctcss shape)
uv run python generate_ssrf_codeplug.py \
  --extra-ssrf-root ../my-ssrf-private/ssrf \
  --output site/codeplug.local.json

# Site data.json (freq_mhz/mode_detail shape — e.g. for NeonPlug's
# "Local file (private)" import source)
uv run python generate_ssrf_site.py \
  --extra-ssrf-root ../my-ssrf-private/ssrf \
  --output site/data.local.json
```

For consumers, treat every root as ordinary SSRF-Lite. The public repo remains
the authoritative reference library; private repos should contain personal
overlays such as family channels, home repeaters, hotspots, travel lists, or
locally licensed systems that should not be published. Extra roots can add
entities with unique IDs or explicitly patch fields on an existing entity.

Field patches live in a top-level `overrides` mapping and select entities by
collection and stable ID:

```yaml
ssrf_lite_version: "0.5.3"
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

By default, roots are processed in command-line order, with later roots
taking precedence — but relying on argv order is fragile once more than one
overlay can patch the same entity, since nothing in the data itself records
which root should win. A root can instead declare its own precedence
explicitly with a top-level `_root.yml` file (the leading underscore keeps it
out of `_iter_yaml_files`'s data scan):

```yaml
# my-ssrf-private/ssrf/_root.yml
ssrf_root:
  id: "my_private_overlay"
  precedence: 100   # higher precedence wins on conflict; loads later
```

When present, `precedence` (an integer) determines load order regardless of
argv position — the root with the highest declared precedence is loaded last
and wins any field-patch conflict. Roots that don't declare a precedence keep
falling back to their command-line position, so existing single-overlay setups
need no changes. Two roots declaring the *same* precedence value is a hard
error rather than a silent argv-order tiebreak. Mixing declared and undeclared
roots works, but is only unambiguous if you keep declared values well clear of
the undeclared roots' positional indices (0, 1, 2, ...) — when in doubt,
declare a precedence on every root you pass.

Mappings merge recursively, lists replace, and `null` explicitly clears an
optional value. Entity IDs are immutable. Unknown or ambiguous targets fail
resolution, as do patches that produce an invalid SSRF entity. Prefer unique
file names and IDs in private additions so downstream generators can
distinguish official and personal records cleanly.

## Installation

```bash
pip install "ssrf-lite @ git+https://github.com/Chicago-Offline/ssrf-lite"
```

Or with `uv`:

```bash
uv add "ssrf-lite @ git+https://github.com/Chicago-Offline/ssrf-lite"
```

## Usage

```python
from ssrf import load_ssrf_document, SSRFReference

doc = load_ssrf_document("ssrf/systems/US/IL/Cook/Chicago/amateur/ns9rc.yml")
for assignment in doc.assignments:
    print(assignment.channel_name, assignment.service)
```

## Validation

Every SSRF-Lite file targets a versioned JSON Schema shipped alongside the spec. Each
YAML carries a `# yaml-language-server:` modeline plus top-level `$schema` and
`ssrf_lite_version` keys, so editors and CI can validate without importing the Python
models.

```bash
make schema          # regenerate the JSON Schema from the Pydantic models
make stamp-headers   # (re)apply schema headers to every SSRF-Lite YAML
make validate-schema # verify the schema and headers are up to date (CI)
make test            # run data hygiene and schema tests
```

## Consumers

- [OpenGD77 SSRFLite Generator](https://github.com/emuehlstein/OpenGD77_SSRFLite_Generator) —
  codeplug builder producing OpenGD77, CHIRP, and VGC N76 CSVs from SSRF-Lite data.

## Contributing

New systems, channel plans, and corrections are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md). No YAML required: you can also
[submit a system as an issue](https://github.com/Chicago-Offline/ssrf-lite/issues/new?template=submit_system.yml)
and a maintainer will draft the file.

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
