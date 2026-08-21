#!/usr/bin/env python3
"""Apply review-board feedback to produce a curated key-visual set."""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


DEFAULT_RECORD_ROOT = Path("data/output/powerpoint_visual_record")
DEFAULT_REVIEW_ITEMS = DEFAULT_RECORD_ROOT / "key_visuals/review/review_items.json"
DEFAULT_FEEDBACK = Path("data/input/powerpoint/sas-key-visual-feedback.json")
DEFAULT_ADDITIONS = DEFAULT_RECORD_ROOT / "key_visuals/additions/manual_additions.json"
DEFAULT_OUTPUT_DIR = DEFAULT_RECORD_ROOT / "key_visuals/curated"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def truncate(value: str | None, limit: int = 72) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def relative_from_html(path: Path, html_path: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), html_path.parent.resolve())).as_posix()


def feedback_by_id(feedback: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in feedback}


def apply_feedback(items: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    marked = feedback_by_id(feedback)
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []

    for item in items:
        review_id = item["review_id"]
        mark = marked.get(review_id, {})
        disposition = (mark.get("disposition") or "").strip().lower()
        enriched = dict(item)
        enriched["feedback_disposition"] = disposition or "unmarked"
        enriched["feedback_move_target"] = mark.get("move_target") or ""
        enriched["feedback_note"] = mark.get("note") or ""
        if disposition == "remove":
            removed.append(enriched)
        else:
            kept.append(enriched)
    return kept, removed


def load_manual_additions(record_root: Path, additions_path: Path) -> list[dict[str, Any]]:
    if not additions_path.exists():
        return []

    manifest = load_json(record_root / "manifest.json")
    additions = load_json(additions_path)
    deck_by_source = {deck["source_path"]: deck for deck in manifest["decks"]}
    deck_by_filename = {deck["filename"]: deck for deck in manifest["decks"]}

    added: list[dict[str, Any]] = []
    for index, addition in enumerate(additions, start=1):
        deck = deck_by_source.get(addition.get("source_path", "")) or deck_by_filename.get(
            addition.get("filename", "")
        )
        if not deck:
            raise ValueError(f"Could not find source deck for addition {addition}")
        slide_number = int(addition["slide_number"])
        deck_payload = load_json(record_root / deck["slides_json"])
        slide = next((item for item in deck_payload["slides"] if int(item["slide_number"]) == slide_number), None)
        if not slide:
            raise ValueError(f"Could not find slide {slide_number} in {deck['filename']}")
        if not slide.get("image_path"):
            raise ValueError(f"Slide {slide_number} in {deck['filename']} has no rendered image")

        added.append(
            {
                "review_id": addition.get("id") or f"ADD{index:03d}",
                "slide_number": slide_number,
                "score": addition.get("score", 0),
                "title": addition.get("title") or slide.get("title"),
                "hidden": bool(slide.get("hidden", False)),
                "pdf_page_number": slide.get("pdf_page_number"),
                "matches": addition.get("matches", []),
                "image_path": slide["image_path"],
                "word_count": slide.get("word_count", 0),
                "content_hash": slide.get("content_hash"),
                "deck_slug": deck["deck_slug"],
                "filename": deck["filename"],
                "source_path": deck["source_path"],
                "review_group": "manual_addition",
                "feedback_disposition": "manual_addition",
                "feedback_move_target": addition.get("suggested_register_section", ""),
                "feedback_note": addition.get("why_it_matters", ""),
                "addition_source": str(additions_path.resolve()),
            }
        )
    return added


def merge_kept_and_additions(kept: list[dict[str, Any]], additions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(kept)
    existing_images = {item["image_path"] for item in merged}
    for addition in additions:
        if addition["image_path"] in existing_images:
            continue
        existing_images.add(addition["image_path"])
        merged.append(addition)
    return merged


def render_contact_sheet(
    record_root: Path,
    output_path: Path,
    selected: list[dict[str, Any]],
    title: str,
    columns: int = 4,
    thumb_width: int = 380,
    label_height: int = 104,
    gutter: int = 28,
    margin: int = 36,
) -> None:
    font = ImageFont.load_default()
    thumb_height = round(thumb_width * 9 / 16)
    cell_width = thumb_width + gutter
    cell_height = thumb_height + label_height + gutter
    rows = max(1, (len(selected) + columns - 1) // columns)
    width = margin * 2 + columns * cell_width - gutter
    header_height = 72
    height = margin * 2 + header_height + rows * cell_height - gutter

    sheet = Image.new("RGB", (width, height), "#f7f7f4")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, margin), title, fill="#222222", font=font)
    draw.text(
        (margin, margin + 24),
        f"Generated {datetime.now(timezone.utc).isoformat()} | {len(selected)} kept visual artifacts",
        fill="#555555",
        font=font,
    )

    for index, item in enumerate(selected):
        row = index // columns
        column = index % columns
        x = margin + column * cell_width
        y = margin + header_height + row * cell_height
        image_path = record_root / item["image_path"]

        with Image.open(image_path) as image:
            image.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            background = Image.new("RGB", (thumb_width, thumb_height), "#ffffff")
            paste_x = (thumb_width - image.width) // 2
            paste_y = (thumb_height - image.height) // 2
            background.paste(image.convert("RGB"), (paste_x, paste_y))
            sheet.paste(background, (x, y))

        draw.rectangle((x, y, x + thumb_width, y + thumb_height), outline="#d0d0cc")
        label_top = y + thumb_height + 8
        lines = [
            f"{item['review_id']} | score {item.get('score')} | slide {item.get('slide_number')}",
            truncate(item.get("filename"), 56),
            truncate(item.get("title"), 62),
        ]
        for offset, line in enumerate(lines):
            draw.text((x, label_top + offset * 16), line, fill="#222222", font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def write_gallery(record_root: Path, output_dir: Path, kept: list[dict[str, Any]], removed: list[dict[str, Any]]) -> None:
    gallery_path = output_dir / "index.html"

    def card(item: dict[str, Any]) -> str:
        image_src = html.escape(relative_from_html(record_root / item["image_path"], gallery_path))
        title = html.escape(truncate(item.get("title"), 120))
        filename = html.escape(item.get("filename", ""))
        return f"""
        <article class="card">
          <a href="{image_src}"><img src="{image_src}" alt="{title}"></a>
          <div class="meta">
            <strong>{html.escape(item["review_id"])}</strong>
            <h3>{title}</h3>
            <p>{filename} | slide {item.get("slide_number")} | score {item.get("score")}</p>
          </div>
        </article>
        """

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS Curated Key Visuals</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #f7f7f4; color: #202428; }}
    header {{ padding: 24px 30px; background: #fff; border-bottom: 1px solid #d8d8d2; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    p {{ margin: 6px 0; font-size: 13px; line-height: 1.4; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; padding: 24px 30px; }}
    .card {{ background: #fff; border: 1px solid #d8d8d2; border-radius: 6px; overflow: hidden; }}
    img {{ display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: contain; background: #eee; }}
    .meta {{ padding: 12px 14px; }}
    h3 {{ margin: 6px 0; font-size: 15px; line-height: 1.25; }}
  </style>
</head>
<body>
  <header>
    <h1>SAS Curated Key Visuals</h1>
    <p>Kept visual artifacts: {len(kept)}. Removed from curated visual record: {len(removed)}.</p>
    <p>Raw screenshots and source slide records remain intact in the full visual record.</p>
  </header>
  <main>
    {''.join(card(item) for item in kept)}
  </main>
</body>
</html>
"""
    gallery_path.write_text(html_text, encoding="utf-8")


def write_outputs(
    record_root: Path,
    output_dir: Path,
    kept: list[dict[str, Any]],
    removed: list[dict[str, Any]],
    additions: list[dict[str, Any]],
    feedback_path: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "feedback_path": str(feedback_path.resolve()),
        "policy": "Items marked remove are removed from the curated visual record only; raw source evidence remains intact.",
        "kept_count": len(kept),
        "removed_count": len(removed),
        "manual_addition_count": len(additions),
        "kept": kept,
        "removed": removed,
        "manual_additions": additions,
    }
    (output_dir / "curation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "kept_visuals.json").write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "removed_from_visual_record.json").write_text(
        json.dumps(removed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "manual_additions.json").write_text(
        json.dumps(additions, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    render_contact_sheet(record_root, output_dir / "curated_contact_sheet.png", kept, "SAS Curated Key Visuals")
    write_gallery(record_root, output_dir, kept, removed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply SAS key-visual feedback to the curated visual record.")
    parser.add_argument("--record-root", type=Path, default=DEFAULT_RECORD_ROOT)
    parser.add_argument("--review-items", type=Path, default=DEFAULT_REVIEW_ITEMS)
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--additions", type=Path, default=DEFAULT_ADDITIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    record_root = args.record_root.resolve()
    items = load_json(args.review_items.resolve())["items"]
    feedback = load_json(args.feedback.resolve())
    kept, removed = apply_feedback(items, feedback)
    additions = load_manual_additions(record_root, args.additions.resolve())
    kept = merge_kept_and_additions(kept, additions)
    write_outputs(record_root, args.output_dir.resolve(), kept, removed, additions, args.feedback)

    print(f"Kept visual artifacts: {len(kept)}")
    print(f"Removed from curated visual record: {len(removed)}")
    print(f"Manual additions: {len(additions)}")
    print(f"Curated gallery: {args.output_dir.resolve() / 'index.html'}")
    print(f"Curated contact sheet: {args.output_dir.resolve() / 'curated_contact_sheet.png'}")


if __name__ == "__main__":
    main()
