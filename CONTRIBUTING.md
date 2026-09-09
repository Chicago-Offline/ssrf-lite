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
