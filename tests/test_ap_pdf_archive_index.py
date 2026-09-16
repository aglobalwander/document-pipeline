"""Static contracts for the tracked AP raw-PDF edition index."""

import json
import sys
from argparse import Namespace
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "scripts/standards/ap_editions.json"
SCRIPT_DIR = ROOT / "scripts/standards"
sys.path.insert(0, str(SCRIPT_DIR))

# Depends on the gitignored AP raw-PDF corpus under data/input; excluded by default.
pytestmark = pytest.mark.integration

import ap_pdf_archive as archive_module  # noqa: E402
from ap_pdf_archive import (
    detected_source_labels,
    label_resolution,
    load_rows,
)  # noqa: E402


def load_index():
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def test_ap_index_is_complete_private_and_product_neutral():
    index = load_index()

    assert index["schema"] == "pipeline-documents.ap-pdf-edition-index.v2"
    assert index["downstream_permission"] == "private_internal_reference_only"
    assert index["public_redistribution_allowed"] is False
    assert index["counts"] == {
        "changed_since_review_baseline": 2,
        "current_official_bytes_retained": 40,
        "exact_to_review_baseline": 38,
        "packages": 40,
    }
    assert len(index["packages"]) == 40
    assert sum(len(row["named_offerings"]) for row in index["packages"].values()) == 43

    serialized = json.dumps(index).lower()
    assert "/users/" not in serialized
    assert "drupal" not in serialized
    assert "curriculearn" not in serialized


def test_ap_index_uses_content_addressed_paths_and_exact_comparison_states():
    index = load_index()
    changed = set()

    for package_id, row in index["packages"].items():
        assert row["current_artifact_sha256"] in row["artifacts"]
        current = row["artifacts"][row["current_artifact_sha256"]]
        path = current["archive_path"]
        assert path.startswith(
            f"data/input/pdfs/standards/ap_guide_archive/{package_id}/"
        )
        assert f"/{current['sha256']}/" in path
        assert row["official_url"].startswith(
            "https://apcentral.collegeboard.org/media/pdf/"
        )

        assert row["content_review_state"] == "owned_outside_pipeline"
        if row["comparison_state"] == "exact_august_review_baseline_bytes":
            assert current["sha256"] == row["review_baseline"]["sha256"]
            assert row["archive_state"] == "verified_current_bytes"
        else:
            changed.add(package_id)
            assert row["comparison_state"] == "different_from_august_review_baseline"
            assert current["sha256"] != row["review_baseline"]["sha256"]
            assert (
                row["archive_state"] == "verified_current_bytes_distinct_from_baseline"
            )

    assert changed == {"ap-art-and-design", "ap-music-theory"}


def test_current_art_and_music_labels_do_not_inherit_stale_baseline_metadata():
    packages = load_index()["packages"]
    art = packages["ap-art-and-design"]
    music = packages["ap-music-theory"]
    art_current = art["artifacts"][art["current_artifact_sha256"]]
    music_current = music["artifacts"][music["current_artifact_sha256"]]

    assert art["review_baseline"]["primary_effective_label"] == "Effective Fall 2024"
    assert art_current["effective_label"] == "Effective Fall 2026"
    assert art_current["label_resolution_state"] == "single_detected_label"
    assert music["review_baseline"]["primary_effective_label"] == "Effective Fall 2026"
    assert music_current["effective_label"] == "Effective Fall 2026"
    assert music_current["label_resolution_state"] == "single_detected_label"


def test_pilot_and_multiple_label_documents_fail_closed():
    pilot = detected_source_labels(
        "",
        "For Use Beginning with the 2024-25 School Year Pilot",
    )
    assert pilot == ["For Use Beginning with the 2024-25 School Year Pilot"]
    assert label_resolution(pilot, pilot[0])["effective_label"] == pilot[0]

    multiple = ["Effective Fall 2024", "Effective Fall 2026"]
    resolved = label_resolution(multiple, "Effective Fall 2026")
    assert resolved["effective_label"] is None
    assert resolved["baseline_primary_label_present"] is True
    assert (
        resolved["label_resolution_state"] == "multiple_detected_labels_review_required"
    )


def test_real_index_keeps_ambiguous_labels_as_review_holds():
    packages = load_index()["packages"]
    for package_id in ("ap-precalculus", "ap-psychology"):
        row = packages[package_id]
        current = row["artifacts"][row["current_artifact_sha256"]]
        assert current["effective_label"] is None
        assert current["baseline_primary_label_present"] is True
        assert (
            current["label_resolution_state"]
            == "multiple_detected_labels_review_required"
        )

    networking = packages["ap-networking"]
    current = networking["artifacts"][networking["current_artifact_sha256"]]
    assert current["effective_label"] == (
        "For Use Beginning with the 2026-2027 School Year Pilot"
    )
    assert current["label_resolution_state"] == "single_detected_label"


def test_source_manifest_rejects_incomplete_package_set(tmp_path):
    rows = []
    for number in range(39):
        rows.append(
            {
                "official_courses": [f"Course {number}"],
                "official_document_url": f"https://example.test/{number}.pdf",
                "package_id": f"ap-test-{number}",
                "snapshot_path": f"snapshots/{number}.md",
                "source_pdf_bytes": 1,
                "source_pdf_pages": 1,
                "source_pdf_sha256": f"{number:064x}",
                "source_retrieved_on": "2026-08-16",
            }
        )
    truncated = tmp_path / "manifest.json"
    truncated.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="40 unique packages"):
        load_rows(truncated)


def synthetic_verifier_contract(tmp_path):
    repo = tmp_path / "repo"
    index_path = repo / "scripts/standards/ap_editions.json"
    archive_root = repo / "data/input/pdfs/standards/ap_guide_archive"
    rows = []
    matrix_rows = []
    packages = {}
    metadata_by_path = {}
    for number in range(40):
        package_id = f"ap-test-{number}"
        artifact_sha = f"{number + 1:064x}"
        offerings = [f"Course {number}"]
        if number < 3:
            offerings.append(f"Course {number} companion")
        source = {
            "official_courses": offerings,
            "official_document_url": "https://example.test/guide.pdf",
            "official_effective_label": "Effective Fall 2026",
            "official_primary_effective_label": "Effective Fall 2026",
            "package_id": package_id,
            "snapshot_path": f"snapshots/{package_id}.md",
            "source_pdf_bytes": 10,
            "source_pdf_pages": 1,
            "source_pdf_sha256": artifact_sha,
            "source_retrieved_on": "2026-08-16",
        }
        rows.append(source)
        matrix_rows.append({"package_id": package_id})
        relative = (
            f"data/input/pdfs/standards/ap_guide_archive/{package_id}/"
            f"{artifact_sha}/guide.pdf"
        )
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")
        metadata = {
            "bytes": 10,
            "detected_effective_labels": ["Effective Fall 2026"],
            "encrypted": "no",
            "mime_type": "application/pdf",
            "pages": 1,
            "pdf_version": "1.7",
            "sha256": artifact_sha,
        }
        metadata_by_path[str(path.resolve())] = metadata
        artifact = {
            "archive_path": relative,
            "bytes": 10,
            "encrypted": "no",
            "observed_on": "2026-08-29",
            "pages": 1,
            "pdf_version": "1.7",
            "sha256": artifact_sha,
            **label_resolution(["Effective Fall 2026"], "Effective Fall 2026"),
        }
        packages[package_id] = {
            "archive_state": "verified_current_bytes",
            "artifact_role": "course_and_exam_description",
            "artifacts": {artifact_sha: artifact},
            "comparison_state": "exact_august_review_baseline_bytes",
            "content_review_state": "owned_outside_pipeline",
            "current_artifact_sha256": artifact_sha,
            "named_offerings": offerings,
            "official_url": source["official_document_url"],
            "review_baseline": archive_module.expected_baseline(
                source, {artifact_sha: artifact}
            ),
        }
    manifest = tmp_path / "manifest.json"
    matrix = tmp_path / "matrix.json"
    manifest.write_text(json.dumps(rows), encoding="utf-8")
    matrix.write_text(json.dumps({"rows": matrix_rows}), encoding="utf-8")
    manifest_sha = sha256(manifest.read_bytes()).hexdigest()
    matrix_sha = sha256(matrix.read_bytes()).hexdigest()
    args = Namespace(
        archive_root=archive_root,
        expected_matrix_sha256=matrix_sha,
        expected_source_manifest_sha256=manifest_sha,
        index=index_path,
        matrix=matrix,
        matrix_ref="authority:matrix.json",
        repo_root=repo,
        source_manifest=manifest,
        source_manifest_ref="authority:manifest.json",
    )
    index = {
        "authority": {
            "readiness_matrix_ref": args.matrix_ref,
            "readiness_matrix_sha256": matrix_sha,
            "review_baseline_manifest_ref": args.source_manifest_ref,
            "review_baseline_manifest_sha256": manifest_sha,
        },
        "claim_class": "source_summary",
        "counts": {
            "changed_since_review_baseline": 0,
            "current_official_bytes_retained": 40,
            "exact_to_review_baseline": 40,
            "packages": 40,
        },
        "downstream_permission": "private_internal_reference_only",
        "packages": packages,
        "public_redistribution_allowed": False,
        "schema": "pipeline-documents.ap-pdf-edition-index.v2",
    }
    return args, index, metadata_by_path


def test_verifier_uses_external_seals_and_rejects_key_or_baseline_drift(
    tmp_path, monkeypatch
):
    args, index, metadata_by_path = synthetic_verifier_contract(tmp_path)
    monkeypatch.setattr(archive_module, "require_tools", lambda: None)
    monkeypatch.setattr(
        archive_module,
        "pdf_metadata",
        lambda path: metadata_by_path[str(path.resolve())],
    )
    assert archive_module.verify_index(args, index)["packages"] == 40

    authority_drift = deepcopy(index)
    authority_drift["authority"]["review_baseline_manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="independently supplied"):
        archive_module.verify_index(args, authority_drift)

    key_drift = deepcopy(index)
    first = key_drift["packages"]["ap-test-0"]
    artifact = first["artifacts"].pop(first["current_artifact_sha256"])
    false_key = "f" * 64
    first["artifacts"][false_key] = artifact
    first["current_artifact_sha256"] = false_key
    with pytest.raises(ValueError, match="artifact key/hash mismatch"):
        archive_module.verify_index(args, key_drift)

    baseline_drift = deepcopy(index)
    baseline_drift["packages"]["ap-test-0"]["review_baseline"][
        "primary_effective_label"
    ] = "Effective Fall 2025"
    with pytest.raises(ValueError, match="baseline projection mismatch"):
        archive_module.verify_index(args, baseline_drift)


def test_archive_locations_and_package_ids_fail_closed(tmp_path):
    args, _, _ = synthetic_verifier_contract(tmp_path)
    args.archive_root = args.repo_root / "somewhere-else"
    with pytest.raises(ValueError, match="canonical path"):
        archive_module.validate_locations(args, include_archive=True)
    with pytest.raises(ValueError, match="unsafe package_id"):
        archive_module.validate_package_id("../escape")
