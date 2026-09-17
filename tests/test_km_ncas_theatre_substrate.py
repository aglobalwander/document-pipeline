"""Hermetic checks for the substrate that turns the withheld reads into joins.

`build_substrate` is pure over the document records.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_ncas_theatre_substrate import build_substrate  # noqa: E402


def cell(code, band="K", page=4, inline=None, bbox=(10.0, 20.0, 60.0, 30.0)):
    return {"column_code_printed": code, "inline_code": inline, "column_header": band,
            "page": page, "bbox": list(bbox)}


def doc(file, cells):
    return {"file": file, "sha": "sha-" + file[:4], "cells": cells}


def test_a_code_printed_in_two_documents_names_both():
    """The 315's real problem: 557 codes print in more than one document, so identity is ambiguous."""
    documents = [doc("Music at a Glance.pdf", [cell("MU:Cr2.1.1a")]),
                 doc("Music Tech Strand at a Glance.pdf", [cell("MU:Cr2.1.1a")])]

    index, _ = build_substrate(documents)

    assert set(index["MU:Cr2.1.1a"]["documents"]) == {
        "Music at a Glance.pdf", "Music Tech Strand at a Glance.pdf"}
    assert sum(index["MU:Cr2.1.1a"]["documents"].values()) == 2


def test_the_inline_form_is_indexed_too_and_keeps_the_first_occurrence():
    documents = [doc("Music Tech Strand at a Glance.pdf", [cell(None, inline="MU:Cr1.1.T.Ia", page=4)]),
                 doc("Music Tech Strand at a Glance.pdf", [cell(None, inline="MU:Cr1.1.T.Ia", page=5)])]

    index, _ = build_substrate(documents)

    entry = index["MU:Cr1.1.T.Ia"]
    # `occurrences` is derived when the CSV is written; the index itself holds the per-document count.
    assert sum(entry["documents"].values()) == 2
    assert entry["first_page"] == 4, "the first printed page is kept, not the last"


def test_theatre_cells_carry_their_printed_band():
    documents = [doc("Theatre at a Glance.pdf", [cell("TH:Cr1.1.PK.", band="PreK", page=1, bbox=(5.0, 6.0, 7.0, 8.0))]),
                 doc("Music at a Glance.pdf", [cell("MU:Cr1.1.K", band="K")])]

    _, theatre = build_substrate(documents)

    assert len(theatre) == 1, "only the Theatre document contributes Theatre rows"
    assert theatre[0]["printed_code"] == "TH:Cr1.1.PK." and theatre[0]["band_as_printed"] == "PreK"
    assert theatre[0]["page"] == 1 and theatre[0]["bbox"] == "[5.0, 6.0, 7.0, 8.0]"