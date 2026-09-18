"""Hermetic checks for the R6 read: the whitespace-blind key, the span rule, and the bar that stops an
incidental run being reported as a location.

That last one is the point. The read's worst failure mode is not a miss, it is a match: a run of
characters that happens to occur in a 400-page course description, reported as the printed text of a
row that is not in the document at all. Three of these tests use figures measured on the real AP
Latin rows, where the incidental runs were 16-36 characters of rows 56-747 characters long.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_r6_printed_text_read import (as_printed, build_pages, cover, find, is_contiguous,  # noqa: E402
                                     longest_run, partial_is_a_location, solid, tokens)


def rec(text, page=1, top=100.0):
    return {"md_line": 1, "page": page, "bbox": [85.0, top, 400.0, top + 11.0], "text": text,
            "spans": [{"text": text, "font": "Arial", "size": 10.0, "bold": False}]}


def test_the_key_is_blind_to_whitespace_because_a_lost_space_is_the_row():
    assert solid("in one country") == solid("inonecountry")
    assert solid("inone country") == solid("in onecountry")


def test_the_key_drops_the_punctuation_the_notation_prints():
    assert solid("f (\u03b8 ) = sec \u03b8") == solid("f(\u03b8)=sec\u03b8")


def test_the_key_survives_the_control_characters_the_pdf_layer_emits_for_spaces():
    assert solid("society\x03and\x03culture") == solid("society and culture")


def test_tokens_treat_control_characters_as_separators():
    """The AP layers emit `\\x03` for a space; counting that as one token would falsify every count."""
    assert tokens("society\x03and\x03culture") == ["society", "and", "culture"]


def test_a_row_that_lost_its_spaces_is_located_and_the_printed_tokenisation_comes_back():
    printed = "Social impact of the Great Depression in one country in the Americas"
    pages = build_pages([rec(printed, page=210)])
    hits = find(solid("Social impact of the Great Depression inonecountry in the Americas"), pages)

    assert hits and hits[0]["page"] == 210
    assert hits[0]["text"] == printed, "the guide's own tokenisation, not the row's"


def test_a_span_returns_only_the_lines_it_covers_and_their_union():
    pages = build_pages([rec("Above", page=1, top=10.0), rec("Target run", page=1, top=20.0),
                         rec("Below", page=1, top=30.0)])
    page = pages[1]
    hit = cover(1, page, page["solid"].index(solid("Target")), len(solid("Target")))

    assert [r["text"] for r in hit["recs"]] == ["Target run"]
    assert hit["bbox"] == [85.0, 20.0, 400.0, 31.0]


def test_a_run_split_over_two_printed_lines_returns_both():
    pages = build_pages([rec("AO1.", page=17, top=20.0),
                         rec("Knowledge and understanding", page=17, top=30.0)])
    hits = find(solid("AO1. Knowledge and understanding"), pages)

    assert hits and hits[0]["lines"] == 2


def test_a_span_never_crosses_a_page_break():
    pages = build_pages([rec("Alpha", page=1), rec("Beta", page=2)])

    assert find(solid("Alpha Beta"), pages) == []


def test_the_longest_run_names_what_is_not_printed_on_either_side():
    pages = build_pages([rec("the reciprocal of the cosine function", page=102)])
    row = "prefix: the recprocal of the cosine function :suffix"
    run = longest_run(solid(row), pages)

    assert run is not None and run["length"] > 20
    assert run["start_in_row"] > 0, "the row's head is not printed"
    tail = len(solid(row)) - run["start_in_row"] - run["length"]
    assert tail > 0, "the row's tail is not printed"


def test_a_longest_run_below_the_floor_is_not_a_run_at_all():
    pages = build_pages([rec("the reciprocal of the cosine function", page=102)])

    assert longest_run(solid("xy"), pages) is None


def test_an_incidental_run_is_not_a_location():
    """Measured on the real AP Latin rows: 16-36 characters of rows 56-747 characters long."""
    assert partial_is_a_location(36, 320) is False
    assert partial_is_a_location(17, 71) is False
    assert partial_is_a_location(24, 745) is False
    assert partial_is_a_location(0, 100) is False
    assert partial_is_a_location(140, 424) is False, "140 of 424 is 33% — still not the row"


def test_a_substantial_run_is_a_location():
    assert partial_is_a_location(40, 80) is True
    assert partial_is_a_location(75, 100) is True
    assert partial_is_a_location(300, 310) is True


def test_contiguity_is_order_sensitive():
    assert is_contiguous(["a", "b", "c"], ["b", "c"]) is True
    assert is_contiguous(["a", "b", "c"], ["c", "b"]) is False
    assert is_contiguous(["a"], ["a", "b"]) is False


def test_control_characters_come_back_as_spaces_not_as_bytes():
    """The AP layer's `\\x03` is where a space belongs; returning it verbatim is unusable."""
    assert as_printed("electric\x03and\x03magnetic") == "electric and magnetic"
    assert as_printed("  spaced   out  ") == "spaced out"