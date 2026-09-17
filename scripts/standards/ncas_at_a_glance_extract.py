#!/usr/bin/env python3
"""Read NCAS 'At a Glance' tables cell by cell, keeping codes and lettered parts as printed.

KM request P2 (2026-09-17). For each document (named by sha256, resolved and verified through the
source store's MANIFEST.csv) the PDF text layer is read with PyMuPDF and the table is rebuilt from
geometry, not from a scrape:

  block header   'Anchor Standard N: ...', 'Enduring Understanding: ...', 'Essential Question(s): ...'
                 plus the rotated artistic-process label (CREATING, PERFORMING, ...)
  column header  grade or band label with the code printed beneath it, e.g. 'Pre K' / 'DA:Cr1.1.PK'
                 (Media Arts prints '(MA:Re8.1.PK)', Theatre 'TH:Cr1.1.PK.'; kept raw)
  cell items     lettered parts ('a.', 'b.', or a bold 'a'), or a code printed inline at the start
                 of the cell ('MU:Cr1.1.T.Ia ...'); a cell with neither is one unlettered item
  row label      the rotated process component (Explore, Imagine, ...), fragments joined

A page that opens with cell text and no header continues the previous page's block: a first line
that is not an item start is appended to the last item of its column (split cells), and later
lettered parts keep the column's code.

Nothing is normalised. Irregular printed forms are reported in 'flags' for KM to rule on.

Writes data/output/km_requests/2026-09-17/p2_ncas_at_a_glance/<sha>/cells.jsonl + summary.json.

Usage:
    poetry run python scripts/standards/ncas_at_a_glance_extract.py --sha <sha256> [--sha ...]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

from km_text_layer import OUT_ROOT, STORE, resolve

GRADE = re.compile(r"^(Pre ?K|PreK|Kindergarten|K|\d{1,2}(?:st|nd|rd|th)?|HS Proficient|"
                   r"HS Accomplished|HS Advanced|Novice|Intermediate|Proficient|Accomplished|"
                   r"Advanced)$")
CODE = re.compile(r"^\(?([A-Z]{2}:\s?[A-Za-z.]*\d[\w.\-]*?)\)?\.?$")  # raw; see flags
INLINE_CODE = re.compile(r"^([A-Z]{2}:[A-Za-z]{2}\d+\.[\w.]+?)\s+(.*)$")
LETTER = re.compile(r"^([a-z])(?:\.|\s*[–-])?\s+(.*)$")
TYPO_LETTER = re.compile(r"^(\d[a-z])\s+(.*)$")  # e.g. '2a Demonstrate' in Music Cn10
BAND = re.compile(r"^(Anchor Standard\s*\d+|Enduring Understanding|Essential Question)")
FOOTER = re.compile(r"^(Page \d+|Copyright|State Education Agency|on behalf of|All rights)")
PROCESSES = {"CREATING", "PERFORMING", "PRODUCING", "RESPONDING", "CONNECTING",
             "PRESENTING", "PERFORMING/PRESENTING/PRODUCING"}
CODE_SHAPE = re.compile(r"^[A-Z]{2}:(Cr|Pr|Re|Cn)\d{1,2}\.\d\.([A-Z]\.)?(PK|K|\d{1,2}|I{1,3}|"
                        r"I{1,3}[a-z]|\d{1,2}[a-z]|PK[a-z]|K[a-z])$")


def lines_of(page: pymupdf.Page) -> tuple[list[dict], list[dict]]:
    flat, rotated = [], []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            rec = {"text": "".join(s["text"] for s in line["spans"]).strip(),
                   "raw": "".join(s["text"] for s in line["spans"]),
                   "bbox": [round(v, 1) for v in line["bbox"]],
                   "first_span": spans[0]["text"].strip(),
                   "first_bold": bool(spans[0]["flags"] & 16) or "bold" in spans[0]["font"].lower()}
            (flat if abs(line["dir"][0] - 1) < 0.01 else rotated).append(rec)
    return flat, rotated


def cx(r: dict) -> float:
    return (r["bbox"][0] + r["bbox"][2]) / 2


def cy(r: dict) -> float:
    return (r["bbox"][1] + r["bbox"][3]) / 2


def header_columns(flat: list[dict], row_y: float, next_band_y: float) -> list[dict]:
    """Cluster grade labels (and superscripts, and the code line beneath) into columns."""
    region = [r for r in flat if row_y - 4 <= r["bbox"][1] <= row_y + 34 and r["bbox"][1] < next_band_y
              and (GRADE.match(r["text"]) or CODE.match(r["text"]) or r["text"] in
                   ("st", "nd", "rd", "th", "HS"))]
    region.sort(key=cx)
    clusters: list[list[dict]] = []
    for r in region:
        if clusters and abs(cx(r) - cx(clusters[-1][0])) < 22:
            clusters[-1].append(r)
        else:
            clusters.append([r])
    cols = []
    for cl in clusters:
        cl.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
        code = next((r for r in cl if CODE.match(r["text"])), None)
        label_parts = [r["text"] for r in cl if r is not code]
        if not label_parts:
            continue
        cols.append({"label": re.sub(r"(\d) (st|nd|rd|th)$", r"\1\2", " ".join(label_parts)),
                     "code_printed": code["text"] if code else None,
                     "code_bbox": code["bbox"] if code else None,
                     "center": cx(cl[0]), "bottom": max(r["bbox"][3] for r in cl)})
    return cols


def bounds(cols: list[dict], page_width: float) -> None:
    for i, c in enumerate(cols):
        left = (cols[i - 1]["center"] + c["center"]) / 2 if i else c["center"] - (
            cols[1]["center"] - c["center"]) / 2
        right = (c["center"] + cols[i + 1]["center"]) / 2 if i + 1 < len(cols) else c["center"] + (
            c["center"] - cols[i - 1]["center"]) / 2
        c["x0"], c["x1"] = left, min(right, page_width)


def item_start(r: dict) -> tuple[str | None, str | None, str] | None:
    """Return (letter, inline_code, text) if this line opens a new cell item."""
    t = r["text"]
    m = INLINE_CODE.match(t)
    if m:
        code = m.group(1)
        return (None, code, m.group(2))
    m = TYPO_LETTER.match(t)
    if m and r["first_span"].startswith(m.group(1)):
        return (m.group(1), None, m.group(2))
    m = LETTER.match(t)
    if m and (t[1] == "." or r["first_span"] in (m.group(1), m.group(1) + ".") and r["first_bold"]
              or re.match(r"^[a-z]\s*[–-]", t)):
        return (m.group(1), None, m.group(2))
    return None


def flags_for(item: dict) -> list[str]:
    out = []
    code = item["inline_code"] or item["column_code_printed"]
    if code is None:
        out.append("no_printed_code")
        return out
    bare = code.strip("().")
    if code != bare:
        out.append("code_punctuation_printed")
    if " " in bare or "-" in bare:
        out.append("code_space_or_hyphen_printed")
        bare = bare.replace(" ", "")
    if not CODE_SHAPE.match(bare):
        out.append("code_irregular_shape")
    parts = bare.split(":", 1)[1].split(".")
    if len(parts) > 1 and parts[1] in ("I", "l"):
        out.append("roman_or_letter_in_standard_position")
    hs = item["column_header"].startswith("HS") or item["column_header"] in (
        "Proficient", "Accomplished", "Advanced")
    if not hs and re.search(r"\.I{1,3}[a-z]?$", bare):
        out.append("roman_level_outside_HS_column")
    return out


def extract(sha: str, store: Path) -> tuple[list[dict], dict]:
    row, data = resolve(sha, store)
    doc = pymupdf.open(stream=data, filetype="pdf")
    items: list[dict] = []
    ctx = {"artistic_process": None, "anchor_standard": None, "enduring_understanding": None,
           "essential_question": None}
    cols: list[dict] = []
    open_items: dict[int, dict] = {}
    title = None
    notes = []

    for pno, page in enumerate(doc, start=1):
        flat, rotated = lines_of(page)
        footer_y = min([r["bbox"][1] for r in flat if FOOTER.match(r["text"])] or [page.rect.height])
        flat = [r for r in flat if r["bbox"][1] < footer_y - 1]
        flat.sort(key=lambda r: (round(r["bbox"][1]), r["bbox"][0]))
        if title is None and flat:
            title = flat[0]["text"]

        # Grade header rows on this page, and band lines.
        rows_y = sorted({round(r["bbox"][1]) for r in flat if GRADE.match(r["text"])})
        header_rows = []
        for y in rows_y:
            same = [r for r in flat if abs(r["bbox"][1] - y) <= 3 and GRADE.match(r["text"])]
            if len(same) >= 3 and (not header_rows or y - header_rows[-1] > 10):
                header_rows.append(y)
        bands = [r for r in flat if BAND.match(r["text"])]
        # Segment the page: each segment starts at a band group or a header row.
        events = sorted([(r["bbox"][1], "band", r) for r in bands] +
                        [(y, "header", None) for y in header_rows], key=lambda e: e[0])

        def body_between(y_top: float, y_bottom: float) -> list[dict]:
            return [r for r in flat if y_top <= r["bbox"][1] < y_bottom and not BAND.match(r["text"])]

        segments = []  # (body_top, body_bottom)
        first_event_y = events[0][0] if events else footer_y
        if flat and flat[0]["bbox"][1] < first_event_y - 2 and cols:
            # Page opens with cell text: continuation of the previous block.
            top = next(r["bbox"][1] for r in flat if r["text"].casefold() != (title or "").casefold())
            segments.append((top, first_event_y, True, cols))
        for i, (y, kind, rec) in enumerate(events):
            nxt = events[i + 1][0] if i + 1 < len(events) else footer_y
            if kind == "band":
                t = rec["text"]
                if t.startswith("Anchor Standard"):
                    ctx.update(anchor_standard=t, enduring_understanding=None, essential_question=None)
                    proc = [r for r in rotated if r["bbox"][1] - 20 <= y <= r["bbox"][3] + 20
                            and r["text"].upper().replace(" ", "") in {p.replace(" ", "") for p in PROCESSES}]
                    if proc:
                        ctx["artistic_process"] = proc[0]["text"]
                elif t.startswith("Enduring Understanding"):
                    ctx["enduring_understanding"] = t
                    ctx["essential_question"] = None
                else:
                    ctx["essential_question"] = t
                # A band line wrapped onto the next line (before the next event) is appended.
                extra = [r for r in body_between(rec["bbox"][3] - 1, nxt)
                         if r["bbox"][0] <= rec["bbox"][0] + 2 and not GRADE.match(r["text"])]
                for r in extra[:2]:
                    if r["bbox"][1] - rec["bbox"][3] < 4:
                        key = ("anchor_standard" if t.startswith("Anchor") else
                               "enduring_understanding" if t.startswith("Enduring") else
                               "essential_question")
                        ctx[key] = ctx[key] + " " + r["text"]
                        flat.remove(r)
                continue
            new_cols = header_columns(flat, y, nxt)
            if len(new_cols) >= 3:
                bounds(new_cols, page.rect.width)
                cols = new_cols
                hdr_bottom = max(c["bottom"] for c in cols)
                segments.append((hdr_bottom + 1, nxt, False, cols))
                for c in cols:
                    c.update({k: v for k, v in ctx.items()})
                    c["page"] = pno

        for top, bottom, continued, seg_cols in segments:
            if not continued:
                open_items = {}
            body = [r for r in body_between(top, bottom)
                    if not GRADE.match(r["text"]) and not CODE.match(r["text"])
                    and r["text"].casefold() != (title or "").casefold()]
            left_edge = seg_cols[0]["x0"] if seg_cols else 0
            # Rotated process-component label in this segment's left margin.
            labels = [r for r in rotated if r["bbox"][2] <= left_edge + 2 and
                      top - 2 <= cy(r) <= bottom + 2 and
                      r["text"].upper().replace(" ", "") not in {p.replace(" ", "") for p in PROCESSES}]
            labels.sort(key=lambda r: -r["bbox"][3])
            component = "".join(r["raw"] for r in labels).strip() or None
            for ci, c in enumerate(seg_cols):
                col_lines = sorted([r for r in body if c["x0"] <= cx(r) < c["x1"]],
                                   key=lambda r: (r["bbox"][1], r["bbox"][0]))
                for r in col_lines:
                    start = item_start(r)
                    cur = open_items.get(ci)
                    if start is None and cur is not None:
                        cur["_lines"].append(r)
                        if pno not in cur["_pages"]:
                            cur["_pages"].append(pno)
                        continue
                    letter, inline, _ = start if start else (None, None, None)
                    cur = {
                        "pdf_sha256": sha, "file": row["file"], "document_title": title,
                        "artistic_process": c.get("artistic_process"),
                        "anchor_standard": c.get("anchor_standard"),
                        "enduring_understanding": c.get("enduring_understanding"),
                        "essential_question": c.get("essential_question"),
                        "process_component": component if not continued else
                        (open_items.get("_component") or component),
                        "column_header": c["label"], "column_code_printed": c["code_printed"],
                        "column_code_page": c["page"], "column_code_bbox": c["code_bbox"],
                        "letter": letter, "inline_code": inline,
                        "_lines": [r], "_pages": [pno], "continued_block": continued,
                    }
                    items.append(cur)
                    open_items[ci] = cur
            if component and not continued:
                open_items["_component"] = component

    for it in items:
        lines = it.pop("_lines")
        pages = it.pop("_pages")
        printed = re.sub(r"\s+", " ", " ".join(r["text"] for r in lines)).strip()
        start = item_start(lines[0])
        it["printed"] = printed
        it["text"] = re.sub(r"\s+", " ", " ".join([start[2]] + [r["text"] for r in lines[1:]])).strip() \
            if start else printed
        it["page"] = pages[0]
        it["bbox"] = [min(r["bbox"][0] for r in lines), min(r["bbox"][1] for r in lines),
                      max(r["bbox"][2] for r in lines), max(r["bbox"][3] for r in lines)] \
            if len(pages) == 1 else lines[0]["bbox"]
        if len(pages) > 1:
            it["continues_on_pages"] = pages[1:]
            it["bbox_scope"] = "first line only; cell continues on a later page"
        it["flags"] = flags_for(it)
        it["method"] = f"pdf text layer geometry (PyMuPDF {pymupdf.VersionBind}); no OCR, no model"

    summary = {
        "pdf_sha256": sha, "file": row["file"], "pages": doc.page_count,
        "document_title": title, "items": len(items),
        "column_codes": len({(i["column_code_printed"], i["column_code_page"]) for i in items
                             if i["column_code_printed"]}),
        "inline_codes": sum(1 for i in items if i["inline_code"]),
        "cross_page_items": sum(1 for i in items if "continues_on_pages" in i),
        "flags": dict(Counter(f for i in items for f in i["flags"])),
        "canon_rows_citing_this_document": int(row.get("rows_in_the_canon_citing_it") or 0),
        "notes": notes,
    }
    return items, summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True, action="append")
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--store", type=Path, default=STORE)
    args = ap.parse_args()
    for sha in args.sha:
        items, summary = extract(sha, args.store)
        out = OUT_ROOT / args.date / "p2_ncas_at_a_glance" / sha
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "cells.jsonl", "w", encoding="utf-8") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
        print(f"{summary['file']}: {summary['items']} items, {summary['column_codes']} column codes, "
              f"{summary['inline_codes']} inline, {summary['cross_page_items']} cross-page, "
              f"flags {summary['flags']}, canon rows {summary['canon_rows_citing_this_document']}")


if __name__ == "__main__":
    main()
