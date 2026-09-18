"""Hermetic checks for the prose-adjacency read: notation dropped, line breaks dropped.

Ruling A says AP's notation breaks adjacency, not presence. Two measurements follow from it and both
are pinned here: notation spans must leave the stream, and the guides breaking a word across two lines
(`pho` / `tographs`) must not, or a word the layer split can never be found.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_ap_prose_adjacency_read import is_notation, prose_pages, solid  # noqa: E402


def span(text, font="AktivGrotesk-Regular", size=10.0):
    return {"text": text, "font": font, "size": size, "bold": False}


def rec(text, spans, page=1, top=100.0):
    return {"md_line": 1, "page": page, "bbox": [85.0, top, 400.0, top + 11.0], "text": text,
            "spans": spans}


def test_the_notation_families_km_named_are_not_prose():
    for font in ("MinionPro-Regular", "STIXGeneral", "SymbolMT", "EuclidMathOne", "Wingdings",
                 "ZapfDingbatsITC", "AppleSymbols"):
        assert is_notation(font), font


def test_the_prose_families_are_prose():
    for font in ("AktivGrotesk-Regular", "Lexia-Regular", "ArialMT"):
        assert not is_notation(font), font


def test_notation_spans_leave_the_stream():
    _, streams = prose_pages([
        rec("The secant function, f", [span("The secant function, f")]),
        rec("f of theta equals secant theta",
            [span("f of theta equals secant theta", font="MinionPro-Regular")]),
        rec("is the reciprocal", [span("is the reciprocal")]),
    ])

    assert streams[0] == solid("The secant function, f is the reciprocal")
    assert "foftheta" not in streams[0]


def test_a_line_break_does_not_split_a_word():
    """`pho` and `tographs` are one printed word; the stream must carry it whole."""
    _, streams = prose_pages([rec("pho", [span("pho")]),
                              rec("tographs of the case", [span("tographs of the case")])])

    assert "photographs" in streams[0]


def test_the_printed_line_comes_back_whole_and_as_printed():
    pages, _ = prose_pages([rec("The secant function, f", [span("The secant function, f")])])

    assert pages[1]["recs"][0]["text"] == "The secant function, f"
    assert pages[1]["recs"][0]["_solid"] == solid("The secant function, f")


def test_a_line_of_pure_notation_contributes_no_stream():
    _, streams = prose_pages([rec("3.11.A.1", [span("3.11.A.1", font="MinionPro-Regular")])])

    assert streams == []


def test_a_row_clipped_at_its_start_is_still_a_run_of_the_printed_text():
    """`he secant` for `The secant` is still found, because it matches from the second character.

    Counterintuitive and worth pinning: a row that lost a character is a run of the printed text, which
    is exactly why the read can locate a clipped row at all.
    """
    _, streams = prose_pages([rec("The secant function", [span("The secant function")])])

    assert solid("he secant function") in streams[0]


def test_a_row_damaged_inside_a_word_is_not_a_run():
    """`eciprocal` lost a character mid-word, so the row cannot be a run of the printed text."""
    _, streams = prose_pages([rec("the reciprocal of the cosine function",
                                  [span("the reciprocal of the cosine function")])])

    assert solid("the eciprocal of the cosine function") not in streams[0]


def test_dropping_the_notation_is_what_makes_the_row_contiguous():
    """Ruling A in one case: with the notation line left in, the row is not a run of the stream."""
    _, streams = prose_pages([
        rec("The secant function, f", [span("The secant function, f")]),
        rec("f of theta equals secant theta",
            [span("f of theta equals secant theta", font="MinionPro-Regular")]),
        rec("is the reciprocal", [span("is the reciprocal")]),
    ])

    assert solid("The secant function, f is the reciprocal") in streams[0]