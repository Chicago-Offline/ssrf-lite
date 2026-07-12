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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
