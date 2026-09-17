#!/usr/bin/env python3
"""Acceptance check for KM's P3 row reads (data/output/km_requests/2026-09-17/p3_row_reads).

The reads are evidence, not canon: KM's acceptance requires that each ``read`` row's text is
*printed*, not inferred, and that the crop that shows it exists. This script decides that
mechanically.

Two checks, both run on every row that carries ``printed_text`` (``read`` and
``absence_region_read``):

1. **Presence (hard).** Every token of ``printed_text``, normalised the same way the reader
   normalises, is printed among the words on that row's own region pages of its named sha. A
   token the text layer does not carry is a fail: it would mean the reader produced text that is
   not on the page.
2. **Crops (hard).** Every ``regions[].crop`` (and every crop attached under
   ``printed_in_other_documents``) exists, resolved relative to the reads file's directory.

A third, **order (soft)** check is reported but does not fail the run. It asks whether the tokens
run in the same order in the region's reading-order stream. They do not always, and that is not a
defect:

- AP Calculus/Precalculus/Statistics print maths as glyphs on their own baselines (a fraction's
  numerator, denominator and the word ``over`` are separate lines), so any linearisation of the
  page reorders them.
- AP pages also print rubric codes (``4b``, ``2b``) and annotation letters inside the statement's
  bounding box; the reader keeps the statement and drops the code.
- The GOLD reader deliberately puts the printed ``Objective N`` heading before its title.

The plain "contiguous substring of the text layer" rule the handoff plan proposed therefore fails
for ~58 *correct* rows on two-column and maths pages, because the raw word stream interleaves
columns. Presence is the check that survives all three cases; order is reported for a human.

Usage:
    poetry run python scripts/standards/check_p3_reads.py
    poetry run python scripts/standards/check_p3_reads.py --reads path/to/reads.jsonl --show 40
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from km_row_reads import page_words, tokens

DEFAULT_READS = Path("data/output/km_requests/2026-09-17/p3_row_reads/reads.jsonl")
TEXT_STATUSES = ("read", "absence_region_read")


def region_pages(row: dict) -> list[int]:
    return sorted({reg["page"] for reg in row.get("regions") or []})


def region_page_tokens(sha: str, pages: list[int]) -> collections.Counter:
    return collections.Counter(w["tok"] for p in pages for w in page_words(sha, p))


def region_stream(sha: str, row: dict, pad: float = 3.0) -> list[str]:
    """Tokens of the words inside the row's own crop boxes, in visual reading order."""
    by_page: dict[int, list[list[float]]] = {}
    for reg in row.get("regions") or []:
        by_page.setdefault(reg["page"], []).append(reg["bbox"])
    out: list[str] = []
    for p in sorted(by_page):
        boxes = by_page[p]
        keep = []
        for w in page_words(sha, p):
            cx = (w["bbox"][0] + w["bbox"][2]) / 2
            cy = (w["bbox"][1] + w["bbox"][3]) / 2
            if any(b[0] - pad <= cx <= b[2] + pad and b[1] - pad <= cy <= b[3] + pad
                   for b in boxes):
                keep.append(w)
        keep.sort(key=lambda w: (round(w["bbox"][1] / 3), w["bbox"][0]))
        out += [w["tok"] for w in keep]
    return out


def is_ordered_subsequence(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return all(any(h == t for h in it) for t in needle)


def crop_refs(row: dict) -> list[str]:
    refs = [reg["crop"] for reg in row.get("regions") or [] if reg.get("crop")]
    for alt in row.get("printed_in_other_documents") or []:
        refs += [reg["crop"] for reg in alt.get("regions") or [] if reg.get("crop")]
    return refs


def check(rows: list[dict], base: Path) -> tuple[list, list, list]:
    presence_fail, crop_fail, order_fail = [], [], []
    for row in rows:
        for ref in crop_refs(row):
            if not (base / ref).exists():
                crop_fail.append((row.get("request_id"), ref))
        if row.get("status") not in TEXT_STATUSES:
            continue
        rid = row.get("request_id")
        pages = region_pages(row)
        if not pages:
            presence_fail.append((rid, "no region"))
            continue
        toks = tokens(row.get("printed_text") or "")
        if not toks:
            presence_fail.append((rid, "empty printed_text"))
            continue
        available = region_page_tokens(row["pdf_sha256"], pages)
        wanted = collections.Counter(toks)
        if any(available[t] < n for t, n in wanted.items()):
            missing = sorted(t for t, n in wanted.items() if available[t] < n)
            presence_fail.append((rid, "not printed on region pages: " + ", ".join(missing[:8])))
        if not is_ordered_subsequence(toks, region_stream(row["pdf_sha256"], row)):
            order_fail.append((rid, row.get("framework"), row.get("read_method")))
    return presence_fail, crop_fail, order_fail


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reads", type=Path, default=DEFAULT_READS)
    ap.add_argument("--show", type=int, default=20, help="max failing ids to print")
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.reads.open(encoding="utf-8")]
    base = args.reads.parent
    presence_fail, crop_fail, order_fail = check(rows, base)

    checked = sum(1 for r in rows if r.get("status") in TEXT_STATUSES)
    crops = sum(len(crop_refs(r)) for r in rows)
    print(f"rows {len(rows)}  text rows checked {checked}  crop refs {crops}")
    print(f"presence (hard): {'PASS' if not presence_fail else f'FAIL {len(presence_fail)}'}")
    print(f"crops    (hard): {'PASS' if not crop_fail else f'FAIL {len(crop_fail)}'}")
    print(f"order    (soft): {len(order_fail)} rows reorder "
          f"{dict(collections.Counter(fw for _, fw, _ in order_fail))} "
          f"{dict(collections.Counter(m for _, _, m in order_fail))}")
    for label, fails in (("presence", presence_fail), ("crops", crop_fail)):
        for rid, why in fails[:args.show]:
            print(f"  {label} {rid}: {why}")
    if order_fail:
        print("  order review (expected for maths glyphs/rubric codes/GOLD headings):")
        for rid, fw, method in order_fail[:args.show]:
            print(f"    {rid} {fw} {method}")

    if presence_fail or crop_fail:
        sys.exit(1)
    print("P3 acceptance: PASS")


if __name__ == "__main__":
    main()