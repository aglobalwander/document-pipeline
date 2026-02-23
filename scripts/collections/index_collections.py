#!/usr/bin/env python3
"""Build a top-level inventory index for a large research root."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from inventory_collection import build_inventory_report
from registry_utils import write_yaml_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index top-level collections under a research root for ETL planning."
    )
    parser.add_argument("--source_root", required=True, help="Root directory containing collections.")
    parser.add_argument(
        "--exclude_dir",
        action="append",
        default=[],
        help="Directory to exclude (repeatable, absolute or relative to source_root).",
    )
    parser.add_argument(
        "--output_path",
        default="data/output/collections/indexes/research_root_index.yaml",
        help="YAML output path for index report.",
    )
    parser.add_argument(
        "--max_collections",
        type=int,
        help="Optional limit on number of top-level collections to index.",
    )
    return parser.parse_args()


def _resolve_excludes(root: Path, excludes: List[str]) -> List[Path]:
    out: List[Path] = []
    for raw in excludes:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = root / p
        out.append(p.resolve())
    return out


def _should_exclude(path: Path, exclude_paths: List[Path]) -> bool:
    for ex in exclude_paths:
        try:
            path.resolve().relative_to(ex)
            return True
        except ValueError:
            continue
    return False


def main() -> None:
    args = parse_args()
    source_root = Path(args.source_root).expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise SystemExit(f"Invalid source_root: {source_root}")

    exclude_paths = _resolve_excludes(source_root, args.exclude_dir)
    top_dirs = [p for p in sorted(source_root.iterdir()) if p.is_dir()]
    top_dirs = [p for p in top_dirs if not _should_exclude(p, exclude_paths)]
    if args.max_collections is not None:
        top_dirs = top_dirs[: max(0, args.max_collections)]

    collections: List[Dict[str, Any]] = []
    totals = {
        "collections_indexed": 0,
        "processable_total": 0,
        "processable_pdf": 0,
        "processable_docx": 0,
        "processable_pptx": 0,
        "files_total": 0,
        "cruft_total": 0,
        "unsupported_total": 0,
    }

    for directory in top_dirs:
        report = build_inventory_report(
            source_dir=directory,
            recursive=True,
            exclude_dirs=args.exclude_dir,
        )
        collection_row = {
            "name": directory.name,
            "path": str(directory),
            "processable_total": report["processable_total"],
            "processable_by_type": report["processable_by_type"],
            "total_files": report["total_files"],
            "cruft_total": report["cruft_total"],
            "unsupported_total": report["unsupported_total"],
            "estimated_processing_minutes": report["estimated_processing_minutes"],
        }
        collections.append(collection_row)

        totals["collections_indexed"] += 1
        totals["processable_total"] += report["processable_total"]
        totals["processable_pdf"] += report["processable_by_type"]["pdf"]
        totals["processable_docx"] += report["processable_by_type"]["docx"]
        totals["processable_pptx"] += report["processable_by_type"]["pptx"]
        totals["files_total"] += report["total_files"]
        totals["cruft_total"] += report["cruft_total"]
        totals["unsupported_total"] += report["unsupported_total"]

    index_payload = {
        "source_root": str(source_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "excluded_directories": [str(p) for p in exclude_paths],
        "totals": totals,
        "collections": sorted(collections, key=lambda r: (-r["processable_total"], r["name"])),
    }

    output_path = Path(args.output_path).expanduser().resolve()
    write_yaml_file(output_path, index_payload)

    print(f"Indexed collections: {totals['collections_indexed']}")
    print(f"Processable files: {totals['processable_total']}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()

