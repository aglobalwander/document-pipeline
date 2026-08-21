#!/usr/bin/env python3
"""Classify the curated SAS visual register and build a visual timeline."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RECORD_ROOT = Path("data/output/powerpoint_visual_record")
DEFAULT_CURATED_DIR = DEFAULT_RECORD_ROOT / "key_visuals/curated"
DEFAULT_ANALYSIS_DIR = DEFAULT_RECORD_ROOT / "analysis"


PHASES: list[dict[str, str]] = [
    {
        "id": "ttgs",
        "label": "TTGs / Transdisciplinary Transfer Goals",
        "period": "2018-2019",
        "called_work": "TTGs, transfer indicators, I-can / can-do statements",
        "problem": "Move aspirational learner outcomes toward usable transfer language.",
        "visual_language": "goal lists, indicators, I-can statements, rubric-like language",
        "current_read": "Historical foundation; still relevant through TTGs, but not the whole current story.",
    },
    {
        "id": "dtgs_macro_gvc",
        "label": "DTGs / Macro Curriculum / GVC",
        "period": "2018-2022",
        "called_work": "DTGs, Macro Curriculum Blueprint, guaranteed and viable curriculum, performance evidence",
        "problem": "Make transfer, standards, understandings, assessment, and units coherent across courses and divisions.",
        "visual_language": "blueprints, banks of a river, curriculum elements, performance-evidence chains",
        "current_read": "Still a strong design substrate; needs translation into the current Learning Ecosystem architecture.",
    },
    {
        "id": "sas_forward_wasc",
        "label": "SAS Forward / WASC / Strategic Pillars",
        "period": "2022-2024",
        "called_work": "SAS Forward, WASC action plans, strategic pillars, programs and facilities",
        "problem": "Reduce strategic sprawl and connect curriculum work to schoolwide priorities, programs, spaces, and evidence.",
        "visual_language": "pillars, action-plan tables, programs-and-spaces diagrams, strategic-priority frames",
        "current_read": "Institutional coherence layer; active as source history and as bridge into Vision/Core Commitments and the Logic Model.",
    },
    {
        "id": "vision_core_commitments",
        "label": "Vision / Core Commitments / Learning Ecosystem",
        "period": "2023-2025",
        "called_work": "Vision, Mission, Core Commitments, Learning Principles, Learning Ecosystem",
        "problem": "Name the shared purpose and commitments that should organize the next version of learning at SAS.",
        "visual_language": "vision/mission frames, alignment diagrams, commitment graphics, learning-principle summaries",
        "current_read": "Current narrative container; should connect back to TTGs/DTGs and forward into implementation.",
    },
    {
        "id": "principles_of_practice",
        "label": "Principles of Practice",
        "period": "2023-2026",
        "called_work": "7 Principles of Practice, Learning Principles, PoPs inquiry",
        "problem": "Translate the vision into shared pedagogy and observable practice.",
        "visual_language": "principles lists, inquiry cycles, ERD progression, reflection/application scaffolds",
        "current_read": "Pedagogical bridge between institutional commitments and classroom implementation.",
    },
    {
        "id": "pl_plan",
        "label": "PL Plan / Professional Learning System",
        "period": "2024-2026",
        "called_work": "Professional Learning System, PL Plan, ERDs, lesson series, celebration of learning",
        "problem": "Turn the coherence story into adult learning, classroom practice, feedback loops, and implementation routines.",
        "visual_language": "PL journeys, timelines, lesson-series diagrams, support and measurement frames",
        "current_read": "Primary adult-learning mechanism for Learning Ecosystem implementation.",
    },
    {
        "id": "udl",
        "label": "UDL / Universal Design for Learning",
        "period": "2024-2026",
        "called_work": "UDL foundations, removing barriers, multiple means of representation/engagement/expression",
        "problem": "Make learning more accessible and agency-supportive by designing for variability.",
        "visual_language": "continuums, foundations, barrier-removal language, flexible-expression prompts",
        "current_read": "One of the current implementation strands underneath the Learning Ecosystem and PL Plan.",
    },
    {
        "id": "crp",
        "label": "CRP / Culturally Responsive Pedagogy",
        "period": "2024-2026",
        "called_work": "CRP, culturally responsive teaching/pedagogy, inclusion/equity in learning",
        "problem": "Connect inclusion/equity commitments to pedagogy, mindset, relationships, and classroom practice.",
        "visual_language": "mindset/strategy language, inquiry prompts, equity-linked practice frames",
        "current_read": "One of the current implementation strands underneath the Learning Ecosystem and PL Plan.",
    },
    {
        "id": "ai",
        "label": "AI / Artificial Intelligence",
        "period": "2024-2026",
        "called_work": "AI foundations, AI tools, educator/student support, learner agency",
        "problem": "Build educator capacity for AI use while connecting it to agency, planning, and learning design.",
        "visual_language": "inquiry prompts, tool-use processes, knowledge/skill/attitude frames",
        "current_read": "Emerging implementation strand; should be narrated as part of learning design rather than as a separate technology initiative.",
    },
]


PHASE_BY_ID = {phase["id"]: phase for phase in PHASES}


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
        deck_slug = payload["deck_slug"]
        for slide in payload["slides"]:
            lookup[(deck_slug, int(slide["slide_number"]))] = slide
    return lookup


def joined_text(item: dict[str, Any], slide: dict[str, Any] | None) -> str:
    parts = [
        item.get("review_id"),
        item.get("filename"),
        item.get("title"),
        item.get("feedback_note"),
    ]
    if slide:
        parts.extend([slide.get("title"), slide.get("content"), slide.get("notes")])
    labels = " ".join(match.get("label", "") for match in item.get("matches", []))
    parts.append(labels)
    return "\n".join(compact(str(part)) for part in parts if compact(str(part))).lower()


def infer_phase(item: dict[str, Any], slide: dict[str, Any] | None) -> tuple[str, str]:
    filename = str(item.get("filename", "")).lower()
    title = str(item.get("title", "")).lower()
    text = joined_text(item, slide)
    review_id = str(item.get("review_id", ""))
    slide_number = int(item.get("slide_number", 0))

    if review_id == "ADD006":
        return "udl", "continuum slide foregrounds UDL alongside CRP and AI"
    if review_id == "ADD012":
        return "ai", "inquiry slide uses AI process/prompting to connect UDL, CRP, and AI"
    if review_id in {"ADD011", "ADD013", "ADD014", "ADD015", "ADD009"}:
        return "pl_plan", "manual addition from 2024-26 PL Plan / implementation decks"
    if review_id == "ADD010":
        return "vision_core_commitments", "Learning Ecosystem slide frames mission, vision, design, and Principles of Practice"
    if "pl plan tidbits" in filename:
        return "pl_plan", "PL Plan source deck"
    if "morning framing" in filename:
        if "professional learning plan" in title or "pl plan" in text:
            return "pl_plan", "professional-learning plan slide"
        if "ai" in text and "prompt" in text:
            return "ai", "AI-enabled inquiry/process slide"
        return "vision_core_commitments", "Learning Ecosystem / vision source deck"
    if "_master_sas_slides" in filename or "master sas slides" in filename:
        if slide_number == 49:
            return "principles_of_practice", "ERD slide documents inquiry into the 7 Principles of Practice"
        if slide_number == 76:
            return "vision_core_commitments", "logic-model slide bridges Core Commitments and Learning Ecosystem implementation"
        if "udl" in text:
            return "udl", "master-deck slide foregrounds UDL/CRP/AI continuum"
        return "pl_plan", "master-deck implementation visual"

    if review_id in {"ADD016", "ADD017", "ADD018", "ADD019", "ADD020", "ADD021"}:
        if review_id == "ADD021":
            return "principles_of_practice", "hidden source slide for the 7 Principles of Practice"
        return "sas_forward_wasc", "manual addition from SAS Forward Programs/FDP board deck"
    if "sas forward" in filename or "strategic pillars" in filename or "fdp" in filename:
        if "principles of practice" in text:
            return "principles_of_practice", "SAS Forward visual connects vision to 7 Principles of Practice"
        return "sas_forward_wasc", "SAS Forward / programs / spaces / strategic-pillar visual"
    if "priorities & vision 2023-2024" in filename or "schoolwide priorities 2022-2023" in filename:
        if "learning principles" in text or "our learning principles" in text:
            return "vision_core_commitments", "learning-principles slide under the vision/core-commitments layer"
        return "sas_forward_wasc", "schoolwide priorities / WASC / vision visual"
    if "priorities 22-23" in filename or "global citizenship" in filename or "whom do we serve" in filename:
        return "vision_core_commitments", "2022-24 cultures / Core Commitments visual"

    if "macro" in filename or "macro" in text or "curriculum blueprint" in text or "gvc" in text or "guaranteed" in text:
        return "dtgs_macro_gvc", "DTG / macro curriculum / GVC / performance-evidence language"
    if "dtglearningcafe" in filename or "2021-22" in filename or "2021-2022" in filename:
        return "dtgs_macro_gvc", "DTG/GVC translation into schoolwide-priorities period"
    if "dtg" in text and ("essential" in text or "understanding" in text or "performance" in text):
        return "dtgs_macro_gvc", "DTG / EU / EQ / performance-evidence architecture"

    if "ttg" in filename or "dtg keynote" in filename or "i can" in filename or "performance indicators" in filename:
        return "ttgs", "TTG / learner-outcome source deck"
    if re.search(r"\bttg\b|transdisciplinary transfer", text):
        return "ttgs", "TTG / transfer-goal language"

    if "culturally responsive" in text or re.search(r"\bcrp\b", text):
        return "crp", "CRP / culturally responsive pedagogy language"

    if "vision" in text or "mission" in text or "alignment" in text or "core commitments" in text:
        return "vision_core_commitments", "mission / vision / alignment / Core Commitments visual"

    return "vision_core_commitments", "needs human review; defaulted to vision/alignment layer"


def infer_period(item: dict[str, Any]) -> str:
    filename = str(item.get("filename", "")).lower()
    if "2018" in filename or "ttg final" in filename or "ttg group" in filename:
        return "2018-2019"
    if "2021" in filename or "learningcafe" in filename:
        return "2021-2022"
    if "22-23" in filename or "2022" in filename or "strategic pillars" in filename:
        return "2022-2023"
    if "2023-2024" in filename or "sep7" in filename or "fdp" in filename or "whom do we serve" in filename:
        return "2023-2024"
    if "morning framing" in filename or "pl plan" in filename or "master" in filename:
        return "2024-2026"
    return "date-needed"


def classify(record_root: Path, curated_dir: Path) -> list[dict[str, Any]]:
    kept = load_json(curated_dir / "kept_visuals.json")
    slide_lookup = load_slide_lookup(record_root)
    records: list[dict[str, Any]] = []
    for item in kept:
        slide = slide_lookup.get((item["deck_slug"], int(item["slide_number"])))
        phase_id, rationale = infer_phase(item, slide)
        records.append(
            {
                "review_id": item.get("review_id"),
                "phase_id": phase_id,
                "phase_label": PHASE_BY_ID[phase_id]["label"],
                "period": infer_period(item),
                "filename": item.get("filename"),
                "slide_number": item.get("slide_number"),
                "title": compact(item.get("title"), 120),
                "image_path": item.get("image_path"),
                "source_path": item.get("source_path"),
                "hidden": bool(item.get("hidden")),
                "classification_rationale": rationale,
                "content_excerpt": compact((slide or {}).get("content"), 320),
                "matches": [match.get("label") for match in item.get("matches", [])],
            }
        )
    records.sort(
        key=lambda record: (
            [phase["id"] for phase in PHASES].index(record["phase_id"]),
            record["period"],
            str(record["filename"]),
            int(record["slide_number"] or 0),
        )
    )
    return records


def rel(path: Path, from_path: Path) -> str:
    return Path(os.path.relpath(path.resolve(), from_path.parent.resolve())).as_posix()


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "review_id",
        "phase_label",
        "period",
        "filename",
        "slide_number",
        "title",
        "classification_rationale",
        "image_path",
        "source_path",
        "content_excerpt",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fields})


def write_json(path: Path, records: list[dict[str, Any]]) -> None:
    counts = Counter(record["phase_label"] for record in records)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "visual_count": len(records),
        "phase_counts": dict(counts),
        "classification_policy": "Working classification for curated SAS visual register; source screenshots and decks remain unchanged.",
        "phases": PHASES,
        "visuals": records,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, records: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["phase_id"]].append(record)

    lines = [
        "# SAS Visual Register Classification",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Purpose: classify the curated visual record by the institutional problem each visual helped SAS communicate.",
        "",
        "This is a working classification. It does not remove or demote source evidence; it makes the visual history easier to reason about.",
        "",
    ]
    for phase in PHASES:
        phase_records = grouped.get(phase["id"], [])
        lines.extend(
            [
                f"## {phase['label']}",
                "",
                f"- Period: {phase['period']}",
                f"- What SAS called the work: {phase['called_work']}",
                f"- Problem it was solving: {phase['problem']}",
                f"- Visual language: {phase['visual_language']}",
                f"- Current read: {phase['current_read']}",
                f"- Visuals classified here: {len(phase_records)}",
                "",
            ]
        )
        for record in phase_records:
            lines.append(
                f"- `{record['review_id']}` `{record['filename']}` slide {record['slide_number']}: "
                f"{record['title']} — {record['classification_rationale']}"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def timeline_card(record_root: Path, html_path: Path, record: dict[str, Any]) -> str:
    image_src = html.escape(rel(record_root / record["image_path"], html_path))
    title = html.escape(record["title"] or f"Slide {record['slide_number']}")
    filename = html.escape(str(record["filename"]))
    rationale = html.escape(record["classification_rationale"])
    excerpt = html.escape(record["content_excerpt"])
    return f"""
      <article class="visual-card">
        <a href="{image_src}"><img src="{image_src}" alt="{title}"></a>
        <div class="visual-meta">
          <div class="eyebrow">{html.escape(str(record["review_id"]))} · slide {record["slide_number"]} · {html.escape(record["period"])}</div>
          <h3>{title}</h3>
          <p class="deck">{filename}</p>
          <p>{rationale}</p>
          <p class="excerpt">{excerpt}</p>
        </div>
      </article>
    """


def write_html(path: Path, record_root: Path, records: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["phase_id"]].append(record)
    counts = Counter(record["phase_label"] for record in records)
    phase_nav = "\n".join(
        f'<a href="#{phase["id"]}">{html.escape(phase["label"])} <span>{len(grouped.get(phase["id"], []))}</span></a>'
        for phase in PHASES
    )

    sections = []
    for phase in PHASES:
        phase_records = grouped.get(phase["id"], [])
        cards = "\n".join(timeline_card(record_root, path, record) for record in phase_records)
        sections.append(
            f"""
    <section id="{phase["id"]}" class="phase">
      <div class="phase-copy">
        <div class="period">{html.escape(phase["period"])}</div>
        <h2>{html.escape(phase["label"])}</h2>
        <dl>
          <dt>What SAS called the work</dt><dd>{html.escape(phase["called_work"])}</dd>
          <dt>Problem it was solving</dt><dd>{html.escape(phase["problem"])}</dd>
          <dt>Visual language</dt><dd>{html.escape(phase["visual_language"])}</dd>
          <dt>What remains current</dt><dd>{html.escape(phase["current_read"])}</dd>
        </dl>
      </div>
      <div class="visual-grid">
        {cards}
      </div>
    </section>
            """
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS Curriculum Story Visual Timeline</title>
  <style>
    :root {{
      --ink: #20242a;
      --muted: #626972;
      --line: #d6d8d2;
      --paper: #fbfaf7;
      --panel: #ffffff;
      --blue: #235a7c;
      --green: #54735b;
      --gold: #b0762a;
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
      z-index: 5;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .summary {{
      max-width: 960px;
      color: var(--muted);
      line-height: 1.45;
      margin: 0 0 18px;
    }}
    nav {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    nav a {{
      color: var(--blue);
      border: 1px solid var(--line);
      background: #f6f7f4;
      text-decoration: none;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
    }}
    nav span {{
      color: var(--muted);
      margin-left: 4px;
      font-weight: 400;
    }}
    main {{
      padding: 0 36px 48px;
    }}
    .source-strip {{
      margin: 24px 0;
      padding: 16px;
      border-left: 4px solid var(--gold);
      background: #fffdf5;
      max-width: 1180px;
      line-height: 1.45;
    }}
    .phase {{
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 24px;
      padding: 30px 0;
      border-top: 1px solid var(--line);
    }}
    .phase-copy {{
      position: sticky;
      top: 128px;
      align-self: start;
    }}
    .period {{
      color: var(--green);
      font-weight: 700;
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0;
      margin-bottom: 8px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 23px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    dl {{
      margin: 0;
      display: grid;
      gap: 12px;
    }}
    dt {{
      font-weight: 700;
      font-size: 13px;
    }}
    dd {{
      margin: 3px 0 0;
      color: var(--muted);
      line-height: 1.45;
      font-size: 14px;
    }}
    .visual-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 18px;
    }}
    .visual-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
    }}
    .visual-card img {{
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: contain;
      background: #f1f2ef;
      border-bottom: 1px solid var(--line);
    }}
    .visual-meta {{
      padding: 12px 14px 14px;
    }}
    .eyebrow {{
      color: var(--green);
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    h3 {{
      margin: 0 0 8px;
      font-size: 16px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    p {{
      margin: 0 0 8px;
      line-height: 1.42;
      font-size: 14px;
    }}
    .deck, .excerpt {{
      color: var(--muted);
      font-size: 12px;
    }}
    .counts {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 860px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .phase {{ grid-template-columns: 1fr; }}
      .phase-copy {{ position: static; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>SAS Curriculum Story Visual Timeline</h1>
    <p class="summary">A working visual history of how SAS communicated learner outcomes, curriculum coherence, WASC/SAS Forward, Core Commitments, and the Learning Ecosystem across the curated PowerPoint visual register.</p>
    <nav>{phase_nav}</nav>
    <div class="counts">{" · ".join(f"{html.escape(label)}: {count}" for label, count in counts.items())}</div>
  </header>
  <main>
    <div class="source-strip">
      <strong>Use:</strong> read each phase as a claim about what SAS was trying to make coherent, not as a recommendation to reuse every visual. Source screenshots remain in the extracted PowerPoint visual record.
    </div>
    {"".join(sections)}
  </main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-root", type=Path, default=DEFAULT_RECORD_ROOT)
    parser.add_argument("--curated-dir", type=Path, default=DEFAULT_CURATED_DIR)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    args = parser.parse_args()

    record_root = args.record_root
    curated_dir = args.curated_dir
    analysis_dir = args.analysis_dir
    analysis_dir.mkdir(parents=True, exist_ok=True)

    records = classify(record_root, curated_dir)
    write_json(curated_dir / "visual_register_classification.json", records)
    write_csv(curated_dir / "visual_register_classification.csv", records)
    write_markdown(curated_dir / "visual_register_classification.md", records)
    write_html(analysis_dir / "sas_curriculum_story_visual_timeline.html", record_root, records)

    print(f"Classified {len(records)} visuals")
    print(curated_dir / "visual_register_classification.md")
    print(analysis_dir / "sas_curriculum_story_visual_timeline.html")


if __name__ == "__main__":
    main()
