#!/usr/bin/env python3
"""Inventory utility for external collection processing."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple

from registry_utils import write_yaml_file

SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
}

CRUFT_FILENAMES = {
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}

CRUFT_SUFFIXES = {
    ".crdownload",
    ".part",
    ".tmp",
    ".download",
}


def is_cruft(path: Path) -> bool:
    """Return True when file appears to be temporary/system cruft."""
    name_lower = path.name.lower()
    if name_lower in CRUFT_FILENAMES:
        return True
    if any(name_lower.endswith(suffix) for suffix in CRUFT_SUFFIXES):
        return True
    if name_lower.startswith("._"):
        return True
    if name_lower.startswith("~$"):
        return True
    return False


def _normalize_excludes(source_dir: Path, excludes: List[str] | None) -> List[Path]:
    """Resolve exclude inputs to absolute paths rooted at source when needed."""
    normalized: List[Path] = []
    for raw in excludes or []:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (source_dir / p)
        normalized.append(p.resolve())
    return normalized


def _is_excluded(path: Path, excluded_dirs: List[Path]) -> bool:
    for excluded in excluded_dirs:
        try:
            path.resolve().relative_to(excluded)
            return True
        except ValueError:
            continue
    return False


def _list_files(source_dir: Path, recursive: bool) -> List[Path]:
    iterator = source_dir.rglob("*") if recursive else source_dir.glob("*")
    return sorted(path for path in iterator if path.is_file())


def _estimate_processing_minutes(processable_by_type: Dict[str, int]) -> Tuple[float, float]:
    # Conservative rough estimate based on observed local runtimes.
    pdf = processable_by_type.get("pdf", 0)
    docx = processable_by_type.get("docx", 0)
    pptx = processable_by_type.get("pptx", 0)

    lower = (pdf * 0.35) + (docx * 0.20) + (pptx * 0.30)
    upper = (pdf * 0.55) + (docx * 0.35) + (pptx * 0.45)
    return round(lower, 1), round(upper, 1)


def build_inventory_report(
    source_dir: Path,
    recursive: bool = True,
    exclude_dirs: List[str] | None = None,
) -> Dict[str, Any]:
    """Scan a source directory and classify files for processing readiness."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_dir}")

    excluded_paths = _normalize_excludes(source_dir, exclude_dirs)
    all_files = _list_files(source_dir, recursive=recursive)
    files = [path for path in all_files if not _is_excluded(path, excluded_paths)]
    processable_files: List[Path] = []
    cruft_files: List[Path] = []
    unsupported_files: List[Path] = []

    ext_counts: Dict[str, int] = {}
    processable_by_type = {"pdf": 0, "docx": 0, "pptx": 0}
    directory_breakdown: Dict[str, int] = {}

    for file_path in files:
        rel_path = file_path.relative_to(source_dir)
        ext = file_path.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if is_cruft(file_path):
            cruft_files.append(file_path)
            continue

        if ext in SUPPORTED_EXTENSIONS:
            processable_files.append(file_path)
            file_type = SUPPORTED_EXTENSIONS[ext]
            processable_by_type[file_type] += 1
            rel_parent = rel_path.parent.as_posix() if rel_path.parent != Path(".") else "."
            directory_breakdown[rel_parent] = directory_breakdown.get(rel_parent, 0) + 1
        else:
            unsupported_files.append(file_path)

    est_min, est_max = _estimate_processing_minutes(processable_by_type)

    return {
        "source_directory": str(source_dir.resolve()),
        "recursive": recursive,
        "excluded_directories": [str(path) for path in excluded_paths],
        "excluded_files_total": len(all_files) - len(files),
        "total_files": len(files),
        "processable_total": len(processable_files),
        "processable_by_type": processable_by_type,
        "cruft_total": len(cruft_files),
        "unsupported_total": len(unsupported_files),
        "estimated_processing_minutes": {"min": est_min, "max": est_max},
        "extension_counts": dict(sorted(ext_counts.items(), key=lambda item: item[0])),
        "directory_breakdown": dict(
            sorted(directory_breakdown.items(), key=lambda item: (-item[1], item[0]))
        ),
        "processable_files": [path.relative_to(source_dir).as_posix() for path in processable_files],
        "cruft_files": [path.relative_to(source_dir).as_posix() for path in cruft_files],
        "unsupported_files": [path.relative_to(source_dir).as_posix() for path in unsupported_files],
    }


def _print_report(report: Dict[str, Any], max_list_items: int) -> None:
    print(f"Source: {report['source_directory']}")
    print(f"Recursive scan: {report['recursive']}")
    print(f"Total files found: {report['total_files']}")
    print(f"Processable: {report['processable_total']}")
    print(f"  PDF:  {report['processable_by_type']['pdf']}")
    print(f"  DOCX: {report['processable_by_type']['docx']}")
    print(f"  PPTX: {report['processable_by_type']['pptx']}")
    print(f"Cruft: {report['cruft_total']}")
    print(f"Unsupported: {report['unsupported_total']}")
    print(
        "Estimated processing time: "
        f"{report['estimated_processing_minutes']['min']} - "
        f"{report['estimated_processing_minutes']['max']} minutes"
    )

    if report["directory_breakdown"]:
        print("Top directories (processable files):")
        for idx, (folder, count) in enumerate(report["directory_breakdown"].items(), start=1):
            if idx > max_list_items:
                break
            print(f"  {folder}: {count}")

    if report["cruft_files"]:
        print("Cruft examples:")
        for item in report["cruft_files"][:max_list_items]:
            print(f"  {item}")

    if report["unsupported_files"]:
        print("Unsupported examples:")
        for item in report["unsupported_files"][:max_list_items]:
            print(f"  {item}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a source directory and inventory files before collection processing."
    )
    parser.add_argument("--source_dir", required=True, help="Directory to inventory.")
    parser.add_argument(
        "--recursive",
        dest="recursive",
        action="store_true",
        help="Scan recursively (default).",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Scan only the top-level directory.",
    )
    parser.set_defaults(recursive=True)
    parser.add_argument(
        "--output_path",
        help="Optional YAML path for writing full inventory report.",
    )
    parser.add_argument(
        "--max_list_items",
        type=int,
        default=20,
        help="Maximum number of list entries shown in console output.",
    )
    parser.add_argument(
        "--exclude_dir",
        action="append",
        default=[],
        help="Directory to exclude (repeatable, absolute or relative to source_dir).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = Path(args.source_dir).expanduser().resolve()
    report = build_inventory_report(
        source_dir,
        recursive=args.recursive,
        exclude_dirs=args.exclude_dir,
    )
    _print_report(report, max_list_items=max(1, args.max_list_items))

    if args.output_path:
        output_path = Path(args.output_path).expanduser().resolve()
        write_yaml_file(output_path, report)
        print(f"Wrote inventory report: {output_path}")


if __name__ == "__main__":
    main()
