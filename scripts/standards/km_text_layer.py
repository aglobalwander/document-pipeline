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
# The marker prints on the title/imprint pages, but not always in the first three: SEHS prints
# `First assessment 2026` on page 7, which is why it read as unresolved. Eight pages covers every
# guide in the store without reaching the syllabus body.
MARKER_PAGES = 8


def read_markers(records: list[dict], max_page: int = MARKER_PAGES) -> list[dict]:
    """First-assessment markers with the page each prints on, in page order.

    Compared case-insensitively: `first assessment 2023` and `First assessment 2023` are the same
    marker, and treating them as two is what put Film in a review hold for one document.
    """
    found: list[dict] = []
    seen: set[str] = set()
    for rec in records:
        if rec["page"] > max_page:
            break
        for match in MARKER_RX.finditer(rec["text"]):
            key = match.group(0).lower()
            if key not in seen:
                seen.add(key)
                found.append({"marker": match.group(0), "page": rec["page"]})
    return found


def marker_resolution(found: list[dict]) -> tuple[str | None, str]:
    """(edition_marker, marker_resolution_state).

    The **earliest page carrying a marker governs**: a guide's own edition statement prints on its
    title/imprint pages, while a later page that names another year is referring to the superseded
    edition. Biology (2028) prints `First assessment 2028` on pages 1-2 and `First assessment 2025`
    on page 7 — the 2028 edition is the guide, the 2025 mention is the previous one. A hold is
    recorded only when the markers on that earliest page name different years, which is genuine
    ambiguity; when no marker prints in the window the state is `unresolved`.
    """
    if not found:
        return None, "unresolved"
    first_page = min(f["page"] for f in found)
    on_page = [f["marker"] for f in found if f["page"] == first_page]
    years = {match.group(0)[-4:] for match in (MARKER_RX.search(m) for m in on_page) if match}
    if len(years) != 1:
        return None, "multiple_detected_markers_review_hold"
    if len(on_page) == 1:
        return on_page[0], "single_detected_marker"
    return on_page[0], "single_year_multiple_markers"


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


def refresh_markers(root: Path, request: str, date: str) -> None:
    """Re-read each stored guide's marker from its text layer and update `source.json`.

    Store-free: the text layer is already on disk, so a marker-rule change does not mean re-hashing
    every PDF. Only the marker fields are rewritten; the bytes and the markdown hash are untouched.
    """
    changed = 0
    for layer in sorted((root / date / request).glob("*/text_layer.jsonl")):
        source_path = layer.parent / "source.json"
        if not source_path.exists():
            continue
        records = [json.loads(line) for line in layer.open(encoding="utf-8")]
        found = read_markers(records)
        marker, state = marker_resolution(found)
        source = json.loads(source_path.read_text(encoding="utf-8"))
        before = (source.get("edition_marker"), source.get("marker_resolution_state"))
        source["edition_marker"] = marker
        source["detected_markers"] = [f["marker"] for f in found]
        source["detected_marker_pages"] = found
        source["marker_detection_source"] = f"pdf_text_pages_1_through_{MARKER_PAGES}"
        source["marker_resolution_state"] = state
        source["marker_rule"] = ("the earliest page carrying a marker governs; a hold is recorded "
                                 "only when that page names more than one year")
        source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
        flag = ""
        if (marker, state) != before:
            changed += 1
            flag = f"   <== was {before[0]!r} ({before[1]})"
        print(f"{source.get('file'):46} {str(marker):30} {state}{flag}")
    print(f"\n{changed} of the files in {date}/{request} changed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True, help="request folder name, e.g. p1_ib_guides")
    ap.add_argument("--sha", action="append", default=[], help="repeatable")
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--store", type=Path, default=STORE)
    ap.add_argument("--reread-markers", action="store_true",
                    help="re-read the marker from each stored text layer and update source.json "
                         "(no store access; use after a marker-rule change)")
    args = ap.parse_args()

    if args.reread_markers:
        refresh_markers(OUT_ROOT, args.request, args.date)
        return

    if not args.sha:
        raise SystemExit("--sha is required unless --reread-markers is given")

    for sha in args.sha:
        row, data = resolve(sha, args.store)
        md, records, pages = text_layer(data)
        found = read_markers(records)
        marker, marker_state = marker_resolution(found)
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
            "edition_marker": marker,
            "detected_markers": [f["marker"] for f in found],
            "detected_marker_pages": found,
            "marker_detection_source": f"pdf_text_pages_1_through_{MARKER_PAGES}",
            "marker_resolution_state": marker_state,
            "marker_rule": ("the earliest page carrying a marker governs; a hold is recorded only "
                            "when that page names more than one year"),
            "guide_markdown_sha256": hashlib.sha256((out / "guide.md").read_bytes()).hexdigest(),
        }
        (out / "source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
        print(f"{row['file']}: {pages} pp, {len(records)} lines, markers {markers} -> {out}")


if __name__ == "__main__":
    main()
