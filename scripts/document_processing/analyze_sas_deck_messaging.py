#!/usr/bin/env python3
"""Analyze SAS PowerPoint visual-record text for messaging trajectory."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RECORD_ROOT = Path("data/output/powerpoint_visual_record")
DEFAULT_OUTPUT_DIR = DEFAULT_RECORD_ROOT / "analysis"


TERM_PATTERNS: dict[str, str] = {
    "TTG": r"\bTTGs?\b|Transdisciplinary Transfer Goals?",
    "DTG": r"\bDTGs?\b|Disciplinary Transfer Goals?",
    "transfer_goals": r"transfer goals?|long[- ]term transfer goals?",
    "macro_blueprint": r"macro curriculum|macro approach|curriculum blueprint|macro[- ]curriculum|blueprint",
    "performance_evidence": r"performance indicators?|performance tasks?|cornerstone tasks?|evidence",
    "assessment": r"\bassessment\b|assessments",
    "GVC": r"guaranteed and viable curriculum|\bGVC\b",
    "WASC": r"\bWASC\b|action plans?|focus areas?",
    "SAS_Forward": r"SAS Forward|strategic pillars?|5 pillars|promise and plan",
    "core_commitments": r"core commitments?|mission|vision|cultures?",
    "learning_ecosystem": r"learning ecosystem",
    "principles_of_practice": r"principles of practice|\bPoP\b",
    "professional_learning": r"professional learning|\bPL\b|early release days?|\bERD\b|cohort",
    "UDL": r"\bUDL\b|Universal Design for Learning",
    "CRP": r"\bCRP\b|Culturally Responsive Pedagogy",
    "AI": r"\bAI\b|Artificial Intelligence",
    "learner_agency": r"learner agency|student agency|agency",
    "wellbeing_belonging": r"wellbeing|well-being|belonging|joy and care|shared responsibility",
    "programs_spaces": r"programs?|learning spaces?|facility|facilities|\bFDP\b",
}


PERIOD_RULES: list[tuple[str, str]] = [
    (r"Morning Framing|PL Plan Tidbits|master_sas|master sas|_master_sas", "2024-26 Learning Ecosystem / PL System"),
    (r"2023-2024|2023-24|Sep7|FDP|Whom Do We Serve", "2023-24 Priorities / WASC / Programs-FDP"),
    (r"2022|22-23|2022-2023|SAS FORWARD|STRATEGIC PILLARS|Global Citizenship|26 Oct ERD", "2022-23 SAS Forward / Strategic Pillars"),
    (r"2021|Oct\\. '21|2021-22|2021-2022|LearningCafe", "2021-22 Schoolwide Priorities / DTG Translation"),
    (r"2018|March 23|Sept 26|Oct 17|TTG Final|TTG Group|I Can|DTG Keynote|Performance Indicators|DTG EU&EQ", "2018-19 TTG / DTG / Macro Curriculum Formation"),
    (r"macro curriculum|macro_blueprint|macro blueprint|2 minutes|Alignment", "Date Needed / Macro Curriculum Explainers"),
]


@dataclass
class DeckRecord:
    filename: str
    deck_slug: str
    source_path: str
    slide_count: int
    visible_slide_count: int
    hidden_slide_count: int
    period: str
    term_counts: Counter[str]
    top_slide_evidence: list[dict[str, Any]]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_text(value: str | None) -> str:
    return " ".join(str(value or "").split())


def infer_period(filename: str, deck_text: str) -> str:
    name = filename.lower()
    if any(token in name for token in ["sept 26 2018", "march 23, 2018", "ttg final", "ttg group", "ttg i can", "ttg performance", "dtg keynote"]):
        return "2018-19 TTG / DTG / Macro Curriculum Formation"
    if any(token in name for token in ["2021-22", "2021-2022", "learningcafe", "dtg eu&eq"]):
        return "2021-22 Schoolwide Priorities / DTG Translation"
    if any(token in name for token in ["22-23", "2022-2023", "strategic pillars", "schoolwide priorities 2022", "priorities 22-23"]):
        return "2022-23 SAS Forward / Strategic Pillars"
    if any(token in name for token in ["2023-2024", "2023-24", "sep7", "fdp", "whom do we serve"]):
        return "2023-24 Priorities / WASC / Programs-FDP"
    if any(token in name for token in ["morning framing", "pl plan tidbits", "master_sas", "master sas", "_master_sas"]):
        return "2024-26 Learning Ecosystem / PL System"
    if any(token in name for token in ["macro curriculum", "macro_blueprint", "macro blueprint", "2 minutes", "alignment"]):
        return "Date Needed / Macro Curriculum Explainers"

    haystack = f"{filename}\n{deck_text}"
    for pattern, period in PERIOD_RULES:
        if re.search(pattern, haystack, re.IGNORECASE):
            return period
    return "Unplaced / Needs Human Date"


def count_terms(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for label, pattern in TERM_PATTERNS.items():
        count = len(re.findall(pattern, text, re.IGNORECASE))
        if count:
            counts[label] = count
    return counts


def slide_text(slide: dict[str, Any]) -> str:
    return "\n".join(
        compact_text(slide.get(field))
        for field in ["title", "content", "notes", "normalized_text"]
        if compact_text(slide.get(field))
    )


def top_evidence_slides(slides: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for slide in slides:
        text = slide_text(slide)
        terms = count_terms(text)
        if not terms:
            continue
        scored.append(
            {
                "slide_number": slide["slide_number"],
                "title": slide.get("title"),
                "hidden": slide.get("hidden", False),
                "image_path": slide.get("image_path"),
                "term_counts": dict(terms),
                "excerpt": compact_text(text)[:320],
            }
        )
    scored.sort(key=lambda item: (-sum(item["term_counts"].values()), item["slide_number"]))
    return scored[:limit]


def build_records(record_root: Path) -> list[DeckRecord]:
    manifest = load_json(record_root / "manifest.json")
    records: list[DeckRecord] = []
    seen_hashes: set[str] = set()
    for deck in manifest["decks"]:
        source_hash = deck.get("source_sha256")
        if source_hash in seen_hashes:
            continue
        seen_hashes.add(source_hash)
        payload = load_json(record_root / deck["slides_json"])
        full_text = "\n".join(slide_text(slide) for slide in payload["slides"])
        records.append(
            DeckRecord(
                filename=deck["filename"],
                deck_slug=deck["deck_slug"],
                source_path=deck["source_path"],
                slide_count=deck["slide_count"],
                visible_slide_count=deck["visible_slide_count"],
                hidden_slide_count=deck["hidden_slide_count"],
                period=infer_period(deck["filename"], full_text),
                term_counts=count_terms(full_text),
                top_slide_evidence=top_evidence_slides(payload["slides"]),
            )
        )
    return records


def write_inventory_csv(output_dir: Path, records: list[DeckRecord]) -> None:
    labels = list(TERM_PATTERNS)
    with (output_dir / "deck_messaging_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "period",
                "filename",
                "slide_count",
                "visible_slide_count",
                "hidden_slide_count",
                "top_terms",
                *labels,
            ],
        )
        writer.writeheader()
        for record in records:
            top_terms = ", ".join(
                f"{label}:{count}" for label, count in record.term_counts.most_common(6)
            )
            row = {
                "period": record.period,
                "filename": record.filename,
                "slide_count": record.slide_count,
                "visible_slide_count": record.visible_slide_count,
                "hidden_slide_count": record.hidden_slide_count,
                "top_terms": top_terms,
            }
            for label in labels:
                row[label] = record.term_counts.get(label, 0)
            writer.writerow(row)


def period_summary(records: list[DeckRecord]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    grouped: dict[str, list[DeckRecord]] = defaultdict(list)
    for record in records:
        grouped[record.period].append(record)
    for period, period_records in grouped.items():
        terms: Counter[str] = Counter()
        for record in period_records:
            terms.update(record.term_counts)
        summary[period] = {
            "deck_count": len(period_records),
            "slide_count": sum(record.slide_count for record in period_records),
            "top_terms": terms.most_common(10),
            "decks": [record.filename for record in period_records],
        }
    return summary


def write_json(output_dir: Path, records: list[DeckRecord]) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "unique_deck_count": len(records),
        "period_summary": period_summary(records),
        "decks": [
            {
                "filename": record.filename,
                "deck_slug": record.deck_slug,
                "source_path": record.source_path,
                "period": record.period,
                "slide_count": record.slide_count,
                "visible_slide_count": record.visible_slide_count,
                "hidden_slide_count": record.hidden_slide_count,
                "term_counts": dict(record.term_counts),
                "top_slide_evidence": record.top_slide_evidence,
            }
            for record in records
        ],
    }
    (output_dir / "deck_messaging_analysis.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def evidence_line(record: DeckRecord) -> str:
    terms = ", ".join(f"{label} ({count})" for label, count in record.term_counts.most_common(5))
    return f"- `{record.filename}`: {terms or 'no tracked terms'}."


def write_brief(record_root: Path, output_dir: Path, records: list[DeckRecord]) -> None:
    grouped: dict[str, list[DeckRecord]] = defaultdict(list)
    for record in records:
        grouped[record.period].append(record)

    curated_path = record_root / "key_visuals/curated/curation_summary.json"
    curated = load_json(curated_path) if curated_path.exists() else {}

    ordered_periods = [
        "2018-19 TTG / DTG / Macro Curriculum Formation",
        "2021-22 Schoolwide Priorities / DTG Translation",
        "2022-23 SAS Forward / Strategic Pillars",
        "2023-24 Priorities / WASC / Programs-FDP",
        "2024-26 Learning Ecosystem / PL System",
        "Date Needed / Macro Curriculum Explainers",
    ]

    lines = [
        "# SAS Deck Messaging Timeline",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        f"- Source record: `{record_root}`",
        f"- Unique deck sources analyzed: {len(records)}",
        f"- Curated visual register count: {curated.get('kept_count', 'unknown')}",
        "",
        "This is a source-backed first pass over the text extracted from the PowerPoint visual record. It is intended to explain what the decks actually communicate over time, not to decide the final public narrative.",
        "",
        "## Timeline Read",
        "",
    ]

    period_reads = {
        "2018-19 TTG / DTG / Macro Curriculum Formation": "The early curriculum story is about transfer, performance evidence, and curriculum architecture. The school is trying to move from learner-outcome language into usable transfer goals, indicators, rubrics, and macro/micro curriculum design.",
        "2021-22 Schoolwide Priorities / DTG Translation": "The language moves from TTGs alone into DTGs, guaranteed and viable curriculum, schoolwide priorities, and cultures of joy/care/shared responsibility. The work is becoming divisional and operational.",
        "2022-23 SAS Forward / Strategic Pillars": "The message shifts toward schoolwide strategic coherence: SAS Forward, pillars, promises, targets, wellbeing, belonging, and alignment with WASC action-plan work.",
        "2023-24 Priorities / WASC / Programs-FDP": "WASC, SAS Forward, programs, and facilities become part of the same coherence argument. The question becomes how programs and learning spaces support the vision, desired skills, and Principles of Practice.",
        "2024-26 Learning Ecosystem / PL System": "The current story consolidates around the Learning Ecosystem and professional learning system: UDL, CRP, AI, learner agency, Principles of Practice, logic model, and implementation across time.",
        "Date Needed / Macro Curriculum Explainers": "These decks are conceptually central to the macro-curriculum story, but need a human date/source check before they are used as chronological evidence.",
    }

    for period in ordered_periods:
        period_records = grouped.get(period, [])
        if not period_records:
            continue
        terms = Counter()
        for record in period_records:
            terms.update(record.term_counts)
        lines.extend(
            [
                f"### {period}",
                "",
                period_reads[period],
                "",
                f"Decks: {len(period_records)}. Slides: {sum(record.slide_count for record in period_records)}.",
                "",
                "Top tracked language: "
                + ", ".join(f"{label} ({count})" for label, count in terms.most_common(8))
                + ".",
                "",
                "Evidence decks:",
                "",
            ]
        )
        lines.extend(evidence_line(record) for record in sorted(period_records, key=lambda item: item.filename))
        lines.append("")

    lines.extend(
        [
            "## What The Trajectory Suggests",
            "",
            "1. SAS keeps returning to the same coherence problem.",
            "",
            "Across the decks, the labels change, but the question stays stable: how do we connect mission and vision to curriculum, assessment, transfer, schoolwide priorities, professional learning, programs, and evidence without creating another layer of disconnected language?",
            "",
            "2. The curriculum story broadens into an institutional coherence story.",
            "",
            "The TTG / DTG / macro-blueprint work begins as curriculum architecture. By 2022-2024, that architecture is being nested inside WASC priorities, SAS Forward, programs, facilities, and schoolwide cultures. By 2024-2026, it appears inside a Learning Ecosystem and PL system.",
            "",
            "3. WASC functions as an organizing mirror, not just an accreditation event.",
            "",
            "The WASC language is used to connect priorities, action plans, evidence, and focus areas. The useful read is that WASC helps SAS test whether the pieces are coherent and visible enough to guide action.",
            "",
            "4. Professional learning becomes the implementation mechanism.",
            "",
            "The newer decks move heavily toward UDL, CRP, AI, learner agency, PL timelines, lesson series, consultants, reflection, and celebration of learning. That suggests the story is no longer only what the framework is, but how adults learn it into practice.",
            "",
            "5. The visual drift matters because the underlying story is stable.",
            "",
            "The curated register shows many different visual grammars for the same institutional logic: cycles, pillars, pyramids, timelines, ecosystems, continuums, and one-page posters. The next synthesis should preserve the real history while proposing a clearer current visual language.",
            "",
            "## Useful Next Questions",
            "",
            "- What is the smallest source-backed narrative that connects TTGs / DTGs, SAS Forward, WASC, Core Commitments, Learning Ecosystem, and the current PL plan?",
            "- Which terms are still active operating language, and which are historical evidence only?",
            "- Which visuals show real institutional adoption versus workshop facilitation scaffolds?",
            "- Where do the curated visuals need source dates, audience labels, and human confirmation?",
            "- What is the next coherent visual model that respects this history without reproducing the drift?",
            "",
            "## Generated Evidence Files",
            "",
            "- `deck_messaging_analysis.json`",
            "- `deck_messaging_inventory.csv`",
        ]
    )

    (output_dir / "sas_deck_messaging_timeline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze SAS deck messaging from the PPTX visual record.")
    parser.add_argument("--record-root", type=Path, default=DEFAULT_RECORD_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    record_root = args.record_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    records = build_records(record_root)
    write_inventory_csv(output_dir, records)
    write_json(output_dir, records)
    write_brief(record_root, output_dir, records)

    print(f"Analyzed unique deck sources: {len(records)}")
    print(f"Brief: {output_dir / 'sas_deck_messaging_timeline.md'}")
    print(f"Inventory: {output_dir / 'deck_messaging_inventory.csv'}")
    print(f"JSON: {output_dir / 'deck_messaging_analysis.json'}")


if __name__ == "__main__":
    main()
