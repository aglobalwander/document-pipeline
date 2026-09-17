"""Hermetic checks for the unit-statements extractor.

The segmentation is pure: it reads records, not PDFs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_unit_statements import is_furniture, is_table_span, paragraphs  # noqa: E402

PITCH = 13.0


def rec(text, md_line, page=1, x=60.0, y=100.0, size=9.5):
    return {"text": text, "md_line": md_line, "page": page, "bbox": [x, y, x + 300.0, y + 12.0],
            "spans": [{"size": size, "bold": False}]}


def test_wrapped_lines_become_one_statement():
    """A guide wraps a paragraph across lines; the paragraph, not the line, is the statement."""
    layer = [rec("When exploring music in context, students will learn how to", 1, y=233.4),
             rec("engage with a diverse range of music that will broaden their", 2, y=246.4),
             rec("horizons and provide stimuli in personal, local and global contexts.", 3, y=259.4)]

    items = paragraphs(layer, PITCH)

    assert len(items) == 1
    assert items[0]["text"].startswith("When exploring music in context")
    assert items[0]["unit_layout"] == "prose"


def test_a_vertical_gap_starts_a_new_statement():
    layer = [rec("First paragraph line one", 1, y=100.0), rec("and its second line", 2, y=113.0),
             rec("A separate paragraph after a gap", 3, y=160.0)]

    items = paragraphs(layer, PITCH)

    assert [i["text"] for i in items] == [
        "First paragraph line one and its second line", "A separate paragraph after a gap"]


def test_furniture_never_becomes_a_statement():
    assert is_furniture(rec("45", 1))
    assert is_furniture(rec("Language A: literature guide", 2))
    assert is_furniture(rec("Standard level and higher level: 2 hours", 3))
    assert not is_furniture(rec("Students will learn to engage with music", 4))


def test_a_bullet_starts_a_statement_and_drops_the_glyph():
    """Literature prints its guiding questions as bullets; the question is the statement."""
    layer = [rec("\u2022", 1, y=100.0), rec("Why and how do we study literature?", 2, y=113.0)]

    items = paragraphs(layer, PITCH)

    assert [i["text"] for i in items] == ["Why and how do we study literature?"]


def test_side_by_side_cells_mark_the_unit_body_as_a_table():
    """Dance's assessment-criteria grids put two cells on one baseline."""
    layer = []
    for n in range(6):
        y = 200.0 + n * 13.0
        layer += [rec(f"Composition and analysis {n}", 2 * n + 1, x=60.0, y=y),
                  rec(f"External assessment criteria {n}", 2 * n + 2, x=320.0, y=y)]

    assert is_table_span(layer) is True
    assert all(item["unit_layout"] == "table" for item in paragraphs(layer, PITCH))


def test_a_bare_list_marker_starts_the_next_item_and_is_not_kept():
    """KM asked for trailing list numbers to be stripped; the markers print as their own runs."""
    layer = [rec("Why and how do we study literature?", 1, y=100.0),
             rec("2.", 2, y=120.0), rec("How are we affected by literary texts?", 3, y=133.0)]

    items = paragraphs(layer, PITCH)

    assert [i["text"] for i in items] == [
        "Why and how do we study literature?", "How are we affected by literary texts?"]


def test_a_sentence_ending_in_a_number_is_left_intact():
    """Eight items legitimately end in a number; a text strip would corrupt them."""
    layer = [rec("What was your reason for choosing this work?", 1, y=100.0),
             rec("The composition and analysis component at SL are illustrated in figure 2.",
                 2, y=160.0)]

    items = paragraphs(layer, PITCH)

    assert items[-1]["text"].endswith("illustrated in figure 2.")


def test_a_wrapped_paragraph_is_not_a_table():
    layer = [rec(f"line {n} of one wrapped paragraph", n, y=100.0 + n * 13.0) for n in range(8)]

    assert is_table_span(layer) is False
    assert paragraphs(layer, PITCH)[0]["unit_layout"] == "prose"