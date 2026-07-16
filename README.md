# SSRF-Lite

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

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
