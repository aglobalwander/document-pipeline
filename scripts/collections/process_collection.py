#!/usr/bin/env python3
"""Process an external collection directory without copying files into data/input."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from doc_processing.config import get_settings
from doc_processing.document_pipeline import DocumentPipeline

from inventory_collection import build_inventory_report
from registry_utils import (
    load_yaml_file,
    slugify_collection_name,
    update_registry,
    write_yaml_file,
)

logger = logging.getLogger(__name__)

OUTPUT_EXTENSIONS = {
    "text": ".txt",
    "markdown": ".md",
    "json": ".json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process files from an external collection directory through the existing pipeline."
    )
    parser.add_argument("--source_dir", required=True, help="External source directory to process.")
    parser.add_argument(
        "--collection_name",
        help="Collection key used under data/output/collections. Defaults to source directory name.",
    )
    parser.add_argument(
        "--output_root",
        default="data/output/collections",
        help="Root directory for collection outputs.",
    )
    parser.add_argument(
        "--registry_path",
        default="data/processing_registry.yaml",
        help="Master registry YAML path.",
    )
    parser.add_argument(
        "--pipeline_type",
        default="text",
        choices=["text", "markdown", "json"],
        help="Primary pipeline type when not writing all formats.",
    )
    parser.add_argument(
        "--recursive",
        dest="recursive",
        action="store_true",
        help="Process source directory recursively (default).",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Process only top-level files.",
    )
    parser.set_defaults(recursive=True)

    formats_group = parser.add_mutually_exclusive_group()
    formats_group.add_argument(
        "--output_all_formats",
        dest="output_all_formats",
        action="store_true",
        help="Write text/markdown/json for each file (default).",
    )
    formats_group.add_argument(
        "--no_output_all_formats",
        dest="output_all_formats",
        action="store_false",
        help="Write only one output format based on --pipeline_type.",
    )
    parser.set_defaults(output_all_formats=True)

    parser.add_argument(
        "--pdf_processor",
        default="enhanced_docling",
        choices=["enhanced_docling", "docling", "pymupdf", "gemini", "gpt"],
        help="PDF processor used in exclusive strategy.",
    )
    parser.add_argument("--dry_run", action="store_true", help="Preview processing without executing pipeline.")
    parser.add_argument("--resume", action="store_true", help="Skip files already processed successfully.")
    parser.add_argument(
        "--workers",
        type=int,
        default=get_settings().CONCURRENT_TASKS,
        help=(
            "Number of worker processes (default: CONCURRENT_TASKS setting). "
            "Use 1 for sequential processing. Each worker loads its own model set, so raise this only when memory allows."
        ),
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=get_settings().MAX_RETRIES,
        help="Attempts per file before recording a failure (default: MAX_RETRIES setting).",
    )
    parser.add_argument(
        "--ocr", dest="ocr", action="store_true", default=None,
        help="Force Docling OCR on (default: Docling decides per page).",
    )
    parser.add_argument(
        "--no_ocr", dest="no_ocr", action="store_true",
        help="Disable Docling OCR for PDFs that already carry a text layer.",
    )
    parser.add_argument(
        "--images_scale", type=float,
        help="Scale factor for Docling page/picture images.",
    )
    parser.add_argument(
        "--max_files",
        type=int,
        help="Optional limit for number of processable files to run in this invocation.",
    )
    parser.add_argument(
        "--exclude_dir",
        action="append",
        default=[],
        help="Directory to exclude (repeatable, absolute or relative to source_dir).",
    )

    ready_group = parser.add_mutually_exclusive_group()
    ready_group.add_argument(
        "--ready_for_ingestion",
        dest="ready_for_ingestion",
        action="store_true",
        help="Mark collection ready for downstream ingestion in manifest/registry.",
    )
    ready_group.add_argument(
        "--not_ready_for_ingestion",
        dest="ready_for_ingestion",
        action="store_false",
        help="Mark collection as not ready for downstream ingestion.",
    )
    parser.set_defaults(ready_for_ingestion=None)

    return parser.parse_args()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _formats_to_write(output_all_formats: bool, pipeline_type: str) -> List[str]:
    if output_all_formats:
        return ["text", "markdown", "json"]
    return [pipeline_type]


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, ensure_ascii=False)


def _extract_payloads(
    processed_document: Dict[str, Any], pipeline_type: str, output_all_formats: bool
) -> Dict[str, str]:
    primary = _coerce_text(processed_document.get("content"))
    text_payload = _coerce_text(processed_document.get("text_content")) or primary
    markdown_payload = (
        _coerce_text(processed_document.get("markdown_content"))
        or _coerce_text(processed_document.get("markdown"))
        or primary
    )
    json_payload = _coerce_text(processed_document.get("json_content"))
    if not json_payload:
        json_payload = json.dumps(processed_document, indent=2, ensure_ascii=False)

    if output_all_formats:
        return {
            "text": text_payload,
            "markdown": markdown_payload,
            "json": json_payload,
        }

    if pipeline_type == "markdown":
        return {"markdown": markdown_payload}
    if pipeline_type == "json":
        return {"json": json_payload}
    return {"text": text_payload}


def _build_output_paths(collection_root: Path, relative_source_path: Path) -> Dict[str, Path]:
    return {
        "text": collection_root / "text" / relative_source_path.with_suffix(OUTPUT_EXTENSIONS["text"]),
        "markdown": collection_root
        / "markdown"
        / relative_source_path.with_suffix(OUTPUT_EXTENSIONS["markdown"]),
        "json": collection_root / "json" / relative_source_path.with_suffix(OUTPUT_EXTENSIONS["json"]),
    }


def _outputs_exist(output_paths: Dict[str, Path], target_formats: List[str]) -> bool:
    return all(output_paths[fmt].exists() for fmt in target_formats)


def _outputs_ready(output_paths: Dict[str, Path], target_formats: List[str]) -> bool:
    """Require output files to exist and be non-empty."""
    for fmt in target_formats:
        output_path = output_paths[fmt]
        if not output_path.exists():
            return False
        try:
            if output_path.stat().st_size <= 0:
                return False
        except OSError:
            return False
    return True


def _load_previous_successes(manifest_path: Path) -> Dict[str, Dict[str, Any]]:
    manifest = load_yaml_file(manifest_path, {})
    processed_files = manifest.get("processed_files", [])
    if not isinstance(processed_files, list):
        return {}
    success_map: Dict[str, Dict[str, Any]] = {}
    for row in processed_files:
        if not isinstance(row, dict):
            continue
        if row.get("status") == "success" and row.get("relative_path"):
            success_map[row["relative_path"]] = row
    return success_map


def _build_pipeline_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Pipeline config shared by every file in the collection run."""
    # Page rasterisation is only consumed by the GPT vision path; the Docling,
    # PyMuPDF, Gemini and Claude paths read the PDF directly.
    needs_page_images = args.pdf_processor == "gpt"
    return {
        "pipeline_type": args.pipeline_type,
        "pdf_processor_strategy": "exclusive",
        "default_pdf_processor": args.pdf_processor,
        "output_all_formats": args.output_all_formats,
        "use_cache": True,
        "detect_columns": True,
        "docling_extract_tables": True,
        "docling_do_ocr": _resolve_docling_ocr(args),
        "docling_images_scale": args.images_scale,
        "pdf_loader_config": {"generate_page_images": needs_page_images},
    }


def _resolve_docling_ocr(args: argparse.Namespace):
    """Map --ocr/--no_ocr to a Docling option (None keeps Docling's default)."""
    if getattr(args, "no_ocr", False):
        return False
    if getattr(args, "ocr", False):
        return True
    return None


def _write_payloads(
    output_paths: Dict[str, Path], payloads: Dict[str, str], target_formats: List[str]
) -> None:
    """Write one file's payloads into the collection output tree."""
    for fmt in target_formats:
        output_path = output_paths[fmt]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(payloads.get(fmt, ""))


# One pipeline per worker process: Docling models load once per process instead
# of once per file.
_WORKER_PIPELINE: DocumentPipeline | None = None


def _worker_init(pipeline_config: Dict[str, Any]) -> None:
    """ProcessPoolExecutor initializer: build the worker's pipeline once."""
    global _WORKER_PIPELINE
    # Spawned workers do not inherit the parent's logging configuration.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
    _WORKER_PIPELINE = DocumentPipeline(config=pipeline_config)


def _process_one(task: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a single file, returning payloads instead of writing them.

    Runs in a worker process (or in-process for the sequential path), so it must
    stay picklable and must not touch the manifest/registry.
    """
    global _WORKER_PIPELINE
    pipeline = _WORKER_PIPELINE
    if pipeline is None:
        pipeline = DocumentPipeline(config=task["pipeline_config"])
        _WORKER_PIPELINE = pipeline

    attempts = max(1, int(task.get("retries") or 1))
    last_error: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            processed = pipeline.process_document(str(task["source_path"]))
            if not isinstance(processed, dict):
                raise RuntimeError(f"Unexpected pipeline result type: {type(processed)}")
            if processed.get("error"):
                raise RuntimeError(str(processed["error"]))

            payloads = _extract_payloads(
                processed, task["pipeline_type"], task["output_all_formats"]
            )
            outcome: Dict[str, Any] = {
                "status": "success",
                "payloads": payloads,
                "processing_method": processed.get("processing_method", "unknown"),
            }
            if attempt > 1:
                outcome["attempts"] = attempt
            return outcome
        except Exception as exc:  # noqa: BLE001 - reported through the outcome
            last_error = str(exc)
            logger.warning(
                f"Attempt {attempt}/{attempts} failed for {task['source_path']}: {exc}"
            )

    return {"status": "failed", "error": last_error or "processing failed"}


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    args = parse_args()
    started_at = time.time()
    run_started_iso = _now_iso()

    source_dir = Path(args.source_dir).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    registry_path = Path(args.registry_path).expanduser().resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        raise SystemExit(f"Invalid source directory: {source_dir}")

    collection_name = slugify_collection_name(args.collection_name or source_dir.name)
    collection_root = output_root / collection_name
    manifest_path = collection_root / "manifest.yaml"

    inventory = build_inventory_report(
        source_dir=source_dir,
        recursive=args.recursive,
        exclude_dirs=args.exclude_dir,
    )
    processable_relative = [Path(path_str) for path_str in inventory["processable_files"]]
    processable_files = [source_dir / rel_path for rel_path in processable_relative]
    processable_files = sorted(processable_files)
    if args.max_files is not None:
        processable_files = processable_files[: max(0, args.max_files)]

    formats_to_write = _formats_to_write(args.output_all_formats, args.pipeline_type)
    previous_manifest = load_yaml_file(manifest_path, {})
    previous_successes = _load_previous_successes(manifest_path) if args.resume else {}
    ready_for_ingestion = (
        args.ready_for_ingestion
        if args.ready_for_ingestion is not None
        else bool(previous_manifest.get("ready_for_ingestion", False))
    )

    successes = 0
    failures = 0
    resume_skips = 0
    errors: List[str] = []
    run_records: List[Dict[str, Any]] = []
    pending: List[Tuple[Dict[str, Any], Dict[str, Path], Path]] = []

    for index, source_path in enumerate(processable_files, start=1):
        relative_path = source_path.relative_to(source_dir)
        relative_key = relative_path.as_posix()
        output_paths = _build_output_paths(collection_root, relative_path)

        record: Dict[str, Any] = {
            "index": index,
            "source_path": str(source_path),
            "relative_path": relative_key,
            "extension": source_path.suffix.lower().lstrip("."),
            "status": "pending",
            "output_files": {fmt: str(output_paths[fmt]) for fmt in formats_to_write},
            "started_at": _now_iso(),
        }

        if args.resume and _outputs_ready(output_paths, formats_to_write):
            record["status"] = "skipped_resume"
            record["completed_at"] = _now_iso()
            if relative_key not in previous_successes:
                record["resume_reason"] = "existing_outputs"
            resume_skips += 1
            run_records.append(record)
            continue

        if args.dry_run:
            record["status"] = "planned"
            record["completed_at"] = _now_iso()
            run_records.append(record)
            continue

        pending.append((record, output_paths, source_path))

    # --- Execute pending work (worker processes, or sequential) ---
    outcomes: Dict[str, Dict[str, Any]] = {}
    if pending:
        pipeline_config = _build_pipeline_config(args)
        retries = max(1, int(args.retries or 1))
        tasks = [
            {
                "source_path": str(source_path),
                "pipeline_config": pipeline_config,
                "pipeline_type": args.pipeline_type,
                "output_all_formats": args.output_all_formats,
                "retries": retries,
            }
            for _, _, source_path in pending
        ]

        workers = max(1, int(args.workers or 1))
        if workers > 1 and len(tasks) > 1:
            logger.info(
                f"Processing {len(tasks)} file(s) across {workers} worker processes "
                f"(retries={retries})"
            )
            with ProcessPoolExecutor(
                max_workers=workers,
                initializer=_worker_init,
                initargs=(pipeline_config,),
            ) as executor:
                future_map = {executor.submit(_process_one, task): task for task in tasks}
                for future in as_completed(future_map):
                    task = future_map[future]
                    try:
                        outcomes[task["source_path"]] = future.result()
                    except Exception as exc:  # noqa: BLE001 - recorded per file
                        outcomes[task["source_path"]] = {
                            "status": "failed",
                            "error": str(exc),
                        }
        else:
            logger.info(f"Processing {len(tasks)} file(s) sequentially (retries={retries})")
            _worker_init(pipeline_config)
            for task in tasks:
                outcomes[task["source_path"]] = _process_one(task)

    for record, output_paths, source_path in pending:
        outcome = outcomes.get(str(source_path)) or {
            "status": "failed",
            "error": "no result produced",
        }
        if outcome.get("status") == "success":
            _write_payloads(output_paths, outcome.get("payloads", {}), formats_to_write)
            record["status"] = "success"
            record["processing_method"] = outcome.get("processing_method", "unknown")
            if outcome.get("attempts"):
                record["attempts"] = outcome["attempts"]
            successes += 1
        else:
            record["status"] = "failed"
            record["error"] = outcome.get("error", "unknown error")
            failures += 1
            errors.append(f"{record['relative_path']}: {record['error']}")
        record["completed_at"] = _now_iso()
        run_records.append(record)

    previous_records = previous_manifest.get("processed_files", [])
    merged_records: Dict[str, Dict[str, Any]] = {}
    if isinstance(previous_records, list):
        for row in previous_records:
            if isinstance(row, dict) and row.get("relative_path"):
                merged_records[row["relative_path"]] = row

    for row in run_records:
        rel = row.get("relative_path")
        if not rel:
            continue
        if row.get("status") == "skipped_resume" and rel in merged_records:
            # Keep successful historical record so future resume checks remain stable.
            continue
        merged_records[rel] = row

    processed_file_records = [
        merged_records[key] for key in sorted(merged_records.keys())
    ]

    total_processable = len(processable_files)
    duration_seconds = round(time.time() - started_at, 2)

    if args.dry_run:
        status = "dry_run"
    elif total_processable == 0:
        status = "no_files"
    elif failures == 0:
        status = "complete"
    elif successes == 0:
        status = "failed"
    else:
        status = "partial"

    manifest = {
        "collection_name": collection_name,
        "source_directory": str(source_dir),
        "output_directory": str(collection_root),
        "processing_date": datetime.now().date().isoformat(),
        "started_at": run_started_iso,
        "completed_at": _now_iso(),
        "duration_seconds": duration_seconds,
        "status": status,
        "dry_run": args.dry_run,
        "options": {
            "recursive": args.recursive,
            "exclude_dirs": args.exclude_dir,
            "pipeline_type": args.pipeline_type,
            "output_all_formats": args.output_all_formats,
            "resume": args.resume,
            "pdf_processor": args.pdf_processor,
            "max_files": args.max_files,
            "workers": args.workers,
            "retries": args.retries,
            "docling_do_ocr": _resolve_docling_ocr(args),
        },
        "files_processed": {
            "discovered_total": inventory["total_files"],
            "processable_total": total_processable,
            "pdf": sum(1 for p in processable_files if p.suffix.lower() == ".pdf"),
            "docx": sum(1 for p in processable_files if p.suffix.lower() == ".docx"),
            "pptx": sum(1 for p in processable_files if p.suffix.lower() == ".pptx"),
            "succeeded": successes,
            "failed": failures,
            "skipped_resume": resume_skips,
            "cruft": inventory["cruft_total"],
            "unsupported": inventory["unsupported_total"],
        },
        "errors": errors,
        "ready_for_ingestion": ready_for_ingestion,
        "processed_files": processed_file_records,
    }

    collection_root.mkdir(parents=True, exist_ok=True)
    write_yaml_file(manifest_path, manifest)

    if not args.dry_run:
        registry_entry = {
            "name": collection_name,
            "source_path": str(source_dir),
            "output_path": str(collection_root),
            "manifest_path": str(manifest_path),
            "status": status,
            "processing_date": manifest["processing_date"],
            "files_processed": successes,
            "files_failed": failures,
            "files_total": total_processable,
            "ready_for_ingestion": ready_for_ingestion,
            "processable_by_type": {
                "pdf": manifest["files_processed"]["pdf"],
                "docx": manifest["files_processed"]["docx"],
                "pptx": manifest["files_processed"]["pptx"],
            },
        }
        update_registry(registry_path, registry_entry)

    print(f"Collection: {collection_name}")
    print(f"Status: {status}")
    print(f"Source: {source_dir}")
    print(f"Manifest: {manifest_path}")
    print(
        "Files: "
        f"processable={total_processable}, "
        f"succeeded={successes}, failed={failures}, skipped_resume={resume_skips}"
    )
    if not args.dry_run:
        print(f"Registry updated: {registry_path}")
    print(f"Duration: {duration_seconds} seconds")


if __name__ == "__main__":
    main()
