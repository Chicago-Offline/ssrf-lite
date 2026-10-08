"""Ship-the-schema guardrails.

These tests keep the committed JSON Schema, the stamped YAML headers, and the
Pydantic source of truth in lock-step, and confirm every SSRF-Lite document
validates against the shipped schema exactly as an external editor or CI tool
would (without importing the Pydantic models).
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

import yaml

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import generate_ssrf_schema
import stamp_ssrf_headers

SSRF_DIR = PROJECT_ROOT / "ssrf"
SCHEMA_PATH = (
    SSRF_DIR / "_schema" / f"ssrf-lite-{generate_ssrf_schema.SPEC_VERSION}.schema.json"
)

try:
    from jsonschema import Draft202012Validator

    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - exercised only without the dev extra
    HAS_JSONSCHEMA = False


def _reference_yaml_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for subdir in ("systems", "plans"):
        files.extend((SSRF_DIR / subdir).rglob("*.yml"))
    return sorted(files)


class SchemaFreshnessTest(unittest.TestCase):
    def test_committed_schema_matches_models(self) -> None:
        expected = generate_ssrf_schema.render(generate_ssrf_schema.build_schema())
        actual = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            actual,
            expected,
            "ssrf-lite JSON Schema is stale. Run 'python generate_ssrf_schema.py'.",
        )

    def test_dcs_polarity_is_constrained_and_defaults_to_normal(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        mode_properties = schema["$defs"]["Mode"]["properties"]

        for field in ("dcs_tx_polarity", "dcs_rx_polarity"):
            self.assertEqual(mode_properties[field]["enum"], ["N", "I"])
            self.assertEqual(mode_properties[field]["default"], "N")


class HeaderStampTest(unittest.TestCase):
    def test_all_files_have_up_to_date_headers(self) -> None:
        stale: list[str] = []
        for path in _reference_yaml_files():
            original = path.read_text(encoding="utf-8")
            updated = stamp_ssrf_headers.transform(
                original, stamp_ssrf_headers._relative_schema_path(path)
            )
            if updated != original:
                stale.append(path.relative_to(PROJECT_ROOT).as_posix())
        self.assertEqual(
            stale,
            [],
            "Files missing up-to-date schema headers. Run 'python stamp_ssrf_headers.py'.",
        )


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not installed")
class JsonSchemaValidationTest(unittest.TestCase):
    def test_all_documents_validate_against_shipped_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        failures: list[str] = []
        for path in _reference_yaml_files():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
            for error in errors:
                location = "/".join(str(part) for part in error.path) or "<root>"
                rel = path.relative_to(PROJECT_ROOT).as_posix()
                failures.append(f"{rel}: {location}: {error.message}")

        if failures:
            self.fail("JSON Schema validation failures:\n" + "\n".join(failures))

    def test_override_blocks_validate_against_shipped_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        valid = {
            "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
            "overrides": {
                "assignments": [
                    {
                        "id": "asg_example",
                        "patch": {"channel_name": "LOCAL NAME"},
                    }
                ]
            },
        }
        self.assertEqual(list(validator.iter_errors(valid)), [])

        missing_patch = {
            "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
            "overrides": {"assignments": [{"id": "asg_example"}]},
        }
        self.assertTrue(list(validator.iter_errors(missing_patch)))

        unknown_collection = {
            "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
            "overrides": {"unknown_entities": []},
        }
        self.assertTrue(list(validator.iter_errors(unknown_collection)))

    def test_verified_block_validates_against_shipped_schema(self) -> None:
        """Freshness markers (v0.8.0) are optional but strictly shaped."""

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        def _doc(verified: object) -> dict:
            return {
                "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
                "assignments": [
                    {"id": "asgn_example", "usage": "repeater", "verified": verified}
                ],
            }

        # A full block and the minimal required pair both validate.
        full = {
            "date": "2026-09-27",
            "method": "on-air",
            "by": "WRXC682",
            "note": "Checked into the Sunday net.",
        }
        self.assertEqual(list(validator.iter_errors(_doc(full))), [])
        self.assertEqual(
            list(validator.iter_errors(_doc({"date": "2026-09-27", "method": "published"}))),
            [],
        )

        # Absence is legal: "never verified" is a valid state.
        self.assertEqual(
            list(
                validator.iter_errors(
                    {
                        "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
                        "assignments": [{"id": "asgn_example", "usage": "repeater"}],
                    }
                )
            ),
            [],
        )

        # date and method are both required when the block is present.
        self.assertTrue(list(validator.iter_errors(_doc({"method": "on-air"}))))
        self.assertTrue(list(validator.iter_errors(_doc({"date": "2026-09-27"}))))

        # Malformed dates are rejected rather than silently stored.
        for bad_date in ("2026-9-27", "27-09-2026", "September 27 2026", ""):
            self.assertTrue(
                list(validator.iter_errors(_doc({"date": bad_date, "method": "on-air"}))),
                f"expected date {bad_date!r} to be rejected",
            )

        # Unknown methods and stray keys are rejected.
        self.assertTrue(
            list(validator.iter_errors(_doc({"date": "2026-09-27", "method": "vibes"})))
        )
        self.assertTrue(
            list(
                validator.iter_errors(
                    _doc({"date": "2026-09-27", "method": "on-air", "confirms": "x"})
                )
            )
        )

    def test_verified_block_accepted_on_rf_chains(self) -> None:
        """v0.8.0: chains carry freshness independently of assignments."""

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        def _chain(extra: dict) -> dict:
            chain = {
                "id": "ch_example",
                "station_id": "stn_example",
                "rx": {"freq_mhz": 453.775},
                "tx": {"emission": "11K2F3E"},
                "mode": {"type": "FM"},
            }
            chain.update(extra)
            return {
                "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
                "rf_chains": [chain],
            }

        # Present and absent both validate.
        self.assertEqual(
            list(
                validator.iter_errors(
                    _chain(
                        {
                            "verified": {
                                "date": "2026-09-27",
                                "method": "monitor",
                                "by": "WRXC682",
                            }
                        }
                    )
                )
            ),
            [],
        )
        self.assertEqual(list(validator.iter_errors(_chain({}))), [])

        # Same strictness as on assignments: required pair, date shape,
        # closed method enum, no stray keys.
        for bad in (
            {"method": "monitor"},
            {"date": "2026-09-27"},
            {"date": "9/27/26", "method": "monitor"},
            {"date": "2026-09-27", "method": "rumour"},
            {"date": "2026-09-27", "method": "monitor", "extra": 1},
        ):
            self.assertTrue(
                list(validator.iter_errors(_chain({"verified": bad}))),
                f"expected chain verified={bad!r} to be rejected",
            )

        # Chain and assignment freshness are independent, not mirrored:
        # a freshly heard chain may hang off a stale assignment claim.
        both = {
            "ssrf_lite_version": generate_ssrf_schema.SPEC_VERSION,
            "rf_chains": [
                {
                    "id": "ch_example",
                    "station_id": "stn_example",
                    "rx": {"freq_mhz": 453.775},
                    "tx": {"emission": "11K2F3E"},
                    "mode": {"type": "FM"},
                    "verified": {"date": "2026-09-27", "method": "monitor"},
                }
            ],
            "assignments": [
                {
                    "id": "asg_example",
                    "usage": "repeater",
                    "rf_chain_id": "ch_example",
                    "verified": {"date": "2024-01-15", "method": "published"},
                }
            ],
        }
        self.assertEqual(list(validator.iter_errors(both)), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
