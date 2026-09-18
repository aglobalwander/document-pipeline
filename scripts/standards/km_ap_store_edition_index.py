#!/usr/bin/env python3
"""What each AP source in the store *is*, from the document's own statement.

A source we hold must be identifiable: not "the Latin CED" but **which** edition of it, read off the
document rather than inferred from a filename. This walks every AP row in the store's `MANIFEST.csv`,
takes the text layer delivered for its sha, and reports the edition marker and the page it prints on.

It also answers the holding question the store now poses: **where a course has more than one edition
in the store, which is the latest** — 2020 and 2025 both exist for AP Latin — because the newest
edition governs the extraction and the choice has to be *stated*, never adopted silently.

No body read and no text comparison: the marker is the document's own front matter, and nothing here
reads a statement or matches a row.

Usage:
    poetry run python scripts/standards/km_ap_store_edition_index.py [--date 2026-09-18]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_text_layer import MARKER_PAGES, OUT_ROOT, marker_resolution, read_markers

STORE = Path.home() / (
    "Library/CloudStorage/OneDrive-ShanghaiAmericanSchool/2_Models-Frameworks-Research/"
    "_Standards Frameworks/_curriculum_ontology_sources")
LAYERS_REQUEST = "ap_store_layers"
EDITION_RX = re.compile(r"(\d{4})\s*$")
FIELDS = ["course_key", "file", "sha256", "pdf_pages", "status", "marker", "edition_year", "page",
          "marker_state", "detected_markers", "detected_marker_pages", "pages_read", "evidence"]


def course_key(file: str) -> str:
    """The course a document belongs to: its name with the edition stripped off.

    `AP Latin Course and Exam Description, Effective Fall 2020.pdf` and `…Fall 2025.pdf` are one
    course in two editions, and grouping them is what makes the latest visible.
    """
    name = re.sub(r"\.pdf$", "", file)
    name = re.sub(r",?\s*Effective\s+\w+\s+\d{4}\s*$", "", name)
    return name.strip()


def read_row(row: dict, date: str) -> dict:
    out = {k: "" for k in FIELDS}
    out.update({"course_key": course_key(row["file"]), "file": row["file"],
                "sha256": row["sha256"]})
    base = OUT_ROOT / date / LAYERS_REQUEST / row["sha256"]
    source_path = base / "source.json"
    if not source_path.exists():
        out["status"] = "layer_missing"
        out["evidence"] = f"no layer under {LAYERS_REQUEST}/ for this sha"
        return out
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source["pdf_sha256"] != row["sha256"]:
        out["status"] = "layer_sha_mismatch"
        out["evidence"] = (f"the layer records {source['pdf_sha256'][:16]} against the store's "
                           f"{row['sha256'][:16]}")
        return out
    records = [json.loads(line) for line in (base / "text_layer.jsonl").open(encoding="utf-8")]

    found = read_markers(records)
    marker, state = marker_resolution(found)
    page = next((f["page"] for f in found if f["marker"] == marker), None) if marker else None
    match = EDITION_RX.search(marker) if marker else None
    out.update({
        "pdf_pages": source["pdf_pages"], "marker": marker or "",
        "edition_year": match.group(1) if match else "", "page": page or "", "marker_state": state,
        "detected_markers": "; ".join(f["marker"] for f in found),
        "detected_marker_pages": "; ".join(f"p.{f['page']}" for f in found),
        "pages_read": f"pages 1-{min(MARKER_PAGES, source['pdf_pages'])}",
    })
    if marker:
        out["status"] = "marker_printed"
        out["evidence"] = f"the document states {marker!r} on p.{page}"
    elif "hold" in state:
        out["status"] = "marker_review_hold"
        out["evidence"] = (f"the document states {len(found)} editions "
                           f"({out['detected_markers']}) and names no single one")
    else:
        out["status"] = "no_marker_printed"
        out["evidence"] = f"no edition marker prints in the first {MARKER_PAGES} pages"
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-18")
    ap.add_argument("--store", type=Path, default=STORE)
    args = ap.parse_args()

    with (args.store / "MANIFEST.csv").open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["framework"] == "AP"]
    out = [read_row(r, args.date) for r in rows]

    base = OUT_ROOT / args.date / LAYERS_REQUEST
    with (base / "ap_store_edition_index.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)

    by_course: dict[str, list[dict]] = collections.defaultdict(list)
    for r in out:
        by_course[r["course_key"]].append(r)
    latest = {}
    for key, editions in by_course.items():
        if len(editions) < 2:
            continue
        years = sorted({r["edition_year"] for r in editions if r["edition_year"]})
        latest[key] = {"newest_edition_year": years[-1] if years else "",
                       "editions_held": [{"year": r["edition_year"], "file": r["file"]}
                                         for r in editions]}
    summary = {
        "documents": len(out),
        "by_status": dict(collections.Counter(r["status"] for r in out)),
        "by_edition_year": dict(sorted(collections.Counter(
            r["edition_year"] or "(none)" for r in out).items())),
        "courses_with_more_than_one_edition_held": latest,
        "method": ("the marker each document prints, read from the layer km_text_layer.py wrote from "
                   "the store's hash-verified bytes; no body read"),
        "edition_rule": ("where more than one edition is held the newest governs the extraction; this "
                         "index states which is which and does not choose"),
        "apply_authorized": False,
    }
    (base / "ap_store_edition_index_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"documents {len(out)} | {dict(collections.Counter(r['status'] for r in out))}")
    for r in out:
        print(f"   {r['file'][:56]:58} {(r['marker'] or r['marker_state'])[:24]:26} p.{r['page']}")
    print(f"\ncourses held in more than one edition: {len(latest)}")
    for key, info in latest.items():
        print(f"   {key[:52]}: newest {info['newest_edition_year']} of "
              f"{[e['year'] for e in info['editions_held']]}")
    print(f"-> {base}/ap_store_edition_index.csv")


if __name__ == "__main__":
    main()