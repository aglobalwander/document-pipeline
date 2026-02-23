#!/usr/bin/env python3
"""Build a dedupe-first ingestion review package for Knowledge Hub handoff."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set

from registry_utils import load_yaml_file, write_yaml_file

DEFAULT_INCLUDED_STATUSES = {"success", "skipped_resume"}
KNOWN_JSONL_FIELDS = (
    "source_id",
    "source_path",
    "source",
    "path",
    "file_name",
    "filename",
    "document_id",
    "title",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create ingestion review files with filename-based duplicate flags."
    )
    parser.add_argument(
        "--collections_root",
        default="/Volumes/My Passport/knowledge-hub/collections",
        help="Root containing per-collection folders with manifest.yaml.",
    )
    parser.add_argument(
        "--existing_jsonl",
        action="append",
        default=[],
        help="Path or glob for existing JSONL files (repeatable).",
    )
    parser.add_argument(
        "--existing_path",
        action="append",
        default=[],
        help="Existing file or directory to index by filename (repeatable).",
    )
    parser.add_argument(
        "--existing_name_list",
        action="append",
        default=[],
        help="Text file with one existing filename/path per line (repeatable).",
    )
    parser.add_argument(
        "--out_dir",
        default="/Volumes/My Passport/knowledge-hub/review",
        help="Output directory for handoff package.",
    )
    parser.add_argument(
        "--report_prefix",
        default="ingestion_review",
        help="Output filename prefix.",
    )
    return parser.parse_args()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = Path(value).stem
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def _iter_manifest_paths(collections_root: Path) -> Iterable[Path]:
    for manifest in sorted(collections_root.glob("*/manifest.yaml")):
        if manifest.parent.name == "indexes":
            continue
        yield manifest


def _collect_candidates(collections_root: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    for manifest_path in _iter_manifest_paths(collections_root):
        manifest = load_yaml_file(manifest_path, {})
        collection_name = str(manifest.get("collection_name", manifest_path.parent.name))
        status = str(manifest.get("status", "unknown"))
        processed_files = manifest.get("processed_files", [])
        if not isinstance(processed_files, list):
            continue

        for entry in processed_files:
            if not isinstance(entry, dict):
                continue
            file_status = str(entry.get("status", "unknown"))
            if file_status not in DEFAULT_INCLUDED_STATUSES:
                continue

            source_path = str(entry.get("source_path", ""))
            relative_path = str(entry.get("relative_path", ""))
            output_files = entry.get("output_files", {})
            output_json = ""
            if isinstance(output_files, dict):
                output_json = str(output_files.get("json", ""))

            source_name = Path(source_path).name if source_path else Path(relative_path).name
            normalized_name = _normalize_name(source_name)

            rows.append(
                {
                    "collection": collection_name,
                    "collection_manifest_status": status,
                    "file_status": file_status,
                    "source_path": source_path,
                    "relative_path": relative_path,
                    "source_filename": source_name,
                    "source_filename_normalized": normalized_name,
                    "output_json": output_json,
                }
            )

    return rows


def _expand_patterns(patterns: List[str]) -> List[Path]:
    resolved: List[Path] = []
    for raw in patterns:
        raw_path = Path(raw).expanduser()
        if any(ch in raw for ch in ["*", "?", "["]):
            resolved.extend(sorted(Path(p) for p in glob.glob(str(raw_path), recursive=True)))
        elif raw_path.exists():
            resolved.append(raw_path)
    return resolved


def _add_existing_name(existing_keys: Set[str], value: str) -> None:
    value = value.strip()
    if not value:
        return
    normalized = _normalize_name(value)
    if normalized:
        existing_keys.add(normalized)


def _collect_existing_keys(args: argparse.Namespace) -> Set[str]:
    keys: Set[str] = set()

    for path in _expand_patterns(args.existing_jsonl):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                for field in KNOWN_JSONL_FIELDS:
                    val = payload.get(field)
                    if isinstance(val, str):
                        _add_existing_name(keys, val)

    for path in _expand_patterns(args.existing_path):
        if path.is_file():
            _add_existing_name(keys, path.name)
            continue
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    _add_existing_name(keys, f.name)

    for path in _expand_patterns(args.existing_name_list):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                _add_existing_name(keys, line)

    return keys


def _label_action(in_existing: bool, in_batch_count: int) -> str:
    if in_existing:
        return "exclude_existing_filename_match"
    if in_batch_count > 1:
        return "review_batch_filename_collision"
    return "ingest_candidate"


def _write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    collections_root = Path(args.collections_root).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = _collect_candidates(collections_root)
    existing_keys = _collect_existing_keys(args)

    batch_counts = Counter(row["source_filename_normalized"] for row in candidates if row["source_filename_normalized"])
    collection_counts = Counter(row["collection"] for row in candidates)

    enriched: List[Dict[str, str]] = []
    for row in candidates:
        key = row["source_filename_normalized"]
        duplicate_existing = key in existing_keys if key else False
        duplicate_batch_count = int(batch_counts.get(key, 0))
        action = _label_action(duplicate_existing, duplicate_batch_count)
        enriched.append(
            {
                **row,
                "duplicate_filename_existing": str(duplicate_existing).lower(),
                "duplicate_filename_in_batch_count": str(duplicate_batch_count),
                "suggested_action": action,
            }
        )

    to_exclude = [r for r in enriched if r["suggested_action"] == "exclude_existing_filename_match"]
    to_review = [r for r in enriched if r["suggested_action"] == "review_batch_filename_collision"]
    to_ingest = [r for r in enriched if r["suggested_action"] == "ingest_candidate"]

    prefix = args.report_prefix
    all_csv = out_dir / f"{prefix}_all.csv"
    keep_csv = out_dir / f"{prefix}_ingest.csv"
    exclude_csv = out_dir / f"{prefix}_exclude_filename_match.csv"
    review_csv = out_dir / f"{prefix}_review_batch_collisions.csv"
    summary_yaml = out_dir / f"{prefix}_summary.yaml"

    fieldnames = [
        "collection",
        "collection_manifest_status",
        "file_status",
        "source_path",
        "relative_path",
        "source_filename",
        "source_filename_normalized",
        "output_json",
        "duplicate_filename_existing",
        "duplicate_filename_in_batch_count",
        "suggested_action",
    ]

    _write_csv(all_csv, enriched, fieldnames)
    _write_csv(keep_csv, to_ingest, fieldnames)
    _write_csv(exclude_csv, to_exclude, fieldnames)
    _write_csv(review_csv, to_review, fieldnames)

    summary = {
        "generated_at": _now_iso(),
        "collections_root": str(collections_root),
        "existing_keys_count": len(existing_keys),
        "candidates_total": len(enriched),
        "suggested_ingest_count": len(to_ingest),
        "suggested_exclude_existing_filename_count": len(to_exclude),
        "suggested_review_batch_collision_count": len(to_review),
        "collections_candidate_counts": dict(sorted(collection_counts.items())),
        "outputs": {
            "all_csv": str(all_csv),
            "ingest_csv": str(keep_csv),
            "exclude_csv": str(exclude_csv),
            "review_csv": str(review_csv),
        },
        "notes": [
            "Filename match is a fast first-pass dedupe signal; use content hash/title/source_path in phase 2.",
            "Rows marked 'review_batch_filename_collision' share a normalized filename inside this ETL corpus.",
            "Preserve source_path and collection for provenance even when excluded from ingestion.",
        ],
    }
    write_yaml_file(summary_yaml, summary)

    print(f"Summary: {summary_yaml}")
    print(f"All candidates: {all_csv}")
    print(f"Suggested ingest: {keep_csv}")
    print(f"Suggested exclude (filename match): {exclude_csv}")
    print(f"Suggested review (batch collisions): {review_csv}")
    print(
        "Counts: "
        f"total={len(enriched)}, "
        f"ingest={len(to_ingest)}, "
        f"exclude_existing_filename={len(to_exclude)}, "
        f"review_batch_collisions={len(to_review)}"
    )


if __name__ == "__main__":
    main()
