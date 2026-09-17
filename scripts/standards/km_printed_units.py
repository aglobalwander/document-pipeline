#!/usr/bin/env python3
"""Enumerate the DP guides that print their own statement unit.

KM's ruling (P4 answers, §2): build **one** context spine rather than ten statement grammars, *and*
enumerate the guide's own unit where the guide prints one. Three (and Dance if its headings print as
units) do:

  literature, language_and_literature  `Areas of exploration` — AoE1..AoE3, each with its six printed
                                      guiding conceptual questions (AoE1-Q1..Q6)
  music                               printed component headings — comp-explorectx, comp-experiment,
                                      comp-present, comp-contemphl, comp-total
  dance                               printed component headings — comp-ca, comp-wds, comp-perf

The enumeration is label-driven and evidence-only: KM's canon already names each unit, so this walks
the canon rows in scope and returns the guide's own printed line for each one, with page, bbox and
md_line. A label that does not print is reported `not_found` and never invented.

Reads only local files: KM's `dp_canonical.csv`, and the stored `text_layer.jsonl` per guide.
Writes `printed_units.csv` and `printed_units_summary.json` into the P4 request directory.

Usage:
    poetry run python scripts/standards/km_printed_units.py [--subject music] [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_p4_statements import SUBJECT_GUIDE, _text_of
from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
CANON = KM / "dp_canonical/dp_canonical.csv"
REQUEST = "p4_dp_statements"
# The codes KM named in §2, per subject slug. Nothing outside this scope is enumerated.
SCOPE = {
    "literature": r"^AoE\d+(-Q\d+|-TOK)?$",
    "language_and_literature": r"^AoE\d+(-Q\d+|-TOK)?$",
    "music": r"^comp-",
    "dance": r"^comp-",
    # KM asked for the two subjects still without a printed basis. Visual arts prints its three
    # syllabus areas and its two framing sections; psychology prints its four branches, its six
    # concepts and its four content areas — all of them canon codes standing on printed headings.
    "visual_arts": r"^(CREATE|CONNECT|COMMUNICATE|INTEGRATE|INQUIRY|STUDIO)$",
    "psychology": r"^(branch-|concept-|content-)",
}
# code prefix -> KM subject slug, for the guide file that holds it.
SLUG_OF = {"literature": "Literature", "language_and_literature": "Language and Literature",
           "music": "Music", "dance": "Dance", "visual_arts": "Visual Arts",
           "psychology": "Psychology"}
FIELDS = ["subject", "pdf_sha256", "code", "label", "parent_code", "printed_text", "match",
          "is_heading", "page", "bbox", "md_line"]

QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
DASHES = {"\u2014": "-", "\u2013": "-", "\u2012": "-"}


def norm(text: str | None) -> str:
    """Comparable form: case, whitespace, quote and dash variants, trailing punctuation."""
    value = (text or "").replace("\u00a0", " ")
    for src, dst in {**QUOTES, **DASHES}.items():
        value = value.replace(src, dst)
    return re.sub(r"\s+", " ", value).strip().strip(".,;:\u2022").lower()


def size_of(rec: dict) -> float:
    return max((span.get("size", 0) for span in (rec.get("spans") or [])), default=0.0)


def find_printed(label: str, layer: list[dict]) -> tuple[str, dict] | None:
    """The guide's own line for a canon label, ranked so a heading beats prose that merely mentions it."""
    want = norm(label)
    if not want:
        return None
    rank = {"exact": 3, "prefix": 2, "contained": 1}
    best: tuple[int, str, dict] | None = None
    for rec in layer:
        text = norm(_text_of(rec))
        if not text:
            continue
        if text == want:
            kind = "exact"
        elif text.startswith(want):
            kind = "prefix"
        elif want in text:
            kind = "contained"
        else:
            continue
        score = rank[kind] * 2 + (1 if size_of(rec) >= 12 else 0)
        if best is None or score > best[0]:
            best = (score, kind, rec)
    return None if best is None else (best[1], best[2])


def guide_sha(subject_head: str, base: Path) -> str | None:
    """The stored guide for a subject, from its `source.json` file name."""
    wanted = SUBJECT_GUIDE.get(subject_head)
    for source_path in sorted(base.glob("*/source.json")):
        record = json.loads(source_path.read_text(encoding="utf-8"))
        if record.get("file") == wanted:
            return source_path.parent.name
    return None


def canon_rows(subjects: list[str]) -> dict[str, list[dict]]:
    with CANON.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        slug = (row.get("subject") or "").strip()
        if slug in subjects:
            out[slug].append(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--subject", default=None,
                    help="one slug or a comma-separated list; default every subject in scope")
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    subjects = ([s.strip() for s in args.subject.split(",") if s.strip()]
                if args.subject else sorted(SCOPE))
    canon = canon_rows(subjects)

    rows, not_found = [], []
    per: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for slug in subjects:
        pattern = re.compile(SCOPE[slug])
        sha = guide_sha(SLUG_OF[slug], base)
        per[slug]["codes"] = sum(1 for r in canon[slug] if pattern.match(r["code"]))
        if not sha:
            per[slug]["no_guide"] = 1
            continue
        layer = [json.loads(line) for line in
                 (base / sha / "text_layer.jsonl").open(encoding="utf-8")]
        per[slug]["sha"] = sha
        for row in canon[slug]:
            if not pattern.match(row["code"]):
                continue
            found = find_printed(row["label"], layer)
            if not found:
                per[slug]["not_found"] += 1
                not_found.append({"subject": slug, "code": row["code"], "label": row["label"]})
                continue
            kind, rec = found
            per[slug][kind] += 1
            rows.append({
                "subject": SLUG_OF[slug], "pdf_sha256": sha, "code": row["code"],
                "label": row["label"], "parent_code": row.get("parent_code") or None,
                "printed_text": _text_of(rec), "match": kind,
                "is_heading": size_of(rec) >= 12, "page": rec["page"],
                "bbox": json.dumps(rec["bbox"]), "md_line": rec["md_line"],
            })

    with (base / "printed_units.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "units_enumerated": len(rows),
        "codes_in_scope": sum(c["codes"] for c in per.values()),
        "not_found": not_found,
        "by_subject": {k: dict(v) for k, v in sorted(per.items())},
        "scope": {k: SCOPE[k] for k in sorted(per)},
        "method": "KM canon label -> the guide's own printed line, from the cached text layer",
    }
    (base / "printed_units_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                     encoding="utf-8")
    for slug, counts in sorted(per.items()):
        print(f"{slug:26} codes {counts['codes']:3} | enumerated {counts['exact']:3} exact, "
              f"{counts['prefix']:2} prefix, {counts['contained']:2} contained | "
              f"not_found {counts['not_found']}")
    print(f"\nunits {len(rows)} of {summary['codes_in_scope']} in scope -> "
          f"{base}/printed_units.csv")
    for miss in not_found:
        print(f"   not printed: {miss['subject']} {miss['code']} {miss['label'][:48]!r}")


if __name__ == "__main__":
    main()