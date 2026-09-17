"""Hermetic checks for the P3 row reads and their acceptance gate.

The reader and the gate normally read PDFs from the OneDrive source store, which the default suite
must not depend on. These tests cover the pure helpers and drive ``check_p3_reads.check`` with the
page readers monkeypatched, so the PASS/FAIL contract is exercised without a PDF. The end-to-end run
against the store stays in the handoff evidence, not here.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

import check_p3_reads as gate  # noqa: E402
import km_row_reads as reader  # noqa: E402

SHA = "a" * 64


def make_row(rid="P3-0001", status="read", text="Alpha beta", regions=None, other=None):
    return {
        "request_id": rid,
        "framework": "ap",
        "status": status,
        "pdf_sha256": SHA,
        "printed_text": text,
        "regions": regions if regions is not None else [
            {"page": 1, "bbox": [0.0, 0.0, 10.0, 10.0], "crop": "crops/P3-0001_p1.png"}],
        "printed_in_other_documents": other or [],
    }


@pytest.mark.parametrize("raw,expected", [
    ("Explain\u2019s", "explains"),      # curly apostrophe is the printed form
    ("LO", "lo"),
    ("1.A.i", "1ai"),
    ("(MA:Re8.1.PK)", "mare81pk"),       # punctuation dropped, never repaired
    ("\u2013III", "iii"),
])
def test_norm_flattens_printed_form_for_comparison_only(raw, expected):
    assert reader.norm(raw) == expected


def test_tokens_split_on_whitespace_slash_and_dashes():
    assert reader.tokens("LO 1.A.i") == ["lo", "1ai"]
    assert reader.tokens("a/b\u2013c\u2014d") == ["a", "b", "c", "d"]


@pytest.mark.parametrize("key,expected", [
    ("LO", True), ("EK", True), ("KC-2.1", True), ("Unit", True), ("2.1.A", True),
    ("1.A.i", False), ("AA.1", False),
])
def test_code_start_recognises_the_printed_row_keys(key, expected):
    assert bool(reader.CODE_START.match(key)) is expected


def test_region_pages_and_crop_refs_cover_main_and_other_documents():
    row = make_row(regions=[
        {"page": 2, "bbox": [0, 0, 1, 1], "crop": "crops/a.png"},
        {"page": 1, "bbox": [0, 0, 1, 1]},
    ], other=[{"regions": [{"page": 3, "bbox": [0, 0, 1, 1], "crop": "crops/b.png"}]}])

    assert gate.region_pages(row) == [1, 2]
    assert gate.crop_refs(row) == ["crops/a.png", "crops/b.png"]


def test_is_ordered_subsequence_rejects_reordering():
    assert gate.is_ordered_subsequence(["a", "b"], ["a", "x", "b"]) is True
    assert gate.is_ordered_subsequence(["b", "a"], ["a", "b"]) is False
    assert gate.is_ordered_subsequence([], ["a"]) is True


def patch_pages(monkeypatch, available, stream=None):
    monkeypatch.setattr(gate, "region_page_tokens",
                        lambda sha, pages: Counter(available))
    monkeypatch.setattr(gate, "region_stream",
                        lambda sha, row, pad=3.0: list(stream if stream is not None else available))


def test_check_passes_when_every_token_is_printed_and_every_crop_exists(monkeypatch, tmp_path):
    (tmp_path / "crops").mkdir()
    (tmp_path / "crops" / "P3-0001_p1.png").write_bytes(b"x")
    patch_pages(monkeypatch, ["alpha", "beta"])

    presence, crops, order = gate.check([make_row()], tmp_path)

    assert presence == [] and crops == [] and order == []


def test_check_fails_presence_when_a_token_is_not_printed(monkeypatch, tmp_path):
    (tmp_path / "crops").mkdir()
    (tmp_path / "crops" / "P3-0001_p1.png").write_bytes(b"x")
    patch_pages(monkeypatch, ["alpha"])  # 'beta' is not on the page

    presence, crops, _ = gate.check([make_row()], tmp_path)

    assert crops == []
    assert presence and presence[0][0] == "P3-0001"
    assert "beta" in presence[0][1]


def test_check_fails_crops_when_the_crop_file_is_absent(monkeypatch, tmp_path):
    patch_pages(monkeypatch, ["alpha", "beta"])

    presence, crops, _ = gate.check([make_row()], tmp_path)

    assert presence == []
    assert crops == [("P3-0001", "crops/P3-0001_p1.png")]


def test_check_reports_order_without_failing(monkeypatch, tmp_path):
    (tmp_path / "crops").mkdir()
    (tmp_path / "crops" / "P3-0001_p1.png").write_bytes(b"x")
    patch_pages(monkeypatch, ["beta", "alpha"])  # same tokens, linearised the other way

    presence, crops, order = gate.check([make_row()], tmp_path)

    assert presence == [] and crops == []
    assert [f[0] for f in order] == ["P3-0001"]


def test_check_skips_presence_for_non_text_statuses_but_still_checks_crops(monkeypatch, tmp_path):
    patch_pages(monkeypatch, [])
    rows = [make_row(rid="P3-0002", status="not_in_document", text="")]
    rows[0]["regions"] = [{"page": 4, "bbox": [0, 0, 1, 1], "crop": "crops/missing.png"}]

    presence, crops, order = gate.check(rows, tmp_path)

    assert presence == [] and order == []
    assert crops == [("P3-0002", "crops/missing.png")]


def write_reads(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_main_exits_nonzero_on_presence_fail_and_zero_on_pass(monkeypatch, tmp_path, capsys):
    reads = tmp_path / "reads.jsonl"
    write_reads(reads, [make_row()])
    monkeypatch.setattr(gate, "region_page_tokens", lambda sha, pages: Counter(["alpha", "beta"]))
    monkeypatch.setattr(gate, "region_stream", lambda sha, row, pad=3.0: ["alpha", "beta"])
    (tmp_path / "crops").mkdir()
    (tmp_path / "crops" / "P3-0001_p1.png").write_bytes(b"x")

    monkeypatch.setattr(sys, "argv", ["check_p3_reads.py", "--reads", str(reads)])
    gate.main()
    assert "P3 acceptance: PASS" in capsys.readouterr().out

    monkeypatch.setattr(gate, "region_page_tokens", lambda sha, pages: Counter(["alpha"]))
    with pytest.raises(SystemExit) as excinfo:
        gate.main()
    assert excinfo.value.code == 1
    assert "presence (hard): FAIL" in capsys.readouterr().out