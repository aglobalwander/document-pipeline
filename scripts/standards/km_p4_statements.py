#!/usr/bin/env python3
"""P4: locate KM's 9,272 reference statements in the 23 DP guides, and audit the editions.

KM's P4 request asks for every statement under each topic as printed, with its printed code, the
topic code from the guide heading, the printed level (SL/HL/AHL), page and bbox, plus the guide's
AOs. KM also supplied `p4_dp_statements_reference.csv` (9,272 rows: printed_code, statement_text,
subject_head, subject_area, code_form, arts_language) so coverage can be measured both ways.

This script answers the part of P4 that needs no per-subject grammar, for all 22 subjects at once:
it locates each reference row in the named guide's own text layer and returns the printed line(s)
with page, bbox and md_line. Nothing is invented: a row that cannot be placed is reported as
`not_located`, and the text returned is the guide's text, never the reference's.

Two audits come with it:

  edition   the reference's stated edition (`subject_area`) against the first-assessment marker read
            from the document itself (`source.json`). A disagreement is recorded as a
            label-versus-marker candidate — the failure KM has already corrected four times (dance
            2015 -> 2013, film 2019 -> 2023) — and is resolved by the coverage result, not assumed:
            if the reference text locates in the named guide, the label is stale; if it does not,
            the canon text is from another edition.
  coverage  how many reference rows were located, per subject, and how the arts/language subjects
            KM flags (`arts_language`) fare — they are the 10 guides with no extractor.

Reads only local files: the KM request folder, `data/output/km_requests/<date>/p4_dp_statements/`
(the text layers written by `km_text_layer.py`) and, for the code check, `dp_canonical.csv`.
No OCR, no model.

Usage:
    poetry run python scripts/standards/km_p4_statements.py --audit
    poetry run python scripts/standards/km_p4_statements.py --locate [--subject Biology]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_row_reads import tokens
from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
REQUESTS = KM / "pipeline_requests_2026-09-17"
REFERENCE = REQUESTS / "p4_dp_statements_reference.csv"
GUIDES = REQUESTS / "p4_dp_guides.csv"
CANONICAL = KM / "dp_canonical/dp_canonical.csv"
REQUEST = "p4_dp_statements"

# subject_head (KM's reference) -> file (KM's guide list). Verified against p4_dp_guides.csv.
SUBJECT_GUIDE = {
    "Biology": "Biology (2025).pdf",
    "Business Management": "Business Management (2024).pdf",
    "Chemistry": "Chemistry (2025).pdf",
    "Computer Science": "Computer Science (2027).pdf",
    "Dance": "Dance (2013).pdf",
    "Design Technology": "Design Technology (2027).pdf",
    "ESS": "ESS (2026).pdf",
    "Economics": "Economics (2024).pdf",
    "Film": "Film (2023).pdf",
    "Global Politics": "Global Politics (2026).pdf",
    "History": "History (2028).pdf",
    "Language ab initio": "Language Ab Initio.pdf",
    "Language B": "Language B (2020).pdf",
    "Language and Literature": "Language and Literature (2026).pdf",
    "Literature": "Literature (2026).pdf",
    "Mathematics Analysis and Approaches": "Mathematics AA (2021).pdf",
    "Mathematics Applications and Interpretation": "Mathematics AI (2021).pdf",
    "Music": "Music (2022).pdf",
    "Physics": "Physics (2025).pdf",
    "Psychology": "Psychology (2027).pdf",
    "SEHS": "SEHS (2026).pdf",
    "Theatre": "Theatre (2024).pdf",
    "Visual Arts": "Visual Arts (2027).pdf",
}
YEAR = re.compile(r"\b(19|20)\d{2}\b")
WINDOW = 3  # records either side of a candidate when a statement spans printed lines


def reference_rows() -> list[dict]:
    with REFERENCE.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def guides_by_file() -> dict[str, dict]:
    with GUIDES.open(newline="", encoding="utf-8") as fh:
        return {r["file"]: r for r in csv.DictReader(fh)}


def layer(sha: str, date: str) -> list[dict]:
    path = OUT_ROOT / date / REQUEST / sha / "text_layer.jsonl"
    if not path.exists():
        raise SystemExit(f"no text layer at {path}; run km_text_layer.py first")
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def source(sha: str, date: str) -> dict:
    path = OUT_ROOT / date / REQUEST / sha / "source.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def index(records: list[dict]) -> dict[str, set[int]]:
    """token -> record ids, for the rarest-token candidate lookup."""
    post: dict[str, set[int]] = collections.defaultdict(set)
    for i, rec in enumerate(records):
        for tok in set(tokens(rec["text"])):
            post[tok].add(i)
    return post


def candidate_ids(post: dict[str, set[int]], toks: list[str]) -> set[int]:
    """Candidates for the rarest token that is actually printed.

    Intersecting the postings of several tokens assumed a statement sits on one printed line. Guides
    wrap statements across two or three lines, so that assumption produced false ``not_located``
    rows; the rarest single token is the selective anchor, and the span check decides the match.
    """
    known = sorted({t for t in toks if t in post}, key=lambda t: len(post[t]))
    if not known:
        return set()
    return set(post[known[0]])


def covers(toks: list[str], rec: dict) -> float:
    have = collections.Counter(tokens(rec["text"]))
    want = collections.Counter(toks)
    hit = sum(min(n, have[t]) for t, n in want.items())
    return hit / sum(want.values())


def spans_all(toks: list[str], records: list[dict], ids: list[int]) -> bool:
    """True when the records in ``ids`` together carry every token of ``toks``."""
    have = collections.Counter(t for i in ids for t in tokens(records[i]["text"]))
    want = collections.Counter(toks)
    return all(have[t] >= n for t, n in want.items())


def span_covers(toks: list[str], records: list[dict], ids: list[int]) -> float:
    """Fraction of ``toks`` carried by the records in ``ids`` together, duplicates respected."""
    have = collections.Counter(t for i in ids for t in tokens(records[i]["text"]))
    want = collections.Counter(toks)
    return sum(min(have[t], n) for t, n in want.items()) / sum(want.values())


def doc_covers(toks: list[str], doc_tokens: collections.Counter) -> float:
    want = collections.Counter(toks)
    return round(sum(min(doc_tokens[t], n) for t, n in want.items()) / sum(want.values()), 2)


# ---------------------------------------------------------------------------------------------
# Printed heading context (also used by ib_depth_to_statements.py)
# ---------------------------------------------------------------------------------------------
# Two printed signals are used, both from the guide and neither inferred:
#   1. a *section-shaped* heading — Physics prints `A.1 Kinematics`, Chemistry prints
#      `Structure 1. Models of the particulate nature of matter` and `Structure 1.1—Introduction…`;
#   2. failing that, a line set larger than the guide's body text, or bold and short.
# The guides' own furniture (hour/level markers, guiding and linking questions) is excluded: in
# Chemistry `Standard level and higher level: 2 hours` is bold and nearer than the real heading, so
# without the exclusion it becomes the "heading" and the qualifier reads `Standard level…`.
SECTION_HEADING = re.compile(
    r"^(?:[A-D]\.\d+\s+\S"                                                    # `A.1 Kinematics`
    r"|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+\d+(?:\.\d+)*[.\u2014\u2013-]\s)"     # `Structure 1. …`
)
FURNITURE = re.compile(r"^(standard level|higher level|additional higher level|guiding question|"
                       r"linking question|assessment|syllabus|time\b)", re.I)
HEADING_MAX_CHARS = 90
BODY_MARGIN = 1.5
LABEL_RE = re.compile(r"^([A-Z][A-Za-z&/'’ -]{1,40}?)\s+(\d+(?:\.\d+)*)")


def body_size(layer: list[dict]) -> float:
    """The guide's body text size: the most common largest-span size on its lines."""
    sizes: collections.Counter = collections.Counter()
    for rec in layer:
        spans = rec.get("spans") or []
        if spans:
            sizes[round(max(s.get("size", 0) for s in spans), 1)] += 1
    return sizes.most_common(1)[0][0] if sizes else 10.0


def _text_of(rec: dict) -> str:
    return (rec.get("text") or "").strip().lstrip("#* ").strip()


def is_section_heading(rec: dict) -> bool:
    text = _text_of(rec)
    return bool(text) and not FURNITURE.match(text) and bool(SECTION_HEADING.match(text))


def is_large_heading(rec: dict, body: float) -> bool:
    text = _text_of(rec)
    if not text or len(text) > HEADING_MAX_CHARS or FURNITURE.match(text):
        return False
    spans = rec.get("spans") or []
    if not spans:
        return False
    size = max(s.get("size", 0) for s in spans)
    if size >= body + BODY_MARGIN:
        return True
    bold = any(s.get("bold") for s in spans)
    return bold and size >= body + 0.5 and len(text.split()) <= 8 and not text.endswith(".")


def headings_above(md_line: int | None, layer: list[dict], count: int = 1) -> list[str]:
    """The nearest printed section headings above a line, nearest first (section-shaped first)."""
    if not md_line:
        return []
    above = [rec for rec in layer if rec["md_line"] < md_line]
    section = [_text_of(rec) for rec in reversed(above) if is_section_heading(rec)]
    if section:
        return section[:count]
    body = body_size(layer)
    return [_text_of(rec) for rec in reversed(above) if is_large_heading(rec, body)][:count]


def printed_qualifier(printed_text: str | None, code: str | None) -> tuple[str | None, str | None]:
    """The section qualifier printed on the row's own line: `Structure 1.1.1—Elements …`.

    Chemistry prints the qualified code inline, which is what KM asked for (`Structure 1.1.1` rather
    than `1.1.1`). Returns the label and the qualified code, or (None, None) when the line does not
    carry one — nothing is invented.
    """
    text = (printed_text or "").strip()
    code = (code or "").strip()
    if not text or not code:
        return None, None
    match = re.match(r"^([A-Z][A-Za-z&/'’ -]{1,40}?)\s+" + re.escape(code) + r"(?![0-9.])", text)
    if not match:
        return None, None
    label = match.group(1).strip()
    return label, f"{label} {code}"


def printed_context(md_line: int | None, layer: list[dict], code: str | None,
                    printed_text: str | None = None) -> dict:
    """`printed_heading`, `section_qualifier` and the qualified code for one located row."""
    heading = next(iter(headings_above(md_line, layer, 1)), None)
    label, qualified = printed_qualifier(printed_text, code)
    if label is None and heading and code:
        # Fall back to the section label the nearest printed heading carries (`Structure 1. Models…`
        # -> `Structure`); a heading that is itself only a code (`A.1 Kinematics`) yields no label.
        match = LABEL_RE.match(heading)
        if match:
            label = match.group(1)
            qualified = f"{label} {code}"
    return {
        "printed_heading": heading,
        "section_qualifier": label,
        "statement_code_qualified": qualified,
    }
def locate_row(row: dict, records: list[dict], post: dict[str, set[int]],
               doc_tokens: collections.Counter | None = None) -> dict:
    toks = tokens(row["statement_text"])
    out = {"match": "not_located", "coverage": 0.0, "doc_coverage": None, "matched_printed": None,
           "md_line": None, "page": None, "bbox": None, "span_pages": None, "code_in_region": False}
    if not toks:
        out["match"] = "empty_statement_text"
        return out

    ids = candidate_ids(post, toks)
    if not ids:
        if doc_tokens is not None:
            out["doc_coverage"] = doc_covers(toks, doc_tokens)
        return out

    windows = {i: list(range(max(0, i - WINDOW), min(len(records), i + WINDOW + 1)))
               for i in sorted(ids)}
    exact = sorted(i for i in ids if spans_all(toks, records, [i]))
    if exact:
        best, span, out["match"], out["coverage"] = exact[0], [exact[0]], "located_exact", 1.0
    else:
        good = [i for i, w in windows.items() if spans_all(toks, records, w)]
        if good:
            best, span = good[0], windows[good[0]]
            out["match"], out["coverage"] = "located_adjacent", 1.0
        else:
            best = max(windows, key=lambda i: span_covers(toks, records, windows[i]))
            span = windows[best]
            out["match"] = "partial"
            out["coverage"] = round(span_covers(toks, records, span), 2)
            if doc_tokens is not None:
                out["doc_coverage"] = doc_covers(toks, doc_tokens)

    span = sorted(set(span))
    out["matched_printed"] = " ".join(records[i]["text"] for i in span)
    out["md_line"] = records[best]["md_line"]
    out["page"] = records[best]["page"]
    out["span_pages"] = sorted({records[i]["page"] for i in span})
    boxes = [records[i]["bbox"] for i in span]
    out["bbox"] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                   max(b[2] for b in boxes), max(b[3] for b in boxes)]
    code = (row.get("printed_code") or "").strip()
    near = " ".join(records[i]["text"]
                    for i in range(max(0, best - 2), min(len(records), best + 3)))
    out["code_in_region"] = bool(code) and code in near
    return out


def years_in(text: str) -> list[int]:
    return [int(m.group(0)) for m in YEAR.finditer(text or "")]


def edition_audit(date: str) -> list[dict]:
    rows = reference_rows()
    guides = guides_by_file()
    rows_by_subject = collections.defaultdict(list)
    for r in rows:
        rows_by_subject[r["subject_head"]].append(r)

    out = []
    for subject, file in SUBJECT_GUIDE.items():
        guide = guides.get(file) or {}
        sha = guide.get("sha256", "")
        src = source(sha, date) if sha else {}
        ref_area = rows_by_subject[subject][0]["subject_area"] if rows_by_subject[subject] else ""
        marker = src.get("edition_marker") or ""
        marker_year = years_in(marker)[-1] if years_in(marker) else None
        ref_years = years_in(ref_area)
        out.append({
            "subject": subject, "file": file, "pdf_sha256": sha,
            "guide_marker": marker or None,
            "marker_resolution_state": src.get("marker_resolution_state"),
            "reference_area": ref_area,
            "reference_years": ref_years,
            "edition_agrees": (marker_year in ref_years) if marker_year and ref_years else None,
            "reference_rows": len(rows_by_subject[subject]),
            "arts_language": rows_by_subject[subject][0]["arts_language"] if rows_by_subject[subject] else None,
        })
    return out


def canonical_codes() -> dict[str, set[str]]:
    """canonical subject slug -> printed codes, from KM's dp_canonical.csv."""
    if not CANONICAL.exists():
        return {}
    with CANONICAL.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        code_col = next((c for c in cols if c.lower() == "code"), None)
        subj_col = next((c for c in cols if c.lower() == "subject"), None)
        if not code_col or not subj_col:
            return {}
        out: dict[str, set[str]] = collections.defaultdict(set)
        for r in reader:
            out[r[subj_col].strip().lower()].add((r[code_col] or "").strip())
    return out


def locate(date: str, only: str | None) -> tuple[list[dict], list[dict]]:
    rows = reference_rows()
    guides = guides_by_file()
    audit = {a["subject"]: a for a in edition_audit(date)}
    out: list[dict] = []
    for subject, file in SUBJECT_GUIDE.items():
        if only and subject != only:
            continue
        sha = (guides.get(file) or {}).get("sha256", "")
        if not sha:
            continue
        records = layer(sha, date)
        post = index(records)
        page_tokens = collections.defaultdict(collections.Counter)
        doc_tokens: collections.Counter = collections.Counter()
        for rec in records:
            page_tokens[rec["page"]].update(tokens(rec["text"]))
            doc_tokens.update(tokens(rec["text"]))
        for r in [x for x in rows if x["subject_head"] == subject]:
            hit = locate_row(r, records, post, doc_tokens)
            printed = hit.pop("matched_printed") or ""
            rec = {
                "pdf_sha256": sha, "file": file, "subject": subject,
                "subject_area": r["subject_area"], "arts_language": r["arts_language"],
                "reference_standard_id": r["standard_id"],
                "printed_code": r["printed_code"], "reference_text": r["statement_text"],
                "code_form": r["code_form"],
                "printed_text": printed,
                "guide_marker": audit[subject]["guide_marker"],
                "edition_agrees": audit[subject]["edition_agrees"],
                "method": "pdf text layer via PyMuPDF; located by printed key and text; no OCR, no model",
                **hit,
                **printed_context(hit.get("md_line"), records, r["printed_code"], printed),
                "canon_subject_slug": CANON_SUBJECT.get(subject),
            }
            if printed:
                want = collections.Counter(tokens(printed))
                have: collections.Counter = collections.Counter()
                for p in (rec["span_pages"] or [rec["page"]]):
                    have.update(page_tokens[p])
                rec["verbatim"] = all(have[t] >= n for t, n in want.items())
            else:
                rec["verbatim"] = None
            out.append(rec)
    return out, list(audit.values())


# subject_head (KM's reference) -> subject slug in KM's dp_canonical.csv.
CANON_SUBJECT = {
    "Biology": "biology", "Business Management": "business_management",
    "Chemistry": "chemistry", "Computer Science": "computer_science", "Dance": "dance",
    "Design Technology": "design_technology", "ESS": "ess", "Economics": "economics",
    "Film": "film", "Global Politics": "global_politics", "History": "history",
    "Language ab initio": "language_ab_initio", "Language B": "language_b",
    "Language and Literature": "language_and_literature", "Literature": "literature",
    "Mathematics Analysis and Approaches": "mathematics_aa",
    "Mathematics Applications and Interpretation": "mathematics_ai",
    "Music": "music", "Physics": "physics", "Psychology": "psychology", "SEHS": "sehs",
    "Theatre": "theatre", "Visual Arts": "visual_arts",
}


def topic_of(code: str, codes: set[str]) -> str | None:
    """Longest canonical code that is a prefix of the printed statement code (the topic it sits under)."""
    best = None
    low = (code or "").strip().lower()
    for c in codes:
        if c and low.startswith(c.lower()) and (best is None or len(c) > len(best)):
            best = c
    return best


DIGITS = re.compile(r"\d+(?:\.\d+)*")


def tolerant_topic_of(code: str, codes: set[str]) -> str | None:
    """Topic match that tolerates the mechanical differences between the two layers.

    Compared on the numeric tail, so the pairs the layers really use still match: `AHL1.10` against
    `AHL 1.10` (spacing), `R1.1` against `Reactivity 1.1` (theme name instead of letter), `A1.1`
    against `1.1.1` (the reference drops the theme letter). Reported alongside the strict result, not
    instead of it, because it is deliberately permissive: a numeric tail can coincide across themes.
    """
    low = (code or "").strip().lower()
    tail = DIGITS.search(low)
    if not tail:
        return None
    want = tail.group(0)
    best = None
    for c in codes:
        m = DIGITS.search((c or "").lower())
        if m and want.startswith(m.group(0)) and (best is None or len(m.group(0)) > len(best)):
            best = c
    return best


def code_check(rows: list[dict]) -> tuple[list[dict], dict]:
    """KM's acceptance asks that each statement's *topic* exist in dp_canonical, not its own code:
    the canonical layer is coarser than the statement set (1,788 rows against 9,272 statements).
    Misses are listed, never coerced."""
    canon = canonical_codes()
    if not canon:
        return [], {"canonical": "unavailable"}
    misses: collections.Counter = collections.Counter()
    stats = collections.Counter()
    for r in rows:
        slug = CANON_SUBJECT.get(r["subject"])
        code = (r["printed_code"] or "").strip()
        codes = canon.get(slug or "", set())
        topic = topic_of(code, codes) if codes else None
        loose = tolerant_topic_of(code, codes) if codes and topic is None else None
        if not slug:
            stats["subject_not_in_canonical"] += 1
        elif not code:
            stats["no_printed_code"] += 1
        elif topic is None and loose is None:
            stats["topic_not_in_canonical_strict_and_tolerant"] += 1
            misses[(r["subject"], code)] += 1
        elif topic is None:
            stats["topic_only_under_tolerant_matching"] += 1
        elif topic.lower() == code.lower():
            stats["statement_is_its_own_topic"] += 1
        else:
            stats["topic_is_a_canonical_row"] += 1
    out = [{"subject": s, "printed_code": c, "rows": n}
           for (s, c), n in sorted(misses.items(), key=lambda kv: (-kv[1], kv[0]))]
    return out, dict(stats)


def summarise(rows: list[dict], audit: list[dict]) -> dict:
    by_subject: dict[str, collections.Counter] = {}
    for r in rows:
        by_subject.setdefault(r["subject"], collections.Counter())[r["match"]] += 1
    loc_pct = {}
    for subj, counts in by_subject.items():
        n = sum(counts.values())
        loc_pct[subj] = round(100 * (counts["located_exact"] + counts["located_adjacent"]) / n, 1)
    diag: collections.Counter = collections.Counter()
    for r in rows:
        if r["match"] != "not_located" or r.get("doc_coverage") is None:
            continue
        c = r["doc_coverage"]
        diag["text_absent_from_the_named_guide (<0.5)" if c < 0.5 else
             "text_mostly_absent (0.5-0.9)" if c < 0.9 else
             "text_present_but_not_contiguous (>=0.9)"] += 1
    return {
        "rows": len(rows),
        "by_match": dict(collections.Counter(r["match"] for r in rows)),
        "by_subject": {k: dict(v) for k, v in sorted(by_subject.items())},
        "located_pct_by_subject": dict(sorted(loc_pct.items())),
        "not_located_diagnosis": dict(diag),
        "arts_language": dict(sorted(collections.Counter(
            f"{r['arts_language']}/{r['match']}" for r in rows).items())),
        "verbatim_failures": [r["reference_standard_id"] for r in rows if r["verbatim"] is False],
        "code_in_region": sum(1 for r in rows if r["code_in_region"]),
        "edition_disagreements": [a["subject"] for a in audit if a["edition_agrees"] is False],
        "edition_unknown": [a["subject"] for a in audit if a["edition_agrees"] is None],
        "method": "pdf text layer via PyMuPDF; located by printed key and text; no OCR, no model",
    }


def summary_markdown(summary: dict, audit: list[dict], misses: list[dict],
                     stats: dict | None = None) -> str:
    kinds = sorted({k for v in summary["by_subject"].values() for k in v})
    out = ["# P4: DP statements located in the named guides", "",
           "**Method:** PDF text layer via PyMuPDF, no OCR and no model. Each reference row is "
           "located in the guide KM named for that subject, by that guide's own text layer. The "
           "text returned is the guide's text, never the reference's.", "",
           "## Coverage", "", f"- reference rows: **{summary['rows']}**", "",
           "| match | rows |", "|---|---:|"]
    out += [f"| {k} | {v} |" for k, v in sorted(summary["by_match"].items())]
    out += ["", "## By subject", "", "| subject | located % | " + " | ".join(kinds) + " |",
            "|---|---:|" + "---:|" * len(kinds)]
    for subj, counts in summary["by_subject"].items():
        out.append(f"| {subj} | {summary['located_pct_by_subject'][subj]}% | "
                   + " | ".join(str(counts.get(k, 0)) for k in kinds) + " |")
    if summary.get("not_located_diagnosis"):
        out += ["", "## Why a row was not located", "",
                "Measured against the whole named guide, so a genuine edition gap is distinguishable "
                "from a matching limit:", "", "| diagnosis | rows |", "|---|---:|"]
        out += [f"| {k} | {v} |" for k, v in sorted(summary["not_located_diagnosis"].items())]
        out += ["", "- **absent from the named guide** — the reference text is not in this document "
                "at all: an edition difference, not an extraction failure.",
                "- **present but not contiguous** — the text is in the guide but does not run as one "
                "printed line or short window (tables, columns, rubric boxes); this is a matching "
                "limit of the method and is reported as such.", ""]
    out += ["", "## Edition label against the printed marker", "",
            "| subject | reference label | marker read from the document | agrees |", "|---|---|---|---|"]
    for a in audit:
        agrees = {True: "yes", False: "**no**", None: "not read"}[a["edition_agrees"]]
        out.append(f"| {a['subject']} | {a['reference_area']} | {a['guide_marker'] or '—'} | {agrees} |")
    out += ["", "A disagreement is a label-versus-marker candidate, not a verdict — KM has already "
            "corrected four such labels (dance 2015→2013, film 2019→2023). The coverage table "
            "decides it per subject: text that locates in the named guide means the label is stale, "
            "text that does not means the canon rows come from another edition. Both are reported, "
            "neither is repaired here.", ""]
    if misses:
        out += ["## Printed statement codes with no canonical topic (listed, not coerced)", "",
                "KM's acceptance is that each statement's *topic* exists in `dp_canonical.csv`, whose "
                "canonical layer is coarser than the statement set (1,788 rows against 9,272 "
                "statements), so a statement code deeper than the canonical one is expected and only "
                "a missing *topic* is a miss.", "",
                "| subject | printed code | rows |", "|---|---|---:|"]
        out += [f"| {m['subject']} | `{m['printed_code']}` | {m['rows']} |" for m in misses[:60]]
        if len(misses) > 60:
            out.append(f"| … | {len(misses) - 60} more | |")
        out.append("")
    if stats:
        out += ["## Topic-code check", "",
                "| outcome | rows |", "|---|---:|"]
        out += [f"| {k} | {v} |" for k, v in sorted(stats.items())]
        out.append("")
    out += ["## Checks", "",
            f"- verbatim failures: **{len(summary['verbatim_failures'])}** (every located text is "
            "re-tokenised against its own page of the same sha)",
            f"- rows whose printed code sits inside the matched region: **{summary['code_in_region']}**",
            f"- edition label disagreements: **{len(summary['edition_disagreements'])}**",
            f"- subjects whose marker could not be read: **{len(summary['edition_unknown'])}**", "",
            "## Status of the four P4 parts", "",
            "- **Statement location (this file):** done for all 22 subjects, from KM's own reference "
            "list, without inventing a grammar per subject.",
            "- **Not yet returned:** the per-subject depth artifacts (topics, printed levels, AOs) "
            "and the coverage-against-the-Hub-export figures per topic, which come from the "
            "extractor reruns (`ib_guide_extract*.py` -> `ib_depth_to_statements.py`).",
            "- **Blocked:** the 10 arts/language subjects have no extractor; KM's reference already "
            "enumerates them (1,554 rows flagged `arts_language=yes`), but what KM counts as a "
            "*statement* there still needs its ruling before 10 grammars are built.", ""]
    return "\n".join(out)


AO = re.compile(r"\bAO\s?(\d)\b")


def aos(date: str) -> list[dict]:
    """The assessment objectives as printed, for every guide — KM asked for these too.

    Bounded and evidence-only: a line is returned when it carries an ``AOn`` marker, verbatim with
    page, bbox and md_line. No section grammar, so a guide that prints its AOs as unnumbered bullets
    (ToK does) yields no rows rather than an invented mapping; that is reported, not filled in.
    """
    guides = guides_by_file()
    out: list[dict] = []
    for subject, file in SUBJECT_GUIDE.items():
        sha = (guides.get(file) or {}).get("sha256", "")
        if not sha:
            continue
        for rec in layer(sha, date):
            found = AO.findall(rec["text"])
            if not found:
                continue
            out.append({
                "pdf_sha256": sha, "file": file, "subject": subject,
                "printed_ao_numbers": sorted({int(n) for n in found}),
                "ao_at_line_start": bool(re.match(r"^\s*AO\s?\d\b", rec["text"])),
                "text": rec["text"], "page": rec["page"], "bbox": rec["bbox"],
                "md_line": rec["md_line"],
                "method": "pdf text layer via PyMuPDF; no OCR, no model",
            })
    return out


def aos_summary(rows: list[dict]) -> dict:
    per = collections.defaultdict(set)
    lines = collections.Counter()
    for r in rows:
        lines[r["subject"]] += 1
        per[r["subject"]].update(r["printed_ao_numbers"])
    return {s: {"ao_numbers": sorted(n) or None, "lines_carrying_an_ao_marker": lines[s]}
            for s, n in sorted(per.items())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--audit", action="store_true", help="write the edition audit only")
    ap.add_argument("--locate", action="store_true", help="locate the reference rows")
    ap.add_argument("--aos", action="store_true", help="return the printed assessment objectives")
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--subject", default=None, help="limit the work to one subject_head")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out_dir = args.out or (OUT_ROOT / args.date / REQUEST)

    if args.aos:
        rows = aos(args.date)
        summary = aos_summary(rows)
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "aos.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        (out_dir / "aos_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                  encoding="utf-8")
        print(f"ao lines {len(rows)} across {len(summary)} subjects")
        for s, v in summary.items():
            print(f"  {s:46} AOs {v['ao_numbers']}  lines {v['lines_carrying_an_ao_marker']}")
        print(f"subjects with no printed AO marker: "
              f"{sorted(set(SUBJECT_GUIDE) - set(summary))}")
        print(f"-> {out_dir}/aos.jsonl, aos_summary.json")
        return

    audit = edition_audit(args.date)
    if args.subject:
        audit = [a for a in audit if a["subject"] == args.subject]
    if not args.locate:
        for a in audit:
            print(f"{a['subject']:46} {str(a['guide_marker']):24} "
                  f"{a['reference_area'][:46]:48} agrees={a['edition_agrees']}")
        print(f"\nedition disagreements: {sum(1 for a in audit if a['edition_agrees'] is False)}"
              f"  unknown: {sum(1 for a in audit if a['edition_agrees'] is None)}"
              f"  reference rows: {sum(a['reference_rows'] for a in audit)}")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "edition_audit.json").write_text(json.dumps(audit, indent=2) + "\n",
                                                    encoding="utf-8")
        return

    rows, _ = locate(args.date, args.subject)
    summary = summarise(rows, audit)
    misses, stats = code_check(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "statements_located.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out_dir / "summary.json").write_text(
        json.dumps({"summary": summary, "topic_code_check": stats, "code_misses": misses,
                    "edition_audit": audit}, indent=2) + "\n", encoding="utf-8")
    (out_dir / "SUMMARY.md").write_text(summary_markdown(summary, audit, misses, stats),
                                        encoding="utf-8")
    print(f"rows {summary['rows']}  matches {summary['by_match']}")
    print(f"edition disagreements {summary['edition_disagreements']}  "
          f"verbatim failures {len(summary['verbatim_failures'])}  topic-code misses {len(misses)}")
    print(f"topic-code check {stats}")
    print(f"-> {out_dir}/statements_located.jsonl, summary.json, SUMMARY.md")


if __name__ == "__main__":
    main()