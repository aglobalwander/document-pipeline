#!/usr/bin/env python3
"""Build human-facing contact sheets from a PowerPoint visual record."""

from __future__ import annotations

import argparse
import html
import json
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


DEFAULT_RECORD_ROOT = Path("data/output/powerpoint_visual_record")
DEFAULT_OUTPUT_DIR = DEFAULT_RECORD_ROOT / "key_visuals"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def truncate(value: str | None, limit: int = 72) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def deck_order(manifest: dict[str, Any]) -> dict[str, int]:
    return {deck["deck_slug"]: index for index, deck in enumerate(manifest["decks"])}


def dedupe_candidates(candidates: list[dict[str, Any]], order_by_deck: dict[str, int]) -> list[dict[str, Any]]:
    visible = [
        candidate
        for candidate in candidates
        if candidate.get("image_path") and not candidate.get("hidden")
    ]
    visible.sort(
        key=lambda item: (
            -int(item.get("score", 0)),
            order_by_deck.get(item.get("deck_slug", ""), 9999),
            int(item.get("slide_number", 9999)),
        )
    )

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in visible:
        key = str(candidate.get("content_hash") or candidate.get("image_path"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)
    return selected


def select_ranked(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return candidates[:limit]


def select_by_deck(
    candidates: list[dict[str, Any]],
    order_by_deck: dict[str, int],
    max_per_deck: int,
) -> list[dict[str, Any]]:
    by_deck: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_deck.setdefault(candidate["deck_slug"], []).append(candidate)

    selected: list[dict[str, Any]] = []
    for deck_slug in sorted(by_deck, key=lambda slug: order_by_deck.get(slug, 9999)):
        deck_candidates = sorted(
            by_deck[deck_slug],
            key=lambda item: (-int(item.get("score", 0)), int(item.get("slide_number", 9999))),
        )
        selected.extend(deck_candidates[:max_per_deck])
    return selected


def relative_from_html(path: Path, html_path: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), html_path.parent.resolve())).as_posix()


def render_contact_sheet(
    record_root: Path,
    output_path: Path,
    selected: list[dict[str, Any]],
    title: str,
    columns: int = 4,
    thumb_width: int = 360,
    label_height: int = 118,
    gutter: int = 28,
    margin: int = 36,
) -> None:
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    thumb_height = round(thumb_width * 9 / 16)
    cell_width = thumb_width + gutter
    cell_height = thumb_height + label_height + gutter
    rows = max(1, (len(selected) + columns - 1) // columns)
    width = margin * 2 + columns * cell_width - gutter
    header_height = 72
    height = margin * 2 + header_height + rows * cell_height - gutter

    sheet = Image.new("RGB", (width, height), "#f7f7f4")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, margin), title, fill="#222222", font=title_font)
    draw.text(
        (margin, margin + 24),
        f"Generated {datetime.now(timezone.utc).isoformat()} | {len(selected)} visual artifacts",
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
            f"{index + 1}. score {item.get('score')} | slide {item.get('slide_number')}",
            truncate(item.get("filename"), 52),
            truncate(item.get("title"), 58),
        ]
        match_labels = ", ".join(match["label"] for match in item.get("matches", [])[:4])
        if match_labels:
            lines.append(truncate(match_labels, 58))
        for offset, line in enumerate(lines):
            draw.text((x, label_top + offset * 16), line, fill="#222222", font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def write_gallery(
    record_root: Path,
    output_dir: Path,
    ranked: list[dict[str, Any]],
    by_deck: list[dict[str, Any]],
) -> None:
    gallery_path = output_dir / "index.html"
    selected_manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_root": str(record_root.resolve()),
        "ranked_count": len(ranked),
        "by_deck_count": len(by_deck),
        "ranked": ranked,
        "by_deck": by_deck,
    }
    (output_dir / "selected_key_visuals.json").write_text(
        json.dumps(selected_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    def card(item: dict[str, Any], number: int) -> str:
        image_src = html.escape(relative_from_html(record_root / item["image_path"], gallery_path))
        deck = html.escape(str(item.get("filename", "")))
        title = html.escape(truncate(item.get("title"), 120))
        labels = ", ".join(match["label"] for match in item.get("matches", []))
        labels = html.escape(labels)
        source = html.escape(item["image_path"])
        return f"""
        <article class="card">
          <a href="{image_src}"><img src="{image_src}" alt="{title}"></a>
          <div class="meta">
            <div class="rank">#{number} | score {item.get("score")} | slide {item.get("slide_number")}</div>
            <h3>{title}</h3>
            <p>{deck}</p>
            <p class="labels">{labels}</p>
            <p class="source">{source}</p>
          </div>
        </article>
        """

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS PowerPoint Key Visual Record</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #1f2428;
      background: #f7f7f4;
    }}
    header {{
      padding: 28px 32px 20px;
      border-bottom: 1px solid #d8d8d2;
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 26px;
      line-height: 1.2;
    }}
    nav a {{
      color: #124c7c;
      margin-right: 18px;
      text-decoration: none;
      font-weight: 700;
    }}
    section {{
      padding: 28px 32px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 22px;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #d8d8d2;
      border-radius: 6px;
      overflow: hidden;
    }}
    .card img {{
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: contain;
      background: #eee;
    }}
    .meta {{
      padding: 12px 14px 14px;
    }}
    .rank, .labels, .source {{
      color: #596168;
      font-size: 12px;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 20px;
    }}
    h3 {{
      margin: 6px 0;
      font-size: 15px;
      line-height: 1.25;
    }}
    p {{
      margin: 6px 0;
      font-size: 13px;
      line-height: 1.35;
    }}
  </style>
</head>
<body>
  <header>
    <h1>SAS PowerPoint Key Visual Record</h1>
    <nav>
      <a href="contact_sheet_ranked.png">Ranked contact sheet</a>
      <a href="contact_sheet_by_deck.png">Deck-diverse contact sheet</a>
      <a href="selected_key_visuals.json">Selected JSON</a>
    </nav>
  </header>
  <section id="ranked">
    <h2>Highest-Signal Visual Artifacts</h2>
    <div class="grid">
      {''.join(card(item, number) for number, item in enumerate(ranked, start=1))}
    </div>
  </section>
  <section id="by-deck">
    <h2>Deck-Diverse Visual Artifacts</h2>
    <div class="grid">
      {''.join(card(item, number) for number, item in enumerate(by_deck, start=1))}
    </div>
  </section>
</body>
</html>
"""
    gallery_path.write_text(textwrap.dedent(html_text), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build key visual contact sheets from a PPTX visual record.")
    parser.add_argument("--record-root", type=Path, default=DEFAULT_RECORD_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ranked-limit", type=int, default=48)
    parser.add_argument("--max-per-deck", type=int, default=2)
    args = parser.parse_args()

    record_root = args.record_root.resolve()
    output_dir = args.output_dir.resolve()
    manifest = load_json(record_root / "manifest.json")
    candidates = load_json(record_root / "key_slide_candidates.json")
    order_by_deck = deck_order(manifest)
    deduped = dedupe_candidates(candidates, order_by_deck)

    ranked = select_ranked(deduped, args.ranked_limit)
    by_deck = select_by_deck(deduped, order_by_deck, args.max_per_deck)

    render_contact_sheet(
        record_root,
        output_dir / "contact_sheet_ranked.png",
        ranked,
        "SAS PowerPoint Visual Record: Highest-Signal Artifacts",
    )
    render_contact_sheet(
        record_root,
        output_dir / "contact_sheet_by_deck.png",
        by_deck,
        "SAS PowerPoint Visual Record: Deck-Diverse Artifacts",
    )
    write_gallery(record_root, output_dir, ranked, by_deck)

    print(f"Deduped visible candidates: {len(deduped)}")
    print(f"Ranked contact sheet: {output_dir / 'contact_sheet_ranked.png'}")
    print(f"Deck-diverse contact sheet: {output_dir / 'contact_sheet_by_deck.png'}")
    print(f"Gallery: {output_dir / 'index.html'}")


if __name__ == "__main__":
    main()
