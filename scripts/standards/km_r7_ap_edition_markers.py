#!/usr/bin/env python3
"""R7: the edition marker each AP course description prints, with the page it prints on.

KM's request (2026-09-18, R7) is bounded on purpose: *the edition marker as the document prints it,
with the page it prints on; where the document states no edition, an explicit `not_printed` with the
region read.* **10 rows, no body read, no text comparison.** `networking` is expected `not_printed` —
its file is a Course Framework that states no edition — and it is kept in the list deliberately so a
course is recorded rather than hidden.

Nothing here reads a statement or matches a row. It resolves each sha through the store's
`MANIFEST.csv`, takes the text layer `km_text_layer.py` wrote from those verified bytes, and reports
what the document's own front matter says about its edition. That is the discipline KM used to close
the IB labels: the marker read from the document rather than inferred from a filename.

The marker rule is `km_text_layer`'s, unchanged — IB's `First assessment YYYY` / `First examinations
YYYY` and AP's `Effective Fall YYYY`, searched over a **joined** page because an AP cover prints
`Effective` and `Fall 2026` on two printed lines. A document that states two editions holds rather
than picking one.

Usage:
    poetry run python scripts/standards/km_r7_ap_edition_markers.py [--date 2026-09-18]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

from km_text_layer import MARKER_PAGES, OUT_ROOT, marker_resolution, read_markers

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
ROWS = KM / "pipeline_requests_2026-09-18/r7_ap_edition_markers_10.csv"
REQUEST = "r7_ap_edition_markers"
FIELDS = ["course", "canon_edition", "audit_verdict", "guide_file", "guide_sha256", "status",
          "marker", "page", "marker_state", "detected_markers", "detected_marker_pages",
          "pages_read", "region_read", "evidence"]
REGION_LINES = 3
REGION_CHARS = 96


def load_layer(sha: str, date: str) -> tuple[list[dict], dict]:
    base = OUT_ROOT / date / REQUEST / sha
    records = [json.loads(line) for line in (base / "text_layer.jsonl").open(encoding="utf-8")]
    return records, json.loads((base / "source.json").read_text(encoding="utf-8"))


def region_read(records: list[dict], pages: int = 2) -> str:
    """What the front matter states instead, for a document that prints no edition.

    An explicit region read rather than a blank: the request asks for `not_printed` *with the region
    read*, so the answer to "states no edition" says what the front pages do print.
    """
    out: list[str] = []
    for page in range(1, pages + 1):
        lines = [r["text"].strip() for r in records
                 if r["page"] == page and r["text"].strip()][:REGION_LINES]
        if lines:
            out.append(f"p.{page}: " + " | ".join(line[:REGION_CHARS] for line in lines))
    return " ; ".join(out) or "no text on the first pages"


def read_row(row: dict, date: str, cache: dict) -> dict:
    out = {k: "" for k in FIELDS}
    out.update({k: row[k] for k in ("course", "canon_edition", "audit_verdict", "guide_file",
                                    "guide_sha256")})
    sha = row["guide_sha256"]
    if sha not in cache:
        cache[sha] = load_layer(sha, date)
    records, source = cache[sha]
    if source["pdf_sha256"] != sha:
        out["status"] = "layer_sha_mismatch"
        out["evidence"] = (f"the layer records {source['pdf_sha256'][:16]} against the request's "
                           f"{sha[:16]}; the document read is not this row's")
        return out

    found = read_markers(records)
    marker, state = marker_resolution(found)
    page = next((f["page"] for f in found if f["marker"] == marker), None) if marker else None
    out.update({
        "marker_state": state,
        "detected_markers": "; ".join(f["marker"] for f in found),
        "detected_marker_pages": "; ".join(f"p.{f['page']}" for f in found),
        "pages_read": f"pages 1-{min(MARKER_PAGES, source['pdf_pages'])}",
    })
    if marker:
        out.update({"status": "marker_printed", "marker": marker, "page": page,
                    "evidence": f"the document prints {marker!r} on p.{page}"})
        return out

    out["region_read"] = region_read(records)
    if "hold" in state:
        out["status"] = "marker_review_hold"
        out["evidence"] = (f"the document prints {len(found)} edition statements "
                           f"({out['detected_markers']}) and names no single edition; held")
        return out
    out["status"] = "no_marker_printed"
    out["evidence"] = (f"no edition marker prints in the first {MARKER_PAGES} pages; the "
                       f"front matter reads as recorded in `region_read`")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=Path, default=ROWS)
    ap.add_argument("--date", default="2026-09-18")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.rows.open(newline="", encoding="utf-8")))
    cache: dict[str, tuple] = {}
    out = [read_row(r, args.date, cache) for r in rows]

    base = OUT_ROOT / args.date / REQUEST
    with (base / "r7_ap_edition_markers_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)

    by_status = collections.Counter(r["status"] for r in out)
    summary = {
        "rows": len(out),
        "by_status": dict(by_status),
        "markers": {r["course"]: {"marker": r["marker"], "page": r["page"]}
                    for r in out if r["status"] == "marker_printed"},
        "no_marker_printed": [r["course"] for r in out if r["status"] == "no_marker_printed"],
        "review_holds": {r["course"]: r["marker_state"] for r in out
                         if r["status"] == "marker_review_hold"},
        "method": ("the text layer km_text_layer.py wrote from the store's hash-verified bytes; the "
                   "marker rule is km_text_layer's, IB and AP, searched over a joined page"),
        "no_body_read": True,
        "apply_authorized": False,
        "note": "a marker read from the document's own statement, never inferred from a filename",
    }
    (base / "r7_ap_edition_markers_read_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"rows {len(out)} | {dict(by_status)}")
    for r in out:
        print(f"   {r['course'][:34]:36} {r['status']:18} "
              f"{(r['marker'] or r['marker_state'])[:32]:34} p.{r['page']}")
    print(f"-> {base}/r7_ap_edition_markers_read.csv")


if __name__ == "__main__":
    main()