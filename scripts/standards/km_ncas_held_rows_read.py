#!/usr/bin/env python3
"""R1: locate KM's 205 NCAS held rows in the At-a-Glance pages already returned.

KM's request (2026-09-18, R1) wants, for each row, the code **as printed** with page and bbox, or an
explicit **no_printed_code** with the region read. Neither outcome is a defect; an unread row is.

The search covers the twelve documents P2 already read, by sha256: their text layers (the printed
line, verbatim) and their cells (the printed column code and the documented inline form). A row's
code is matched whitespace- and case-insensitively; where it has no code, its printed form (an anchor
title such as `Anchor Standard 1`) and then its statement text are tried, because a row that is not
printed is a result and must be reported as one rather than left blank.

Usage:
    poetry run python scripts/standards/km_ncas_held_rows_read.py [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
ROWS = KM / "pipeline_requests_2026-09-18/r1_ncas_205_held_rows.csv"
P2_REQUEST = "p2_ncas_at_a_glance"
FIELDS = ["code", "code_as_printed", "discipline", "status", "match_kind", "matched_as_printed",
          "matched_text", "document", "pdf_sha256", "page", "bbox", "md_line", "region_read"]


def squish(value) -> str:
    """Comparable form: case, whitespace and punctuation removed (codes print with both)."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def load_documents(base: Path) -> list[dict]:
    documents = []
    for src in sorted(base.glob("*/source.json")):
        record = json.loads(src.read_text(encoding="utf-8"))
        layer = [json.loads(line) for line in (src.parent / "text_layer.jsonl").open(encoding="utf-8")]
        cells_path = src.parent / "cells.jsonl"
        cells = [json.loads(line) for line in cells_path.open(encoding="utf-8")] if cells_path.exists() else []
        documents.append({"file": record["file"], "sha": src.parent.name,
                          "layer": layer, "cells": cells})
    return documents


def locate(row: dict, documents: list[dict]) -> dict:
    code = (row.get("code") or "").strip()
    as_printed = (row.get("code_as_printed") or "").strip()
    statement = (row.get("statement_as_km_holds_it") or "").strip()
    wanted = [t for t in (code, as_printed) if t]
    for doc in documents:
        if code:
            for cell in doc["cells"]:
                for field in ("column_code_printed", "inline_code"):
                    if squish(cell.get(field)) and squish(cell.get(field)) == squish(code):
                        return {"status": "printed", "match_kind": "exact",
                                "matched_as_printed": cell.get(field),
                                "matched_text": (cell.get("printed") or "")[:160],
                                "document": doc["file"], "pdf_sha256": doc["sha"],
                                "page": cell.get("page"), "bbox": json.dumps(cell.get("bbox")),
                                "md_line": None, "region_read": ""}
        for target in wanted:
            for rec in doc["layer"]:
                if squish(target) and squish(target) in squish(rec["text"]):
                    return {"status": "printed", "match_kind": "exact",
                            "matched_as_printed": target,
                            "matched_text": rec["text"][:160], "document": doc["file"],
                            "pdf_sha256": doc["sha"], "page": rec["page"],
                            "bbox": json.dumps(rec["bbox"]), "md_line": rec["md_line"],
                            "region_read": ""}
    # A code with a corrupt prefix still prints its tail: KM's `MU-T:CN11.0.T.IIa` prints as
    # `CN11.0.T.IIa` in the Music Tech strand. Tried last, reported as a tail match so the canon
    # defect is visible rather than hidden behind a success.
    if code and (":" in code or "-" in code):
        tail = code.split(":")[-1].split("-")[-1]
        if tail and tail != code:
            for doc in documents:
                for rec in doc["layer"]:
                    if squish(tail) in squish(rec["text"]):
                        return {"status": "printed", "match_kind": "tail",
                                "matched_as_printed": tail, "matched_text": rec["text"][:160],
                                "document": doc["file"], "pdf_sha256": doc["sha"],
                                "page": rec["page"], "bbox": json.dumps(rec["bbox"]),
                                "md_line": rec["md_line"], "region_read": ""}
    # Not printed: name the region read, so the row is a result rather than a blank.
    head = " ".join(statement.split()[:6])
    where = "; ".join(d["file"] for d in documents)
    near = None
    for doc in documents:
        for rec in doc["layer"]:
            if head and squish(head) in squish(rec["text"]):
                near = (doc["file"], doc["sha"], rec["page"], rec["bbox"], rec["text"][:120])
                break
        if near:
            break
    region = f"searched {len(documents)} documents ({where}); "
    region += (f"the statement's opening appears at {near[0]} p{near[2]} but no printed code or "
               f"anchor title for this row was found there" if near else
               "neither the code, the anchor title, nor the statement's opening was found")
    return {"status": "no_printed_code", "match_kind": "", "matched_as_printed": "", "matched_text": "",
            "document": near[0] if near else "", "pdf_sha256": near[1] if near else "",
            "page": near[2] if near else "", "bbox": json.dumps(near[3]) if near else "",
            "md_line": None, "region_read": region}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--rows", type=Path, default=ROWS)
    args = ap.parse_args()

    base = OUT_ROOT / args.date / P2_REQUEST
    documents = load_documents(base)
    rows = list(csv.DictReader(args.rows.open(newline="", encoding="utf-8")))
    out = []
    for row in rows:
        out.append({"code": row.get("code", ""), "code_as_printed": row.get("code_as_printed", ""),
                    "discipline": row.get("discipline", ""), **locate(row, documents)})

    with (base / "r1_held_rows_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    printed = [r for r in out if r["status"] == "printed"]
    summary = {"rows": len(out), "printed": len(printed),
               "no_printed_code": len(out) - len(printed),
               "documents_searched": [d["file"] for d in documents],
               "by_discipline": {d: sum(1 for r in out if r["discipline"] == d) for d in
                                 sorted({r["discipline"] for r in out})},
               "method": "exact code match in cells, then code/anchor-title/statement in the text layer"}
    (base / "r1_held_rows_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"rows {len(out)} | printed {len(printed)} | no_printed_code {len(out) - len(printed)}")
    for r in printed[:5]:
        print(f"   {r['code'] or r['code_as_printed']:22} -> {r['matched_as_printed'][:20]!r:22} p{r['page']:>3} {r['document'][:28]}")
    for r in [x for x in out if x["status"] != "printed"][:3]:
        print(f"   NO PRINT: {(r['code'] or r['code_as_printed'])[:22]:22} | {r['region_read'][:90]}")
    print(f"-> {base}/r1_held_rows_read.csv")


if __name__ == "__main__":
    main()
