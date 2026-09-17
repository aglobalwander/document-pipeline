#!/usr/bin/env python3
"""Give each of KM's 838 unit-grain holds its printed statement unit.

KM's `dp_statements_hold.csv` names 838 rows that carry no printed per-statement code — the guides
print their statements without codes, so the row's *unit* is whatever heading the guide prints above
it. KM's ruling (P4 answers, §2) is to build the spine once rather than ten statement grammars, and
`dp_statements_hold.csv` is the list to answer by name.

The holds are keyed to our own `statements.csv` rows (subject + statement text), which is where KM
measured them from — not to the reference rows in `statements_arts.csv`, which belong to the other
deliverable. For each hold this returns the guide's own printed heading above the row, the section
qualifier when the guide prints one, and the two nearest headings as theme and topic.

Reads only local files: KM's hold list, the stored `statements.csv` and `text_layer.jsonl` per sha.
Writes `statements_unit_grain.csv` and `unit_grain_summary.json` into the P4 request directory.

Usage:
    poetry run python scripts/standards/km_unit_grain_spine.py [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_p4_statements import CANON_SUBJECT, printed_context
from km_reference_context import context_for
from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
HOLDS = KM / "dp_canonical/dp_statements_hold.csv"
REQUEST = "p4_dp_statements"
FIELDS = ["subject", "pdf_sha256", "page", "statement_code", "statement_text", "match",
          "printed_heading", "section_qualifier", "statement_code_qualified", "theme_context",
          "topic_context", "context_pages_back", "md_line"]


# KM's acceptance (§3) found that apparent duplicate groups are the guide's own front matter: a
# contents list repeats the names its body prints, so it looks duplicated by nature. KM excluded 96
# rows as `source_is_front_matter` and asked this repo either to exclude them at source or to confirm
# the reading. Both are done here: the rows are excluded from the artifact and written to an audit
# file with the class that matched, so nothing is dropped silently. The classes are the guides'
# course-level sections and the contents-style repetition, taken from the headings we already emit —
# and the rule is heading-based, deliberately not page-based: pages 45-46 carry Global Politics front
# matter *and* legitimate Physics body rows under `B.1 Thermal energy transfers`.
FRONT_MATTER = (
    (re.compile(r"^First (assessment|examinations) \d{4}$"), "cover line"),
    (re.compile(r"^(Contents|Appendices)$", re.I), "contents list"),
    (re.compile(r"^IB (mission statement|learner profile)", re.I), "IB boilerplate"),
    (re.compile(r"^Nature of the subject", re.I), "course-level section"),
    (re.compile(r"^Distinction between (SL and HL|HL and SL)", re.I), "course-level section"),
    (re.compile(r"^Connections to subjects and programmes", re.I), "course-level section"),
    (re.compile(r"^Approaches to (learning|teaching)", re.I), "course-level section"),
    (re.compile(r"^Structure of the syllabus", re.I), "course-level section"),
    (re.compile(r"^Thematic studies:\s*Summary outline$", re.I), "summary-outline table"),
    (re.compile(r"^(The )?Concepts$", re.I), "section heading without a canon topic"),
    (re.compile(r"^Suggested concepts embedded in this topic$", re.I), "section heading without a canon topic"),
    (re.compile(r"^Developing skills through the focused study$", re.I), "section heading without a canon topic"),
    (re.compile(r"^Physics and international-mindedness$", re.I), "front-matter section"),
)


def front_matter_class(heading: str | None) -> str | None:
    """The front-matter class a printed heading belongs to, or None for syllabus content."""
    text = (heading or "").strip()
    for pattern, name in FRONT_MATTER:
        if pattern.search(text):
            return name
    return None


def split_front_matter(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(syllabus rows, front-matter rows). Excluded rows keep their class for the audit file."""
    kept, excluded = [], []
    for row in rows:
        name = front_matter_class(row.get("printed_heading"))
        if name:
            excluded.append({**row, "front_matter_class": name})
        else:
            kept.append(row)
    return kept, excluded


def norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\u00a0", " ")).strip().lower()


def load_statements(base: Path) -> tuple[dict, dict]:
    """(subject_head, text) -> row, plus the text layer per sha, for the stored statements."""
    index: dict[tuple[str, str], dict] = {}
    layers: dict[str, list[dict]] = {}
    for csv_path in sorted(base.glob("*/statements.csv")):
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                index.setdefault((norm(row["subject"]), norm(row["statement_text"])), row)
        layer_path = csv_path.parent / "text_layer.jsonl"
        if layer_path.exists():
            layers[csv_path.parent.name] = [
                json.loads(line) for line in layer_path.open(encoding="utf-8")]
    return index, layers


def subject_head_for(slug: str) -> str:
    """KM's slug back to the subject_head our rows carry (`global_politics` -> `Global Politics`)."""
    return next((head for head, s in CANON_SUBJECT.items() if s == slug), slug)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--holds", type=Path, default=HOLDS)
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    with args.holds.open(newline="", encoding="utf-8") as fh:
        holds = [r for r in csv.DictReader(fh) if r["hold"] == "unit_grain_no_printed_code"]
    index, layers = load_statements(base)

    rows, unmatched = [], []
    per: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for hold in holds:
        slug = hold["subject"].strip()
        subject_head = subject_head_for(slug)
        row = (index.get((norm(subject_head), norm(hold["statement"])))
               or index.get((norm(slug), norm(hold["statement"]))))
        per[slug]["held"] += 1
        if not row:
            per[slug]["unmatched"] += 1
            unmatched.append({"subject": slug, "page": hold["page"],
                              "statement_text": hold["statement"]})
            continue
        sha = row["pdf_sha256"]
        layer = layers.get(sha) or []
        md_line = int(row["md_line"]) if row.get("md_line") else None
        context = printed_context(md_line, layer, row["statement_code"], row.get("printed_text"))
        theme, topic, back = context_for(md_line, layer) if md_line else (None, None, None)
        per[slug]["joined"] += 1
        if topic:
            per[slug]["with_topic"] += 1
        rows.append({
            "subject": row["subject"], "pdf_sha256": sha, "page": row["page"],
            "statement_code": row["statement_code"], "statement_text": row["statement_text"],
            "match": row["match"], **context, "theme_context": theme, "topic_context": topic,
            "context_pages_back": back, "md_line": md_line,
        })

    # KM's front matter is excluded at source; the matched class is kept in an audit file so the
    # reading stays checkable and nothing disappears silently.
    rows, fm_rows = split_front_matter(rows)
    head_to_slug = {head: slug for head, slug in CANON_SUBJECT.items()}
    for row in fm_rows:
        per[head_to_slug.get(row["subject"], row["subject"])]["excluded_front_matter"] += 1
    with (base / "front_matter_excluded.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS + ["front_matter_class"])
        writer.writeheader()
        writer.writerows(fm_rows)

    with (base / "statements_unit_grain.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "holds_named_by_km": len(holds),
        "joined_to_our_statements": len(rows) + len(fm_rows),
        "syllabus_rows_after_exclusion": len(rows),
        "front_matter_excluded": len(fm_rows),
        "front_matter_by_class": dict(collections.Counter(r["front_matter_class"] for r in fm_rows)),
        "with_a_printed_heading": sum(1 for r in rows if r["printed_heading"]),
        "with_a_printed_topic_context": sum(1 for r in rows if r["topic_context"]),
        "with_a_section_qualifier": sum(1 for r in rows if r["section_qualifier"]),
        "unmatched": unmatched,
        "by_subject": {k: dict(v) for k, v in sorted(per.items())},
        "key": "KM subject slug + statement text against the stored statements.csv rows",
        "method": "printed headings from the cached text layer; no OCR, no model",
    }
    (base / "unit_grain_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                  encoding="utf-8")
    for slug, counts in sorted(per.items(), key=lambda kv: -kv[1]["held"]):
        extra = f" | UNMATCHED {counts['unmatched']}" if counts["unmatched"] else ""
        print(f"{slug:22} held {counts['held']:4} | joined {counts['joined']:4} | with a printed "
              f"topic {counts['with_topic']:4}{extra}")
    print(f"\nholds {len(holds)} | joined {len(rows)} | printed heading "
          f"{summary['with_a_printed_heading']} | topic context "
          f"{summary['with_a_printed_topic_context']} | section qualifier "
          f"{summary['with_a_section_qualifier']}")
    print(f"-> {base}/statements_unit_grain.csv")


if __name__ == "__main__":
    main()