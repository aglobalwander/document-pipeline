#!/usr/bin/env python3
"""Build source-sequenced SAS concept visual artifacts.

This differs from the slide/deck timeline. Dates come from WASC/KM source
records; images are attached as visual artifacts that show how SAS later
communicated each concept.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RECORD_ROOT = Path("data/output/powerpoint_visual_record")
DEFAULT_ANALYSIS_DIR = DEFAULT_RECORD_ROOT / "analysis"


EVENTS: list[dict[str, Any]] = [
    {
        "id": "eagles-eslrs-ttgs",
        "period": "Pre-2016 -> Spring 2017",
        "concept": "EAGLES / ESLRs -> TTGs",
        "introduced": "Historic EAGLES were the predecessor learner-outcome frame. In 2016-2017 SAS reframed schoolwide learner outcomes as long-term transdisciplinary transfer goals, later referred to as TTGs.",
        "source_basis": [
            "2017 WASC school report: draft ESLRs were to replace the historic EAGLES and become long-term transdisciplinary transfer goals.",
            "2020 WASC self-study: TTGs and performance indicators began through 2016-2017 ERD work and final draft was adopted in spring of that school year.",
            "ALT OneNote Aug/Sep 2016: ESLRs, curriculum alignment, McTighe, long-term transfer goals, and macro curriculum alignment appear together.",
        ],
        "source_confidence": "High for lineage and 2016-2017 transition; lower for original EAGLES adoption date.",
        "visual_read": "The available visuals show the translation phase: TTG indicators, rubrics, I-can statements, and faculty sensemaking about how TTGs would be used.",
        "visuals": [
            {
                "label": "TTG performance-indicator work",
                "deck_slug": "ttg-performance-indicators-fbbb30299a",
                "slide_number": 2,
            },
            {
                "label": "TTG rubric and performance indicators as map/GPS",
                "deck_slug": "march-23-2018-ttg-final-team-meeting-e1f94e24e6",
                "slide_number": 5,
            },
            {
                "label": "TTG I Can / Can Do statements",
                "deck_slug": "pxes-wed-oct-17-ttg-i-can-statements-63ed5dbea8",
                "slide_number": 4,
            },
        ],
    },
    {
        "id": "macro-blueprint-dtgs",
        "period": "2016-2018",
        "concept": "Macro Curriculum Blueprint and DTGs",
        "introduced": "The Macro Curriculum Blueprint became an explicit schoolwide architecture in 2016-2017. DTGs were planned in 2017 and drafted in 2018 as the discipline-specific translation layer.",
        "source_basis": [
            "September 2016 ALT retreat: macro curriculum alignment, Jay McTighe blueprint, operationalizing the blueprint, and long-term transfer goals were introduced together.",
            "March 2017 ALT agreements: SAS would use McTighe's curriculum blueprint as the frame of reference.",
            "2017-2018 ALT/SharePoint records: DTGs planned, drafted, and moved through teacher-leader work.",
        ],
        "source_confidence": "High.",
        "visual_read": "The visuals show the architecture becoming explicit: macro versus micro curriculum, long-term transfer, standards, EUs/EQs, and cornerstone/performance tasks.",
        "visuals": [
            {
                "label": "Essential elements of a curriculum blueprint",
                "deck_slug": "final-2-minutes-to-understand-2-macro-curriculum-e7d0a5a983",
                "slide_number": 3,
            },
            {
                "label": "Macro blueprint video visual",
                "deck_slug": "macro-blueprint-videos-8086caacf0",
                "slide_number": 5,
            },
            {
                "label": "DTG/GVC translation in schoolwide priorities",
                "deck_slug": "dtglearningcafe-pxes-level-1-2-oct-21-1-b2bb209ca3",
                "slide_number": 4,
            },
        ],
    },
    {
        "id": "implementation-deepening",
        "period": "2019-2021",
        "concept": "GVC, UbD, Atlas, EUs/EQs, and Performance Evidence",
        "introduced": "The blueprint moved into implementation and deepening: DTG EUs/EQs, UbD, Atlas documentation, performance tasks, TTG progressions, and measurement tools.",
        "source_basis": [
            "2020 WASC self-study action-plan language: develop, implement, and document components of the Macro Curriculum Blueprint.",
            "2022 WASC interim report: 2021-2022 priorities included DTG integration, Atlas documentation, TTGs/DTGs, performance tasks, and UbD.",
            "January 2021 ALT notes: WASC, TTGs, DTGs, learning principles, and Macro Curriculum Blueprint were reconnected.",
        ],
        "source_confidence": "High.",
        "visual_read": "The visuals show the operationalization layer: priorities, Atlas documentation, DTG integration, performance tasks, and UbD capacity.",
        "visuals": [
            {
                "label": "2021-2022 schoolwide priorities and GVC alignment",
                "deck_slug": "00-2021-22-schoolwide-priorities-1-3383594b38",
                "slide_number": 2,
            },
            {
                "label": "GVC outcomes: DTGs, Atlas, TTGs, performance tasks, UbD",
                "deck_slug": "00-2021-22-schoolwide-priorities-1-3383594b38",
                "slide_number": 3,
            },
        ],
    },
    {
        "id": "sas-forward-wasc",
        "period": "2021-2023",
        "concept": "SAS Forward, WASC Priorities, and Strategic Pillars",
        "introduced": "SAS Forward and WASC action-plan priorities became the institutional alignment layer around the curriculum work, connecting learner outcomes to programs, spaces, cultures, and strategic priorities.",
        "source_basis": [
            "2021-2026 WASC action plan and interim reporting: schoolwide priorities align to WASC action plans and SAS Forward strategies.",
            "2022-2023 deck evidence: SAS Forward strategic pillars were socialized and used as a visual planning frame.",
            "2024 WASC report: WASC action-plan areas were incorporated into the Logic Model and current improvement structure.",
        ],
        "source_confidence": "Medium-high for the sequence; exact first SAS Forward launch date may need a separate source check.",
        "visual_read": "The visuals show a move from curriculum architecture to institutional alignment: pillars, WASC action plans, programs, facilities, and future-facing student preparation.",
        "visuals": [
            {
                "label": "SAS Forward strategic pillars overview",
                "deck_slug": "sas-forward-strategic-pillars-sy22-23-9d34cc51ae",
                "slide_number": 2,
            },
            {
                "label": "Five strategic pillars",
                "deck_slug": "sas-forward-strategic-pillars-sy22-23-9d34cc51ae",
                "slide_number": 3,
            },
            {
                "label": "WASC action plans in schoolwide priorities",
                "deck_slug": "sas-priorities-vision-2023-2024-slide-deck-1-9cc67a0711",
                "slide_number": 4,
            },
        ],
    },
    {
        "id": "vision-pops",
        "period": "Spring 2023 -> 2023-2024",
        "concept": "New Vision and 7 Principles of Practice",
        "introduced": "In spring 2023, SAS developed a draft new Vision Statement and articulated the 7 Principles of Practice, launching a commitment to reimagining learning.",
        "source_basis": [
            "2024 WASC final report: spring 2023 Head of School-led process developed a draft Vision Statement and 7 Principles of Practice.",
            "2024 WASC final report: 2023-2024 ERDs focused on investigating the 7 Principles of Practice.",
            "2024 WASC final report: PoPs were introduced in 2023 and guided program examples and the Logic Model foundation.",
        ],
        "source_confidence": "High.",
        "visual_read": "The visuals show the new purpose and pedagogy layer: Vision, learning principles, PoPs, and the first visual bridge from institutional direction into classroom practice.",
        "visuals": [
            {
                "label": "Draft/current Vision visual",
                "deck_slug": "sas-priorities-vision-2023-2024-slide-deck-1-9cc67a0711",
                "slide_number": 16,
            },
            {
                "label": "Learning principles",
                "deck_slug": "sas-priorities-vision-2023-2024-slide-deck-9cc67a0711",
                "slide_number": 14,
            },
            {
                "label": "SAS Vision and 7 Principles of Practice",
                "deck_slug": "sas-forward-programs-and-fdp-sep7-board-9744121828",
                "slide_number": 6,
            },
        ],
    },
    {
        "id": "learning-ecosystem-logic-model",
        "period": "Fall 2023 -> 2024-2026",
        "concept": "Core Commitments, Logic Model, and Learning Ecosystem",
        "introduced": "After the Vision/PoPs work, SAS developed a Logic Model for Change. The 2024 WASC record names Core Commitments, Learning Ecosystem, and Professional Learning System as major focus areas.",
        "source_basis": [
            "2024 WASC final report: CIC worked from fall 2023 on a Logic Model encompassing WASC action-plan areas.",
            "2024 WASC final report: five focus areas identified: Core Commitments, Learning Ecosystem, Professional Learning System, Program Evaluation, Data Collection and Analysis.",
            "Learning Ecosystem SharePoint mirror: 2024-2025 work aims for clarity about the future SAS learning experience and PK-12/divisional learning experience descriptions.",
        ],
        "source_confidence": "High for WASC focus areas; medium for exact Learning Ecosystem SharePoint surface/canonical home.",
        "visual_read": "The visuals show the coherence container becoming explicit: mission/vision/design, Learning Ecosystem, Logic Model, and the need for a shared future learning experience.",
        "visuals": [
            {
                "label": "Designing our Learning Ecosystem",
                "deck_slug": "morning-framing-sep-16-online-pl-day-4f8c70326c",
                "slide_number": 12,
            },
            {
                "label": "Logic Model 2024-26",
                "deck_slug": "master-sas-slides-1-79f581bc4a",
                "slide_number": 76,
            },
            {
                "label": "Strategic alignment of programs and practices",
                "deck_slug": "alignment-1-cdfc0fce82",
                "slide_number": 1,
            },
        ],
    },
    {
        "id": "pl-system",
        "period": "2023-2026",
        "concept": "Professional Learning System and PL Plan",
        "introduced": "Professional learning became the implementation mechanism for the Learning Ecosystem: ERDs, PoP inquiry, UDL/CRP/AI foundations, lesson series, feedback, reflection, and celebration of learning.",
        "source_basis": [
            "2024 WASC final report: ERD structure supported PoP inquiry and the Professional Learning System became a Logic Model focus area.",
            "2024 WASC action-plan language: Professional Learning System aligns PL, PGPE, community of practice, and Core Commitments.",
            "2024-2026 PL decks: PL Plan links PoPs to UDL, CRP, AI, consultants, lesson series, reflection, and evidence.",
        ],
        "source_confidence": "High for WASC/Logic Model focus; high for deck evidence of PL Plan articulation.",
        "visual_read": "The visuals show implementation architecture: a journey from PoPs to UDL/CRP/AI foundations and then into classroom implementation, support, and evidence.",
        "visuals": [
            {
                "label": "PoP inquiry through ERDs",
                "deck_slug": "master-sas-slides-1-79f581bc4a",
                "slide_number": 49,
            },
            {
                "label": "Professional learning plan",
                "deck_slug": "morning-framing-sep-16-online-pl-day-4f8c70326c",
                "slide_number": 13,
            },
            {
                "label": "PL Plan journey",
                "deck_slug": "pl-plan-tidbits-in-development-daacc9ae91",
                "slide_number": 1,
            },
            {
                "label": "PL days timeline",
                "deck_slug": "pl-plan-tidbits-in-development-daacc9ae91",
                "slide_number": 4,
            },
        ],
    },
    {
        "id": "udl-crp-ai",
        "period": "2021-2026",
        "concept": "UDL, CRP, and AI as Current Implementation Strands",
        "introduced": "UDL and CRP appear in WASC/DEIB/student-support work before they are consolidated into the 2024-2026 PL Plan. AI enters through GenAI guidelines and task-force work in 2023, then becomes one of the PL implementation strands.",
        "source_basis": [
            "2022 WASC interim: UDL introduced to early adopters and used in divisional professional learning; CRP explored through DEIB and culturally responsive teaching competencies.",
            "2025 WASC interim: GenAI guidelines were developed in spring 2023; SAS sponsored AI PL and established a GenAI Task Force.",
            "2024-2026 PL decks: UDL, CRP, and AI are presented together as current learning-design strands supporting learner agency.",
        ],
        "source_confidence": "High for WASC mentions; high for current PL-deck consolidation.",
        "visual_read": "The visuals show three formerly separate strands becoming a combined professional-learning and learner-agency frame.",
        "visuals": [
            {
                "label": "UDL / CRP / AI continuum of learning",
                "deck_slug": "master-sas-slides-1-79f581bc4a",
                "slide_number": 23,
            },
            {
                "label": "CRP as culture-of-innovation connection",
                "deck_slug": "26-oct-erd-self-guided-exploration-b86c66ca89",
                "slide_number": 7,
            },
            {
                "label": "UDL, CRP, AI inquiry process",
                "deck_slug": "morning-framing-sep-16-online-pl-day-4f8c70326c",
                "slide_number": 21,
            },
        ],
    },
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: str | None, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split())
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def load_slide_lookup(record_root: Path) -> dict[tuple[str, int], dict[str, Any]]:
    lookup: dict[tuple[str, int], dict[str, Any]] = {}
    for slides_json in (record_root / "decks").glob("*/slides.json"):
        payload = load_json(slides_json)
        for slide in payload["slides"]:
            lookup[(payload["deck_slug"], int(slide["slide_number"]))] = {
                **slide,
                "filename": payload["filename"],
                "deck_slug": payload["deck_slug"],
                "source_path": payload["source_path"],
            }
    return lookup


def rel(path: Path, from_path: Path) -> str:
    return Path(os.path.relpath(path.resolve(), from_path.parent.resolve())).as_posix()


def enrich_events(record_root: Path) -> list[dict[str, Any]]:
    lookup = load_slide_lookup(record_root)
    enriched: list[dict[str, Any]] = []
    for event in EVENTS:
        visuals = []
        for visual in event["visuals"]:
            slide = lookup.get((visual["deck_slug"], int(visual["slide_number"])))
            item = dict(visual)
            if slide:
                item.update(
                    {
                        "filename": slide["filename"],
                        "title": compact(slide.get("title"), 140),
                        "content_excerpt": compact(slide.get("content"), 320),
                        "image_path": slide.get("image_path"),
                        "hidden": bool(slide.get("hidden")),
                        "source_path": slide.get("source_path"),
                    }
                )
            else:
                item["missing"] = True
            visuals.append(item)
        enriched.append({**event, "visuals": visuals})
    return enriched


def write_json(path: Path, events: list[dict[str, Any]]) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "timeline_type": "concept-introduction timeline; dates from WASC/KM source records, not deck chronology",
        "event_count": len(events),
        "events": events,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, events: list[dict[str, Any]]) -> None:
    lines = [
        "# SAS Concept Introduction Visual Timeline",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This timeline is sequenced by WASC/KM source records, not by slide-deck dates. Images are attached as visual artifacts showing how SAS communicated each concept.",
        "",
    ]
    for event in events:
        lines.extend(
            [
                f"## {event['period']} - {event['concept']}",
                "",
                event["introduced"],
                "",
                f"**Source confidence:** {event['source_confidence']}",
                "",
                "**Source basis:**",
                "",
            ]
        )
        for source in event["source_basis"]:
            lines.append(f"- {source}")
        lines.extend(["", f"**Visual read:** {event['visual_read']}", "", "**Image artifacts:**", ""])
        for visual in event["visuals"]:
            label = visual["label"]
            filename = visual.get("filename", "missing")
            slide = visual["slide_number"]
            title = visual.get("title", "")
            lines.append(f"- {label}. Provenance: `{filename}` slide {slide}. {title}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def visual_card(record_root: Path, html_path: Path, visual: dict[str, Any]) -> str:
    if visual.get("missing") or not visual.get("image_path"):
        return f"""
          <article class="visual missing">
            <div class="missing-box">No rendered image found</div>
            <h3>{html.escape(visual["label"])}</h3>
            <p>Deck slug: {html.escape(str(visual["deck_slug"]))}, slide {visual["slide_number"]}</p>
          </article>
        """
    image_src = html.escape(rel(record_root / visual["image_path"], html_path))
    label = html.escape(visual["label"])
    filename = html.escape(str(visual.get("filename", "")))
    title = html.escape(str(visual.get("title", "")))
    excerpt = html.escape(str(visual.get("content_excerpt", "")))
    return f"""
      <article class="visual">
        <a href="{image_src}"><img src="{image_src}" alt="{label}"></a>
        <div class="visual-body">
          <h3>{label}</h3>
          <p class="title">{title}</p>
          <p class="excerpt">{excerpt}</p>
          <details>
            <summary>Provenance</summary>
            <p class="meta">{filename} · slide {visual["slide_number"]}</p>
          </details>
        </div>
      </article>
    """


def write_image_register_html(path: Path, record_root: Path, events: list[dict[str, Any]]) -> None:
    sections = []
    for event in events:
        cards = []
        for visual in event["visuals"]:
            if visual.get("missing") or not visual.get("image_path"):
                cards.append(
                    f"""
        <article class="image-card missing">
          <div class="missing-box">No image found</div>
          <h3>{html.escape(visual["label"])}</h3>
        </article>
                    """
                )
                continue
            image_src = html.escape(rel(record_root / visual["image_path"], path))
            label = html.escape(str(visual["label"]))
            filename = html.escape(str(visual.get("filename", "")))
            title = html.escape(str(visual.get("title", "")))
            cards.append(
                f"""
        <article class="image-card">
          <a href="{image_src}"><img src="{image_src}" alt="{label}"></a>
          <div class="caption">
            <h3>{label}</h3>
            <p>{title}</p>
            <details>
              <summary>Source record</summary>
              <p>{filename} · slide {visual["slide_number"]}</p>
            </details>
          </div>
        </article>
                """
            )
        sections.append(
            f"""
    <section class="concept" id="{html.escape(event["id"])}">
      <div class="concept-head">
        <p class="period">{html.escape(event["period"])}</p>
        <h2>{html.escape(event["concept"])}</h2>
        <p>{html.escape(event["visual_read"])}</p>
      </div>
      <div class="image-grid">{"".join(cards)}</div>
    </section>
            """
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS Concept Visual Register</title>
  <style>
    :root {{
      --ink: #1f252b;
      --muted: #626b73;
      --line: #d5d8d2;
      --paper: #faf9f4;
      --panel: #ffffff;
      --blue: #245d79;
      --green: #506f5d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    header {{
      padding: 30px 36px 20px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.12;
      letter-spacing: 0;
    }}
    .summary {{
      max-width: 1060px;
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    main {{ padding: 8px 36px 44px; }}
    .concept {{
      border-top: 1px solid var(--line);
      padding: 28px 0 34px;
    }}
    .concept-head {{
      max-width: 1080px;
      margin-bottom: 16px;
    }}
    .period {{
      margin: 0 0 6px;
      color: var(--green);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .concept-head p:last-child {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
      font-size: 14px;
    }}
    .image-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 18px;
      align-items: start;
    }}
    .image-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
    }}
    .image-card img {{
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: contain;
      background: #eef0ec;
      border-bottom: 1px solid var(--line);
    }}
    .caption {{
      padding: 11px 13px 13px;
    }}
    h3 {{
      margin: 0 0 5px;
      font-size: 15px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .caption p, details {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}
    details {{ margin-top: 8px; }}
    summary {{
      color: var(--blue);
      cursor: pointer;
      font-weight: 700;
    }}
    .missing-box {{
      display: grid;
      place-items: center;
      aspect-ratio: 16 / 9;
      background: #eceee8;
      color: var(--muted);
      font-weight: 700;
    }}
    @media (max-width: 760px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .image-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>SAS Concept Visual Register</h1>
    <p class="summary">Key images organized by when the underlying ideas entered or consolidated in SAS source records. The images are evidence of how SAS communicated the ideas visually; the sequence comes from WASC/KM records, not from the deck dates.</p>
  </header>
  <main>
    {"".join(sections)}
  </main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def write_contact_sheet(path: Path, record_root: Path, events: list[dict[str, Any]]) -> bool:
    magick = shutil.which("magick")
    if not magick:
        return False

    inputs: list[str] = []
    for event in events:
        for visual in event["visuals"]:
            image_path = visual.get("image_path")
            if not image_path:
                continue
            source = record_root / image_path
            if not source.exists():
                continue
            label = f"{event['period']}\\n{visual['label']}"
            inputs.extend(["-label", label, str(source)])

    if not inputs:
        return False

    command = [
        magick,
        "montage",
        "-background",
        "#faf9f4",
        "-fill",
        "#1f252b",
        "-pointsize",
        "18",
        *inputs,
        "-thumbnail",
        "520x292",
        "-tile",
        "3x",
        "-geometry",
        "+18+42",
        str(path),
    ]
    subprocess.run(command, check=True)
    return True


def write_html(path: Path, record_root: Path, events: list[dict[str, Any]]) -> None:
    nav = "\n".join(
        f'<a href="#{html.escape(event["id"])}">{html.escape(event["concept"])}</a>'
        for event in events
    )
    sections = []
    for event in events:
        sources = "\n".join(f"<li>{html.escape(source)}</li>" for source in event["source_basis"])
        cards = "\n".join(visual_card(record_root, path, visual) for visual in event["visuals"])
        sections.append(
            f"""
    <section id="{html.escape(event["id"])}" class="event">
      <div class="event-copy">
        <div class="period">{html.escape(event["period"])}</div>
        <h2>{html.escape(event["concept"])}</h2>
        <p>{html.escape(event["introduced"])}</p>
        <p class="confidence"><strong>Confidence:</strong> {html.escape(event["source_confidence"])}</p>
        <h4>Source basis</h4>
        <ul>{sources}</ul>
        <h4>Visual read</h4>
        <p>{html.escape(event["visual_read"])}</p>
      </div>
      <div class="visuals">{cards}</div>
    </section>
            """
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS Concept Introduction Visual Timeline</title>
  <style>
    :root {{
      --ink: #1f252b;
      --muted: #626b73;
      --line: #d5d8d2;
      --paper: #faf9f4;
      --panel: #ffffff;
      --blue: #245d79;
      --green: #506f5d;
      --gold: #a87428;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    header {{
      padding: 28px 36px 22px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 4;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .summary {{
      max-width: 1020px;
      color: var(--muted);
      line-height: 1.45;
      margin: 0 0 16px;
    }}
    nav {{
      display: flex;
      gap: 9px;
      flex-wrap: wrap;
    }}
    nav a {{
      color: var(--blue);
      text-decoration: none;
      border: 1px solid var(--line);
      background: #f6f7f4;
      border-radius: 6px;
      padding: 7px 9px;
      font-size: 12px;
      font-weight: 700;
    }}
    main {{ padding: 0 36px 46px; }}
    .note {{
      max-width: 1180px;
      margin: 24px 0 6px;
      padding: 14px 16px;
      border-left: 4px solid var(--gold);
      background: #fffdf4;
      color: var(--muted);
      line-height: 1.45;
    }}
    .event {{
      display: grid;
      grid-template-columns: minmax(300px, 420px) minmax(0, 1fr);
      gap: 24px;
      padding: 30px 0;
      border-top: 1px solid var(--line);
    }}
    .event-copy {{
      position: sticky;
      top: 130px;
      align-self: start;
    }}
    .period {{
      color: var(--green);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 23px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    h4 {{
      margin: 14px 0 6px;
      font-size: 13px;
    }}
    p, li {{
      font-size: 14px;
      line-height: 1.45;
    }}
    p {{ margin: 0 0 10px; }}
    ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
    .confidence {{ color: var(--muted); }}
    .visuals {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 18px;
      align-content: start;
    }}
    .visual {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
    }}
    .visual img {{
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: contain;
      background: #f0f1ee;
      border-bottom: 1px solid var(--line);
    }}
    .visual-body {{ padding: 12px 14px 14px; }}
    h3 {{
      margin: 0 0 7px;
      font-size: 16px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .meta, .excerpt {{
      color: var(--muted);
      font-size: 12px;
    }}
    .title {{ font-size: 13px; font-weight: 700; }}
    .missing-box {{
      display: grid;
      place-items: center;
      aspect-ratio: 16 / 9;
      background: #eceee8;
      color: var(--muted);
      font-weight: 700;
    }}
    @media (max-width: 900px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .event {{ grid-template-columns: 1fr; }}
      .event-copy {{ position: static; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>SAS Concept Introduction Visual Timeline</h1>
    <p class="summary">Sequenced from WASC/KM source records, then illustrated with key image artifacts from the PowerPoint visual register. This is not a slide-deck chronology.</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <div class="note"><strong>Reading rule:</strong> the date belongs to the concept's introduction or institutional consolidation in WASC/KM records. The image may come from a later deck if that is the clearest surviving visual artifact.</div>
    {"".join(sections)}
  </main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-root", type=Path, default=DEFAULT_RECORD_ROOT)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    args = parser.parse_args()

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    events = enrich_events(args.record_root)
    write_json(args.analysis_dir / "sas_concept_introduction_visual_timeline.json", events)
    write_markdown(args.analysis_dir / "sas_concept_introduction_visual_timeline.md", events)
    write_html(args.analysis_dir / "sas_concept_introduction_visual_timeline.html", args.record_root, events)
    write_image_register_html(args.analysis_dir / "sas_concept_visual_register.html", args.record_root, events)
    contact_sheet = args.analysis_dir / "sas_concept_visual_register_contact_sheet.png"
    wrote_contact_sheet = write_contact_sheet(contact_sheet, args.record_root, events)
    print(f"Wrote {len(events)} concept events")
    print(args.analysis_dir / "sas_concept_introduction_visual_timeline.html")
    print(args.analysis_dir / "sas_concept_visual_register.html")
    if wrote_contact_sheet:
        print(contact_sheet)


if __name__ == "__main__":
    main()
