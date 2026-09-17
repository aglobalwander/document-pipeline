#!/usr/bin/env python3
"""Write the PDF text layer for a KM request, reading the source by sha256 from the store.

KM names documents by sha256 (see docs/handoff/INCOMING.md, 2026-09-17). This script resolves
the sha through the store's MANIFEST.csv, verifies the bytes it reads, and writes under
``data/output/km_requests/<date>/<request>/<sha256>/``:

  guide.md          page-linearized markdown, pages joined by '---'. Reproduces the shape the
                    ib_guide_extract*.py grammars were written against: a line is wrapped in
                    '**' when any span on it is bold, '#'/'##' mark large type.
  text_layer.jsonl  one record per non-blank markdown line: md line number, page, bbox, the
                    line text as printed, and per-span font/size/bold.
  source.json       pdf_sha256, manifest file, page count, method, edition markers read from
                    the first pages.

No OCR, no model: method is the PDF's own text layer via PyMuPDF.

Usage:
    poetry run python scripts/standards/km_text_layer.py --request p1_ib_guides \
        --sha d1a7bcb5fc89cbb93ba4feb785832f6209fe3f3098d699b33c4eba99e66b9ee1
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import pymupdf

STORE = Path.home() / (
    "Library/CloudStorage/OneDrive-ShanghaiAmericanSchool/2_Models-Frameworks-Research/"
    "_Standards Frameworks/_curriculum_ontology_sources")
OUT_ROOT = Path("data/output/km_requests")
MARKER_RX = re.compile(r"[Ff]irst (?:assessments?|examinations?)\s+\d{4}")


def is_bold(span: dict) -> bool:
    font = span["font"].lower()
    return bool(span["flags"] & 16) or "bold" in font or "black" in font


def resolve(sha: str, store: Path) -> tuple[dict, bytes]:
    with open(store / "MANIFEST.csv", newline="", encoding="utf-8") as fh:
        row = next((r for r in csv.DictReader(fh) if r["sha256"] == sha), None)
    if row is None:
        raise SystemExit(f"sha256 {sha} is not in {store / 'MANIFEST.csv'}")
    data = (store / row["directory"] / row["file"]).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha:
        raise SystemExit(f"bytes of {row['file']} hash to {actual}, manifest says {sha}")
    return row, data


def text_layer(data: bytes) -> tuple[list[str], list[dict], int]:
    doc = pymupdf.open(stream=data, filetype="pdf")
    md: list[str] = []
    records: list[dict] = []
    for pno, page in enumerate(doc, start=1):
        if pno > 1:
            md += ["", "---", ""]
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in line["spans"]).strip()
                size = max(s["size"] for s in spans)
                if size >= 17:
                    rendered = "# " + text
                elif size >= 12.5:
                    rendered = "## " + text
                elif any(is_bold(s) for s in spans):
                    rendered = "**" + text + "**"
                else:
                    rendered = text
                md.append(rendered)
                records.append({
                    "md_line": len(md), "page": pno,
                    "bbox": [round(v, 1) for v in line["bbox"]], "text": text,
                    "spans": [{"text": s["text"], "font": s["font"], "size": round(s["size"], 1),
                               "bold": is_bold(s)} for s in spans],
                })
    return md, records, doc.page_count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True, help="request folder name, e.g. p1_ib_guides")
    ap.add_argument("--sha", required=True, action="append", help="repeatable")
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--store", type=Path, default=STORE)
    args = ap.parse_args()

    for sha in args.sha:
        row, data = resolve(sha, args.store)
        md, records, pages = text_layer(data)
        markers = []
        for rec in records:
            if rec["page"] > 3:
                break
            markers += [m for m in MARKER_RX.findall(rec["text"]) if m not in markers]
        out = OUT_ROOT / args.date / args.request / sha
        out.mkdir(parents=True, exist_ok=True)
        (out / "guide.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        with open(out / "text_layer.jsonl", "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        source = {
            "pdf_sha256": sha,
            "file": row["file"],
            "directory": row["directory"],
            "pdf_pages": pages,
            "method": f"pdf text layer (PyMuPDF {pymupdf.VersionBind}); no OCR, no model",
            "edition_marker": markers[0] if len(markers) == 1 else None,
            "detected_markers": markers,
            "marker_detection_source": "pdf_text_pages_1_through_3",
            "marker_resolution_state": {0: "unresolved", 1: "single_detected_marker"}.get(
                len(markers), "multiple_detected_markers_review_hold"),
            "guide_markdown_sha256": hashlib.sha256((out / "guide.md").read_bytes()).hexdigest(),
        }
        (out / "source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
        print(f"{row['file']}: {pages} pp, {len(records)} lines, markers {markers} -> {out}")


if __name__ == "__main__":
    main()
