import zipfile

from scripts.document_processing.build_pptx_visual_record import (
    extract_slide_visibility,
    rank_key_slides,
    slugify,
)


def test_slugify_keeps_stable_human_readable_stem():
    assert slugify("SAS Priorities & Vision 2023-2024 Slide Deck") == (
        "sas-priorities-vision-2023-2024-slide-deck"
    )


def test_rank_key_slides_prioritizes_curriculum_terms():
    slides = [
        {
            "slide_number": 1,
            "title": "Welcome",
            "content": "Agenda and logistics",
            "notes": "",
            "word_count": 3,
            "content_hash": "a",
        },
        {
            "slide_number": 2,
            "title": "Macro Curriculum Blueprint",
            "content": "TTGs, DTGs, transfer goals, and performance tasks",
            "notes": "Connect to WASC.",
            "word_count": 9,
            "content_hash": "b",
        },
    ]

    ranked = rank_key_slides(slides, {2: "slides/slide_002.png"})

    assert len(ranked) == 1
    assert ranked[0]["slide_number"] == 2
    assert ranked[0]["image_path"] == "slides/slide_002.png"
    assert {match["label"] for match in ranked[0]["matches"]} >= {
        "ttg",
        "dtg",
        "macro_curriculum",
        "performance_evidence",
    }


def test_extract_slide_visibility_reads_hidden_slide_state(tmp_path):
    pptx_path = tmp_path / "hidden-slide.pptx"
    with zipfile.ZipFile(pptx_path, "w") as archive:
        archive.writestr(
            "ppt/presentation.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId1"/>
    <p:sldId id="257" r:id="rId2"/>
  </p:sldIdLst>
</p:presentation>""",
        )
        archive.writestr(
            "ppt/_rels/presentation.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "ppt/slides/slide1.xml",
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>',
        )
        archive.writestr(
            "ppt/slides/slide2.xml",
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" show="0"/>',
        )

    visibility = extract_slide_visibility(pptx_path)

    assert [slide["slide_number"] for slide in visibility] == [1, 2]
    assert [slide["hidden"] for slide in visibility] == [False, True]
