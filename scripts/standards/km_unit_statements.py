#!/usr/bin/env python3
"""Extract the statements that print *under* an enumerated unit.

KM's ruling (b) on the P4 acceptance: for Dance, Music, Literature and Language and Literature the
enumerated unit **is** the key, so their statements are wanted under it — keyed
`(subject, unit_code, statement)` — using `comp-ca`, `AoE1-Q1`, `comp-explorectx` … Those guides print
named units and no statement codes, which is why they were refused at statement grain.

This walks each enumerated unit's printed span (from its heading to the next heading) and returns the
guide's own printed items:

  * an item starts at a bullet glyph, or at a line set off from the previous line by a vertical gap
    larger than the guide's own line pitch — the guides wrap a paragraph across several lines, so the
    paragraph, not the line, is the smallest honest statement;
  * the guides' furniture never becomes a statement: page numbers, running heads and the hour/level
    markers (`FURNITURE` in `km_p4_statements`);
  * a span whose records repeat their vertical position within a page is a **table**, not prose
    (Dance's assessment-criteria grids do this). Those items are emitted with `layout=table` so KM can
    rule on them instead of reading interleaved cells as statements.

Nothing is inferred: every statement is the guide's own text, with page, bbox and md_line.

Usage:
    poetry run python scripts/standards/km_unit_statements.py [--subject music] [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_p4_statements import FURNITURE, _text_of, is_large_heading, is_section_heading
from km_printed_units import size_of
from km_text_layer import OUT_ROOT

REQUEST = "p4_dp_statements"
PAGE_NUMBER = re.compile(r"^\d{1,3}$")
RUNNING_HEAD = re.compile(r"\bguide\b|\bFirst assessment \d{4}\b|^\d{4}$", re.I)
BULLET = re.compile(r"^[\u2022\u25aa\uf0b7\u25cf\u25cb\-–—]\s*$|^[\u2022\u25aa\uf0b7\u25cf\u25cb]\s+")
FIELDS = ["subject", "pdf_sha256", "unit_code", "unit_label", "item_index", "statement_text",
          "unit_layout", "page", "bbox", "md_line", "source_line"]
GUIDES = {"Dance": "Dance (2013).pdf", "Music": "Music (2022).pdf",
          "Literature": "Literature (2026).pdf",
          "Language and Literature": "Language and Literature (2026).pdf"}


def pitch(layer: list[dict]) -> float:
    """The guide's own line pitch: the median vertical step between consecutive lines."""
    steps = []
    for prev, rec in zip(layer, layer[1:]):
        if rec["page"] != prev["page"]:
            continue
        step = rec["bbox"][1] - prev["bbox"][1]
        if 0 < step < 40:
            steps.append(step)
    steps.sort()
    return steps[len(steps) // 2] if steps else 13.0


def is_furniture(rec: dict) -> bool:
    text = _text_of(rec)
    return (not text) or bool(PAGE_NUMBER.match(text)) or bool(RUNNING_HEAD.search(text)) \
        or bool(FURNITURE.match(text))


def is_table_span(records: list[dict]) -> bool:
    """A span is a table when its printed lines sit **side by side**, not when they wrap.

    Dance's assessment-criteria grids put two cells on one baseline, so pairs share a y and differ in
    x. A wrapped prose paragraph never does: consecutive lines differ by the guide's line pitch. The
    first version of this test compared raw ys, which the guides' page numbers satisfied against the
    body line they sit beside, and so flagged every span as a table.
    """
    body = [rec for rec in records if not is_furniture(rec)]
    side_by_side = 0
    for prev, rec in zip(body, body[1:]):
        if rec["page"] != prev["page"]:
            continue
        if abs(rec["bbox"][1] - prev["bbox"][1]) <= 2 and rec["bbox"][0] - prev["bbox"][0] >= 20:
            side_by_side += 1
    return side_by_side >= 5


def paragraphs(records: list[dict], line_pitch: float) -> list[dict]:
    """Group a span's records into printed items, marking the span's layout."""
    table = is_table_span(records)
    items, current, source = [], None, None
    for rec in records:
        if is_furniture(rec):
            continue
        text = _text_of(rec)
        if is_section_heading(rec) or is_large_heading(rec, 9.5):
            current = None
            continue
        starts = BULLET.match(text) is not None
        if current is None or starts or (
                current and rec["bbox"][1] - current["last_y"] > line_pitch * 1.6):
            if current:
                items.append(current)
            current = {"text": BULLET.sub("", text).strip(), "page": rec["page"],
                       "bbox": list(rec["bbox"]), "md_line": rec["md_line"],
                       "source_line": rec["text"], "last_y": rec["bbox"][1]}
        else:
            current["text"] = re.sub(r"\s+", " ", f"{current['text']} {text}").strip()
            current["bbox"] = [min(current["bbox"][0], rec["bbox"][0]),
                               min(current["bbox"][1], rec["bbox"][1]),
                               max(current["bbox"][2], rec["bbox"][2]),
                               max(current["bbox"][3], rec["bbox"][3])]
            current["last_y"] = rec["bbox"][1]
    if current:
        items.append(current)
    for item in items:
        item.pop("last_y", None)
        # `unit_layout` describes the **unit's body**, not the item: a unit whose pages carry a
        # criteria table is flagged whole, because the flag is a span-level fact and reading it as a
        # claim about one item would be wrong. Dance's units are such tables, and their cells are not
        # sentences — KM should rule on the grain there before anything is keyed.
        item["unit_layout"] = "table" if table else "prose"
        item["source_line"] = item["source_line"][:120]
    return items

def guide_layer(subject: str, base: Path) -> tuple[str | None, list[dict]]:
    """The stored guide and its text layer for one enumerated subject."""
    wanted = GUIDES[subject]
    for source_path in sorted(base.glob("*/source.json")):
        record = json.loads(source_path.read_text(encoding="utf-8"))
        if record.get("file") == wanted:
            layer = [json.loads(line) for line in
                     (source_path.parent / "text_layer.jsonl").open(encoding="utf-8")]
            return source_path.parent.name, layer
    return None, []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--subject", default=None)
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    units = list(csv.DictReader((base / "printed_units.csv").open(newline="", encoding="utf-8")))
    subjects = [args.subject] if args.subject else sorted(GUIDES)

    rows, per = [], collections.defaultdict(collections.Counter)
    for subject in subjects:
        sha, layer = guide_layer(subject, base)
        if not sha:
            per[subject]["no_guide"] = 1
            continue
        line_pitch = pitch(layer)
        mine = sorted((u for u in units if u["subject"] == subject and u["match"]),
                      key=lambda u: int(u["md_line"]))
        last_line = max(r["md_line"] for r in layer)
        for i, unit in enumerate(mine):
            start = int(unit["md_line"])
            next_unit = int(mine[i + 1]["md_line"]) if i + 1 < len(mine) else last_line
            # A unit's body ends where the next *section-shaped* heading begins (the strict rule, so a
            # sub-heading inside the unit does not cut it) or at the next unit, whichever comes first.
            boundary = next((r["md_line"] for r in layer
                             if r["md_line"] > start + 1 and is_section_heading(r)), None)
            end = min(next_unit, boundary) if boundary else next_unit
            # The span includes the unit's own printed line: for the question units (`AoE1-Q1`) that
            # line *is* the statement, and it is the guide's printed text for the unit either way. A
            # large-type unit heading is still dropped by the heading rule inside `paragraphs`.
            items = paragraphs([r for r in layer if start <= r["md_line"] < end], line_pitch)
            per[subject]["units"] += 1
            per[subject]["items"] += len(items)
            if any(item["unit_layout"] == "table" for item in items):
                per[subject]["table_units"] += 1
            for n, item in enumerate(items, start=1):
                rows.append({
                    "subject": subject, "pdf_sha256": sha, "unit_code": unit["code"],
                    "unit_label": unit["label"], "item_index": n,
                    "statement_text": item["text"], "unit_layout": item["unit_layout"],
                    "page": item["page"], "bbox": json.dumps(item["bbox"]),
                    "md_line": item["md_line"], "source_line": item["source_line"],
                })

    with (base / "statements_units.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "units_with_statements": sum(c["units"] for c in per.values()),
        "statements": len(rows),
        "by_layout": dict(collections.Counter(r["unit_layout"] for r in rows)),
        "units_whose_body_is_a_table": sum(c["table_units"] for c in per.values()),
        "by_subject": {k: dict(v) for k, v in sorted(per.items())},
        "key": "(subject, unit_code, statement), as KM ruled",
        "method": "printed items under each enumerated unit from the cached text layer; no OCR, no model",
    }
    (base / "statements_units_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                        encoding="utf-8")
    for subject, counts in sorted(per.items()):
        print(f"{subject:24} units {counts['units']:3} | items {counts['items']:5} | "
              f"table-shaped units {counts['table_units']:3}")
    print(f"\nstatements {len(rows)} | layouts {summary['by_layout']} -> {base}/statements_units.csv")


if __name__ == "__main__":
    main()
