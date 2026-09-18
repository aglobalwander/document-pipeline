#!/usr/bin/env python3
"""Ruling A applied: match AP rows on the serpentine prose token sequence, notation skipped.

KM ruled (2026-09-18) that AP's notation breaks **adjacency, not presence**: the text layer marks the
notation by font (prose `AktivGrotesk-*` / `Lexia-*`; math and symbols in `MinionPro`, `STIX*`,
`Symbol*`, `EuclidMath*`, `Wingdings`, `ZapfDingbatsITC`, `AppleSymbols`, …), and KM's own test showed
that comparing against prose spans alone changed token membership **not at all** — the same 23 rows at
100% and the same 9 at 80–91%. What the interleaving destroys is the row's tokens being *contiguous*.

So this read walks the document as a **prose token sequence with notation tokens dropped**, and asks
whether the row's tokens form a contiguous run in *that* sequence. Skipping notation when checking
adjacency is the whole change.

Three outcomes, and the second is the one Ruling A predicts:

  printed         the row's tokens are a contiguous run of the prose token sequence
  not_adjacent    every token is present, none is contiguous — presence without adjacency
  not_in_document a token the row holds is printed nowhere, and the missing tokens are named

`tokens_present` / `tokens_total` are reported on every row so presence and adjacency stay separable:
a row that fails with all tokens present is Ruling A's case, and a row that fails with tokens missing
is KM's (the 9 rows at 80–91%, whose absent token KM is picking up).

Re-measured from the layers already delivered. No source acquisition, no re-read.

Usage:
    poetry run python scripts/standards/km_ap_prose_adjacency_read.py [--date 2026-09-18]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

from km_r6_printed_text_read import (REQUEST as R6_REQUEST, ROWS, as_printed, cover, find,  # noqa: E402
                                     longest_run, partial_is_a_location, resolve, solid, tokens)
from km_text_layer import OUT_ROOT

# KM's font families for notation. A span is prose unless one of these matches its font, so an
# unlisted notation family stays in the sequence and can only make a row fail, never pass: the
# tolerance can hide a match but cannot invent one.
NOTATION_FONTS = ("minionpro", "stix", "symbol", "euclidmath", "wingdings", "zapfdingbats",
                  "applesymbols")
REQUEST = "r6_ap_prose_adjacency"
FIELDS = ["subject_or_course", "code", "text_as_km_holds_it", "guide_file", "guide_sha256",
          "status", "rule", "printed_text", "page", "bbox", "tokens_total", "tokens_present",
          "missing_tokens", "missing_head", "missing_tail", "evidence"]


def is_notation(font: str) -> bool:
    return any(n in (font or "").lower() for n in NOTATION_FONTS)


def prose_pages(records: list[dict]) -> tuple[dict[int, dict], list[str]]:
    """Per page, the prose **character** stream with the printed line each stretch came from.

    Three decisions, each named because each is a measurement rather than a fact:

    - **notation dropped**, which is Ruling A: the notation is what breaks adjacency;
    - **line breaks dropped**, because the guides break words across lines (`pho` / `tographs`,
      `Kath` / `erine`), and a token test cannot see a word the layer split;
    - the printed **line** is kept whole for the answer, so KM is handed what the guide prints,
      notation and all, rather than a reconstruction.

    The returned page shape is the one `km_r6_printed_text_read`'s `find` / `cover` / `longest_run`
    already work on, so the ruled matcher reuses the tested machinery instead of a second copy of it.
    """
    pages: dict[int, dict] = {}
    for rec in records:
        prose = [s for s in rec["spans"] if s["text"].strip() and not is_notation(s["font"])]
        page = pages.setdefault(rec["page"], {"solid": "", "starts": [], "recs": []})
        page["starts"].append(len(page["solid"]))
        page["recs"].append({**rec, "_solid": solid(" ".join(s["text"] for s in prose))})
        page["solid"] += page["recs"][-1]["_solid"]
    streams = [pages[p]["solid"] for p in sorted(pages) if pages[p]["solid"]]
    return pages, streams


def read_row(row: dict, shas: dict, cache: dict) -> dict:
    out = {k: "" for k in FIELDS}
    out.update({k: row[k] for k in ("subject_or_course", "code", "text_as_km_holds_it")})
    sha = shas.get(("AP", row["subject_or_course"]), "")
    if not sha:
        out["status"] = "no_source_resolved"
        out["evidence"] = f"KM's editions table names no document for {row['subject_or_course']!r}"
        return out
    out["guide_sha256"] = sha
    if sha not in cache:
        base = OUT_ROOT / "2026-09-18" / R6_REQUEST / sha
        records = [json.loads(line) for line in
                   (base / "text_layer.jsonl").open(encoding="utf-8")]
        source = json.loads((base / "source.json").read_text(encoding="utf-8"))
        cache[sha] = (*prose_pages(records), source["file"])
    pages, streams, out["guide_file"] = cache[sha]

    needle = solid(row["text_as_km_holds_it"])
    row_words = list(dict.fromkeys(w for w in (solid(t) for t in tokens(row["text_as_km_holds_it"]))
                                   if w))
    if not needle:
        out["status"] = "row_carries_no_text"
        return out

    missing = [w for w in row_words if not any(w in stream for stream in streams)]
    out["tokens_total"] = len(row_words)
    out["tokens_present"] = len(row_words) - len(missing)
    if missing:
        out["missing_tokens"] = "; ".join(missing)[:300]

    hits = find(needle, pages)
    if hits:
        best = hits[0]
        out.update({
            "status": "printed", "rule": "the_row_is_contiguous_in_the_prose_stream",
            "printed_text": as_printed(best["text"]), "page": best["page"], "bbox": best["bbox"],
            "evidence": (f"{len(needle)} characters contiguous over {best['lines']} printed line(s) "
                         f"once notation is skipped"),
        })
        return out

    run = longest_run(needle, pages)
    if run is not None and partial_is_a_location(run["length"], len(needle)):
        hit = cover(run["page"], pages[run["page"]], run["at"], run["length"])
        out.update({
            "status": "printed_partial",
            "rule": f"only_{run['length']}_of_{len(needle)}_characters_are_printed",
            "printed_text": as_printed(hit["text"]), "page": hit["page"], "bbox": hit["bbox"],
            "evidence": f"the longest printed run is {run['length']} of {len(needle)} characters",
        })
        return out

    if not missing:
        out.update({
            "status": "not_adjacent", "rule": "every_word_is_present_and_none_is_contiguous",
            "evidence": (f"all {len(row_words)} of the row's words are printed in "
                         f"{out['guide_file']}, and the row is not contiguous even with notation "
                         f"skipped — presence without adjacency, which is Ruling A's case"),
        })
        return out

    out.update({
        "status": "not_in_document", "rule": f"{len(missing)}_word(s)_are_printed_nowhere",
        "evidence": (f"{len(missing)} of {len(row_words)} words are printed nowhere in "
                     f"{out['guide_file']}: {out['missing_tokens'][:110]}"),
    })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=Path, default=ROWS)
    ap.add_argument("--date", default="2026-09-18")
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(args.rows.open(newline="", encoding="utf-8"))
            if r["framework"] == "AP"]
    shas = resolve()
    cache: dict[str, tuple] = {}
    out = [read_row(r, shas, cache) for r in rows]

    base = OUT_ROOT / args.date / REQUEST
    base.mkdir(parents=True, exist_ok=True)
    with (base / "r6_ap_prose_adjacency_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)

    by_status = collections.Counter(r["status"] for r in out)
    presence = collections.Counter(
        "all_tokens_present" if r["tokens_total"] and r["tokens_present"] == r["tokens_total"]
        else "tokens_missing" for r in out if r["status"] != "no_source_resolved")
    summary = {
        "rows": len(out),
        "by_status": dict(by_status),
        "presence": dict(presence),
        "by_subject": {s: dict(collections.Counter(r["status"] for r in out
                                                   if r["subject_or_course"] == s))
                       for s in sorted({r["subject_or_course"] for r in out})},
        "notation_fonts": list(NOTATION_FONTS),
        "method": ("the row's tokens against the document's prose token sequence, notation spans "
                   "dropped, adjacency checked on that sequence"),
        "re_measured_from": f"data/output/km_requests/2026-09-18/{R6_REQUEST}/",
        "apply_authorized": False,
        "note": ("presence and adjacency are reported separately: `not_adjacent` means every token is "
                 "printed and none is contiguous, which is Ruling A's case"),
    }
    (base / "r6_ap_prose_adjacency_read_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"rows {len(out)} | {dict(by_status)} | presence {dict(presence)}")
    for r in out:
        if r["status"] != "printed":
            print(f"   {r['status']:16} {r['subject_or_course'][:26]:28} "
                  f"{r['tokens_present']}/{r['tokens_total']} tokens | {r['missing_tokens'][:44]}")
    print(f"-> {base}/r6_ap_prose_adjacency_read.csv")


if __name__ == "__main__":
    main()