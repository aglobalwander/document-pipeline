"""Hermetic checks for the R1 read: code matching, the tail fallback, and the region read.

`locate` takes its documents as an argument, so these run on synthetic layers and cells.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_ncas_held_rows_read import locate, squish  # noqa: E402


def doc(file, sha, layer=(), cells=()):
    return {"file": file, "sha": sha, "layer": list(layer), "cells": list(cells)}


def rec(text, page=1, md_line=1, bbox=(10.0, 20.0, 60.0, 30.0)):
    return {"text": text, "page": page, "md_line": md_line, "bbox": list(bbox)}


def row(code="", as_printed="", statement="A statement"):
    return {"code": code, "code_as_printed": as_printed, "statement_as_km_holds_it": statement}


def test_an_exact_code_match_reports_the_cell_page_and_bbox():
    documents = [doc("Music at a Glance.pdf", "abc", cells=[
        {"column_code_printed": "MU:Cr2.1.1a", "inline_code": None, "page": 9,
         "bbox": [70.0, 245.5, 200.0, 258.0], "printed": "MU:Cr2.1.1a  With limited"}])]

    out = locate(row("MU:Cr2.1.1a", "MU:Cr2.1.1a"), documents)

    assert out["status"] == "printed"
    assert out["match_kind"] == "exact"
    assert out["page"] == 9 and out["pdf_sha256"] == "abc"


def test_an_anchor_title_row_matches_the_printed_title():
    """The 115 rows with no code: their printed form is the anchor title, not a code."""
    documents = [doc("Media Arts at a Glance.pdf", "def", layer=[
        rec("Anchor Standard 1:  Generate and conceptualize artistic ideas and work.", page=1)])]

    out = locate(row("", "Anchor Standard 1", "Generate and conceptualize artistic ideas"), documents)

    assert out["status"] == "printed"
    assert out["page"] == 1 and out["document"] == "Media Arts at a Glance.pdf"


def test_a_corrupt_prefix_still_matches_its_tail_and_is_flagged():
    documents = [doc("Music Tech Strand at a Glance.pdf", "ghi", layer=[rec("CN11.0.T.IIa", page=4)])]

    out = locate(row("MU-T:CN11.0.T.IIa", "MU-T:CN11.0.T.IIa"), documents)

    assert out["status"] == "printed"
    assert out["match_kind"] == "tail", "a corrupt prefix must not be reported as an exact hit"
    assert out["matched_as_printed"] == "CN11.0.T.IIa" and out["page"] == 4


def test_an_unread_row_is_a_named_region_not_a_blank():
    documents = [doc("Theatre at a Glance.pdf", "jkl", layer=[rec("Something else", page=2)])]

    out = locate(row("ZZ:Cr9.9.9", "ZZ:Cr9.9.9", "A statement that does not print"), documents)

    assert out["status"] == "no_printed_code"
    assert "searched 1 documents" in out["region_read"]
    assert "Theatre at a Glance.pdf" in out["region_read"]


def test_the_region_read_names_where_the_statement_opening_does_appear():
    documents = [doc("Dance at a Glance.pdf", "mno", layer=[
        rec("A statement that does not print is here", page=7)])]

    out = locate(row("ZZ:Cr9.9.9", "ZZ:Cr9.9.9", "A statement that does not print"), documents)

    assert out["status"] == "no_printed_code"
    assert "p7" in out["region_read"]


def test_codes_compare_without_case_whitespace_or_punctuation():
    assert squish("MU:Cr2.1.1a") == squish("mu : cr2 . 1 . 1a")
    assert squish(None) == ""