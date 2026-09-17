"""Hermetic checks for the printed-unit enumeration.

The label match is pure: it reads records, not PDFs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_printed_units import SCOPE, find_printed, norm  # noqa: E402


def rec(text, md_line=1, page=1, size=9.5):
    return {"text": text, "md_line": md_line, "page": page, "bbox": [0.0, 0.0, 1.0, 1.0],
            "spans": [{"size": size, "bold": False}]}


def test_quotes_dashes_and_spacing_do_not_block_a_match():
    """KM's canon labels and the guides disagree only in quote and dash style."""
    assert norm("How valid is the notion of a \u201cclassic\u201d text?") == norm(
        'How valid is the notion of a "classic" text?')
    assert norm("Topic 3\u2014 Geometry") == norm("Topic 3- Geometry")
    assert norm("Change is essential\u00a0for  businesses") == norm("change is essential for businesses")
    assert norm(None) == ""


def test_a_canon_label_matches_the_guides_own_line():
    layer = [rec("Readers, writers and texts", 1108, 28, 14.0)]
    kind, hit = find_printed("Readers, writers and texts", layer)

    assert kind == "exact"
    assert hit["page"] == 28


def test_a_heading_beats_prose_that_merely_mentions_the_label():
    """The guide says the phrase inside a paragraph too; the printed unit is the heading."""
    layer = [rec("the area of exploration of readers, writers and texts aims to introduce", 1, 29),
             rec("Readers, writers and texts", 2, 28, 14.0)]

    kind, hit = find_printed("Readers, writers and texts", layer)

    assert kind == "exact"
    assert hit["md_line"] == 2


def test_a_label_that_does_not_print_is_reported_not_invented():
    assert find_printed("No such unit prints here", [rec("Something else entirely")]) is None


def test_scope_covers_the_subjects_km_named_and_nothing_else():
    """KM's scope: the two Literature guides' areas of exploration, Music and Dance components, then
    Visual Arts and Psychology — the two subjects still without a printed basis."""
    assert set(SCOPE) == {"literature", "language_and_literature", "music", "dance",
                          "visual_arts", "psychology"}
    assert SCOPE["music"].startswith("^comp-") and SCOPE["dance"].startswith("^comp-")
    assert "AoE" in SCOPE["literature"] and "AoE" in SCOPE["language_and_literature"]
    assert "CREATE" in SCOPE["visual_arts"]
    assert SCOPE["psychology"].startswith("^(branch-|concept-|content-)")