#!/usr/bin/env python3
"""R2: the Dance assessment-criteria rows KM holds, read from the printed page.

KM's request (2026-09-18, R2) wants, per canon row, the **printed criterion text** with page and
bbox, the **lettered sub-item as printed**, and — where the guide prints an AO statement separately
from the criteria table — **both locations recorded** rather than one preferred.

KM's page numbers are canon page numbers: its `p.9` is this PDF's page 17 (the four AO statements)
and its `pp.10-11` are pages 18-19 (the section `Assessment objectives in practice`). The read
therefore locates by **text**, not by page index, and reports the page it actually found — which is
how the mapping is stated rather than assumed. The table's columns are level descriptors and are not
rows: one canon row is one criterion, so a match is one printed item however many lines it wraps to.

Usage:
    poetry run python scripts/standards/km_dance_criteria_read.py [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
ROWS = KM / "pipeline_requests_2026-09-18/r2_dance_assessment_criteria.csv"
GUIDE = "Dance (2013).pdf"
REQUEST = "p4_dp_statements"
SEARCH_PAGES = (16, 17, 18, 19, 20)
FIELDS = ["canon_code", "layer", "label_as_km_holds_it", "status", "location", "letter_printed",
          "printed_text", "page", "bbox", "md_lines"]


def squish(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def locate_spans(pool: list[dict], opening: str) -> list[tuple[str, int, list[dict]]]:
    """Every page where ``opening`` prints, with the records the match spans.

    A guide wraps a criterion across two or three lines, so the opening words rarely sit in one
    record. Each page's records are concatenated with their whitespace stripped and the opening is
    found in that string; the records covering the span are then recovered by walking the offsets.
    Matching this way is what finds the second location — the practice table repeats an item that also
    prints in the AO statements.
    """
    spans = []
    for page in sorted({rec["page"] for rec in pool}):
        on_page = [rec for rec in pool if rec["page"] == page]
        joined, offsets = "", []
        for rec in on_page:
            piece = squish(rec["text"])
            offsets.append((len(joined), len(joined) + len(piece), rec))
            joined += piece
        start = joined.find(opening)
        if start < 0:
            continue
        end = start + len(opening)
        covering = [rec for lo, hi, rec in offsets if hi > start and lo < end]
        if covering:
            spans.append((page, covering[0]["md_line"], covering))
    return spans


def item_at(match: dict, layer: list[dict]) -> dict:
    """The printed item a matched line belongs to: its wrapped continuation lines, joined."""
    page, y = match["page"], match["bbox"][1]
    same = [r for r in layer if r["page"] == page and r["md_line"] >= match["md_line"]]
    lines = [match]
    for rec in same[1:]:
        # A lettered sub-item starts a new criterion and must not be glued onto the previous one.
        # The letters print lowercase (`a.`…`e.`), so the stop rule has to accept both cases — the
        # first version matched only `[A-Z]\.` and silently merged `b.` into the row above.
        if rec["bbox"][1] - y > 16 or re.match(r"^[A-Za-z]\.\s|^\d+\.\s", rec["text"].strip()):
            break
        lines.append(rec)
        y = rec["bbox"][1]
    boxes = [r["bbox"] for r in lines]
    return {"text": " ".join(r["text"].strip() for r in lines),
            "page": page, "md_lines": json.dumps([r["md_line"] for r in lines]),
            "bbox": json.dumps([min(b[0] for b in boxes), min(b[1] for b in boxes),
                                max(b[2] for b in boxes), max(b[3] for b in boxes)])}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--rows", type=Path, default=ROWS)
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    guide = next(p.parent for p in base.glob("*/source.json")
                 if json.loads(p.read_text(encoding="utf-8")).get("file") == GUIDE)
    layer = [json.loads(line) for line in (guide / "text_layer.jsonl").open(encoding="utf-8")]
    pool = [r for r in layer if r["page"] in SEARCH_PAGES]

    rows = list(csv.DictReader(args.rows.open(newline="", encoding="utf-8")))
    out = []
    for row in rows:
        label = row["label_as_km_holds_it"].strip()
        # The canon label carries an `AO1.` prefix the guide prints on a different line, so it is
        # stripped before matching; the prefix is not part of the criterion's printed text.
        core = re.sub(r"^AO\d+\.\s*", "", label)
        opening = squish(" ".join(core.split()[:5]))
        letter = row["canon_code"].split("-")[-1] if row["layer"] == "assessment_objective_item" else ""
        spans = locate_spans(pool, opening)
        if not spans:
            out.append({"canon_code": row["canon_code"], "layer": row["layer"],
                        "label_as_km_holds_it": label, "status": "no_printed_text",
                        "location": "", "letter_printed": "", "printed_text": "", "page": "",
                        "bbox": "", "md_lines": ""})
            continue
        for page, first_line, covering in spans:
            item = item_at(covering[0], layer)
            # p17 prints the AO statements and their items (canon p.9); pp.18-19 print the practice
            # table (canon pp.10-11). Both are reported when both print, as the acceptance asks.
            location = "ao_statement" if page <= 17 else "criteria_table"
            printed_letter = ""
            if letter:
                printed_letter = ("yes" if re.search(rf"\b{letter}\.", item["text"])
                                  or re.match(rf"^{letter}\b", item["text"]) else "not_printed")
            out.append({"canon_code": row["canon_code"], "layer": row["layer"],
                        "label_as_km_holds_it": label, "status": "printed", "location": location,
                        "letter_printed": printed_letter, "printed_text": item["text"][:400],
                        "page": item["page"], "bbox": item["bbox"], "md_lines": item["md_lines"]})

    with (base / "r2_dance_criteria_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    located = {r["canon_code"] for r in out if r["status"] == "printed"}
    both = {r["canon_code"] for r in out if r["status"] == "printed" and r["location"] == "ao_statement"} & \
           {r["canon_code"] for r in out if r["status"] == "printed" and r["location"] == "criteria_table"}
    summary = {"canon_rows": len(rows), "located": len(located),
               "rows_returned": len(out),
               "with_both_locations": sorted(both),
               "by_location": {loc: sum(1 for r in out if r["location"] == loc)
                               for loc in sorted({r["location"] for r in out if r["location"]})},
               "letters_not_printed": sorted({r["canon_code"] for r in out if r["letter_printed"] == "not_printed"}),
               "method": "located by printed text, not page index; columns are level descriptors, not rows"}
    (base / "r2_dance_criteria_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"canon rows {len(rows)} | located {len(located)} | returned {len(out)}")
    print(f"by location {summary['by_location']} | both locations {summary['with_both_locations']}")
    print(f"letters not printed: {summary['letters_not_printed']}")
    for r in out[:6]:
        print(f"   {r['canon_code']:8} {r['location']:15} letter={r['letter_printed'] or '-':11} p{r['page']:>3} | {r['printed_text'][:60]!r}")
    print(f"-> {base}/r2_dance_criteria_read.csv")


if __name__ == "__main__":
    main()
