#!/usr/bin/env python3
"""R5: for each of KM's 267 derived DP codes, the printed string it stands for.

KM's request (2026-09-18, R5) wants, per row, *the printed string the code stands for, with page and
bbox; where the guide prints no string for it, an explicit not_printed with the region read.*

KM built the mapping the evidence it held supports — `dp_code_to_printed.csv`, 104 of 371 rows, on
`label == printed_text` for the enumerated printed units. Its residue is 267 rows and it read
chemistry as **0 of 32**, because the guide prints `Structure 1.1—Introduction to the particulate
nature of matter` where the canon holds `Introduction to the particulate nature of matter`. That is
not a lookup failure: the printed string is there, carrying a section prefix the label omits.

The same reason hides the other subjects. The text layer is one record per printed **line**, and these
guides wrap a heading or a table cell across lines: Dance prints `AO1.` and `Knowledge and
understanding` as two lines on p.17; Psychology prints `Animal research/animal` then wraps to
`models`; Music's roles print as a row of single words. A per-line equality test cannot see any of
those, which is why this read matches on **tokens over a window of consecutive lines**.

Tolerances, named so no ruling is made silently:

  printed           the label's tokens are printed on one line (allowing a leading section or AO
                    prefix the label omits, e.g. `Structure 1.1—` or `AO1.`)
  printed_wrapped   the label's tokens are printed across consecutive lines — the guide's own wrap
  not_printed       no window of any size carries the label; the row gets the region read instead

Every row reports `occurrences` (how many windows carry the label) and `heading` (whether the best
window is bold or set larger than body text), because a two-word label such as `Identity` occurs in
prose as well as in a heading and KM has to see which one this is. Ranking prefers a standalone
heading over prose and the first page over later ones; it never discards the others.

For a `not_printed` row the region read walks the canon's own `parent_code` chain from
`dp_canonical.csv` to the nearest ancestor whose own label this read locates, and reports that as the
region with its page and bbox. That is what makes the grain difference visible: it shows the printed
heading the row sits under, rather than reporting an absence.

No OCR, no model: the PDF's own text layer, written by `km_text_layer.py` from the store by sha256.

Usage:
    poetry run python scripts/standards/km_dp_printed_read.py [--date 2026-09-18]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import unicodedata
from pathlib import Path

from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
ROWS = KM / "pipeline_requests_2026-09-18/r5_dp_printed_strings_267.csv"
CANON = KM / "dp_canonical/dp_canonical.csv"
REQUEST = "r5_dp_printed"
MAX_WINDOW = 3
FIELDS = ["subject", "code", "label_as_km_holds_it", "guide_file", "guide_sha256", "status", "rule",
          "printed_form", "page", "bbox", "occurrences", "heading", "lines_used",
          "region_code", "region_label", "region_printed", "region_page", "region_bbox", "evidence"]
# The guides do not agree with each other, or with the labels written from them: Psychology prints
# `behavior` where the canon writes `behaviour`, Dance prints `programme` where a label may carry
# `program`. A closed list, applied only when the label is otherwise unlocatable, and always
# reported as `*_spelling_tolerant` so the tolerance is KM's to accept or reject.
SPELL = {"behaviour": "behavior", "behaviours": "behaviors", "behavioural": "behavioral",
         "organise": "organize", "organised": "organized", "organising": "organizing",
         "recognise": "recognize", "recognised": "recognized", "analyse": "analyze",
         "analysed": "analyzed", "analysing": "analyzing", "centre": "center", "colour": "color",
         "programme": "program", "programmes": "programs", "theatre": "theater", "metre": "meter",
         "defence": "defense", "practise": "practice", "labour": "labor", "favour": "favor"}


def norm(tok: str) -> str:
    tok = unicodedata.normalize("NFKC", tok).replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"[^0-9a-z]", "", tok.lower())


def tokens(text: str) -> list[str]:
    """Word tokens, normalised. Split on the separators the guides actually print."""
    return [t for t in (norm(w) for w in re.split(r"[\s/\u2013\u2014\u2012-]+", text or "")) if t]


def variant(tok: str) -> str:
    """A token under the publisher's own spelling drift, from the closed list above."""
    return SPELL.get(tok, tok)


def contains(hay: list[str], needle: list[str]) -> bool:
    """`needle` as a contiguous token run inside `hay`."""
    if not needle or len(needle) > len(hay):
        return False
    first = needle[0]
    for i, t in enumerate(hay):
        if t == first and hay[i:i + len(needle)] == needle:
            return True
    return False


def span(records: list[dict], i: int, j: int, needle: list[str], spelling: bool) -> dict:
    """The printed run of lines `i..j`, with the flags the ranking needs."""
    run = records[i:j + 1]
    line = tokens(records[i]["text"])
    return {
        "start": i, "end": j, "page": records[i]["page"], "window": j - i + 1,
        "bbox": [min(r["bbox"][0] for r in run), min(r["bbox"][1] for r in run),
                 max(r["bbox"][2] for r in run), max(r["bbox"][3] for r in run)],
        "text": " ".join(r["text"] for r in run),
        "heading": any(any(s["bold"] or s["size"] >= 12.5 for s in r["spans"]) for r in run
                       if r["spans"]),
        "spelling": spelling,
        "exact_line": i == j and line == needle,
        "standalone": i == j,
    }


def covering(records: list[dict], needle: list[str], spelling: bool) -> list[dict]:
    """Every minimal printed span whose tokens carry the label, one per starting line.

    Extending from a start line and stopping at the first containment returns the **tightest** span
    that prints the label — so the reported string is the label's own printed run, not a window
    padded with the lines around it. A span never crosses a page.
    """
    out: list[dict] = []
    for i in range(len(records)):
        toks: list[str] = []
        for j in range(i, min(i + MAX_WINDOW, len(records))):
            if records[j]["page"] != records[i]["page"]:
                break
            toks += [variant(t) if spelling else t for t in tokens(records[j]["text"])]
            if contains(toks, needle):
                out.append(span(records, i, j, needle, spelling))
                break
    return out


def locate(label: str, records: list[dict]) -> dict:
    """The span that prints the label, preferring the string the code *stands for*.

    Ranked so a heading or a table cell that **is** the label beats prose that merely contains its
    words: an exact standalone line first, then any standalone line, then a wrapped run; then a
    heading; then the tightest run; then the earlier page. The span count is reported so a two-word
    label that also occurs in body text is visible rather than silently picked. Spelling tolerance is
    a second pass, tried only when the label is otherwise unlocatable, and it is named in `rule`.
    """
    needle = tokens(label)
    found = covering(records, needle, spelling=False)
    tolerant = False
    if not found:
        found = covering(records, [variant(t) for t in needle], spelling=True)
        tolerant = bool(found)
    if not found:
        return {"status": "not_printed", "rule": "no_span_carries_the_label", "occurrences": 0}
    best = min(found, key=lambda w: (not w["exact_line"], not w["standalone"], not w["heading"],
                                     w["window"], w["page"], w["start"]))
    rule = ("label_is_the_printed_line" if best["exact_line"] else
            "label_on_one_printed_line" if best["standalone"] else
            f"label_over_{best['window']}_printed_lines")
    if tolerant:
        rule += "_spelling_tolerant"
    return {
        "status": "printed" if best["standalone"] else "printed_wrapped",
        "rule": rule,
        "printed_form": best["text"],
        "page": best["page"],
        "bbox": best["bbox"],
        "occurrences": len(found),
        "heading": best["heading"],
        "lines_used": best["window"],
        "spans": found,
    }


def load_canon() -> dict[tuple[str, str], dict]:
    with CANON.open(newline="", encoding="utf-8") as fh:
        return {(r["subject"], r["code"]): r for r in csv.DictReader(fh)}


def region(code: str, subject: str, canon: dict, records: list[dict]) -> dict:
    """Walk `parent_code` upward to the nearest ancestor whose own label this read locates."""
    seen: set[str] = set()
    cur = (canon.get((subject, code)) or {}).get("parent_code") or ""
    while cur and cur not in seen:
        seen.add(cur)
        row = canon.get((subject, cur))
        if row is None:
            return {"region_code": cur, "evidence": f"parent {cur} is not a row in dp_canonical"}
        hit = locate(row["label"], records)
        if hit["status"] != "not_printed":
            return {"region_code": cur, "region_label": row["label"],
                    "region_printed": hit["printed_form"], "region_page": hit["page"],
                    "region_bbox": hit["bbox"],
                    "evidence": f"the region prints {cur!r} as {hit['printed_form']!r} "
                                f"(p.{hit['page']})"}
        cur = row.get("parent_code") or ""
    return {"region_code": cur,
            "evidence": "no ancestor in dp_canonical prints a string this read could locate"}


def load_layer(sha: str, cache: dict) -> list[dict]:
    if sha not in cache:
        path = OUT_ROOT / "2026-09-18" / REQUEST / sha / "text_layer.jsonl"
        cache[sha] = [json.loads(line) for line in path.open(encoding="utf-8")]
    return cache[sha]


def read_row(row: dict, canon: dict, cache: dict) -> dict:
    records = load_layer(row["guide_sha256"], cache)
    hit = locate(row["label_as_km_holds_it"], records)
    out = {k: "" for k in FIELDS}
    out.update({k: row[k] for k in ("subject", "code", "label_as_km_holds_it", "guide_file",
                                    "guide_sha256")})
    out.update({k: hit.get(k, "") for k in ("status", "rule", "printed_form", "page", "bbox",
                                            "occurrences", "heading", "lines_used")})
    if hit["status"] == "not_printed":
        out.update(region(row["code"], row["subject"], canon, records))
        out["evidence"] = ("the label is printed nowhere in this guide; "
                           + (out.get("evidence") or "and no ancestor locates"))
    else:
        pages = sorted({w["page"] for w in hit["spans"]})
        out["evidence"] = (f"printed in {len(hit['spans'])} span(s) across {len(pages)} page(s)"
                           + (f"; pages {', '.join(str(p) for p in pages)}" if len(pages) > 1 else ""))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=Path, default=ROWS)
    ap.add_argument("--date", default="2026-09-18")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.rows.open(newline="", encoding="utf-8")))
    canon = load_canon()
    cache: dict[str, list[dict]] = {}
    out = [read_row(r, canon, cache) for r in rows]

    base = OUT_ROOT / args.date / REQUEST
    with (base / "r5_dp_printed_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)

    by_status = collections.Counter(r["status"] for r in out)
    by_subject = collections.Counter((r["subject"], r["status"]) for r in out)
    summary = {
        "rows": len(out),
        "by_status": dict(by_status),
        "by_subject": {f"{s}/{st}": n for (s, st), n in sorted(by_subject.items())},
        "located": by_status["printed"] + by_status["printed_wrapped"],
        "no_region": {r["code"]: r["evidence"][:90] for r in out
                      if r["status"] == "not_printed" and not r.get("region_code")},
        "ambiguous": {r["code"]: int(r["occurrences"] or 0) for r in out
                      if int(r["occurrences"] or 0) > 3},
        "method": ("token match over windows of 1-3 consecutive printed lines, headings preferred; "
                   "no window crosses a page"),
        "apply_authorized": False,
        "note": ("a located string is the printed form the code stands for, not an authorization to "
                 "retire the derived code; a not_printed row carries the region the guide does print"),
    }
    (base / "r5_dp_printed_read_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"rows {len(out)} | {dict(by_status)}")
    for (s, st), n in sorted(by_subject.items()):
        print(f"   {s:24} {st:16} {n}")
    for r in out:
        if r["status"] == "not_printed":
            print(f"   not_printed {r['subject'][:12]:13} {r['code'][:26]:28} | "
                  f"{(r['region_printed'] or r['region_code'] or r['evidence'])[:52]}")
    print(f"-> {base}/r5_dp_printed_read.csv")


if __name__ == "__main__":
    main()