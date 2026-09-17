"""Hermetic checks for the reference-spine context pass.

The heading rule and the context lookup are pure: they read records, not PDFs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

import km_reference_context as ctx  # noqa: E402
from ib_depth_to_statements import dedupe  # noqa: E402
from km_p4_statements import is_large_heading, looks_like_heading, printed_qualifier  # noqa: E402
from km_text_layer import marker_resolution, read_markers  # noqa: E402


def rec(text, md_line, size=9.5, bold=False):
    return {"text": text, "md_line": md_line, "spans": [{"size": size, "bold": bold}]}


def test_a_larger_span_marks_a_heading():
    assert is_large_heading(rec("Making art", 40, size=14.0), 10.5) is True
    assert is_large_heading(rec("Body copy line", 41, size=9.5), 10.5) is False


def test_a_short_bold_line_is_a_heading_but_a_sentence_is_not():
    assert is_large_heading(rec("Artistic processes", 40, bold=True), 9.0) is True
    assert is_large_heading(rec("This bold sentence ends with a full stop.", 40, bold=True),
                            9.0) is False
    assert is_large_heading(rec(" ".join(["word"] * 9), 40, bold=True), 9.0) is False


def test_long_lines_are_never_headings_however_they_are_set():
    assert is_large_heading(rec("x" * 200, 40, size=20.0), 10.5) is False


def test_wrapped_prose_fragments_are_not_headings():
    """KM's complaint about the first spine pass: a wrapped bold line became the topic."""
    assert looks_like_heading("Supporting details (further ex") is False
    assert looks_like_heading("examples)") is False
    assert looks_like_heading("The guide continues into") is False
    assert looks_like_heading("lowercase opinion") is False
    assert looks_like_heading("Structure 1. Models of the particulate nature of matter") is True


def test_context_returns_the_two_nearest_headings_above_the_row():
    layer = [rec("Theme: Art making", 10, size=14.0), rec("body", 12),
             rec("Topic: Experiments", 20, size=12.5), rec("body", 22),
             rec("body", 30), rec("the row itself", 40)]

    theme, topic, back = ctx.context_for(40, layer)

    assert (theme, topic) == ("Theme: Art making", "Topic: Experiments")
    assert back == 20


def test_context_is_none_when_nothing_headed_precedes_the_row():
    layer = [rec("body", 10), rec("body", 20)]

    assert ctx.context_for(20, layer) == (None, None, None)


def test_context_ignores_lines_at_or_below_the_row():
    layer = [rec("Heading after", 50, size=14.0), rec("body", 10)]

    assert ctx.context_for(20, layer) == (None, None, None)


def jsonl(*pairs):
    """A minimal text layer: (page, text) pairs in file order."""
    return [{"md_line": i + 1, "page": page, "text": text, "spans": [{"size": 9.5, "bold": False}]}
            for i, (page, text) in enumerate(pairs)]


def test_the_section_qualifier_comes_from_the_rows_own_printed_line():
    """KM: the guide prints `Structure 1.1.1` and `Reactivity 1.1.1`, both arriving as `1.1.1`."""
    assert printed_qualifier("Structure 1.1.1\u2014Elements are the primary constituents of matter",
                             "1.1.1") == ("Structure", "Structure 1.1.1")
    assert printed_qualifier("Reactivity 1.1.1\u2014The mole is a fundamental unit", "1.1.1") == (
        "Reactivity", "Reactivity 1.1.1")


def test_no_qualifier_is_invented_when_the_line_does_not_carry_one():
    assert printed_qualifier("Elements are the primary constituents of matter", "1.1.1") == (None, None)
    assert printed_qualifier("", "1.1.1") == (None, None)
    assert printed_qualifier("Structure 2.1.4\u2014Reaction rates", "") == (None, None)


def test_a_marker_read_once_resolves_to_a_single_year():
    found = read_markers(jsonl((1, "First assessment 2026")))
    assert marker_resolution(found) == ("First assessment 2026", "single_detected_marker")


def test_case_variants_are_one_marker_not_two():
    """Film prints `first assessment 2023` and `First assessment 2023`; that was a false hold."""
    found = read_markers(jsonl((1, "Second edition, first assessment 2023"),
                               (2, "Second edition, First assessment 2023")))
    assert [f["marker"] for f in found] == ["first assessment 2023"]
    assert marker_resolution(found) == ("first assessment 2023", "single_detected_marker")


def test_a_marker_beyond_the_title_pages_is_still_read():
    """SEHS prints its marker on page 7, which a pages 1-3 window missed."""
    found = read_markers(jsonl((1, "Contents"), (7, "First assessment 2026")))
    assert marker_resolution(found) == ("First assessment 2026", "single_detected_marker")


def test_the_earliest_page_carrying_a_marker_governs():
    """Biology (2028) prints 2028 on pages 1-2 and a 2025 mention on page 7: the 2028 edition wins."""
    found = read_markers(jsonl((1, "First assessment 2028"), (2, "First assessment 2028"),
                               (7, "First assessment 2025")))
    assert marker_resolution(found) == ("First assessment 2028", "single_detected_marker")


def test_conflicting_years_on_the_same_page_are_a_hold():
    found = read_markers(jsonl((1, "First assessment 2024"), (1, "First assessment 2022")))
    assert marker_resolution(found) == (None, "multiple_detected_markers_review_hold")


def test_no_marker_at_all_is_unresolved():
    assert marker_resolution(read_markers(jsonl((1, "At a Glance table")))) == (None, "unresolved")


def test_exact_duplicate_rows_are_dropped_and_reported():
    """KM found `design_technology 1.1.2` twice; the second copy is removed, not silently lost."""
    row = {"subject": "Design Technology", "topic_code": "B1.1", "statement_code": "1.1.2",
           "statement_text": "Apply user-centred design", "page": 46, "md_line": 900}
    kept, dropped = dedupe([dict(row), dict(row)])
    assert len(kept) == 1 and len(dropped) == 1
    assert dropped[0]["statement_code"] == "1.1.2"


def test_a_statement_printed_under_two_topics_is_kept():
    row = {"subject": "Chemistry", "topic_code": "Structure 1.1", "statement_code": "1.1.1",
           "statement_text": "Elements are the primary constituents", "page": 32, "md_line": 1765}
    other = {**row, "topic_code": "Reactivity 1.1"}
    kept, dropped = dedupe([dict(row), other])
    assert len(kept) == 2 and not dropped