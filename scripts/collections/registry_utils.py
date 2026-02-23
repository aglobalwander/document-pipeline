#!/usr/bin/env python3
"""Shared YAML helpers for collection manifests and processing registry."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

DEFAULT_REGISTRY: Dict[str, Any] = {
    "version": "1.0",
    "collections": [],
}


def now_iso() -> str:
    """Return an ISO-8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def slugify_collection_name(value: str) -> str:
    """Create a stable collection slug from user input."""
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "collection"


def load_yaml_file(path: Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Load YAML from disk, returning a dict fallback when missing/empty."""
    fallback = {} if default is None else dict(default)
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        return fallback
    return data


def write_yaml_file(path: Path, payload: Dict[str, Any]) -> None:
    """Write YAML payload to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)


def load_registry(path: Path) -> Dict[str, Any]:
    """Load the processing registry with defaults."""
    registry = load_yaml_file(path, DEFAULT_REGISTRY)
    if "version" not in registry:
        registry["version"] = DEFAULT_REGISTRY["version"]
    if "collections" not in registry or not isinstance(registry["collections"], list):
        registry["collections"] = []
    return registry


def _collection_index(collections: List[Dict[str, Any]], name: str) -> int:
    for idx, entry in enumerate(collections):
        if entry.get("name") == name:
            return idx
    return -1


def update_registry(path: Path, entry: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a collection entry in the master registry."""
    if not entry.get("name"):
        raise ValueError("Registry entry must include a non-empty 'name' field.")

    registry = load_registry(path)
    collections = registry["collections"]

    merged_entry = dict(entry)
    merged_entry["updated_at"] = now_iso()

    existing_idx = _collection_index(collections, merged_entry["name"])
    if existing_idx >= 0:
        current = collections[existing_idx]
        current.update(merged_entry)
        collections[existing_idx] = current
    else:
        collections.append(merged_entry)

    write_yaml_file(path, registry)
    return registry


def get_collections_ready(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return collections marked ready for downstream ingestion."""
    collections = registry.get("collections", [])
    return [entry for entry in collections if entry.get("ready_for_ingestion") is True]

