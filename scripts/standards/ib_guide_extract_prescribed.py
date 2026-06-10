#!/usr/bin/env python3
"""Depth extractor for IB DP guides using the PRESCRIBED-CONTENT grammar
(I&S family: Global Politics 2026; History 2028 expected to follow).

Grammar: units are major '# ' sections; within each, page-linearized 3-column
tables (**Prescribed topic** | prescribed content | supporting details). v1 does
NOT attempt content-vs-supporting column attribution — each prescribed topic
captures all of its bullets/prose as items (honest unit-page fidelity; item-grain
split is a later refinement if CL needs it).

Also extracts: course AOs ('## Title' + bullets in the assessment-objectives
region) and HL inquiry questions ('## Additional questions for research...').

Usage:
    poetry run python scripts/standards/ib_guide_extract_prescribed.py \
        --guide data/output/markdown/ib_guides/global_politics_2026.md \
        --subject global_politics --out data/output/ib_native/global_politics/depth.json
"""
import argparse
import json
import pathlib
import re

SPECS = {
    "global_politics": {
        "units": [
            (1, r"^# Core topics: Understanding power and global", "Core topics: Understanding power and global politics", "both"),
            (2, r"^# Thematic studies: Rights and justice", "Thematic study: Rights and justice", "both"),
            (3, r"^# Thematic studies: Development and sustainability", "Thematic study: Development and sustainability", "both"),
            (4, r"^# Thematic studies: Peace and conflict", "Thematic study: Peace and conflict", "both"),
            (5, r"^## HL extension topic areas: Global political challenges", "HL extension: Global political challenges", "HL"),
        ],
        "unit_end": r"^## Additional questions for research",
        "ao_start": r"objectives \(AOs\)\.",
        "ao_end": r"^# Assessment objectives in practice",
        "questions_start": r"^## Additional questions for research",
        "questions_end": r"^# ",
        "furniture": r"^(\d{1,3}|Global politics guide|---|Syllabus content|Figure \d+.*)$",
    },
}


def parse_aos(lines):
    aos, current = [], None
    for ln in lines:
        m = re.match(r"^## (.+)$", ln)
        if m:
            current = {"code": f"AO{len(aos) + 1}", "title": m.group(1).strip(), "bullets": []}
            aos.append(current)
            continue
        if current is None:
            continue
        if ln == "•":
            current["bullets"].append("")
        elif current["bullets"] and not ln.startswith(("#", "**")):
            current["bullets"][-1] = re.sub(r"\s+", " ", current["bullets"][-1] + " " + ln).strip()
        elif not current["bullets"] and ln and not ln.startswith(("#", "**")):
            current.setdefault("lead", "")
            current["lead"] = re.sub(r"\s+", " ", current.get("lead", "") + " " + ln).strip()
    return aos


def parse_questions(lines):
    out, category = [], ""
    for ln in lines:
        m = re.match(r"^\*\*(\d+\.\s*.+?)\*\*$", ln)
        if m:
            category = m.group(1).strip()
            continue
        if ln == "•":
            out.append({"text": "", "category": category})
        elif out and not out[-1]["text"].endswith("?") and not ln.startswith(("#", "**")):
            out[-1]["text"] = re.sub(r"\s+", " ", out[-1]["text"] + " " + ln).strip()
    return [q for q in out if q["text"].endswith("?")]


def parse_unit_topics(lines, furniture):
    """Bold headers (joined across lines) start prescribed topics; everything under
    a topic (bullets + prose) becomes its items."""
    topics, current, bold_buf, item_open = [], None, [], False
    header_skip = re.compile(r"^(Prescribed topic|Prescribed content|Supporting details.*|examples?\))$")
    for ln in lines:
        if not ln or re.match(furniture, ln):
            continue
        if ln.startswith("**") and ln.endswith("**"):
            text = ln.strip("*").strip()
            if header_skip.match(text):
                bold_buf = []
                continue
            bold_buf.append(text)
            item_open = False
            continue
        if bold_buf:
            title = re.sub(r"\s+", " ", " ".join(bold_buf)).strip()
            current = {"title": title, "contested": title.lower().startswith("contested"),
                       "items": []}
            topics.append(current)
            bold_buf = []
        if current is None:
            continue
        if ln in ("•", "▪"):
            current["items"].append("")
            item_open = True
        elif item_open and current["items"]:
            current["items"][-1] = re.sub(r"\s+", " ", current["items"][-1] + " " + ln).strip()
        else:
            # prose (supporting details) — keep as its own item
            if current["items"] and current["items"][-1].endswith((".", ":")) is False \
                    and current["items"] and not item_open:
                current["items"][-1] = re.sub(r"\s+", " ", current["items"][-1] + " " + ln).strip()
            else:
                current["items"].append(ln)
                item_open = False
    for t in topics:
        t["items"] = [i for i in t["items"] if i]
    return [t for t in topics if t["items"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--subject", required=True, choices=SPECS)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = SPECS[args.subject]
    raw = pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " ")
    lines = [l.strip() for l in raw.splitlines()]

    def find(patt, start=0):
        rx = re.compile(patt)
        for i in range(start, len(lines)):
            if rx.match(lines[i]):
                return i
        return -1

    # units
    bounds = []
    for num, patt, title, level in spec["units"]:
        i = find(patt)
        if i < 0:
            raise SystemExit(f"unit anchor not found: {patt}")
        bounds.append((i, num, title, level))
    bounds.sort()
    end_all = find(spec["unit_end"])
    units = []
    for idx, (start, num, title, level) in enumerate(bounds):
        stop = bounds[idx + 1][0] if idx + 1 < len(bounds) else end_all
        topics = parse_unit_topics(lines[start + 1:stop], spec["furniture"])
        units.append({"number": num, "title": title, "level": level, "topics": topics})

    ao_i, ao_j = find(spec["ao_start"]), 0
    ao_j = find(spec["ao_end"], ao_i)
    aos = parse_aos(lines[ao_i + 1:ao_j])

    q_i = find(spec["questions_start"])
    q_j = find(spec["questions_end"], q_i + 1)
    questions = parse_questions(lines[q_i + 1:q_j if q_j > 0 else len(lines)])

    depth = {"subject": args.subject, "units": units,
             "assessment_objectives": aos, "hl_inquiry_questions": questions}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
    n_topics = sum(len(u["topics"]) for u in units)
    n_items = sum(len(t["items"]) for u in units for t in u["topics"])
    print(f"wrote {out}: {len(units)} units, {n_topics} prescribed topics, "
          f"{n_items} items, {len(aos)} AOs, {len(questions)} HL inquiry questions")


if __name__ == "__main__":
    main()
