"""Hermetic checks for the P4 statement locator's matching logic.

The locator reads the KM request folder, the guide text layers and `dp_canonical.csv`; these tests
cover the pure parts — topic resolution, span coverage, candidate lookup, the match states and the
AO marker rule — on synthetic records, so they run without any of those files.
"""

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

import km_p4_statements as p4  # noqa: E402


def rec(text, page=1, md_line=1):
    return {"text": text, "page": page, "bbox": [0.0, 0.0, 10.0, 10.0], "md_line": md_line}


def statement(text, code="A1.1.1"):
    return {"statement_text": text, "printed_code": code}


def test_topic_of_picks_the_longest_canonical_prefix():
    codes = {"A", "A1", "A1.1", "B"}

    assert p4.topic_of("A1.1.3", codes) == "A1.1"
    assert p4.topic_of("A1.1", codes) == "A1.1"
    assert p4.topic_of("B", codes) == "B"
    assert p4.topic_of("C9", codes) is None
    assert p4.topic_of("", codes) is None


def test_spans_all_accepts_a_statement_split_across_printed_lines():
    records = [rec("Water as the medium for life"), rec("supports metabolic reactions")]

    assert p4.spans_all(["water", "life"], records, [0]) is True
    assert p4.spans_all(["water", "metabolic"], records, [0]) is False
    assert p4.spans_all(["water", "metabolic"], records, [0, 1]) is True


def test_candidate_ids_anchors_on_the_rarest_known_token():
    records = [rec("Water as the medium for life"), rec("Cohesion of water molecules"),
               rec("Adhesion to polar materials")]
    post = p4.index(records)

    assert p4.candidate_ids(post, ["cohesion", "molecules"]) == {1}
    assert p4.candidate_ids(post, ["water", "medium"]) == {0}
    # An unprinted word is ignored rather than emptying the candidate set: the span check decides.
    assert p4.candidate_ids(post, ["water", "xylophone"]) == {0, 1}
    assert p4.candidate_ids(post, ["xylophone", "timbre"]) == set()


def test_locate_row_marks_an_exact_single_line_match():
    records = [rec("A1.1.1 Water as the medium for life", md_line=42)]
    post = p4.index(records)

    out = p4.locate_row(statement("Water as the medium for life"), records, post)

    assert out["match"] == "located_exact"
    assert out["md_line"] == 42 and out["span_pages"] == [1]
    assert out["matched_printed"] == "A1.1.1 Water as the medium for life"
    assert out["code_in_region"] is True


def test_locate_row_marks_an_adjacent_match_and_reports_its_pages():
    records = [rec("A1.1.1 Water as the medium for life", page=5, md_line=10),
               rec("supports metabolic reactions in cells", page=5, md_line=11)]
    post = p4.index(records)

    out = p4.locate_row(statement("Water as the medium for life supports metabolic reactions"),
                        records, post)

    assert out["match"] == "located_adjacent"
    assert out["span_pages"] == [5]
    assert out["matched_printed"].startswith("A1.1.1 Water")


def test_locate_row_reports_the_document_coverage_when_it_cannot_match():
    records = [rec("Cohesion of water molecules")]
    post = p4.index(records)
    doc = Counter(p4.tokens("Cohesion of water molecules"))

    out = p4.locate_row(statement("Xylophone timbre"), records, post, doc)

    assert out["match"] == "not_located"
    assert out["doc_coverage"] == 0.0


def test_locate_row_separates_a_scattered_statement_from_an_absent_one():
    records = [rec("Water cohesion"), rec("unrelated bridge text"), rec("and adhesion too")]
    post = p4.index(records)
    doc = Counter(t for r in records for t in p4.tokens(r["text"]))

    # Tokens in the guide, never contiguous: found as an adjacent span, not lost.
    near = p4.locate_row(statement("water adhesion"), records, post, doc)
    assert near["match"] == "located_adjacent"

    # Tokens nowhere in the guide: not_located, and the document coverage says so.
    absent = p4.locate_row(statement("xylophone timbre"), records, post, doc)
    assert absent["match"] == "not_located"
    assert absent["doc_coverage"] == 0.0


def test_locate_row_treats_an_empty_statement_as_unlocatable_not_as_a_failure():
    out = p4.locate_row(statement(""), [], {})

    assert out["match"] == "empty_statement_text"


def test_code_check_separates_a_missing_topic_from_a_deeper_statement_code(monkeypatch):
    monkeypatch.setattr(p4, "canonical_codes", lambda: {"biology": {"A", "A1.1"}})
    rows = [{"subject": "Biology", "printed_code": "A1.1.3"},
            {"subject": "Biology", "printed_code": "Z9.9"},
            {"subject": "Biology", "printed_code": "A"},
            {"subject": "Music", "printed_code": "M1"},
            {"subject": "Xylophone Studies", "printed_code": "X1"}]

    misses, stats = p4.code_check(rows)

    # A subject with no canonical layer is a mapping gap, counted in the stats, not listed as a
    # topic miss (there is no topic set to miss).
    assert misses == [{"subject": "Biology", "printed_code": "Z9.9", "rows": 1},
                      {"subject": "Music", "printed_code": "M1", "rows": 1}]
    assert stats["topic_is_a_canonical_row"] == 1
    assert stats["statement_is_its_own_topic"] == 1
    assert stats["topic_not_in_canonical_strict_and_tolerant"] == 2
    assert stats["subject_not_in_canonical"] == 1


def test_tolerant_topic_matching_absorbs_the_mechanical_layer_differences():
    # spacing: the reference prints "AHL 1.10" where the canonical holds "AHL1.10"
    assert p4.tolerant_topic_of("AHL 1.10", {"AHL1.10"}) == "AHL1.10"
    # theme name instead of letter: "Reactivity 1.1" against canonical "R1.1"
    assert p4.tolerant_topic_of("Reactivity 1.1", {"R1.1"}) == "R1.1"
    # theme letter dropped: reference "1.1.1" against canonical "A1.1"
    assert p4.tolerant_topic_of("1.1.1", {"A1.1"}) == "A1.1"
    # the longest numeric tail wins, so a topic beats the theme row above it
    assert p4.tolerant_topic_of("1.1.1", {"A", "A1", "A1.1"}) == "A1.1"


def test_tolerant_topic_matching_still_refuses_a_code_with_no_numbers():
    assert p4.tolerant_topic_of("ArtMaking-C13", {"AO-CURATE"}) is None
    assert p4.tolerant_topic_of("", {"A1.1"}) is None


def test_code_check_reports_strict_and_tolerant_separately(monkeypatch):
    monkeypatch.setattr(p4, "canonical_codes",
                        lambda: {"mathematics_ai": {"AHL1.10"}, "biology": {"A1.1"}})
    rows = [{"subject": "Mathematics Applications and Interpretation", "printed_code": "AHL 1.10"},
            {"subject": "Biology", "printed_code": "1.1.1"},
            {"subject": "Biology", "printed_code": "Q9.9"}]

    misses, stats = p4.code_check(rows)

    assert misses == [{"subject": "Biology", "printed_code": "Q9.9", "rows": 1}]
    assert stats["topic_only_under_tolerant_matching"] == 2
    assert stats["topic_not_in_canonical_strict_and_tolerant"] == 1


def test_ao_marker_matches_numbered_forms_only():
    for text in ("AO1", "AO 2", "AO3 demonstrate knowledge"):
        assert p4.AO.findall(text)
    for text in ("A01", "AOL", "assessment objective one"):
        assert not p4.AO.findall(text)


def test_years_in_reads_every_year_so_a_two_year_label_can_be_checked():
    assert p4.years_in("DP: Physics (1st assessments 2016, last assessment 2024)") == [2016, 2024]
    assert p4.years_in("no year here") == []