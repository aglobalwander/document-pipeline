#!/usr/bin/env python3
"""Build an HTML feedback board for curated PowerPoint key visuals."""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_KEY_VISUALS_DIR = Path("data/output/powerpoint_visual_record/key_visuals")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def truncate(value: str | None, limit: int = 100) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def relative_from_html(path: Path, html_path: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), html_path.parent.resolve())).as_posix()


def combined_review_items(selected: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    # Start with deck-diverse items because they show the trajectory better;
    # add high-ranked extras after that.
    for source_group in ["by_deck", "ranked"]:
        for item in selected[source_group]:
            key = str(item.get("content_hash") or item.get("image_path"))
            if key in seen:
                continue
            seen.add(key)
            review_item = dict(item)
            review_item["review_group"] = source_group
            review_item["review_id"] = f"KV{len(items) + 1:03d}"
            items.append(review_item)
    return items


def write_items_json(output_dir: Path, items: list[dict[str, Any]]) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "item_count": len(items),
        "instructions": "Use review_id for feedback. Suggested dispositions: keep, remove, move, unsure.",
        "items": items,
    }
    (output_dir / "review_items.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_feedback_template(output_dir: Path, items: list[dict[str, Any]]) -> None:
    lines = [
        "# SAS Key Visual Feedback",
        "",
        "Use this if you want to give feedback in text instead of the HTML board.",
        "",
        "Disposition options: `keep`, `remove`, `move`, `unsure`.",
        "Move target examples: `TTG/DTG story`, `macro blueprint`, `strategic priorities`, `WASC`, `glossary`, `visual drift archive`.",
        "",
        "| ID | Disposition | Move target | Note | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in items:
        source = f"{item['filename']} slide {item['slide_number']}"
        lines.append(f"| {item['review_id']} |  |  |  | {source} |")
    (output_dir / "feedback_template.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def labels_for(item: dict[str, Any]) -> str:
    return ", ".join(match["label"] for match in item.get("matches", [])[:5])


def write_review_board(key_visuals_dir: Path, output_dir: Path, items: list[dict[str, Any]]) -> None:
    html_path = output_dir / "review_board.html"
    record_root = key_visuals_dir.parent

    cards = []
    for item in items:
        image_src = html.escape(relative_from_html(record_root / item["image_path"], html_path))
        review_id = html.escape(item["review_id"])
        title = html.escape(truncate(item.get("title"), 140))
        filename = html.escape(item["filename"])
        labels = html.escape(labels_for(item))
        source = html.escape(f"{item['filename']} | slide {item['slide_number']} | score {item['score']}")
        cards.append(
            f"""
      <article class="card" data-id="{review_id}" data-title="{title}" data-source="{source}">
        <a href="{image_src}"><img src="{image_src}" alt="{title}"></a>
        <div class="body">
          <div class="idline"><strong>{review_id}</strong><span>{html.escape(item['review_group'])}</span></div>
          <h3>{title}</h3>
          <p>{filename} | slide {item['slide_number']} | score {item['score']}</p>
          <p class="labels">{labels}</p>
          <div class="controls" role="group" aria-label="Disposition for {review_id}">
            <button type="button" data-value="keep">Keep</button>
            <button type="button" data-value="remove">Remove</button>
            <button type="button" data-value="move">Move</button>
            <button type="button" data-value="unsure">Unsure</button>
          </div>
          <label>Move target
            <select>
              <option value=""></option>
              <option>TTG/DTG story</option>
              <option>Macro blueprint</option>
              <option>Strategic priorities</option>
              <option>WASC/accreditation</option>
              <option>Glossary/alphabet soup</option>
              <option>Visual drift archive</option>
              <option>Remove/noise</option>
            </select>
          </label>
          <label>Note
            <textarea rows="2" placeholder="What should happen to this visual?"></textarea>
          </label>
        </div>
      </article>
            """
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS Key Visual Review Board</title>
  <style>
    body {{
      margin: 0;
      background: #f5f5f1;
      color: #202428;
      font-family: Arial, Helvetica, sans-serif;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 3;
      background: #fff;
      border-bottom: 1px solid #d8d8d2;
      padding: 18px 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    .toolbar button, .toolbar select {{
      border: 1px solid #bfc4c8;
      background: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 13px;
    }}
    main {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 18px;
      padding: 22px;
    }}
    .card {{
      background: #fff;
      border: 2px solid #d8d8d2;
      border-radius: 8px;
      overflow: hidden;
    }}
    .card[data-status="keep"] {{ border-color: #217a3b; }}
    .card[data-status="remove"] {{ border-color: #a83232; opacity: .62; }}
    .card[data-status="move"] {{ border-color: #b46a00; }}
    .card[data-status="unsure"] {{ border-color: #5c6370; }}
    img {{
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: contain;
      background: #eee;
    }}
    .body {{
      padding: 12px;
    }}
    .idline {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #4d555c;
      font-size: 12px;
      margin-bottom: 6px;
    }}
    h3 {{
      margin: 0 0 6px;
      font-size: 15px;
      line-height: 1.25;
    }}
    p {{
      margin: 5px 0;
      font-size: 12px;
      line-height: 1.35;
    }}
    .labels {{
      color: #606970;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      margin: 10px 0;
    }}
    .controls button {{
      border: 1px solid #bfc4c8;
      background: #f7f7f4;
      border-radius: 6px;
      padding: 7px 6px;
      font-size: 12px;
      cursor: pointer;
    }}
    .controls button.active {{
      background: #202428;
      color: #fff;
      border-color: #202428;
    }}
    label {{
      display: block;
      margin-top: 8px;
      font-size: 12px;
      color: #4d555c;
    }}
    textarea, select {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #c7cbd0;
      border-radius: 6px;
      padding: 7px;
      margin-top: 4px;
      font: inherit;
      background: #fff;
    }}
    #summary {{
      margin-left: auto;
      color: #4d555c;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>SAS Key Visual Review Board</h1>
    <div class="toolbar">
      <button type="button" id="copy">Copy Feedback</button>
      <button type="button" id="download">Download JSON</button>
      <button type="button" id="clear">Clear Marks</button>
      <select id="filter">
        <option value="">Show all</option>
        <option value="keep">Keep</option>
        <option value="remove">Remove</option>
        <option value="move">Move</option>
        <option value="unsure">Unsure</option>
        <option value="unmarked">Unmarked</option>
      </select>
      <span id="summary"></span>
    </div>
  </header>
  <main>
    {''.join(cards)}
  </main>
  <script>
    const storageKey = 'sas-key-visual-review-v1';
    const cards = [...document.querySelectorAll('.card')];
    const state = JSON.parse(localStorage.getItem(storageKey) || '{{}}');

    function cardState(card) {{
      const id = card.dataset.id;
      if (!state[id]) state[id] = {{ disposition: '', target: '', note: '' }};
      return state[id];
    }}

    function save() {{
      localStorage.setItem(storageKey, JSON.stringify(state));
      updateSummary();
    }}

    function applyState() {{
      cards.forEach(card => {{
        const item = cardState(card);
        card.dataset.status = item.disposition || '';
        card.querySelectorAll('.controls button').forEach(button => {{
          button.classList.toggle('active', button.dataset.value === item.disposition);
        }});
        card.querySelector('select').value = item.target || '';
        card.querySelector('textarea').value = item.note || '';
      }});
      applyFilter();
      updateSummary();
    }}

    function feedbackPayload() {{
      return cards.map(card => {{
        const item = cardState(card);
        return {{
          id: card.dataset.id,
          disposition: item.disposition || '',
          move_target: item.target || '',
          note: item.note || '',
          title: card.dataset.title,
          source: card.dataset.source
        }};
      }}).filter(item => item.disposition || item.move_target || item.note);
    }}

    function feedbackText() {{
      const rows = feedbackPayload();
      if (!rows.length) return 'No visual feedback marked yet.';
      return rows.map(item => {{
        const parts = [item.id, item.disposition || 'unmarked'];
        if (item.move_target) parts.push('-> ' + item.move_target);
        if (item.note) parts.push('- ' + item.note);
        parts.push('[' + item.source + ']');
        return parts.join(' ');
      }}).join('\\n');
    }}

    function updateSummary() {{
      const counts = {{ keep: 0, remove: 0, move: 0, unsure: 0, unmarked: 0 }};
      cards.forEach(card => {{
        const disposition = cardState(card).disposition || 'unmarked';
        counts[disposition] += 1;
      }});
      document.querySelector('#summary').textContent =
        `Keep ${{counts.keep}} | Remove ${{counts.remove}} | Move ${{counts.move}} | Unsure ${{counts.unsure}} | Unmarked ${{counts.unmarked}}`;
    }}

    function applyFilter() {{
      const filter = document.querySelector('#filter').value;
      cards.forEach(card => {{
        const disposition = cardState(card).disposition || 'unmarked';
        card.style.display = !filter || filter === disposition ? '' : 'none';
      }});
    }}

    cards.forEach(card => {{
      card.querySelectorAll('.controls button').forEach(button => {{
        button.addEventListener('click', () => {{
          const item = cardState(card);
          item.disposition = item.disposition === button.dataset.value ? '' : button.dataset.value;
          save();
          applyState();
        }});
      }});
      card.querySelector('select').addEventListener('change', event => {{
        cardState(card).target = event.target.value;
        save();
      }});
      card.querySelector('textarea').addEventListener('input', event => {{
        cardState(card).note = event.target.value;
        save();
      }});
    }});

    document.querySelector('#filter').addEventListener('change', applyFilter);
    document.querySelector('#copy').addEventListener('click', async () => {{
      await navigator.clipboard.writeText(feedbackText());
      document.querySelector('#copy').textContent = 'Copied';
      setTimeout(() => document.querySelector('#copy').textContent = 'Copy Feedback', 1200);
    }});
    document.querySelector('#download').addEventListener('click', () => {{
      const blob = new Blob([JSON.stringify(feedbackPayload(), null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'sas-key-visual-feedback.json';
      a.click();
      URL.revokeObjectURL(url);
    }});
    document.querySelector('#clear').addEventListener('click', () => {{
      if (!confirm('Clear all feedback marks on this board?')) return;
      localStorage.removeItem(storageKey);
      Object.keys(state).forEach(key => delete state[key]);
      applyState();
    }});

    applyState();
  </script>
</body>
</html>
"""
    html_path.write_text(html_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a feedback board for SAS key visual artifacts.")
    parser.add_argument("--key-visuals-dir", type=Path, default=DEFAULT_KEY_VISUALS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_KEY_VISUALS_DIR / "review")
    args = parser.parse_args()

    key_visuals_dir = args.key_visuals_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = load_json(key_visuals_dir / "selected_key_visuals.json")
    items = combined_review_items(selected)
    write_items_json(output_dir, items)
    write_feedback_template(output_dir, items)
    write_review_board(key_visuals_dir, output_dir, items)

    print(f"Review items: {len(items)}")
    print(f"Review board: {output_dir / 'review_board.html'}")
    print(f"Feedback template: {output_dir / 'feedback_template.md'}")
    print(f"Review items JSON: {output_dir / 'review_items.json'}")


if __name__ == "__main__":
    main()
