#!/usr/bin/env python3
"""Read the Dance guide's assessment-criteria tables — the pages KM has not requested.

KM named this as the one part of Dance's guide still unread: twenty criteria rows whose text
prints in a two-column table (the component and marker in the left column, the criterion's
descriptor in the right). The unit-statements pass deliberately stops at the next heading, so
these tables fall outside a unit extent and were never captured.

The read is mechanical: on each page that prints an assessment-criteria marker, records are
grouped by their baseline (within 3pt), each row is split at the column boundary into its left and
right cells, and both cells are returned verbatim with page, bbox and md_line. Nothing is inferred
and no cell is joined across a row boundary.

Usage:
    poetry run python scripts/standards/km_dance_criteria.py [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_text_layer import OUT_ROOT

REQUEST = "p4_dp_statements"
GUIDE = "Dance (2013).pdf"
MARKER = re.compile(r"(external|internal) assessment criteria", re.I)
COLUMN_SPLIT_X = 300.0
ROW_TOLERANCE = 3.0
FIELDS = ["page", "row", "left_cell", "right_cell", "is_marker_row", "bbox", "md_lines", "y"]


def guide_dir(base: Path) -> Path:
    for source_path in sorted(base.glob("*/source.json")):
        if json.loads(source_path.read_text(encoding="utf-8")).get("file") == GUIDE:
            return source_path.parent
    raise SystemExit(f"no stored copy of {GUIDE}")


def rows_of(records: list[dict]) -> list[list[dict]]:
    """Group records sharing a baseline into table rows (page-scoped, 3pt tolerance)."""
    rows: list[list[dict]] = []
    for rec in sorted(records, key=lambda r: (r["page"], r["bbox"][1], r["bbox"][0])):
        for row in rows:
            if row[0]["page"] == rec["page"] and abs(row[0]["bbox"][1] - rec["bbox"][1]) <= ROW_TOLERANCE:
                row.append(rec)
                break
        else:
            rows.append([rec])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    guide = guide_dir(base)
    records = [json.loads(line) for line in
               (guide / "text_layer.jsonl").open(encoding="utf-8")]
    pages = sorted({rec["page"] for rec in records if MARKER.search(rec["text"])})

    out: list[dict] = []
    for page in pages:
        on_page = [rec for rec in records if rec["page"] == page]
        for n, row in enumerate(rows_of(on_page), start=1):
            left = [r for r in row if r["bbox"][0] < COLUMN_SPLIT_X]
            right = [r for r in row if r["bbox"][0] >= COLUMN_SPLIT_X]
            if not left and not right:
                continue
            boxes = [r["bbox"] for r in row]
            out.append({
                "page": page, "row": n,
                "left_cell": " ".join(r["text"].strip() for r in sorted(left, key=lambda r: r["bbox"][0])).strip(),
                "right_cell": " ".join(r["text"].strip() for r in sorted(right, key=lambda r: r["bbox"][0])).strip(),
                "is_marker_row": bool(any(MARKER.search(r["text"]) for r in row)),
                "bbox": json.dumps([min(b[0] for b in boxes), min(b[1] for b in boxes),
                                    max(b[2] for b in boxes), max(b[3] for b in boxes)]),
                "md_lines": json.dumps(sorted(r["md_line"] for r in row)),
                "y": round(row[0]["bbox"][1], 1),
            })

    with (base / "dance_criteria.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    marker_rows = sum(1 for r in out if r["is_marker_row"])
    summary = {
        "guide": GUIDE, "pdf_sha256": guide.name, "pages": pages,
        "rows": len(out), "rows_carrying_a_criteria_marker": marker_rows,
        "criterion_rows_with_a_right_cell": sum(1 for r in out if r["right_cell"] and not r["is_marker_row"]),
        "by_page": dict(collections.Counter(r["page"] for r in out)),
        "method": "rows grouped by baseline, cells split at x=300; verbatim, from the cached text layer",
    }
    (base / "dance_criteria_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                      encoding="utf-8")
    print(f"pages with criteria tables: {pages}")
    print(f"rows {len(out)} | marker rows {marker_rows} | criterion rows with a descriptor "
          f"{summary['criterion_rows_with_a_right_cell']}")
    for r in [x for x in out if x["right_cell"] and not x["is_marker_row"]][:5]:
        print(f"   p{r['page']:>3} r{r['row']:>2} | {r['left_cell'][:26]!r:28} | {r['right_cell'][:54]!r}")
    print(f"-> {base}/dance_criteria.csv")


if __name__ == "__main__":
    main()
