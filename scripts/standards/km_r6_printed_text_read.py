#!/usr/bin/env python3
"""R6: the printed text, with its tokenisation as printed, for KM's 94 space-loss / AP-clipping rows.

KM's request (2026-09-18, R6) wants, per row, *the printed text with its tokenisation as printed,
page and bbox.* The rows are the ones where KM's own text is damaged: spaces lost inside it
(`Social impact of the Great Depression inonecountry in the Americas`) or clipped short, mostly on
the AP side. So the string KM holds cannot be matched literally — the defect is in the string.

What this does instead: it removes **every** non-alphanumeric character from both sides and matches
on that. `inonecountry` and `in one country` both reduce to `inonecountry`, so the row is located,
and what comes back is the guide's **own** text for the lines the row covers, joined as printed,
with the page and the bounding box. A clipped row is a prefix of the printed run, so the same
containment finds it; that direction is reported as `printed_contains_the_row` rather than being
silently treated as equality.

Locating is by page-offset rather than by a fixed line window, so a syllabus bullet that runs to
five or six printed lines is covered exactly and the span is never padded: the covered lines are
those whose own text overlaps the matched range, and the bbox is their union. Every row reports how
many times the string occurs in the document, so a common phrase is visible rather than picked.

No OCR, no model: the PDF's own text layer, written by `km_text_layer.py` from the store by sha256.

Usage:
    poetry run python scripts/standards/km_r6_printed_text_read.py [--date 2026-09-18]
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
ROWS = KM / "pipeline_requests_2026-09-18/r6_dp_spaceloss_and_ap_clipping.csv"
EDITIONS = KM / "dp_canonical/dp_subject_editions.csv"
AP_EDITIONS = Path(__file__).with_name("ap_editions.json")
REQUEST = "r6_dp_spaceloss_ap_clipping"
FIELDS = ["framework", "subject_or_course", "code", "text_as_km_holds_it", "layer_or_blank",
          "guide_file", "guide_sha256", "status", "rule", "printed_text", "printed_tokens",
          "page", "bbox", "occurrences", "unmatched_head", "unmatched_tail", "evidence"]
# A run shorter than this is not treated as the printed text: a handful of characters matches by
# chance across a 400-page course description, and a bare short match would read as a located row.
MIN_RUN = 16
# For a row to be reported as *partially* printed, its longest printed run must be both this long and
# this share of the row. Below either, the run is incidental prose that happens to share the
# characters, and reporting it as the row's printed text would invent a location — the exact failure
# this read exists to avoid. The threshold is a judgement, it is named here, and KM can move it: the
# run's length and fraction are in every `not_in_document` row so the call is visible.
PARTIAL_MIN_CHARS = 40
PARTIAL_MIN_FRACTION = 0.5


def solid(text: str) -> str:
    """Every non-alphanumeric removed.

    This is the whole tolerance for R6. The defect being reported *is* a lost space, so a matcher
    that respects spaces cannot find the row it is asked about: `inonecountry` and `in one country`
    both reduce to `inonecountry`. NFKC first, so the guides' ligatures and full-width characters
    reduce to the same letters as KM's plain text.
    """
    return re.sub(r"[^0-9a-z]", "", unicodedata.normalize("NFKC", text or "").lower())


def tokens(text: str) -> list[str]:
    """Word tokens as printed.

    Control characters are separators, not letters: the AP PDFs' own text layer emits `\\x03` where a
    space belongs (`society\\x03and\\x03culture`), so a split on whitespace alone would count that as
    one token and every token figure this read reports would be wrong.
    """
    return [t for t in re.split(r"[\s\x00-\x1f]+", (text or "").strip()) if t]


def as_printed(text: str) -> str:
    """The guide's text with a space wherever the PDF layer emitted a control character.

    The AP layers carry `\\x03` in place of a space (`electric\\x03and\\x03magnetic`), which is not
    something the guide prints. Returning it verbatim would hand KM a string it cannot use, so control
    characters become spaces and runs of whitespace collapse.
    """
    return re.sub(r"[\s\x00-\x1f]+", " ", text or "").strip()


def build_pages(records: list[dict]) -> dict[int, dict]:
    """Per page: the solid text of the whole page, and each line's offset and solid text in it.

    Matching by offset rather than by a fixed window means a run covering six printed lines is
    reported exactly and a run covering one is not padded up to a window size.
    """
    pages: dict[int, dict] = {}
    for rec in records:
        page = pages.setdefault(rec["page"], {"solid": "", "starts": [], "recs": []})
        page["starts"].append(len(page["solid"]))
        page["recs"].append({**rec, "_solid": solid(rec["text"])})
        page["solid"] += page["recs"][-1]["_solid"]
    return pages


def cover(pno: int, page: dict, at: int, length: int) -> dict:
    """The printed lines whose own text overlaps `[at, at+length)` of the page's solid text.

    A line is atomic, so the printed run returned is the guide's own text for those lines and the
    bbox is their union — never padded to a window size, never cut mid-line.
    """
    end = at + length - 1
    lines = [r for offset, r in zip(page["starts"], page["recs"])
             if r["_solid"] and offset <= end and offset + len(r["_solid"]) - 1 >= at]
    return {
        "page": pno, "lines": len(lines), "recs": lines, "at": at, "length": length,
        "text": " ".join(r["text"] for r in lines),
        "solid": "".join(r["_solid"] for r in lines),
        "bbox": [min(r["bbox"][0] for r in lines), min(r["bbox"][1] for r in lines),
                 max(r["bbox"][2] for r in lines), max(r["bbox"][3] for r in lines)],
    }


def find(needle: str, pages: dict[int, dict], cap: int = 200) -> list[dict]:
    """Every site where the whole row is printed, as the printed lines it covers."""
    hits: list[dict] = []
    for pno in sorted(pages):
        at = pages[pno]["solid"].find(needle)
        while at != -1:
            hit = cover(pno, pages[pno], at, len(needle))
            if hit["lines"]:
                hits.append(hit)
                if len(hits) >= cap:
                    return hits
            at = pages[pno]["solid"].find(needle, at + 1)
    return hits


def longest_run(needle: str, pages: dict[int, dict], min_len: int = MIN_RUN) -> dict | None:
    """The longest run of the row's characters that *is* printed, and where it sits in the row.

    Binary search on the run's length, because "some substring of this length is printed" is
    monotone in the length: a printed run of L characters contains printed runs of every shorter
    length. This is what turns a damaged row from a bare miss into a measured one — the head and the
    tail that are **not** printed are named, so a lost space, a lost interior character
    (`reciprocal` -> `eciprocal`), inserted notation alt-text and a row that is simply not in this
    document are four different results rather than one `not_in_document`.
    """
    ordered = [(pno, pages[pno]["solid"]) for pno in sorted(pages)]
    lo, hi, best = min_len, min(len(needle), 400), None
    while lo <= hi:
        mid = (lo + hi) // 2
        hit = None
        for i in range(len(needle) - mid + 1):
            sub = needle[i:i + mid]
            for pno, text in ordered:
                at = text.find(sub)
                if at != -1:
                    hit = {"start_in_row": i, "length": mid, "page": pno, "at": at}
                    break
            if hit:
                break
        if hit:
            best, lo = hit, mid + 1
        else:
            hi = mid - 1
    return best


def partial_is_a_location(run_length: int, needle_length: int) -> bool:
    """Is the longest printed run substantial enough to be the row's printed text?

    Extracted so the judgement is testable rather than buried in a branch: the read's worst failure
    mode is reporting incidental prose as a location, and this is the single place that decides it.
    """
    return (bool(needle_length)
            and run_length >= PARTIAL_MIN_CHARS
            and run_length / needle_length >= PARTIAL_MIN_FRACTION)


def resolve() -> dict[tuple[str, str], str]:
    """(framework, subject_or_course) -> sha256.

    DP from KM's own `dp_subject_editions.csv`; AP from this repo's `ap_editions.json` keyed
    `ap-<slug>`, which is exactly the slug R6 uses. No alias table and no guessing: a row whose
    document cannot be resolved says so.
    """
    out: dict[tuple[str, str], str] = {}
    with EDITIONS.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[("DP", r["subject"])] = r["source_sha256"]
    packages = json.loads(AP_EDITIONS.read_text(encoding="utf-8"))["packages"]
    for slug, pkg in packages.items():
        out[("AP", slug.removeprefix("ap-"))] = pkg["current_artifact_sha256"]
    return out


def is_contiguous(hay: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(hay):
        return False
    return any(hay[i:i + len(needle)] == needle for i in range(len(hay) - len(needle) + 1))


def read_row(row: dict, shas: dict, cache: dict, pages_cache: dict, files: dict) -> dict:
    out = {k: "" for k in FIELDS}
    out.update({k: row[k] for k in ("framework", "subject_or_course", "code",
                                    "text_as_km_holds_it", "layer_or_blank")})
    sha = shas.get((row["framework"], row["subject_or_course"]), "")
    if not sha:
        out["status"] = "no_source_resolved"
        out["evidence"] = (f"KM's editions table names no document for {row['framework']} "
                           f"{row['subject_or_course']!r}")
        return out
    out["guide_sha256"] = sha
    if sha not in cache:
        base = OUT_ROOT / "2026-09-18" / REQUEST / sha
        cache[sha] = [json.loads(line) for line in
                      (base / "text_layer.jsonl").open(encoding="utf-8")]
        pages_cache[sha] = build_pages(cache[sha])
        files[sha] = json.loads((base / "source.json").read_text(encoding="utf-8"))["file"]
    out["guide_file"] = files[sha]

    needle = solid(row["text_as_km_holds_it"])
    row_toks = tokens(row["text_as_km_holds_it"])
    if not needle:
        out["status"] = "row_carries_no_text"
        return out
    hits = find(needle, pages_cache[sha])
    if not hits:
        run = longest_run(needle, pages_cache[sha])
        if run is None or not partial_is_a_location(run["length"], len(needle)):
            found = f"{run['length']} of {len(needle)}" if run else f"none of {len(needle)}"
            out["status"] = "not_in_document"
            out["rule"] = f"best_printed_run_is_{found}_characters"
            out["occurrences"] = 0
            if run:
                out["page"] = run["page"]
                out["unmatched_head"] = run["start_in_row"]
                out["unmatched_tail"] = len(needle) - run["start_in_row"] - run["length"]
            out["evidence"] = (
                f"the row's {len(row_toks)} tokens are not printed as a run in {out['guide_file']}"
                f"; the longest incidental run is {found} characters, below the "
                f"{PARTIAL_MIN_CHARS}-character / {PARTIAL_MIN_FRACTION:.0%} bar, so no location "
                f"is claimed")
            return out
        hit = cover(run["page"], pages_cache[sha][run["page"]], run["at"], run["length"])
        head = run["start_in_row"]
        tail = len(needle) - run["start_in_row"] - run["length"]
        out.update({
            "status": "printed_partial",
            "rule": f"only_{run['length']}_of_{len(needle)}_characters_are_printed",
            "printed_text": as_printed(hit["text"]),
            "printed_tokens": len(tokens(hit["text"])),
            "page": hit["page"],
            "bbox": hit["bbox"],
            "occurrences": 1,
            "unmatched_head": head,
            "unmatched_tail": tail,
            "evidence": (f"{head} character(s) of the row before the printed run and {tail} after it "
                         f"are not printed in {out['guide_file']};"
                         f" the run is printed on p.{hit['page']}"),
        })
        return out

    best = hits[0]
    printed_toks = tokens(best["text"])
    out.update({
        "status": "printed",
        "rule": ("row_text_is_the_printed_text" if solid(best["text"]) == needle else
                 "row_text_within_one_printed_line" if best["lines"] == 1 else
                 f"row_text_over_{best['lines']}_printed_lines"),
        "printed_text": as_printed(best["text"]),
        "printed_tokens": len(printed_toks),
        "page": best["page"],
        "bbox": best["bbox"],
        "occurrences": len(hits),
        "unmatched_head": 0,
        "unmatched_tail": 0,
    })
    ordering = ("the row's tokens are printed in this order" if is_contiguous(printed_toks, row_toks)
                else "the row's tokens are NOT printed as a contiguous run — spacing or clipping")
    out["evidence"] = (f"row {len(row_toks)} tokens against {len(printed_toks)} in the covered "
                       f"printed lines; {ordering}"
                       + (f"; the string occurs {len(hits)} time(s) in this document"
                          if len(hits) > 1 else ""))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=Path, default=ROWS)
    ap.add_argument("--date", default="2026-09-18")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.rows.open(newline="", encoding="utf-8")))
    shas = resolve()
    cache: dict[str, list[dict]] = {}
    pages_cache: dict[str, dict] = {}
    files: dict[str, str] = {}
    out = [read_row(r, shas, cache, pages_cache, files) for r in rows]

    base = OUT_ROOT / args.date / REQUEST
    with (base / "r6_printed_text_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)

    by_status = collections.Counter(r["status"] for r in out)
    by_framework = collections.Counter((r["framework"], r["status"]) for r in out)
    summary = {
        "rows": len(out),
        "by_status": dict(by_status),
        "by_framework": {f"{fw}/{st}": n for (fw, st), n in sorted(by_framework.items())},
        "located": by_status["printed"] + by_status["printed_partial"],
        "documents": len({r["guide_sha256"] for r in out if r["guide_sha256"]}),
        "tolerances": {
            "matching": ("every non-alphanumeric removed from both sides, so a lost space in the "
                         "row is not a miss"),
            "span": ("the printed lines whose own text overlaps the match, a line being atomic, so "
                     "the run is neither padded nor truncated"),
        },
        # Indexed, not keyed by code: R6 carries 42 codes and 52 blanks, and keying by code alone
        # silently collapses the blank rows and any repeat. That mistake cost us an R5 figure.
        "ambiguous": {f"{r['framework']}/{r['subject_or_course']}#{i}": int(r["occurrences"])
                      for i, r in enumerate(out) if int(r["occurrences"] or 0) > 1},
        "apply_authorized": False,
        "note": ("the printed text comes back as the guide prints it; a row whose tokens are not a "
                 "contiguous run of the printed text says so in `evidence`"),
    }
    (base / "r6_printed_text_read_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"rows {len(out)} | {dict(by_status)}")
    for (fw, st), n in sorted(by_framework.items()):
        print(f"   {fw} {st:26} {n}")
    for r in out:
        if r["status"] != "printed":
            print(f"   {r['status']:18} {r['framework']}/{r['subject_or_course'][:20]:22} "
                  f"{r['text_as_km_holds_it'][:44]}")
    print(f"-> {base}/r6_printed_text_read.csv")


if __name__ == "__main__":
    main()