"""Resolve additive SSRF roots and explicit field-level entity patches."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple, Union

import yaml

from .models.pydantic_models import SSRFReference, validate_data


ENTITY_COLLECTIONS: Tuple[str, ...] = (
    "organizations",
    "locations",
    "stations",
    "antennas",
    "rf_chains",
    "channel_plans",
    "authorizations",
    "contacts",
    "assignments",
)


@dataclass(frozen=True)
class ResolvedSSRFDocument:
    """A validated additive document after all overlay patches are applied."""

    root: Path
    path: Path
    reference: SSRFReference
    is_overlay: bool


def _iter_yaml_files(root: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in root.rglob("*.yml")
        if not path.name.startswith("_") and "_schema" not in path.parts
    )


def _load_mapping(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise TypeError(f"{path}: SSRF documents must be mappings at the top level")
    return raw


def _entity_payload(raw: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        collection: deepcopy(raw[collection])
        for collection in ENTITY_COLLECTIONS
        if collection in raw
    }


def _merge_patch(target: Dict[str, Any], patch: Mapping[str, Any]) -> None:
    for key, value in patch.items():
        if key == "id":
            raise ValueError("entity IDs are immutable in SSRF overrides")
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _merge_patch(current, value)
        else:
            target[key] = deepcopy(value)


def resolve_ssrf_roots(
    roots: Sequence[Union[str, Path]],
) -> List[ResolvedSSRFDocument]:
    """Load roots in precedence order and apply explicit entity field patches.

    Additive entities are indexed by collection and stable ID. An ``overrides``
    block selects an existing entity with ``id`` and recursively merges its
    ``patch`` mapping. Lists replace, ``null`` clears optional values, IDs are
    immutable, and unknown targets fail.
    """

    resolved_roots = [Path(root) for root in roots]
    if not resolved_roots:
        return []

    documents: List[Tuple[Path, Path, Dict[str, Any], bool]] = []
    index: Dict[Tuple[str, str], List[Tuple[Dict[str, Any], Path, int]]] = {}

    for root_index, root in enumerate(resolved_roots):
        for path in _iter_yaml_files(root):
            raw = _load_mapping(path)
            payload = _entity_payload(raw)

            for collection, entities in payload.items():
                if not isinstance(entities, list):
                    raise TypeError(f"{path}: '{collection}' must be a list")
                for entity in entities:
                    if not isinstance(entity, dict) or not isinstance(entity.get("id"), str):
                        raise ValueError(f"{path}: every '{collection}' entity needs an ID")
                    key = (collection, entity["id"])
                    index.setdefault(key, []).append((entity, path, root_index))

            if payload:
                documents.append((root, path, payload, root_index > 0))

            overrides = raw.get("overrides", {})
            if overrides is None:
                overrides = {}
            if not isinstance(overrides, dict):
                raise TypeError(f"{path}: 'overrides' must be a mapping")
            unknown_collections = set(overrides) - set(ENTITY_COLLECTIONS)
            if unknown_collections:
                names = ", ".join(sorted(unknown_collections))
                raise ValueError(f"{path}: unknown override collections: {names}")

            for collection, entries in overrides.items():
                if not isinstance(entries, list):
                    raise TypeError(f"{path}: override collection '{collection}' must be a list")
                for entry in entries:
                    if not isinstance(entry, dict):
                        raise TypeError(f"{path}: override entries must be mappings")
                    entity_id = entry.get("id")
                    patch = entry.get("patch")
                    if not isinstance(entity_id, str) or not isinstance(patch, dict):
                        raise ValueError(
                            f"{path}: overrides require string 'id' and mapping 'patch'"
                        )
                    targets = [
                        target
                        for target in index.get((collection, entity_id), [])
                        if target[2] < root_index
                    ]
                    if not targets:
                        raise ValueError(
                            f"{path}: unknown {collection} override target '{entity_id}'"
                        )
                    if len(targets) > 1:
                        target_paths = ", ".join(str(target[1]) for target in targets)
                        raise ValueError(
                            f"{path}: ambiguous {collection} override target "
                            f"'{entity_id}' found in: {target_paths}"
                        )
                    _merge_patch(targets[0][0], patch)

    output: List[ResolvedSSRFDocument] = []
    for root, path, payload, is_overlay in documents:
        try:
            reference = validate_data(payload)
        except Exception as exc:
            raise ValueError(f"{path}: invalid document after overrides: {exc}") from exc
        output.append(
            ResolvedSSRFDocument(
                root=root,
                path=path,
                reference=reference,
                is_overlay=is_overlay,
            )
        )
    return output