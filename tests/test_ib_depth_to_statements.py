"""Hermetic checks for the depth -> statements flattener.

`ib_depth_to_statements.flatten` needs a depth artifact and a text layer; these tests cover the
schema walker that feeds it, which is where the five depth shapes differ, on synthetic dicts.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

import ib_depth_to_statements as flat  # noqa: E402


def row(topic, code, heading):
    return {"subject": "Design Technology", "topic_code": topic, "statement_code": code,
            "printed_heading": heading, "section_qualifier": None,
            "statement_code_qualified": None, "statement_text": "printed text"}


def test_a_colliding_code_is_qualified_from_the_printed_topic_heading():
    """KM's ruling (a): DT prints `A1.1 Ergonomics` over a bare `1.1.1` under three topics."""
    rows = [row("A1.1", "1.1.1", "A1.1 Ergonomics"),
            row("B1.1", "1.1.1", "B1.1 User-centred design"),
            row("C1.1", "1.1.1", "C1.1 Responsibility of the designer")]

    out = flat.qualify_collisions([dict(r) for r in rows])

    assert [r["statement_code_qualified"] for r in out] == [
        "A1.1 1.1.1", "B1.1 1.1.1", "C1.1 1.1.1"]
    assert len({r["statement_code_qualified"] for r in out}) == 3
    assert [r["statement_code"] for r in out] == ["1.1.1"] * 3, "the code stays as printed"


def test_a_unique_code_is_left_unqualified():
    """Biology, ESS, CS and SEHS have zero collisions; KM ruled a qualifier there would be noise."""
    rows = [row("A1.1", "1.1.1", "A1.1 Ergonomics"), row("A1.2", "1.2.1", "A1.2 Something else")]

    out = flat.qualify_collisions([dict(r) for r in rows])

    assert all(r["statement_code_qualified"] is None for r in out)


def test_an_existing_inline_qualifier_is_never_overwritten():
    """Chemistry prints `Structure 1.1.1` inline; its raw codes collide but its qualified ones do not."""
    rows = [row("Structure 1.1", "1.1.1", "Structure 1.1 Introduction"),
            row("Reactivity 1.1", "1.1.1", "Reactivity 1.1 Measuring")]
    for r, qualified in zip(rows, ("Structure 1.1.1", "Reactivity 1.1.1")):
        r["statement_code_qualified"] = qualified

    out = flat.qualify_collisions([dict(r) for r in rows])

    assert [r["statement_code_qualified"] for r in out] == ["Structure 1.1.1", "Reactivity 1.1.1"]


def test_a_colliding_row_with_no_printed_topic_code_stays_unqualified():
    """Nothing is invented: a heading that carries no code yields no qualifier."""
    rows = [row("", "1.1.1", "Ergonomics"), row("", "1.1.1", "User-centred design")]

    out = flat.qualify_collisions([dict(r) for r in rows])

    assert all(r["statement_code_qualified"] is None for r in out)
    assert flat.printed_topic_code({"printed_heading": "A1.1 Ergonomics"}) == "A1.1"
    assert flat.printed_topic_code({"printed_heading": "Ergonomics"}) is None
    assert flat.printed_topic_code({"topic_code": "B1.1"}) == "B1.1"


def test_walks_units_topics_understandings_with_codes_and_levels():
    depth = {"subject": "biology", "units": [{"theme": "A", "topics": [
        {"code": "A1.1", "understandings": [
            {"code": "A1.1.1", "statement": "Water is a medium", "hl_only": False},
            {"code": "A1.1.2", "statement": "Water is cohesive", "hl_only": True}]}]}]}

    rows = flat.statements(depth)

    assert [(r["topic_code"], r["statement_code"], r["level"]) for r in rows] == [
        ("A1.1", "A1.1.1", "SL"), ("A1.1", "A1.1.2", "HL")]


def test_walks_unit_level_understandings_without_codes_maths_style():
    depth = {"subject": "math_aa", "units": [{"number": 1, "title": "Number and algebra",
             "understandings": [{"statement": "Sequences allow prediction", "hl_only": False},
                                {"statement": "Proof by induction", "hl_only": True}]}]}

    rows = flat.statements(depth)

    assert [r["statement_code"] for r in rows] == ["", ""]
    assert [r["level"] for r in rows] == ["SL", "HL"]
    assert all(r["topic_code"] == "Number and algebra" for r in rows)


def test_walks_topic_items_that_are_plain_strings_global_politics_style():
    depth = {"units": [{"number": 1, "title": "Core topics", "topics": [
        {"title": "Framing global politics", "items": ["States", "IGOs"]}]}]}

    rows = flat.statements(depth)

    assert [r["statement_text"] for r in rows] == ["States", "IGOs"]
    assert all(r["topic_code"] == "Framing global politics" for r in rows)


def test_walks_blocks_and_carries_the_printed_aos_business_management_style():
    depth = {"units": [{"number": 1, "title": "Introduction to business management",
             "conceptual_understandings": [{"text": "Change is essential"}],
             "topics": [{"code": "1.1", "title": "What is a business?", "blocks": [
                 {"text": "The nature of business", "ao_depth": ["AO1", "AO2"], "hl_only": False},
                 {"text": "Ansoff matrix", "ao_depth": ["AO3"], "hl_only": True}]}]}]}

    rows = flat.statements(depth)

    assert [r["printed_aos"] for r in rows] == [None, "AO1,AO2", "AO3"]
    assert [r["level"] for r in rows] == ["SL", "SL", "HL"]
    assert rows[1]["topic_code"] == "1.1"
    assert any(r["statement_text"] == "Change is essential" for r in rows)


def test_an_ahl_marker_in_the_text_beats_the_hl_flag():
    depth = {"units": [{"topics": [{"code": "T", "understandings": [
        {"code": "T1", "statement": "AHL only content", "hl_only": False}]}]}]}

    assert flat.statements(depth)[0]["level"] == "AHL"


def test_focused_study_skills_and_string_items_are_collected():
    depth = {"subject": "history", "focused_study_skills": ["Handling sources"],
             "concepts": [{"title": "Cause and consequence",
                           "understandings": [{"statement": "Causes vary in weight"}]}]}

    rows = flat.statements(depth)

    assert {r["statement_text"] for r in rows} == {"Handling sources", "Causes vary in weight"}


def test_a_subject_with_no_hl_signal_marks_its_sl_levels_as_unrecorded():
    depth = {"units": [{"topics": [{"code": "1.1", "understandings": [
        {"code": "1.1.1", "statement": "A perspective is a view", "hl_only": False}]}]}]}

    row = flat.statements(depth)[0]

    assert row["level"] == "SL"
    assert row["level_basis"] == "unrecorded_in_artifact"


def test_a_subject_that_records_hl_keeps_sl_as_a_reading():
    depth = {"units": [{"topics": [{"code": "A1.1", "understandings": [
        {"code": "A1.1.1", "statement": "Water is a medium", "hl_only": False},
        {"code": "A1.1.2", "statement": "Water is cohesive", "hl_only": True}]}]}]}

    rows = flat.statements(depth)

    assert all(r["level_basis"] == "recorded" for r in rows)
    assert [r["level"] for r in rows] == ["SL", "HL"]


def test_walks_visual_arts_2027_shape_of_aos_and_learning_and_teaching():
    depth = {"subject": "visual_arts",
             "assessment_objectives": {"items": [
                 {"text": "curate visual and written materials", "page": 20, "bbox": [1, 2, 3, 4]}]},
             "core_areas": [{"title": "Create", "learning_and_teaching": [
                 {"text": "nurturing art-making practice", "page": 29, "bbox": [1, 2, 3, 4]}]},
                 {"title": "Connect", "learning_and_teaching": [
                     {"text": "connecting with artists", "page": 40, "bbox": [1, 2, 3, 4]}]}]}

    rows = flat.statements(depth)

    assert [r["statement_text"] for r in rows] == [
        "curate visual and written materials", "nurturing art-making practice",
        "connecting with artists"]
    assert [r["topic_code"] for r in rows] == ["visual_arts", "Create", "Connect"]


def test_empty_statements_are_dropped_rather_than_emitted():
    depth = {"units": [{"topics": [{"code": "A", "understandings": [
        {"statement": "  ", "hl_only": False}, {"statement": "Real", "hl_only": False}]}]}]}

    assert [r["statement_text"] for r in flat.statements(depth)] == ["Real"]