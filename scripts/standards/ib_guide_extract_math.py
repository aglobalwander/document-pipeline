#!/usr/bin/env python3
"""Depth extractor for DP Mathematics 2021 (Analysis & Approaches, Applications &
Interpretation) — both share the format.

Per '# Topic N: Title': a '## Concepts' block with 'Suggested concepts embedded in
this topic:' (concept list) and 'Content-specific conceptual understandings:' (• bullets
= understandings, with an 'AHL' sub-run). Units = the 5 topics.

Usage:
    poetry run python scripts/standards/ib_guide_extract_math.py \
        --guide data/output/markdown/ib_guides/mathematics_aa_2021.md --subject math_aa \
        --out data/output/ib_native/math_aa/depth.json
"""
import argparse
import json
import pathlib
import re

TOPIC = re.compile(r"^# Topic (\d): (.+)$")
FURNITURE = re.compile(r"^(\d{1,3}|Mathematics.* guide|---|Syllabus(?: content)?|Syllabus)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    raw = pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " ")
    lines = raw.splitlines()

    # topic bounds
    bounds = [(i, TOPIC.match(l.strip())) for i, l in enumerate(lines) if TOPIC.match(l.strip())]
    units = []
    for idx, (li, m) in enumerate(bounds):
        stop = bounds[idx + 1][0] if idx + 1 < len(bounds) else len(lines)
        seg = [l.strip() for l in lines[li + 1:stop]]
        concepts, understandings = [], []
        mode, hl = None, False
        for s in seg:
            if not s or FURNITURE.match(s):
                continue
            low = s.strip("*").lower()
            if low.startswith("suggested concepts embedded"):
                mode = "concepts"
                continue
            if low.startswith("content-specific conceptual understandings"):
                mode, hl = "u", False
                continue
            if low.startswith("essential understanding"):
                mode = None
                continue
            if s.strip("*").strip() == "AHL" and mode == "u":
                hl = True
                continue
            if s.startswith("## SL content") or s.startswith("## AHL"):
                mode = None
                continue
            if mode == "concepts":
                # 'Generalization, representation, modelling, ...' (may include 'AHL: x, y')
                txt = s.strip("*").replace("AHL:", ",").strip(" .")
                concepts.extend(c.strip().lower() for c in txt.split(",") if c.strip())
                continue
            if mode == "u":
                if s == "•":
                    understandings.append({"statement": "", "hl_only": hl})
                elif understandings and not s.startswith(("#", "**", "AHL")):
                    understandings[-1]["statement"] = re.sub(
                        r"\s+", " ", understandings[-1]["statement"] + " " + s.strip("*")).strip()
        understandings = [u for u in understandings if u["statement"]]
        concepts = list(dict.fromkeys(c for c in concepts if c and len(c) < 30))
        units.append({"number": int(m.group(1)), "title": m.group(2).strip(),
                      "concepts": concepts, "understandings": understandings})

    depth = {"subject": args.subject, "units": units}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
    n_u = sum(len(u["understandings"]) for u in units)
    all_concepts = sorted({c for u in units for c in u["concepts"]})
    print(f"wrote {out}: {len(units)} topics, {n_u} understandings; "
          f"concepts: {all_concepts}")


if __name__ == "__main__":
    main()
