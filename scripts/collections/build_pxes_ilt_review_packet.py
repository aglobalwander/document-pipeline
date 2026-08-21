#!/usr/bin/env python3
"""Build the canonical printable review packet for PXES ILT evidence units."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COLLECTION_DIR = (
    REPO_ROOT
    / "data"
    / "output"
    / "collections"
    / "pxes-ilt-2026-08-17-sticky-evidence"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "output"
    / "pdf"
    / "pxes-ilt-2026-08-17-sticky-evidence-review-packet.pdf"
)


INK = colors.HexColor("#183143")
MUTED = colors.HexColor("#52636F")
TEAL = colors.HexColor("#287C78")
AMBER = colors.HexColor("#C57923")
PALE = colors.HexColor("#F3F5F4")
LINE = colors.HexColor("#CBD3D5")


def ascii_safe(value: Any) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "\u2014": " - ",
        "\u2013": "-",
        "\u2192": " -> ",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return html.escape(text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scaled_image(path: Path, max_width: float, max_height: float) -> Image:
    with PILImage.open(path) as opened:
        width, height = opened.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def page_chrome(canvas: Any, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "PXES ILT - internal SAS review artifact - manual verification required")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=25,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=5 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=MUTED,
            spaceAfter=5 * mm,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=INK,
            spaceAfter=4 * mm,
        ),
        "heading": ParagraphStyle(
            "Heading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=TEAL,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=MUTED,
        ),
        "record": ParagraphStyle(
            "Record",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=INK,
            alignment=TA_CENTER,
        ),
        "status": ParagraphStyle(
            "Status",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=AMBER,
        ),
    }


def collage_pages(records: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [
        Paragraph("PXES ILT evidence review packet", styles["title"]),
        Paragraph(
            "August 17, 2026 - purpose formation session. Canonical Pipeline Documents review artifact. "
            "All 36 sticky notes and the red-marker 09:00-09:10 open-conversation sidebar are indexed below; all records remain manual_review.",
            styles["subtitle"],
        ),
        Paragraph("1. Record-ID image collage", styles["section"]),
    ]
    columns, page_capacity = 3, 12
    for page_start in range(0, len(records), page_capacity):
        if page_start:
            story.extend([PageBreak(), Paragraph("1. Record-ID image collage - continued", styles["section"])] )
        chunk = records[page_start : page_start + page_capacity]
        rows: list[list[Any]] = []
        for row_start in range(0, len(chunk), columns):
            row: list[Any] = []
            for record in chunk[row_start : row_start + columns]:
                image = scaled_image(Path(record["crop_path"]), 48 * mm, 31 * mm)
                layer_label = {
                    "open_discussion_whiteboard": "open discussion",
                    "pair_echo": "pair echo",
                    "shared_thread": "shared thread",
                }.get(record["layer"], record["layer"])
                label = Paragraph(
                    f"{ascii_safe(record['record_id'])}<br/>"
                    f"<font color='#52636F'>{ascii_safe(layer_label)} | "
                    f"{ascii_safe(record['source_marker_normalized'] or 'marker unresolved')}</font>",
                    styles["record"],
                )
                row.append([image, Spacer(1, 1.5 * mm), label])
            while len(row) < columns:
                row.append("")
            rows.append(row)
        table = Table(rows, colWidths=[55 * mm] * columns, rowHeights=[42 * mm] * len(rows))
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
                    ("BACKGROUND", (0, 0), (-1, -1), PALE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            )
        )
        story.append(table)
    return story


def review_card(record: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    marker = record["source_marker_normalized"] or "unresolved"
    metadata = (
        f"<b>{ascii_safe(record['record_id'])}</b><br/>"
        f"Layer: {ascii_safe(record['layer'])}<br/>"
        f"Visible marker: {ascii_safe(marker)} ({ascii_safe(record['marker_confidence'])})<br/>"
        f"Authorship: {ascii_safe(record['authorship'])}<br/>"
        f"Source: {ascii_safe(record['primary_photo'])}"
    )
    proposed = (
        "<b>Proposed transcription</b><br/>"
        f"{ascii_safe(record['proposed_transcription'] or '[no proposal]')}<br/><br/>"
        f"<b>Visual proposal confidence:</b> {ascii_safe(record['transcription_confidence'])}<br/>"
        f"<b>Local OCR token confidence:</b> {ascii_safe(record['ocr_mean_confidence'])}"
    )
    top = Table(
        [
            [
                [
                    scaled_image(Path(record["crop_path"]), 62 * mm, 42 * mm),
                    Spacer(1, 1.5 * mm),
                    Paragraph(metadata, styles["small"]),
                ],
                [
                    Paragraph("MANUAL_REVIEW", styles["status"]),
                    Spacer(1, 1.5 * mm),
                    Paragraph(proposed, styles["body"]),
                ],
            ]
        ],
        colWidths=[75 * mm, 92 * mm],
    )
    top.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    verification = Paragraph(
        "<b>Human-verified transcription / correction</b><br/><br/>"
        "________________________________________________________________________________<br/>"
        "________________________________________________________________________________<br/>"
        "[ ] Text confirmed   [ ] Marker confirmed   [ ] Cross-outs/annotations confirmed   [ ] Keep manual_review",
        styles["small"],
    )
    outer = Table([[top], [verification]], colWidths=[171 * mm])
    outer.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LINEABOVE", (0, 1), (-1, 1), 0.5, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), PALE),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    return outer


def review_pages(records: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [PageBreak(), Paragraph("2. Source image and proposed transcription", styles["section"])]
    story.append(
        Paragraph(
            "Each proposal is adjacent to its source crop. Write corrections in the verification space. "
            "Do not clear manual_review from OCR confidence alone.",
            styles["subtitle"],
        )
    )
    for index, record in enumerate(records):
        story.append(KeepTogether([review_card(record, styles), Spacer(1, 5 * mm)]))
        if index % 2 == 1 and index < len(records) - 1:
            story.append(PageBreak())
    return story


def boundary_pages(styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        PageBreak(),
        Paragraph("3. Interpretation boundary and no-consensus caution", styles["section"]),
        Paragraph("What this packet establishes", styles["heading"]),
        Paragraph(
            "It preserves a bounded visual record: 25 individual-initial notes, 5 participant-authored PE pair echoes, "
            "6 participant-authored ST shared threads, and one focused red-marker sidebar from the substantive 09:00-09:10 open conversation.",
            styles["body"],
        ),
        Paragraph("What it does not establish", styles["heading"]),
        Paragraph(
            "This packet does not establish consensus, a final purpose statement, an institutional commitment, or a complete account of every spoken contribution. "
            "The sidebar is captured evidence for what is visibly scribed; only illegible, occluded, or out-of-frame content is unavailable. There is no audio record.",
            styles["body"],
        ),
        Paragraph("No-consensus caution", styles["heading"]),
        Paragraph(
            "Shared threads are participant-authored convergence signals, not permission to erase individual premises. Keep tensions, minority language, assumptions, "
            "cross-outs, and questions visible. Any synthesis should distinguish source language, proposed pattern, and open choice.",
            styles["body"],
        ),
        Paragraph("Privacy and role", styles["heading"]),
        Paragraph(
            "Use initials only. Prepared crops strip EXIF metadata and retain source hashes back to the Session Planner originals. Scott is working alongside Jonathan "
            "as an SAS colleague and facilitator, at Jonathan's request. Jonathan decides any onward sharing, including with Kim and the VPs.",
            styles["body"],
        ),
    ]


def method_pages(styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        PageBreak(),
        Paragraph("4. Method overview", styles["section"]),
        Paragraph("Evidence lineage", styles["heading"]),
        Paragraph(
            "Session Planner retains the 13 original photographs. Pipeline Documents verifies hashes, auto-orients and strips metadata from working derivatives, "
            "segments 37 review units, and runs local Tesseract OCR without a paid API.",
            styles["body"],
        ),
        Paragraph("Participant-authored layers", styles["heading"]),
        Paragraph(
            "IND records preserve an individual's initials and B/V/A marker. PE records preserve participant-authored pair echoes. ST records preserve "
            "participant-authored shared threads. The red sidebar preserves the substantive open-conversation capture as a separate evidence type.",
            styles["body"],
        ),
        Paragraph("Review rule", styles["heading"]),
        Paragraph(
            "Tesseract text and the adjacent visual transcription are proposals. A human reviewer confirms the image, exact text, source marker, cross-outs, and "
            "annotations before manual_review can be cleared. Illegible text remains unresolved; it is never reconstructed by inference.",
            styles["body"],
        ),
        Paragraph("Cross-repository handoff", styles["heading"]),
        Paragraph(
            "Campaign develops the cross-layer Ember Circles analysis method. Data Analysis owns the bounded SAS mid-project interpretation. Session Planner owns "
            "the meeting design and post-session continuity. Each lane cites this packet but does not silently promote proposed transcription to verified evidence.",
            styles["body"],
        ),
    ]


def next_step_pages(styles: dict[str, ParagraphStyle]) -> list[Any]:
    steps = [
        "1. Human-review the 37 records; resolve uncertain initials and every medium/low proposal.",
        "2. Reissue the transcription surface with verified text while preserving source/proposal history.",
        "3. Apply the Campaign Ember Circles comparison across individual, PE, ST, and open-conversation layers without forcing consensus.",
        "4. Let Data Analysis prepare a bounded 'what seems to be emerging' note for Scott and Jonathan, clearly separating evidence, interpretation, and open choices.",
        "5. Scott and Jonathan reflect together. Jonathan chooses whether and how to share with Kim and the VPs.",
        "6. Co-plan the August 24 meeting so it continues the thread: return the evidence to participants, test the emerging language, and decide the next useful move.",
    ]
    return [
        PageBreak(),
        Paragraph("5. Next steps and follow-up", styles["section"]),
        Paragraph(
            "This is an internal SAS collaboration with Jonathan. The immediate aim is a trustworthy review surface and a thoughtful next conversation, not a "
            "prematurely polished purpose statement.",
            styles["subtitle"],
        ),
        *[Paragraph(step, styles["body"]) for step in steps],
        Paragraph("Companion purpose hypotheses - reference only", styles["heading"]),
        Paragraph(
            "Session Planner's JONATHAN_AUG17_CO_REFLECTION.md holds three analyst-prepared, source-traced hypotheses: "
            "A. Student experience through coherent action; B. Collective capacity for teaching and learning; and "
            "C. Collective ownership across strategy and practice. They are not Pipeline findings, participant-verified language, or a team decision. "
            "Use them only as Scott-and-Jonathan co-planning material after reviewing the source packet.",
            styles["body"],
        ),
        Paragraph(
            "Session Planner: sessions/pxes-ilt-purpose-norms-aug17-24/planning/JONATHAN_AUG17_CO_REFLECTION.md",
            styles["small"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("Jonathan reflection notes", styles["heading"]),
        Paragraph(
            "________________________________________________________________________________<br/><br/>"
            "________________________________________________________________________________<br/><br/>"
            "________________________________________________________________________________<br/><br/>"
            "________________________________________________________________________________",
            styles["body"],
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-dir", type=Path, default=DEFAULT_COLLECTION_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    review_json = args.collection_dir / "review" / "transcription_review.json"
    manifest_path = args.collection_dir / "source_manifest.json"
    records = json.loads(review_json.read_text(encoding="utf-8"))
    if len(records) != 37 or sum(record["manual_review"] for record in records) != 37:
        raise ValueError("Expected 37 manual-review records before packet generation")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    document = BaseDocTemplate(
        str(args.output),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title="PXES ILT August 17 sticky-evidence review packet",
        author="SAS internal working artifact",
        subject="Manual review of individual, pair echo, shared thread, and open-conversation evidence",
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="content",
    )
    document.addPageTemplates([PageTemplate(id="review", frames=[frame], onPage=page_chrome)])

    story: list[Any] = []
    story.extend(collage_pages(records, styles))
    story.extend(review_pages(records, styles))
    story.extend(boundary_pages(styles))
    story.extend(method_pages(styles))
    story.extend(next_step_pages(styles))
    document.build(story)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["canonical_review_pdf"] = str(args.output)
    manifest["canonical_review_pdf_sha256"] = sha256_file(args.output)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "pdf": str(args.output),
                "bytes": args.output.stat().st_size,
                "sha256": manifest["canonical_review_pdf_sha256"],
                "records": len(records),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
