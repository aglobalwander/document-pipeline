"""Hermetic checks for the edition-marker rule in `km_text_layer`.

Two things are pinned: the pattern reads AP's own edition statement as well as IB's, and a page is
searched **joined** rather than line by line. The second is the load-bearing one — an AP course
description prints `Effective` on one line and `Fall 2026` on the next, so a per-line search found the
word and never the marker. That is why no AP artifact could be pinned by its own marker.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_text_layer import MARKER_PAGES, marker_resolution, read_markers  # noqa: E402


def rec(text, page=1):
    return {"md_line": 1, "page": page, "bbox": [0.0, 0.0, 1.0, 1.0], "text": text, "spans": []}


def test_an_ib_marker_still_reads_exactly_as_it_did():
    assert read_markers([rec("First assessment 2025", page=1)]) == [
        {"marker": "First assessment 2025", "page": 1}]


def test_the_first_examinations_wording_still_reads():
    assert read_markers([rec("First examinations 2013", page=1)]) == [
        {"marker": "First examinations 2013", "page": 1}]


def test_an_ap_marker_split_over_two_lines_is_read():
    """The real shape, measured on AP Latin and AP Psychology: `Effective` then `Fall 2025`."""
    assert read_markers([rec("Effective", page=1), rec("Fall 2025", page=1)]) == [
        {"marker": "Effective Fall 2025", "page": 1}]


def test_an_ap_marker_on_one_line_is_read():
    got = read_markers([rec("AP\u00ae Precalculus Course and Exam Description, Effective Fall 2026",
                            page=2)])

    assert got == [{"marker": "Effective Fall 2026", "page": 2}]


def test_the_word_effective_in_prose_is_not_a_marker():
    assert read_markers([rec("with highly effective AP teachers and college faculty", page=11)]) == []


def test_the_same_marker_is_recorded_once_at_its_earliest_page():
    assert read_markers([rec("Effective", page=1), rec("Fall 2025", page=1),
                         rec("Effective Fall 2025", page=2)]) == [
        {"marker": "Effective Fall 2025", "page": 1}]


def test_casing_does_not_make_two_markers():
    assert read_markers([rec("Effective Fall 2024", page=2),
                         rec("effective fall 2024", page=64)]) == [
        {"marker": "Effective Fall 2024", "page": 2}]


def test_pages_after_the_window_are_not_read():
    assert read_markers([rec("Effective Fall 2024", page=MARKER_PAGES + 1)]) == []


def test_the_earliest_page_still_governs():
    marker, state = marker_resolution([{"marker": "First assessment 2028", "page": 1},
                                       {"marker": "First assessment 2025", "page": 7}])

    assert marker == "First assessment 2028" and state == "single_detected_marker"


def test_two_years_on_the_earliest_page_is_still_a_hold():
    marker, state = marker_resolution([{"marker": "Effective Fall 2025", "page": 1},
                                       {"marker": "Effective Fall 2024", "page": 1}])

    assert marker is None and state == "multiple_detected_markers_review_hold"