#!/usr/bin/env python3
"""Flatten a P4 `depth.json` into printed statements with topic, level, page and bbox.

The P4 depth artifacts hold the topic tree the extractors read (units -> topics -> understandings),
but not where each statement is printed. This post-processor joins them to the guide's own text
layer, so every statement carries the page, bbox and md_line of the line it was printed on — the
same shape as `statements_located.jsonl`, which is what makes the two usable together for KM's
acceptance check.

The matching is not re-implemented: it reuses the tested matcher in `km_p4_statements.py`
(rarest-printed-token anchor, span decides), so a wrapped or cross-page statement is found and a
statement that is not in the document is reported rather than placed.

Columns: pdf_sha256, subject, topic_code, statement_code, statement_text, level, page, bbox,
md_line, match, doc_coverage, verbatim, topic_in_canonical.

Level comes from what the extractor recorded: `hl_only` on the understanding, an `AHL` marker in
its code or statement, and the topic's own level marker when the guide prints one.

Usage:
    poetry run python scripts/standards/ib_depth_to_statements.py \
        --depth data/output/km_requests/2026-09-17/p4_dp_statements/<sha>/depth.json \
        --layer data/output/km_requests/2026-09-17/p4_dp_statements/<sha>/text_layer.jsonl \
        --subject biology --sha <sha> --out <dir>
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_p4_statements import (CANON_SUBJECT, SUBJECT_GUIDE, canonical_codes, index, locate_row,
                              printed_context, topic_of)
from km_row_reads import tokens
from km_text_layer import OUT_ROOT

REQUEST = "p4_dp_statements"
AHL = re.compile(r"\bAHL\b|\bHL only\b", re.I)
FIELDS = ["pdf_sha256", "subject", "topic_code", "statement_code", "statement_text", "level",
          "level_basis", "printed_aos", "page", "bbox", "md_line", "printed_text", "match",
          "doc_coverage", "verbatim", "topic_in_canonical",
          # KM's P4 answers, §Action Required: the printed heading above the statement, the code with
          # its printed section qualifier (`Structure 1.1.1`, not `1.1.1`), and the canon subject slug
          # so the row joins KM's layer without a second mapping.
          "printed_heading", "section_qualifier", "statement_code_qualified", "canon_subject_slug"]
# Identity used to drop exact duplicate rows: the same statement, code, topic and page twice.
DEDUPE_KEYS = ("subject", "topic_code", "statement_code", "statement_text", "page", "md_line")


def statements(depth: dict) -> list[dict]:
    """Collect the statement-bearing shapes the depth artifacts use.

    The families do not share one shape: sciences/generic/ESS nest
    ``units -> topics -> understandings``; maths puts ``understandings`` (statement + hl_only, no
    codes) straight on the unit; Global Politics lists ``items`` as strings under a topic; Business
    Management carries ``blocks`` (with the AOs printed against them) and unit-level
    ``conceptual_understandings``; History adds top-level ``concepts`` and ``focused_study_skills``.
    A walker keeps all of them in one pass, with the nearest code/title as the topic context.
    """
    keys = ("understandings", "conceptual_understandings", "items", "blocks",
            "focused_study_skills", "learning_and_teaching")
    out: list[dict] = []

    def add(text: str, code: str | None, hl: bool, topic: str, aos: list | None):
        text = (text or "").strip()
        code = (code or "").strip()
        if not text and not code:
            return
        level = "AHL" if AHL.search(code) or AHL.search(text) else ("HL" if hl else "SL")
        out.append({"topic_code": topic, "statement_code": code, "statement_text": text,
                    "level": level, "level_basis": "recorded",
                    "printed_aos": ",".join(aos or []) or None})

    def walk(node, topic: str):
        if isinstance(node, dict):
            here = node.get("code") or node.get("title") or topic
            for key, val in node.items():
                if key in keys and isinstance(val, list):
                    for it in val:
                        if isinstance(it, str):
                            add(it, None, False, here, None)
                        elif isinstance(it, dict):
                            add(it.get("statement") or it.get("text"), it.get("code"),
                                bool(it.get("hl_only")), here, it.get("ao_depth"))
                elif isinstance(val, (dict, list)):
                    walk(val, here)
        elif isinstance(node, list):
            for it in node:
                walk(it, topic)

    walk(depth, depth.get("subject") or "")
    # A subject whose artifact records no HL understanding at all has no level signal: its guide
    # marks AHL in a form the extractor does not catch (chemistry, physics, ESS and DT all do),
    # so those "SL" values are a default and must not be read as printed.
    if out and not any(r["level"] in ("HL", "AHL") for r in out):
        for r in out:
            if r["level"] == "SL":
                r["level_basis"] = "unrecorded_in_artifact"
    return out


def flatten(depth_path: Path, layer_path: Path, subject: str, sha: str) -> list[dict]:
    depth = json.loads(depth_path.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in layer_path.open(encoding="utf-8")]
    post = index(records)
    doc = collections.Counter(t for r in records for t in tokens(r["text"]))
    page_tokens: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    for rec in records:
        page_tokens[rec["page"]].update(tokens(rec["text"]))
    canon_all = canonical_codes()
    canon = canon_all.get(CANON_SUBJECT.get(subject, ""), set()) or canon_all.get(subject, set())

    rows = []
    for s in statements(depth):
        hit = locate_row({"statement_text": s["statement_text"],
                          "printed_code": s["statement_code"]}, records, post, doc)
        printed = hit["matched_printed"] or ""
        verbatim = None
        if printed:
            want = collections.Counter(tokens(printed))
            have: collections.Counter = collections.Counter()
            for page in hit["span_pages"] or ([hit["page"]] if hit["page"] else []):
                have.update(page_tokens[page])
            verbatim = all(have[t] >= n for t, n in want.items())
        topic = topic_of(s["statement_code"], canon) if canon else None
        rows.append({
            "pdf_sha256": sha, "subject": subject,
            "topic_code": s["topic_code"], "statement_code": s["statement_code"],
            "statement_text": s["statement_text"], "level": s["level"],
            "level_basis": s.get("level_basis"),
            "printed_aos": s.get("printed_aos"),
            "page": hit["page"], "bbox": json.dumps(hit["bbox"]) if hit["bbox"] else None,
            "md_line": hit["md_line"],
            "printed_text": printed or None,
            "match": hit["match"],
            "doc_coverage": hit["doc_coverage"],
            "verbatim": verbatim,
            "topic_in_canonical": bool(topic) if canon else None,
            **printed_context(hit.get("md_line"), records, s["statement_code"], printed),
            "canon_subject_slug": CANON_SUBJECT.get(subject) or subject,
        })
    return rows


def dedupe(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Drop exact duplicate rows and return them, so the removal is reported rather than silent.

    KM found one: `design_technology` `B1.1` / `1.1.2` arrives twice, identical in text, code, topic
    and page. Two rows are duplicates only when every identity field AND the located page/line agree,
    so a statement legitimately printed under two topics is kept.
    """
    seen: set[tuple] = set()
    kept: list[dict] = []
    dropped: list[dict] = []
    for r in rows:
        key = tuple(r.get(k) for k in DEDUPE_KEYS)
        if key in seen:
            dropped.append(r)
            continue
        seen.add(key)
        kept.append(r)
    return kept, dropped


def summarise(rows: list[dict], dropped: list[dict] | None = None) -> dict:
    dropped = dropped or []
    return {
        "statements": len(rows),
        "by_match": dict(collections.Counter(r["match"] for r in rows)),
        "by_level": dict(collections.Counter(r["level"] for r in rows)),
        "by_level_basis": dict(collections.Counter(r["level_basis"] for r in rows)),
        "verbatim_failures": sum(1 for r in rows if r["verbatim"] is False),
        "topic_in_canonical": sum(1 for r in rows if r["topic_in_canonical"]),
        "topic_check_applicable": any(r["topic_in_canonical"] is not None for r in rows),
        "printed_heading": sum(1 for r in rows if r.get("printed_heading")),
        "statement_code_qualified": sum(1 for r in rows if r.get("statement_code_qualified")),
        "canon_subject_slug": sum(1 for r in rows if r.get("canon_subject_slug")),
        "duplicate_rows_dropped": len(dropped),
        "duplicates": [{"subject": r["subject"], "statement_code": r["statement_code"],
                        "topic_code": r["topic_code"], "page": r["page"],
                        "statement_text": r["statement_text"]} for r in dropped],
    }


def subject_for_sha(dirpath: Path) -> str | None:
    """The KM subject_head for a stored guide, from its `source.json` file name."""
    src = dirpath / "source.json"
    if not src.exists():
        return None
    record = json.loads(src.read_text(encoding="utf-8")) or {}
    return {v: k for k, v in SUBJECT_GUIDE.items()}.get(record.get("file"))


def process(depth: Path, subject: str, sha: str | None, out_dir: Path) -> dict:
    """Flatten one depth artifact, drop exact duplicates, and write `statements.csv`."""
    layer = depth.parent / "text_layer.jsonl"
    sha = sha or depth.parent.name
    rows, dropped = dedupe(flatten(depth, layer, subject, sha))
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "statements.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarise(rows, dropped)
    (out_dir / "statements_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                     encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--depth", type=Path, default=None)
    ap.add_argument("--layer", type=Path, default=None,
                    help="defaults to text_layer.jsonl beside the depth file")
    ap.add_argument("--subject", default=None)
    ap.add_argument("--sha", default=None, help="defaults to the sha from the depth file's directory")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--all", action="store_true",
                    help="re-run every stored depth.json (the KM re-run: headings, qualified codes, "
                         "canon slug, duplicate removal)")
    ap.add_argument("--date", default="2026-09-17")
    args = ap.parse_args()

    if args.all:
        base = OUT_ROOT / args.date / REQUEST
        depths = sorted(base.glob("*/depth.json"))
        totals = collections.Counter()
        dropped_all: list[dict] = []
        for depth in depths:
            subject = subject_for_sha(depth.parent)
            if not subject:
                print(f"skip {depth.parent.name}: no subject_head for its source file")
                continue
            summary = process(depth, subject, depth.parent.name, depth.parent)
            totals["statements"] += summary["statements"]
            totals["dropped"] += summary["duplicate_rows_dropped"]
            totals["headings"] += summary["printed_heading"]
            totals["qualified"] += summary["statement_code_qualified"]
            dropped_all += summary["duplicates"]
            print(f"{subject:46} {summary['statements']:5} statements | heading "
                  f"{summary['printed_heading']:5} | qualified code "
                  f"{summary['statement_code_qualified']:5} | dup {summary['duplicate_rows_dropped']}")
        print(f"\ntotal {totals['statements']} statements across {len(depths)} depth artifacts; "
              f"printed_heading {totals['headings']}; qualified codes {totals['qualified']}; "
              f"duplicates dropped {totals['dropped']}")
        for d in dropped_all:
            print(f"  dropped duplicate: {d['subject']} {d['statement_code']} "
                  f"(topic {d['topic_code']}, page {d['page']})")
        return

    if not args.depth or not args.subject:
        raise SystemExit("--depth and --subject are required unless --all is given")
    out_dir = args.out or args.depth.parent
    summary = process(args.depth, args.subject, args.sha, out_dir)
    print(f"{args.subject}: {summary['statements']} statements "
          f"(duplicates dropped {summary['duplicate_rows_dropped']}) -> {out_dir}/statements.csv")
    print(f"   matches {summary['by_match']}  levels {summary['by_level']}  "
          f"verbatim failures {summary['verbatim_failures']}  "
          f"qualified codes {summary['statement_code_qualified']}")


if __name__ == "__main__":
    main()