"""Hermetic checks for the R5 DP printed-string read: the tokeniser, the span rule, the ranking.

The ranking is what these pin, because the read's first pass got it wrong on real rows: it returned
`their artistic intentions and to create with curiosity, empathy and resilience` (prose, p.13) for
the label `Artistic intentions`, where this guide prints the heading on p.31; and it padded a
Psychology cell with the unrelated lines above it. Both are ranking defects, and neither is visible
from a pass/fail count.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_dp_printed_read import contains, locate, region, tokens  # noqa: E402


def rec(text, page=1, size=10.0, bold=False, top=100.0):
    return {"md_line": 1, "page": page, "bbox": [85.0, top, 400.0, top + 11.0], "text": text,
            "spans": [{"text": text, "font": "Arial", "size": size, "bold": bold}]}


def test_the_tokeniser_splits_the_separators_these_guides_print():
    """The section prefix and the em dash are one token boundary, not part of the label."""
    assert tokens("Structure 1.1\u2014Introduction to the particulate nature of matter") == [
        "structure", "11", "introduction", "to", "the", "particulate", "nature", "of", "matter"]


def test_a_printed_section_prefix_the_label_omits_is_a_match_not_a_miss():
    """Chemistry read 0 of 32 only because the label omits `Structure 1.1—`."""
    recs = [rec("Structure 1.1\u2014Introduction to the particulate nature of matter",
                page=39, size=13.0, bold=True)]
    hit = locate("Introduction to the particulate nature of matter", recs)

    assert hit["status"] == "printed"
    assert hit["printed_form"].startswith("Structure 1.1\u2014")
    assert hit["page"] == 39 and hit["bbox"]


def test_a_label_split_by_the_guides_own_wrap_is_read_as_wrapped_and_tightly():
    """`AO1.` and its heading are two printed lines; the span must not pad past them."""
    recs = [rec("Having followed the dance course", page=17, top=214.0),
            rec("AO1.", page=17, bold=True, top=235.0),
            rec("Knowledge and understanding", page=17, top=246.0),
            rec("In internal assessment, demonstrate", page=17, top=258.0)]
    hit = locate("AO1. Knowledge and understanding", recs)

    assert hit["status"] == "printed_wrapped"
    assert hit["lines_used"] == 2, "the tightest run, not a window padded with the lines around it"
    assert hit["printed_form"] == "AO1. Knowledge and understanding"


def test_a_heading_that_is_the_label_beats_prose_that_merely_contains_it():
    """The defect this read shipped first: p.13 prose chosen over the p.31 heading."""
    prose = rec("their artistic intentions and to create with curiosity, empathy and resilience",
                page=13, top=417.0)
    heading = rec("Artistic intentions", page=31, size=13.0, bold=True, top=571.0)
    hit = locate("Artistic intentions", [prose, heading])

    assert hit["status"] == "printed"
    assert hit["rule"] == "label_is_the_printed_line"
    assert hit["page"] == 31 and hit["printed_form"] == "Artistic intentions"
    assert hit["occurrences"] == 2, "both spans are reported, so the choice is visible"


def test_containment_is_a_contiguous_run_not_a_bag_of_words():
    assert contains(["a", "b", "c"], ["a", "c"]) is False
    assert contains(["a", "b", "c"], ["b", "c"]) is True


def test_a_span_never_crosses_a_page_break():
    """Two lines on different pages are not adjacent in print, so joining them would invent text."""
    hit = locate("Alpha Beta", [rec("Alpha", page=1), rec("Beta", page=2)])

    assert hit["status"] == "not_printed"
    assert hit["occurrences"] == 0


def test_a_label_the_guide_does_not_print_is_not_printed_with_no_span():
    hit = locate("Total teaching hours", [rec("Total contact hours", page=30)])

    assert hit["status"] == "not_printed"
    assert hit["rule"] == "no_span_carries_the_label"


def test_spelling_drift_is_a_named_second_pass_not_a_silent_match():
    """The guides print `behavior`; the canon writes `behaviour`. KM rules; the read just labels it."""
    recs = [rec("The role of culture, motivation and technology in shaping human behavior", page=26)]
    hit = locate("The role of culture, motivation and technology in shaping human behaviour", recs)

    assert hit["status"] == "printed"
    assert hit["rule"].endswith("_spelling_tolerant")


def test_an_exact_spelling_match_is_not_labelled_tolerant():
    recs = [rec("Animal research/animal models", page=30)]
    hit = locate("Animal research/animal models", recs)

    assert hit["status"] == "printed"
    assert not hit["rule"].endswith("_spelling_tolerant")


def test_the_region_read_walks_the_canon_parent_chain():
    """A row the guide does not print still carries the printed heading it sits under."""
    canon = {("dance", "ca-outline"): {"parent_code": "comp-ca"},
             ("dance", "comp-ca"): {"parent_code": "", "label": "Composition and analysis"}}
    recs = [rec("Composition and analysis", page=23, size=13.0, bold=True)]
    out = region("ca-outline", "dance", canon, recs)

    assert out["region_code"] == "comp-ca"
    assert out["region_page"] == 23
    assert out["region_printed"] == "Composition and analysis"


def test_a_region_chain_with_no_printable_ancestor_says_so():
    canon = {("music", "matrix-exploring-creator"): {"parent_code": ""}}
    out = region("matrix-exploring-creator", "music", canon, [rec("Filler")])

    assert out["region_code"] == ""
    assert "no ancestor" in out["evidence"]