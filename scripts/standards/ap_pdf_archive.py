#!/usr/bin/env python3
"""Archive and verify current AP PDFs without overwriting legacy inputs.

The command consumes an already downloaded directory containing one PDF named
``<package_id>.pdf`` per source-manifest row. It performs no network access.
Bytes are archived immutably by hash; the tracked index records byte lineage
without claiming content-review or downstream-release authority.
"""

from __future__ import annotations

import argparse

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from doc_processing.utils.file_utils import sha256_file

EXPECTED_PACKAGES = 40
EXPECTED_OFFERINGS = 43
INDEX_SCHEMA = "pipeline-documents.ap-pdf-edition-index.v2"
REQUIRED_TOOLS = ("file", "pdfinfo", "pdftotext")
CANONICAL_ARCHIVE_RELATIVE = Path("data/input/pdfs/standards/ap_guide_archive")
CANONICAL_INDEX_RELATIVE = Path("scripts/standards/ap_editions.json")
PACKAGE_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def command(args: list[str]) -> str:
    return subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    ).stdout


def require_tools() -> None:
    missing = [name for name in REQUIRED_TOOLS if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"missing required tools: {', '.join(missing)}")


def detected_source_labels(title: str, front_text: str) -> list[str]:
    text = f"{title}\n{front_text}"
    labels: list[str] = []
    patterns = (
        (
            r"Effective\s+Fall\s+(\d{4})",
            lambda match: f"Effective Fall {match.group(1)}",
        ),
        (
            r"Use\s+Beginning\s+in\s+Fall\s+(\d{4})",
            lambda match: f"Use Beginning in Fall {match.group(1)}",
        ),
        (
            r"For\s+Use\s+Beginning\s+with\s+the\s+(\d{4})\s*[-–]\s*(\d{2,4})\s+School\s+Year\s+Pilot",
            lambda match: (
                "For Use Beginning with the "
                f"{match.group(1)}-{match.group(2)} School Year Pilot"
            ),
        ),
    )
    for pattern, formatter in patterns:
        for match in re.finditer(pattern, text, re.I):
            label = formatter(match)
            if label not in labels:
                labels.append(label)
    return labels


def label_resolution(labels: list[str], baseline_primary: str) -> dict[str, Any]:
    if len(labels) == 1:
        selected = labels[0]
        state = "single_detected_label"
    elif labels:
        selected = None
        state = "multiple_detected_labels_review_required"
    else:
        selected = None
        state = "no_detected_label_review_required"
    return {
        "baseline_primary_label_present": baseline_primary in labels,
        "detected_effective_labels": labels,
        "effective_label": selected,
        "label_detection_source": "pdf_title_and_pages_1_through_8",
        "label_resolution_state": state,
    }


def pdf_metadata(path: Path) -> dict[str, Any]:
    mime_type = command(["file", "--mime-type", "-b", str(path)]).strip()
    if mime_type != "application/pdf":
        raise ValueError(f"not a PDF: {path} ({mime_type})")
    info: dict[str, str] = {}
    for line in command(["pdfinfo", str(path)]).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    pages = int(info.get("Pages", "0"))
    if pages < 1:
        raise ValueError(f"invalid page count for {path}: {pages}")
    subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
    )
    front_text = command(
        ["pdftotext", "-f", "1", "-l", str(min(pages, 8)), "-layout", str(path), "-"]
    )
    return {
        "bytes": path.stat().st_size,
        "detected_effective_labels": detected_source_labels(
            info.get("Title", ""), front_text
        ),
        "encrypted": info.get("Encrypted", "unknown"),
        "mime_type": mime_type,
        "pages": pages,
        "pdf_version": info.get("PDF version", "unknown"),
        "sha256": sha256_file(path),
    }


def contained_regular_file(path: Path, root: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"candidate must be a regular non-symlink file: {path}")
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    return resolved


def repository_relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def courses_for(row: dict[str, Any]) -> list[str]:
    courses = row["official_courses"]
    if isinstance(courses, str):
        courses = json.loads(courses)
    if (
        not isinstance(courses, list)
        or not courses
        or not all(isinstance(item, str) and item for item in courses)
    ):
        raise ValueError(f"invalid official_courses for {row.get('package_id')}")
    return courses


def validate_package_id(package_id: Any) -> str:
    if (
        not isinstance(package_id, str)
        or PACKAGE_ID_PATTERN.fullmatch(package_id) is None
    ):
        raise ValueError(f"unsafe package_id: {package_id!r}")
    return package_id


def load_rows(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("source manifest must be a JSON array")
    required = {
        "official_courses",
        "official_document_url",
        "package_id",
        "snapshot_path",
        "source_pdf_bytes",
        "source_pdf_pages",
        "source_pdf_sha256",
        "source_retrieved_on",
    }
    for row in value:
        missing = required - set(row)
        if missing:
            raise ValueError(f"source row missing keys: {sorted(missing)}")
    package_ids = [validate_package_id(row["package_id"]) for row in value]
    if len(package_ids) != EXPECTED_PACKAGES or len(package_ids) != len(
        set(package_ids)
    ):
        raise ValueError(
            f"source manifest must contain {EXPECTED_PACKAGES} unique packages"
        )
    offering_count = sum(len(courses_for(row)) for row in value)
    if offering_count != EXPECTED_OFFERINGS:
        raise ValueError(f"source manifest must contain {EXPECTED_OFFERINGS} offerings")
    return sorted(value, key=lambda row: row["package_id"])


def matrix_package_ids(path: Path) -> set[str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("rows", [])
    package_ids = {validate_package_id(row.get("package_id")) for row in rows}
    if len(rows) != EXPECTED_PACKAGES or len(package_ids) != EXPECTED_PACKAGES:
        raise ValueError(
            f"readiness matrix must contain {EXPECTED_PACKAGES} package rows"
        )
    return package_ids


def artifact_filename(row: dict[str, Any]) -> str:
    name = Path(urlparse(row["official_document_url"]).path).name
    if not name.lower().endswith(".pdf"):
        raise ValueError(f"official URL has no PDF filename: {row['package_id']}")
    return name


def split_labels(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def verify_expected_hash(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: expected={expected}, actual={actual}")
    return actual


def artifact_role(row: dict[str, Any]) -> str:
    return (
        "course_framework"
        if row["official_document_url"].endswith("course-framework.pdf")
        else "course_and_exam_description"
    )


def expected_baseline(row: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    baseline_sha = row["source_pdf_sha256"]
    archived = artifacts.get(baseline_sha)
    return {
        "archive_path": archived.get("archive_path") if archived else None,
        "bytes": row["source_pdf_bytes"],
        "effective_labels": split_labels(row.get("official_effective_label", "")),
        "pages": row["source_pdf_pages"],
        "primary_effective_label": row.get("official_primary_effective_label", ""),
        "retrieved_on": row["source_retrieved_on"],
        "sha256": baseline_sha,
        "snapshot_ref": f"knowledge-management:{row['snapshot_path']}",
    }


def validate_locations(
    args: argparse.Namespace, include_archive: bool
) -> tuple[Path, Path]:
    repo_root = args.repo_root.resolve()
    expected_index = (repo_root / CANONICAL_INDEX_RELATIVE).resolve()
    if args.index.resolve() != expected_index:
        raise ValueError(f"index must be the canonical path: {expected_index}")
    expected_archive = (repo_root / CANONICAL_ARCHIVE_RELATIVE).resolve()
    if include_archive and args.archive_root.resolve() != expected_archive:
        raise ValueError(f"archive root must be the canonical path: {expected_archive}")
    return repo_root, expected_archive


def atomic_copy(candidate: Path, destination: Path, expected_sha: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != expected_sha:
            raise ValueError(f"archive collision: {destination}")
        return
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copy2(candidate, temporary)
        if sha256_file(temporary) != expected_sha:
            raise ValueError(f"post-copy hash mismatch: {destination}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_index(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[tuple[Path, Path, str]]]:
    require_tools()
    repo_root, archive_root = validate_locations(args, include_archive=True)
    verify_expected_hash(
        args.source_manifest, args.expected_source_manifest_sha256, "source manifest"
    )
    verify_expected_hash(args.matrix, args.expected_matrix_sha256, "readiness matrix")
    rows = load_rows(args.source_manifest)
    source_ids = {row["package_id"] for row in rows}
    if matrix_package_ids(args.matrix) != source_ids:
        raise ValueError("source manifest and readiness matrix package IDs differ")
    download_root = args.download_dir.resolve()
    prior_packages: dict[str, Any] = {}
    if args.index.exists():
        prior = json.loads(args.index.read_text(encoding="utf-8"))
        verify_index(args, prior)
        prior_packages = prior["packages"]
    packages: dict[str, Any] = {}
    copies: list[tuple[Path, Path, str]] = []
    exact_count = 0
    changed_count = 0

    for row in rows:
        package_id = row["package_id"]
        candidate = contained_regular_file(
            download_root / f"{package_id}.pdf", download_root
        )
        metadata = pdf_metadata(candidate)
        expected_sha = row["source_pdf_sha256"]
        exact = (
            metadata["sha256"] == expected_sha
            and metadata["bytes"] == row["source_pdf_bytes"]
            and metadata["pages"] == row["source_pdf_pages"]
        )
        destination = (
            archive_root / package_id / metadata["sha256"] / artifact_filename(row)
        )
        copies.append((candidate, destination, metadata["sha256"]))
        baseline_primary = row.get("official_primary_effective_label", "")
        observed = {
            "archive_path": repository_relative(destination, repo_root),
            "bytes": metadata["bytes"],
            "encrypted": metadata["encrypted"],
            "observed_on": args.observed_on,
            "pages": metadata["pages"],
            "pdf_version": metadata["pdf_version"],
            "sha256": metadata["sha256"],
            **label_resolution(metadata["detected_effective_labels"], baseline_primary),
        }
        artifacts = dict(prior_packages.get(package_id, {}).get("artifacts", {}))
        artifacts[metadata["sha256"]] = observed
        baseline = expected_baseline(row, artifacts)
        if exact:
            exact_count += 1
            comparison_state = "exact_august_review_baseline_bytes"
            archive_state = "verified_current_bytes"
        else:
            changed_count += 1
            comparison_state = "different_from_august_review_baseline"
            archive_state = "verified_current_bytes_distinct_from_baseline"
        packages[package_id] = {
            "archive_state": archive_state,
            "artifact_role": artifact_role(row),
            "artifacts": artifacts,
            "comparison_state": comparison_state,
            "content_review_state": "owned_outside_pipeline",
            "current_artifact_sha256": metadata["sha256"],
            "named_offerings": courses_for(row),
            "official_url": row["official_document_url"],
            "review_baseline": baseline,
        }

    index = {
        "authority": {
            "readiness_matrix_ref": args.matrix_ref,
            "readiness_matrix_sha256": args.expected_matrix_sha256,
            "review_baseline_manifest_ref": args.source_manifest_ref,
            "review_baseline_manifest_sha256": args.expected_source_manifest_sha256,
        },
        "claim_class": "source_summary",
        "counts": {
            "changed_since_review_baseline": changed_count,
            "current_official_bytes_retained": len(packages),
            "exact_to_review_baseline": exact_count,
            "packages": len(packages),
        },
        "downstream_permission": "private_internal_reference_only",
        "packages": packages,
        "public_redistribution_allowed": False,
        "schema": INDEX_SCHEMA,
    }
    return index, copies


def verify_index(
    args: argparse.Namespace, supplied_value: dict[str, Any] | None = None
) -> dict[str, int]:
    require_tools()
    repo_root, archive_root = validate_locations(args, include_archive=False)
    verify_expected_hash(
        args.source_manifest, args.expected_source_manifest_sha256, "source manifest"
    )
    verify_expected_hash(args.matrix, args.expected_matrix_sha256, "readiness matrix")
    value = supplied_value
    if value is None:
        value = json.loads(args.index.read_text(encoding="utf-8"))
    if value.get("schema") != INDEX_SCHEMA:
        raise ValueError("unexpected index schema")
    if value.get("downstream_permission") != "private_internal_reference_only":
        raise ValueError("unexpected downstream permission")
    if value.get("public_redistribution_allowed") is not False:
        raise ValueError("public redistribution must remain false")
    expected_authority = {
        "readiness_matrix_ref": args.matrix_ref,
        "readiness_matrix_sha256": args.expected_matrix_sha256,
        "review_baseline_manifest_ref": args.source_manifest_ref,
        "review_baseline_manifest_sha256": args.expected_source_manifest_sha256,
    }
    if value.get("authority") != expected_authority:
        raise ValueError(
            "index authority does not match independently supplied seals and references"
        )
    if value.get("claim_class") != "source_summary":
        raise ValueError("unexpected claim class")
    rows = load_rows(args.source_manifest)
    rows_by_id = {row["package_id"]: row for row in rows}
    if matrix_package_ids(args.matrix) != set(rows_by_id):
        raise ValueError("source manifest and readiness matrix package IDs differ")
    packages = value.get("packages", {})
    if set(packages) != set(rows_by_id):
        raise ValueError("index package IDs differ from source authority")
    exact = 0
    changed = 0

    for package_id, row in sorted(packages.items()):
        source = rows_by_id[package_id]
        if row.get("named_offerings") != courses_for(source):
            raise ValueError(f"{package_id}: named offerings mismatch")
        if row.get("official_url") != source["official_document_url"]:
            raise ValueError(f"{package_id}: official URL mismatch")
        if row.get("content_review_state") != "owned_outside_pipeline":
            raise ValueError(f"{package_id}: invalid content-review state")
        if row.get("artifact_role") != artifact_role(source):
            raise ValueError(f"{package_id}: artifact role mismatch")
        baseline = row["review_baseline"]
        current_sha = row["current_artifact_sha256"]
        artifacts = row.get("artifacts", {})
        if current_sha not in artifacts:
            raise ValueError(f"{package_id}: current artifact missing")
        for artifact_sha, artifact in artifacts.items():
            if artifact.get("sha256") != artifact_sha:
                raise ValueError(f"{package_id}: artifact key/hash mismatch")
        if baseline != expected_baseline(source, artifacts):
            raise ValueError(f"{package_id}: baseline projection mismatch")
        for artifact_sha, artifact in artifacts.items():
            path = contained_regular_file(
                repo_root / artifact["archive_path"], archive_root
            )
            expected_path = (
                f"data/input/pdfs/standards/ap_guide_archive/{package_id}/"
                f"{artifact_sha}/{artifact_filename(source)}"
            )
            if artifact["archive_path"] != expected_path:
                raise ValueError(f"{package_id}: archive path mismatch")
            metadata = pdf_metadata(path)
            for key in ("bytes", "encrypted", "pages", "pdf_version", "sha256"):
                if metadata[key] != artifact[key]:
                    raise ValueError(f"{package_id}: {key} mismatch")
            if (
                metadata["detected_effective_labels"]
                != artifact["detected_effective_labels"]
            ):
                raise ValueError(f"{package_id}: detected labels mismatch")
            expected_resolution = label_resolution(
                metadata["detected_effective_labels"],
                baseline["primary_effective_label"],
            )
            for key, expected in expected_resolution.items():
                if artifact.get(key) != expected:
                    raise ValueError(f"{package_id}: historical {key} mismatch")
            try:
                date.fromisoformat(artifact["observed_on"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{package_id}: invalid observed_on") from error
        current = artifacts[current_sha]
        exact_source = (
            current_sha == baseline["sha256"]
            and current["bytes"] == baseline["bytes"]
            and current["pages"] == baseline["pages"]
        )
        if row["comparison_state"] == "exact_august_review_baseline_bytes":
            exact += 1
            if not exact_source or row["archive_state"] != "verified_current_bytes":
                raise ValueError(f"{package_id}: false exact-baseline claim")
        elif row["comparison_state"] == "different_from_august_review_baseline":
            changed += 1
            if (
                exact_source
                or row["archive_state"]
                != "verified_current_bytes_distinct_from_baseline"
            ):
                raise ValueError(f"{package_id}: false changed-source claim")
        else:
            raise ValueError(f"{package_id}: unknown comparison state")
    actual = {
        "changed_since_review_baseline": changed,
        "current_official_bytes_retained": len(packages),
        "exact_to_review_baseline": exact,
        "packages": len(packages),
    }
    if value.get("counts") != actual:
        raise ValueError(
            f"index counts mismatch: expected={value.get('counts')}, actual={actual}"
        )
    return actual


def add_authority_arguments(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--source-manifest", type=Path, required=True)
    command_parser.add_argument("--source-manifest-ref", required=True)
    command_parser.add_argument("--expected-source-manifest-sha256", required=True)
    command_parser.add_argument("--matrix", type=Path, required=True)
    command_parser.add_argument("--matrix-ref", required=True)
    command_parser.add_argument("--expected-matrix-sha256", required=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    archive = subparsers.add_parser(
        "archive", help="archive downloaded PDFs and write the index"
    )
    add_authority_arguments(archive)
    archive.add_argument("--download-dir", type=Path, required=True)
    archive.add_argument("--archive-root", type=Path, required=True)
    archive.add_argument("--index", type=Path, required=True)
    archive.add_argument("--repo-root", type=Path, default=Path.cwd())
    archive.add_argument("--observed-on", required=True)
    verify = subparsers.add_parser(
        "verify", help="verify all bytes and index authority"
    )
    add_authority_arguments(verify)
    verify.add_argument("--index", type=Path, required=True)
    verify.add_argument("--repo-root", type=Path, default=Path.cwd())
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "archive":
        index, copies = build_index(args)
        for candidate, destination, expected_sha in copies:
            atomic_copy(candidate, destination, expected_sha)
        verify_index(args, index)
        atomic_write_json(args.index, index)
        print(json.dumps(index["counts"], sort_keys=True))
        return 0
    counts = verify_index(args)
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
