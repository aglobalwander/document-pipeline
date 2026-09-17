"""Hermetic checks for the reference-spine context pass.

The heading rule and the context lookup are pure: they read records, not PDFs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

import km_reference_context as ctx  # noqa: E402


def rec(text, md_line, size=9.5, bold=False):
    return {"text": text, "md_line": md_line, "spans": [{"size": size, "bold": bold}]}


def test_a_larger_span_marks_a_heading():
    assert ctx.is_heading(rec("Making art", 40, size=14.0)) is True
    assert ctx.is_heading(rec("Body copy line", 41, size=9.5)) is False


def test_a_short_bold_line_is_a_heading_but_a_sentence_is_not():
    assert ctx.is_heading(rec("Artistic processes", 40, bold=True)) is True
    assert ctx.is_heading(rec("This bold sentence ends with a full stop.", 40, bold=True)) is False
    assert ctx.is_heading(rec(" ".join(["word"] * 9), 40, bold=True)) is False


def test_long_lines_are_never_headings_however_they_are_set():
    assert ctx.is_heading(rec("x" * 200, 40, size=20.0)) is False


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