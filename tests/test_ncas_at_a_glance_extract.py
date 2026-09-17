"""Hermetic checks for the NCAS 'At a Glance' cell parsing (KM request P2).

The extractor reads PDFs by sha256 from the OneDrive store; these tests cover the pure line/item
parsers and the flag rules, which is where the printed-form decisions live. Nothing here needs a
fixture. The rules asserted are the ones the P2 return to KM describes: codes are kept as printed
and irregular forms are flagged for KM to rule on, never repaired.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

import ncas_at_a_glance_extract as ncas  # noqa: E402


def line(text, first_span=None, bold=False):
    return {"text": text, "first_span": first_span or text.split()[0], "first_bold": bold}


def item(inline=None, column=None, header="Pre K"):
    return {"inline_code": inline, "column_code_printed": column, "column_header": header}


def test_item_start_keeps_an_inline_code_exactly_as_printed():
    letter, code, text = ncas.item_start(line("MU:Cr1.1.T.Ia Demonstrate",
                                             first_span="MU:Cr1.1.T.Ia", bold=True))

    assert (letter, code, text) == (None, "MU:Cr1.1.T.Ia", "Demonstrate")


@pytest.mark.parametrize("raw,expected", [
    ("a. Generate and conceptualize artistic ideas", ("a", None, "Generate and conceptualize artistic ideas")),
    ("c \u2013 Explore", ("c", None, "Explore")),          # dash-separated printed form
    ("2a Demonstrate", ("2a", None, "Demonstrate")),      # Music Cn10 typo form ('2a')
])
def test_item_start_reads_lettered_parts(raw, expected):
    assert ncas.item_start(line(raw, first_span=raw.split()[0])) == expected


def test_item_start_rejects_text_that_only_looks_lettered():
    assert ncas.item_start(line("b) Explore", first_span="b)")) is None
    # '2a' is only an item start when the line's first span actually starts with it.
    assert ncas.item_start(line("2a Demonstrate", first_span="x")) is None


def test_flags_report_punctuation_and_shape_without_repairing_the_code():
    assert ncas.flags_for(item("(MA:Re8.1.PK)")) == ["code_punctuation_printed"]

    # Theatre's 'TH:Cn11.2.-1.' keeps its hyphen, so the shape check still flags it.
    assert ncas.flags_for(item("TH:Cn11.2.-1.")) == [
        "code_punctuation_printed", "code_space_or_hyphen_printed", "code_irregular_shape"]


def test_flags_mark_a_roman_level_in_the_standard_position():
    assert ncas.flags_for(item("MU:Pr4.I.T.Ia", header="HS Proficient")) == [
        "code_irregular_shape", "roman_or_letter_in_standard_position"]


def test_flags_distinguish_a_roman_band_in_a_high_school_column_from_one_outside_it():
    # Roman numerals are the band by design in HS columns; elsewhere they are reported.
    assert ncas.flags_for(item("DA:Cr1.1.I", header="HS Proficient")) == []
    assert ncas.flags_for(item("DA:Cr1.1.I", header="Pre K")) == ["roman_level_outside_HS_column"]


def test_flags_report_a_missing_printed_code():
    assert ncas.flags_for(item(None, None)) == ["no_printed_code"]


@pytest.mark.parametrize("label", ["Pre K", "PreK", "Kindergarten", "K", "3rd", "HS Advanced",
                                   "Novice", "Intermediate", "Proficient", "Accomplished", "Advanced"])
def test_grade_and_band_labels_are_recognised(label):
    assert ncas.GRADE.match(label)


def test_process_labels_are_not_grade_labels():
    for label in ("CREATING", "RESPONDING", "PERFORMING/PRESENTING/PRODUCING"):
        assert ncas.GRADE.match(label) is None
        assert label in ncas.PROCESSES


@pytest.mark.parametrize("text", ["Anchor Standard 1: Generate and conceptualize",
                                  "Enduring Understanding: Creativity",
                                  "Essential Question(s): What is art?"])
def test_block_headers_are_recognised(text):
    assert ncas.BAND.match(text)


def test_page_furniture_is_recognised_so_it_is_not_read_as_a_cell():
    for text in ("Page 12", "Copyright 2014", "All rights reserved",
                 "State Education Agency Directors of Arts Education"):
        assert ncas.FOOTER.match(text)