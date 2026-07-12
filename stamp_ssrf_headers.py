#!/usr/bin/env python3
"""Stamp SSRF-Lite YAML files with schema-association headers.

Adds (idempotently) to every reference document under ``ssrf/systems`` and
``ssrf/plans``:

1. A ``# yaml-language-server: $schema=...`` modeline so editors (e.g. the
   Red Hat YAML extension) validate the file live.
2. A top-level ``$schema`` key pointing at the versioned JSON Schema, for CI
   tools that read the ``$schema`` property.
3. A top-level ``ssrf_lite_version: "0.5.3"`` key.

It also removes the now-redundant nested ``ssrf_lite.version`` key, leaving the
top-level ``ssrf_lite_version`` as the single source of truth. Provenance in the
``ssrf_lite.sources`` block is preserved.

Re-running the script is safe (idempotent). Use ``--check`` to fail if any file
would change.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re

SPEC_VERSION = "0.5.3"

BASE = pathlib.Path(__file__).parent
SSRF_ROOT = BASE / "ssrf"
SCHEMA_PATH = SSRF_ROOT / "_schema" / f"ssrf-lite-{SPEC_VERSION}.schema.json"

MODELINE_RE = re.compile(r"^#\s*yaml-language-server:\s*\$schema=")
TOP_SCHEMA_RE = re.compile(r"^\$schema\s*:")
TOP_VERSION_RE = re.compile(r"^ssrf_lite_version\s*:")
TOP_KEY_RE = re.compile(r"""^(["']?)([A-Za-z0-9_$-]+)\1\s*:""")
NESTED_VERSION_RE = re.compile(r"^\s+version\s*:")


def _relative_schema_path(yml_path: pathlib.Path) -> str:
    return os.path.relpath(SCHEMA_PATH, yml_path.parent)


def _strip_managed_lines(lines: list[str]) -> list[str]:
    """Remove previously-stamped headers and the redundant nested version."""

    cleaned: list[str] = []
    current_top_key: str | None = None

    for line in lines:
        top_match = TOP_KEY_RE.match(line)
        if top_match:
            current_top_key = top_match.group(2)

        if MODELINE_RE.match(line):
            continue
        if TOP_SCHEMA_RE.match(line):
            continue
        if TOP_VERSION_RE.match(line):
            continue
        if current_top_key == "ssrf_lite" and NESTED_VERSION_RE.match(line):
            continue

        cleaned.append(line)

    return cleaned


def _first_top_key_index(lines: list[str]) -> int:
    for idx, line in enumerate(lines):
        if TOP_KEY_RE.match(line):
            return idx
    return len(lines)


def transform(text: str, rel_schema: str) -> str:
    lines = text.split("\n")
    trailing_newline = text.endswith("\n")
    if trailing_newline:
        lines = lines[:-1]

    lines = _strip_managed_lines(lines)

    insert_at = _first_top_key_index(lines)
    header_keys = [
        f'$schema: "{rel_schema}"',
        f'ssrf_lite_version: "{SPEC_VERSION}"',
    ]
    lines[insert_at:insert_at] = header_keys

    modeline = f"# yaml-language-server: $schema={rel_schema}"
    lines.insert(0, modeline)

    result = "\n".join(lines)
    if trailing_newline:
        result += "\n"
    return result


def iter_yaml_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for subdir in ("systems", "plans"):
        files.extend((SSRF_ROOT / subdir).rglob("*.yml"))
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any file would change; do not write.",
    )
    args = parser.parse_args()

    changed: list[pathlib.Path] = []
    for path in iter_yaml_files():
        original = path.read_text(encoding="utf-8")
        updated = transform(original, _relative_schema_path(path))
        if updated != original:
            changed.append(path)
            if not args.check:
                path.write_text(updated, encoding="utf-8")

    if args.check:
        if changed:
            print("❌ The following files are missing up-to-date schema headers:")
            for path in changed:
                print(f"   - {path.relative_to(BASE)}")
            print("Run 'python stamp_ssrf_headers.py' to fix.")
            return 1
        print("✅ All SSRF-Lite files have up-to-date schema headers.")
        return 0

    if changed:
        print(f"✅ Stamped {len(changed)} file(s):")
        for path in changed:
            print(f"   - {path.relative_to(BASE)}")
    else:
        print("✅ All SSRF-Lite files already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
