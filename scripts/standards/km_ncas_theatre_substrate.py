#!/usr/bin/env python3
"""Substrate for the two reads KM has not requested yet: NCAS source identity, and Theatre's bands.

KM named the milestone's **315 NCAS residuals** and **137 Theatre derived scales** but pinned neither
to a list, and chose to ask rather than invent one. Both need the same thing from this side — the
printed code on the page with its source identity — so this builds that substrate now, and the reads
become joins once the definitions exist rather than new extraction.

This is raw evidence, not an artifact claiming an acceptance check. It is deliberately unopinionated
about what qualifies: it reports what the twelve returned documents print.

  ncas_code_source_index.csv   every distinct printed code -> the document(s) printing it, with a
                               representative page and bbox (the 315's source identity)
  theatre_printed_codes.csv    every Theatre cell -> its printed code, its band as printed, page, bbox
                               (the 137's candidate population)

Usage:
    poetry run python scripts/standards/km_ncas_theatre_substrate.py [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

from km_text_layer import OUT_ROOT

REQUEST = "p2_ncas_at_a_glance"
FIELDS_INDEX = ["printed_code", "documents", "occurrences", "first_page", "first_bbox"]
FIELDS_THEATRE = ["printed_code", "inline_code", "band_as_printed", "page", "bbox", "file"]


def build_substrate(documents: list[dict]) -> tuple[dict, list[dict]]:
    """(printed code -> documents printing it, every Theatre cell with its printed band).

    Pure over the document records, so the aggregation is testable without the pages.
    """
    index: dict[str, dict] = {}
    theatre: list[dict] = []
    for doc in documents:
        for cell in doc["cells"]:
            for field in ("column_code_printed", "inline_code"):
                code = str(cell.get(field) or "").strip()
                if not code:
                    continue
                entry = index.setdefault(code, {"documents": collections.Counter(), "first_page": "",
                                                "first_bbox": ""})
                entry["documents"][doc["file"]] += 1
                if not entry["first_page"]:
                    entry["first_page"] = cell.get("page", "")
                    entry["first_bbox"] = json.dumps(cell.get("bbox"))
            if doc["file"].startswith("Theatre"):
                theatre.append({"printed_code": cell.get("column_code_printed") or "",
                                "inline_code": cell.get("inline_code") or "",
                                "band_as_printed": cell.get("column_header") or "",
                                "page": cell.get("page", ""), "bbox": json.dumps(cell.get("bbox")),
                                "file": doc["file"]})
    return index, theatre


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    documents = []
    for src in sorted(base.glob("*/source.json")):
        record = json.loads(src.read_text(encoding="utf-8"))
        cells_path = src.parent / "cells.jsonl"
        cells = [json.loads(line) for line in cells_path.open(encoding="utf-8")] if cells_path.exists() else []
        documents.append({"file": record["file"], "sha": src.parent.name, "cells": cells})

    index, theatre = build_substrate(documents)

    with (base / "ncas_code_source_index.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS_INDEX)
        writer.writeheader()
        for code in sorted(index):
            entry = index[code]
            writer.writerow({"printed_code": code,
                             "documents": "; ".join(sorted(entry["documents"])),
                             "occurrences": sum(entry["documents"].values()),
                             "first_page": entry["first_page"], "first_bbox": entry["first_bbox"]})
    with (base / "theatre_printed_codes.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS_THEATRE)
        writer.writeheader()
        writer.writerows(theatre)

    shared = sum(1 for e in index.values() if len(e["documents"]) > 1)
    bands = collections.Counter(t["band_as_printed"] for t in theatre)
    summary = {
        "documents": [d["file"] for d in documents],
        "distinct_printed_codes": len(index),
        "codes_printed_in_more_than_one_document": shared,
        "theatre_cells": len(theatre),
        "theatre_bands": dict(bands),
        "theatre_bands_that_are_scales_not_grades": sorted(
            b for b in bands if not b.isdigit() and b not in ("PreK", "K", "HS I", "HS II", "HS III", "HS IV")),
        "method": "printed codes and bands from the cached cells; no OCR, no model",
        "status": "substrate for reads KM has not requested; not an acceptance artifact",
    }
    (base / "substrate_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"documents {len(documents)} | distinct printed codes {len(index)} | "
          f"in more than one document {shared}")
    print(f"theatre cells {len(theatre)} | bands printed: {sorted(bands)[:12]}")
    print(f"-> {base}/ncas_code_source_index.csv, theatre_printed_codes.csv")


if __name__ == "__main__":
    main()
