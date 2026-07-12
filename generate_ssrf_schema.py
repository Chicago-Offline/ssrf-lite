#!/usr/bin/env python3
"""Generate the versioned SSRF-Lite JSON Schema from the Pydantic models.

The Pydantic models in ``ssrf/models/pydantic_models.py`` are the source of
truth for the reference layer. This script serialises them to a standalone
JSON Schema (Draft 2020-12) so that any editor or CI pipeline can validate
SSRF-Lite YAML documents **without importing the Python package**.

Regenerate after changing the models::

    python generate_ssrf_schema.py

Use ``--check`` to fail (non-zero exit) if the committed schema is stale.
"""

from __future__ import annotations

import argparse
import json
import pathlib

from ssrf.models.pydantic_models import SSRFReference

SPEC_VERSION = "0.5.3"

BASE = pathlib.Path(__file__).parent
SCHEMA_DIR = BASE / "ssrf" / "_schema"
SCHEMA_PATH = SCHEMA_DIR / f"ssrf-lite-{SPEC_VERSION}.schema.json"
SCHEMA_ID = (
    "https://raw.githubusercontent.com/emuehlstein/OpenGD77_SSRFLite_Generator/"
    f"main/ssrf/_schema/ssrf-lite-{SPEC_VERSION}.schema.json"
)


def _header_properties() -> dict:
    """Top-level metadata keys allowed alongside the reference entities."""

    return {
        "$schema": {
            "type": "string",
            "description": "Path or URI of the JSON Schema used to validate this document.",
        },
        "ssrf_lite_version": {
            "type": "string",
            "const": SPEC_VERSION,
            "description": "SSRF-Lite specification version this file targets.",
        },
        "ssrf_lite": {
            "type": "object",
            "description": "Optional non-normative provenance/metadata block.",
            "properties": {
                "version": {"type": "string"},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "url": {"type": ["string", "null"]},
                            "accessed": {"type": ["string", "null"]},
                        },
                        "additionalProperties": True,
                    },
                },
            },
            "additionalProperties": True,
        },
        "comments": {
            "type": "array",
            "description": "Optional non-normative freeform notes about the document.",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "additionalProperties": True,
            },
        },
    }


def build_schema() -> dict:
    """Return the full JSON Schema document for SSRF-Lite files."""

    model_schema = SSRFReference.model_json_schema(
        by_alias=True, ref_template="#/$defs/{model}"
    )
    defs = model_schema.pop("$defs", {})
    entity_properties = model_schema.get("properties", {})

    schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "SSRF-Lite Reference Document",
        "description": (
            "Schema for SSRF-Lite YAML reference documents "
            f"(specification v{SPEC_VERSION}). Generated from the Pydantic "
            "models in ssrf/models/pydantic_models.py. See "
            "ssrf/_schema/SSRF-Lite-Spec.md for prose documentation."
        ),
        "type": "object",
        "additionalProperties": False,
        "properties": {**_header_properties(), **entity_properties},
        "$defs": defs,
    }
    return schema


def render(schema: dict) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed schema differs from the generated one.",
    )
    args = parser.parse_args()

    schema = build_schema()
    content = render(schema)

    if args.check:
        if not SCHEMA_PATH.exists():
            print(f"❌ Schema missing: {SCHEMA_PATH}")
            return 1
        current = SCHEMA_PATH.read_text(encoding="utf-8")
        if current != content:
            print(
                f"❌ {SCHEMA_PATH.relative_to(BASE)} is out of date. "
                "Run 'python generate_ssrf_schema.py'."
            )
            return 1
        print(f"✅ {SCHEMA_PATH.relative_to(BASE)} is up to date.")
        return 0

    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(content, encoding="utf-8")
    print(f"✅ Wrote {SCHEMA_PATH.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
