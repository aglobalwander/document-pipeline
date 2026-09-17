"""Hermetic checks for the R2 read: locating a wrapped criterion and the letter finding.

`locate_spans` and `item_at` are pure: they read records, not PDFs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_dance_criteria_read import item_at, locate_spans, squish  # noqa: E402


def rec(text, md_line, page=17, y=200.0, x=85.0):
    return {"text": text, "md_line": md_line, "page": page, "bbox": [x, y, x + 300.0, y + 12.0]}


def test_an_opening_is_found_across_wrapped_lines():
    """A criterion wraps, so its opening words rarely sit inside one record."""
    pool = [rec("Identify the appropriate compositional", 1, y=200.0),
            rec("processes and structures to support dances", 2, y=213.0)]

    spans = locate_spans(pool, squish("Identify the appropriate compositional processes"))

    assert len(spans) == 1
    assert spans[0][0] == 17
    assert len(spans[0][2]) == 2, "the match spans both wrapped lines"


def test_every_page_where_the_text_prints_is_returned():
    """The practice table repeats an item that also prints in the AO statements — both are wanted."""
    pool = [rec("Describe the similarities and differences", 1, page=17),
            rec("Describe the similarities and differences", 9, page=18)]

    spans = locate_spans(pool, squish("Describe the similarities"))

    assert [span[0] for span in spans] == [17, 18]


def test_a_wrapped_item_is_joined_and_stops_at_the_next_lettered_item():
    layer = [rec("Identify the appropriate compositional", 1, y=200.0),
             rec("processes and structures.", 2, y=213.0),
             rec("b. Describe the similarities", 3, y=240.0)]

    item = item_at(layer[0], layer)

    assert item["text"] == "Identify the appropriate compositional processes and structures."
    assert "b. Describe" not in item["text"], "a lowercase lettered item must not be glued on"
    assert item["page"] == 17


def test_a_large_vertical_gap_ends_the_item():
    layer = [rec("Apply in the analytical statement", 1, y=200.0),
             rec("a separate paragraph far below", 2, y=260.0)]

    item = item_at(layer[0], layer)

    assert item["text"] == "Apply in the analytical statement"


def test_the_ao_prefix_is_stripped_before_matching_but_is_not_criterion_text():
    assert squish("Knowledge and understanding") in squish("AO1. Knowledge and understanding")
    assert squish("Knowledge and understanding") in squish("1. Knowledge and understanding")