#!/usr/bin/env python3
"""R3: the 315 NCAS residual rows, read from the pages — with every tolerance labelled.

KM's request (2026-09-18, R3) wants, per row, *the printed code or text with page and bbox*. KM has
already shown this is a join for 292 of the 315 by joining the substrate with a symmetric normaliser;
this computes it independently, from the request file and the substrate, so the two agree by
measurement rather than by reuse. Where they cannot agree the row is a notation or grain question, and
those are **KM's rulings**, so the near-form evidence is returned and the row is flagged rather than
resolved here.

Tolerances, named so no ruling is made silently:
  exact              the printed form, case- and space-insensitive
  normalised         after stripping a leading `Word: ` label prefix, parens, a trailing sub-item
                     letter and a trailing period (the four key defects KM measured in its own file)
  near_form          a printed form of the same family that differs by notation or grain; returned as
                     evidence for a ruling, never as a match
  derived_prefix     a `MU-T:` derived strand prefix (Ruling A family) — not a miss
  no_printed_code    nothing of the family prints; the region read says what does

Usage:
    poetry run python scripts/standards/km_r3_residual_read.py [--date 2026-09-17]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from km_text_layer import OUT_ROOT

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
ROWS = KM / "pipeline_requests_2026-09-18/r3_ncas_315_residual.csv"
RESIDUE_FROM = KM / "ncas_315_join/r3_substrate_join.csv"
REQUEST = "p2_ncas_at_a_glance"
FIELDS = ["native_uuid", "title_or_code", "cause_group", "status", "rule", "printed_form",
          "documents", "page", "bbox", "evidence"]


def exact_key(value) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def normalised(value) -> str:
    """KM's four key defects: label prefix, parens, trailing sub-item letter, trailing period."""
    text = str(value or "").strip()
    # Strip a label prefix only when it is a label, not a discipline code: `Dance: DA:...` ->
    # `DA:...`, while `TH: Re7.1.I.` keeps its `TH:`. Stripping any `Word: ` prefix made the
    # printed spacing form lose its discipline and score as unprinted.
    text = re.sub(r"^(?!(?:TH|MA|MU|VA|DANCE):)[A-Za-z]{3,}:\s+", "", text)
    text = text.strip("()")
    # Trailing sub-item letter, space-separated, with or without the printed period that follows it:
    # `DA:Re8.1.III a.` -> `DA:Re8.1.III`. The period is the whole defect — requiring the letter to sit
    # at end-of-string left the most common printed form (`...a.`) unstripped, so the key stayed
    # asymmetric in exactly the way KM measured one layer up.
    #   Applied tail-first in a loop because a printed cell can stack tails; one pass leaves the second.
    while True:
        stripped = re.sub(r"\s+[a-e]\.?\s*$", "", text)
        if stripped == text:
            break
        text = stripped
    # ...and attached to its code, which is how the printed cells carry it: `MU:Re7.1.3a` -> `MU:Re7.1.3`.
    # Without this the read scored those rows as unprinted, which is the same asymmetric-key defect KM
    # found in its own first pass, one layer down.
    text = re.sub(r"(?<=\d)[a-e]\.?$", "", text)
    text = text.rstrip(".")
    return exact_key(text)


def family_key(value) -> str:
    """Loose family form for near-form evidence: hyphens and the item number are dropped.

    `TH:Cr2.1.I` and the printed `TH:Cr2-I.` reduce to the same string, which is exactly the notation
    question KM has to rule on — so this is used only to find candidates, never to claim a match.
    """
    text = normalised(value)
    text = text.replace("-", ".").replace("..", ".")
    text = re.sub(r"\.1\.", ".", text)               # `.1` item number after the process
    return text.rstrip(".")


def load_substrate(base: Path) -> tuple[dict, list[dict]]:
    index = {}
    with (base / "ncas_code_source_index.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            index.setdefault(exact_key(row["printed_code"]), row)
    theatre = list(csv.DictReader((base / "theatre_printed_codes.csv").open(newline="", encoding="utf-8")))
    return index, theatre


def read_row(row: dict, index: dict, theatre: list[dict]) -> dict:
    code = (row.get("title_or_code") or "").strip()
    issued = exact_key(code)
    relaxed = normalised(code)
    out = {"native_uuid": row.get("native_uuid", ""), "title_or_code": code,
           "cause_group": row.get("cause_group", ""), "status": "no_printed_code", "rule": "",
           "printed_form": "", "documents": "", "page": "", "bbox": "", "evidence": ""}

    hit = index.get(issued) or index.get(relaxed)
    if hit:
        out.update(status="printed", rule="exact" if issued == exact_key(hit["printed_code"])
                   else "normalised", printed_form=hit["printed_code"],
                   documents=hit["documents"], page=hit["first_page"], bbox=hit["first_bbox"])
        return out

    # A derived strand prefix is a known derivation, not a miss (Ruling A family).
    if issued.startswith("MU-T:"):
        stripped = exact_key("MU:" + code.split(":", 1)[1])
        hit = index.get(stripped)
        out.update(status="derived_prefix", rule="MU-T: prefix dropped",
                   printed_form=hit["printed_code"] if hit else "",
                   documents=hit["documents"] if hit else "", page=hit["first_page"] if hit else "",
                   bbox=hit["first_bbox"] if hit else "",
                   evidence="Ruling A family: the strand prefix is derived, not printed")
        return out

    # Near-form evidence for the two families that need a ruling.
    wanted = family_key(code)
    candidates = [(row["printed_code"], row["first_page"], row["first_bbox"], row["documents"])
                  for row in index.values() if family_key(row["printed_code"]) == wanted]
    if candidates:
        # Anything that reaches this branch is notation by construction: the printed form is the
        # same family and differs only by spacing, a hyphen or the item number. The grain question
        # is the *other* branch, where the printed rows are children of a held parent. The first
        # version guessed from the held code's shape and mislabelled four rows as grain.
        rule = "notation"
        out.update(status="near_form", rule=f"needs_{rule}_ruling",
                   printed_form="; ".join(sorted({c[0] for c in candidates})[:4]),
                   documents=candidates[0][3], page=candidates[0][1], bbox=candidates[0][2],
                   evidence=f"{len(candidates)} printed form(s) in the same family; ruling is KM's")
        return out

    # A held parent whose children print is a grain question.
    parent_children = [row for row in index.values()
                       if normalised(row["printed_code"]).startswith(relaxed)]
    if parent_children:
        out.update(status="near_form", rule="needs_grain_ruling",
                   printed_form="; ".join(sorted({r["printed_code"] for r in parent_children})[:4]),
                   documents=parent_children[0]["documents"], page=parent_children[0]["first_page"],
                   bbox=parent_children[0]["first_bbox"],
                   evidence="the printed rows are children of the held parent; grain ruling is KM's")
        return out

    # Nothing of the family prints: name the region and what the family does print.
    prefix = re.match(r"^([A-Z]+:[A-Za-z]+[0-9.]*)", relaxed)
    family = [row["printed_code"] for row in index.values()
              if prefix and exact_key(row["printed_code"]).startswith(prefix.group(1))]
    out["evidence"] = (f"Theatre prints {len(family)} codes in this family "
                       f"({', '.join(sorted(family)[:6])}) and not the row's own" if family else
                       "no printed form of this family in any returned document")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default="2026-09-17")
    ap.add_argument("--rows", type=Path, default=ROWS)
    ap.add_argument("--residue-from", type=Path, default=RESIDUE_FROM,
                    help="KM's join: only its unresolved rows are evidence here")
    args = ap.parse_args()

    base = OUT_ROOT / args.date / REQUEST
    index, theatre = load_substrate(base)
    rows = list(csv.DictReader(args.rows.open(newline="", encoding="utf-8")))
    # Scoped to KM's residue on purpose. KM's join already resolves 292 of 315 and is the stronger
    # artifact for those; this adds evidence only where its own classification says it cannot join, so
    # nothing here competes with it and nothing is claimed for a row KM resolved.
    unresolved = set()
    if args.residue_from.exists():
        with args.residue_from.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("resolved_by_substrate") or "").strip() == "no":
                    unresolved.add((row.get("label_as_km_holds") or "").strip())
    scoped = [row for row in rows if (row.get("title_or_code") or "").strip() in unresolved] or rows
    out = [read_row(row, index, theatre) for row in scoped]

    with (base / "r3_residual_read.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    by_status = collections.Counter(r["status"] for r in out)
    summary = {
        "rows": len(out), "by_status": dict(by_status),
        "resolved": by_status["printed"],
        "needing_a_ruling": {rule: sum(1 for r in out if r["rule"] == rule)
                             for rule in ("needs_notation_ruling", "needs_grain_ruling")},
        "derived_prefix_family": by_status["derived_prefix"],
        "no_printed_code": by_status["no_printed_code"],
        "substrate": {name: json.loads((base / "substrate_summary.json").read_text(encoding="utf-8"))
                                 ["artifact_sha256"][name] for name in
                      ("ncas_code_source_index.csv", "theatre_printed_codes.csv")},
        "method": "independent join: exact, then KM's four key defects normalised, then near-form evidence",
        "apply_authorized": False,
        "note": "a near form is evidence for a ruling, never a match; admission stays KM's",
    }
    (base / "r3_residual_read_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"rows {len(out)} | {dict(by_status)}")
    print(f"needing a ruling {summary['needing_a_ruling']} | derived prefix "
          f"{summary['derived_prefix_family']} | no printed code {summary['no_printed_code']}")
    for r in out:
        if r["status"] in ("no_printed_code", "near_form"):
            print(f"   {r['status']:16} {r['title_or_code'][:30]:32} {r['rule']:22} | {r['evidence'][:56]}")
    print(f"-> {base}/r3_residual_read.csv")


if __name__ == "__main__":
    main()
