"""Data hygiene tests for SSRF-Lite content."""

from __future__ import annotations

import pathlib
import sys
import unittest

import yaml


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ssrf.models import pydantic_models

SSRF_DIR = PROJECT_ROOT / "ssrf"

ALLOWED_ASSIGNMENT_KEYS = {
    "id",
    "rf_chain_id",
    "channel_plan_id",
    "channel_name",
    "usage",
    "service",
    "authorization_id",
    "notes",
}

BANNED_POLICY_KEYS = frozenset({"codeplug", "zones", "comment"})


def _load_assignment_blocks(data: object) -> list[list[dict[str, object]]]:
    blocks: list[list[dict[str, object]]] = []
    if isinstance(data, dict):
        assignments = data.get("assignments")
        if isinstance(assignments, list):
            blocks.append(assignments)
        ssrf_lite = data.get("ssrf_lite")
        if isinstance(ssrf_lite, dict):
            nested_assignments = ssrf_lite.get("assignments")
            if isinstance(nested_assignments, list):
                blocks.append(nested_assignments)
    return blocks


def _format_policy_failure(found: dict[str, frozenset[str]]) -> str:
    if not found:
        return "No assignments with embedded policy-layer fields detected."
    lines = ["Assignments still embedding policy-layer fields:"]
    for path, keys in sorted(found.items()):
        lines.append(f" - {path}: {', '.join(sorted(keys))}")
    return "\n".join(lines)


class SSRFPolicyAuditTest(unittest.TestCase):
    def test_assignments_reference_policy_files(self) -> None:
        actual: dict[str, set[str]] = {}

        for subdir in ("plans", "systems"):
            for path in sorted((SSRF_DIR / subdir).rglob("*.yml")):
                with path.open("r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle)

                for block in _load_assignment_blocks(data):
                    for entry in block:
                        if not isinstance(entry, dict):
                            continue
                        extra_keys = (
                            set(entry) - ALLOWED_ASSIGNMENT_KEYS
                        ) & BANNED_POLICY_KEYS
                        if not extra_keys:
                            continue
                        rel_path = path.relative_to(PROJECT_ROOT).as_posix()
                        actual.setdefault(rel_path, set()).update(extra_keys)

        if actual:
            normalized_actual = {key: frozenset(value) for key, value in actual.items()}
            self.fail(_format_policy_failure(normalized_actual))


class SSRFSchemaValidationTest(unittest.TestCase):
    def test_all_documents_validate_against_schema(self) -> None:
        failures: list[tuple[str, str]] = []

        for path in sorted(SSRF_DIR.rglob("*.yml")):
            try:
                pydantic_models.load_ssrf_document(path)
            except Exception as exc:  # pragma: no cover - surfaced via assertion below
                failures.append((path.relative_to(PROJECT_ROOT).as_posix(), str(exc)))

        if failures:
            lines = ["Schema validation failures detected:"]
            for rel_path, message in failures:
                lines.append(f" - {rel_path}: {message}")
            self.fail("\n".join(lines))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
