#!/usr/bin/env python3
"""Depth extractor for IB DP History (2028) — grammar mode 3 (prose + bold key ideas).

Extracts:
  - 3 syllabus-area units (Focused study both / Thematic study both / Regional study HL),
    each with its option list and structure note as the unit body
  - the four specified historical concepts: definition + three conceptual understandings
    each (the `understandings` payload, concept-linked)
  - focused-study source skills (bold-led bullets under 'Developing skills')

Parked refinements (recorded in the I&S wave anchor): thematic inquiry-question tables
(4 IQ x 4 lines of inquiry per option), regional inquiry topics, AO-alignment enrichment.

Usage:
    poetry run python scripts/standards/ib_guide_extract_history.py \
        --guide data/output/markdown/ib_guides/history_2028.md \
        --out data/output/ib_native/history/depth.json
"""
import argparse
import json
import pathlib
import re

CONCEPTS = ["Cause and consequence", "Continuity and change", "Perspectives", "Significance"]
UNITS = [
    (1, "# Focused study", "Focused study", "both"),
    (2, "# Thematic study", "Thematic study", "both"),
    (3, "# Regional study (HL only)", "Regional study", "HL"),
]
FURNITURE = re.compile(r"^(\d{1,3}|History guide|---|Syllabus content|Syllabus|Introduction|Figure \d+.*)$")


def clean(lines):
    return [l.strip() for l in lines if l.strip() and not FURNITURE.match(l.strip())]


def collect_bullets(lines):
    """• bullets with wrapped (possibly bold-fragmented) continuation lines."""
    out = []
    for ln in lines:
        if ln in ("•", "▪"):
            out.append("")
        elif out and not ln.startswith("#"):
            out[-1] = re.sub(r"\s+", " ", out[-1] + " " + ln.strip("*")).strip()
    return [b for b in out if b]


def extract_concepts(lines):
    """Concept blocks merge across page breaks (headers repeat). Definition prose
    until 'Conceptual understandings'; then bullets."""
    blocks = {c: {"definition": [], "understandings": []} for c in CONCEPTS}
    current, mode = None, None
    for ln in lines:
        bare = ln.strip("*").strip()
        # real per-concept headers are bold; the intro lists the names as plain bullets
        if ln.startswith("**") and bare in CONCEPTS:
            current, mode = blocks[bare], None
            continue
        if current is None:
            continue
        if bare == "Definition":
            mode = "def"
            continue
        if bare == "Conceptual understandings":
            mode = "cu"
            continue
        if ln in ("•", "▪") and mode is None:
            mode = "cu"  # page-break resume: bullets after a repeated header are CUs
        if mode == "def" and not ln.startswith("#"):
            current["definition"].append(bare)
        if mode == "cu":
            if ln in ("•", "▪"):
                current["understandings"].append("")
            elif current["understandings"] and not ln.startswith("#"):
                current["understandings"][-1] = re.sub(
                    r"\s+", " ", current["understandings"][-1] + " " + bare).strip()
    out = []
    for c in CONCEPTS:
        b = blocks[c]
        out.append({"concept": c,
                    "definition": re.sub(r"\s+", " ", " ".join(b["definition"])).strip(),
                    "understandings": [u for u in b["understandings"] if u]})
    return out


def extract_unit(lines, title, level, number):
    """Option list = first bullet run; lead = bold sentence before it; structure
    note = bold lines shortly after the options."""
    body_lines = clean(lines[:60])
    lead, options, post = "", [], []
    i = 0
    while i < len(body_lines) and body_lines[i] not in ("•", "▪"):
        lead += " " + body_lines[i].strip("*")
        i += 1
    while i < len(body_lines):
        ln = body_lines[i]
        if ln.startswith("#"):
            break
        if ln in ("•", "▪"):
            options.append("")
        elif options and not ln.startswith("**"):
            options[-1] = re.sub(r"\s+", " ", options[-1] + " " + ln).strip()
        elif ln.startswith("**"):
            post = body_lines[i:i + 8]
            break
        i += 1
    note = re.sub(r"\s+", " ", " ".join(l.strip("*") for l in post)).strip()
    return {"number": number, "title": title, "level": level,
            "lead": re.sub(r"\s+", " ", lead).strip(),
            "options": [o for o in options if o], "structure_note": note}


def extract_skills(lines):
    """'Developing skills through the focused study' — bold-led bullets."""
    start = next((i for i, l in enumerate(lines)
                  if l.strip().startswith("## Developing skills")), -1)
    if start < 0:
        return []
    seg = clean(lines[start + 1:start + 60])
    end = next((i for i, l in enumerate(seg) if l.startswith("##")), len(seg))
    return collect_bullets(seg[:end])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    raw = pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " ")
    lines = [l.rstrip() for l in raw.splitlines()]

    def find(header, start=0):
        for i in range(start, len(lines)):
            if lines[i].strip() == header:
                return i
        raise SystemExit(f"anchor not found: {header}")

    # concepts: from '# Concepts' to '# Syllabus content' second occurrence region
    ci = find("# Concepts")
    cj = next(i for i in range(ci, len(lines)) if lines[i].strip() == "# Focused study")
    concepts = extract_concepts(clean(lines[ci:cj]))

    units = []
    skills = []
    bounds = [(find(h), n, t, lv) for n, h, t, lv in UNITS]
    bounds.append((find("# Historical investigation"), None, None, None))
    for k in range(3):
        i, n, t, lv = bounds[k]
        seg = lines[i + 1:bounds[k + 1][0]]
        units.append(extract_unit(seg, t, lv, n))
        if n == 1:
            skills = extract_skills(seg)

    depth = {"subject": "history", "units": units, "concepts": concepts,
             "focused_study_skills": skills}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
    n_u = sum(len(c["understandings"]) for c in concepts)
    print(f"wrote {out}: {len(units)} units "
          f"({'/'.join(str(len(u['options'])) for u in units)} options), "
          f"{len(concepts)} concepts with {n_u} understandings, {len(skills)} skills")


if __name__ == "__main__":
    main()
