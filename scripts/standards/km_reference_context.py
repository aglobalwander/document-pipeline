#!/usr/bin/env python3
"""Give a reference row its printed topic context, for the subjects with no depth artifact.

The ten arts/language subjects have no family extractor, so their statements are located but sit
without the topic tree KM's request asks for. Rather than build ten grammars on a guess, this pass
uses KM's own reference rows as the spine and reads the *guide's* headings above each located row:
a line is a heading when its largest span is set larger than the body text, or when it is bold and
short. The two nearest headings above the row become its theme and topic context.

Nothing is inferred: the context is the guide's own printed text, taken from the same text layer as
the row itself, and the row keeps the reference's code so KM can rule on the shape afterwards.

Reads `statements_located.jsonl` from a P4 run plus each guide's `text_layer.jsonl`.
Writes `statements_arts.csv` and `arts_summary.json` into the P4 request directory.

Usage:
    poetry run python scripts/standards/km_reference_context.py --subject "Dance"
    poetry run python scripts/standards/km_reference_context.py            # all arts/language subjects
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

from km_p4_statements import SUBJECT_GUIDE, _text_of, headings_above
from km_text_layer import OUT_ROOT

REQUEST = "p4_dp_statements"
DEFAULT_DATE = "2026-09-17"
# KM flags these subjects `arts_language=yes`; they are the ones with no depth extractor.
ARTS_LANGUAGE = ["Dance", "Film", "Language ab initio", "Language and Literature", "Language B",
                 "Literature", "Music", "Psychology", "Theatre", "Visual Arts"]
FIELDS = ["pdf_sha256", "subject", "reference_standard_id", "printed_code", "reference_text",
          "printed_text", "match", "page", "bbox", "md_line", "theme_context", "topic_context",
          "context_pages_back"]


def context_for(md_line: int, layer: list[dict]) -> tuple[str | None, str | None, int | None]:
    """The two nearest printed headings above this line, nearest first.

    Uses the shared heading rule in `km_p4_statements` — section-shaped headings first (`A.1
    Kinematics`, `Structure 1. Models…`), then large/bold ones — which excludes the guides' furniture
    and wrapped prose fragments. That is the fix for KM's complaint that the first spine pass returned
    "whatever heading the extractor reached, including prose paragraphs".
    """
    found = headings_above(md_line, layer, 2)
    if not found:
        return None, None, None
    topic = found[0]
    theme = found[1] if len(found) > 1 else None
    line = next((rec["md_line"] for rec in reversed(layer)
                 if rec["md_line"] < md_line and _text_of(rec) == topic), None)
    return theme, topic, (md_line - line) if line else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default=DEFAULT_DATE)
    ap.add_argument("--subject", default=None,
                    help="one KM subject_head, or a comma-separated list; default the ten spine subjects")
    ap.add_argument("--all", action="store_true",
                    help="every subject present in statements_located.jsonl, not only the ten "
                         "(the 838 unit-grain rows live in seven guides outside that set)")
    ap.add_argument("--sha", default=None,
                    help="read the layer for this sha instead of the one in the located rows "
                         "(used for Visual Arts, whose rows belong to the 2017 guide)")
    ap.add_argument("--out-name", default="statements_arts.csv")
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    located = [json.loads(line) for line in (base / "statements_located.jsonl").open(encoding="utf-8")]
    if args.subject:
        subjects = [s.strip() for s in args.subject.split(",") if s.strip()]
    elif args.all:
        subjects = sorted({r["subject"] for r in located})
    else:
        subjects = ARTS_LANGUAGE

    rows, per = [], {}
    for subject in subjects:
        file = SUBJECT_GUIDE.get(subject)
        if not file:
            raise SystemExit(f"{subject!r} is not in SUBJECT_GUIDE")
        subject_rows = [r for r in located if r["subject"] == subject]
        if not subject_rows:
            continue
        sha = args.sha or subject_rows[0]["pdf_sha256"]
        layer = [json.loads(line) for line in
                 (base / sha / "text_layer.jsonl").open(encoding="utf-8")]
        counts = collections.Counter()
        if args.sha:
            # A different edition: the located rows carry the *other* guide's md_lines, so the row
            # has to be found again in this layer before its context means anything.
            from km_p4_statements import index, locate_row
            from km_row_reads import tokens
            post, doc = index(layer), collections.Counter(
                t for r in layer for t in tokens(r["text"]))
            relocated = []
            for r in subject_rows:
                hit = locate_row({"statement_text": r["reference_text"],
                                  "printed_code": r["printed_code"]}, layer, post, doc)
                relocated.append({**r, "match": hit["match"], "page": hit["page"],
                                  "bbox": hit["bbox"], "md_line": hit["md_line"],
                                  "printed_text": hit["matched_printed"],
                                  "doc_coverage": hit["doc_coverage"]})
            subject_rows = relocated
        for r in subject_rows:
            counts[r["match"]] += 1
            md = r.get("md_line")
            theme, topic, back = context_for(md, layer) if md else (None, None, None)
            rows.append({"pdf_sha256": sha, "subject": subject,
                         "reference_standard_id": r["reference_standard_id"],
                         "printed_code": r["printed_code"], "reference_text": r["reference_text"],
                         "printed_text": r["printed_text"], "match": r["match"],
                         "page": r["page"], "bbox": json.dumps(r["bbox"]) if r["bbox"] else None,
                         "md_line": md, "theme_context": theme, "topic_context": topic,
                         "context_pages_back": back})
        per[subject] = {"rows": len(subject_rows), "by_match": dict(counts),
                        "with_topic_context": sum(1 for r in rows
                                                  if r["subject"] == subject and r["topic_context"])}

    with (base / args.out_name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (base / "arts_summary.json").write_text(json.dumps(per, indent=2) + "\n", encoding="utf-8")
    for subject, s in per.items():
        print(f"{subject:26} {s['rows']:4} rows | {s['with_topic_context']:4} with a printed topic "
              f"heading above them | {s['by_match']}")
    print(f"total {len(rows)} rows -> {base}/{args.out_name}")


if __name__ == "__main__":
    main()