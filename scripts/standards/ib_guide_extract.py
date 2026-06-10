#!/usr/bin/env python3
"""Extract per-unit depth from an IB DP subject-guide markdown (syllabus content).

First caller: DP Economics (2022). The guide markdown is a page-linearized PDF
conversion; page furniture ('# Unit N:', page numbers, 'Economics guide', '---')
interleaves the content stream, so parsing is anchored on content markers:

  **Recommended (teaching) time ...**   -> starts the next unit (in order 1..4)
  # Real-world issue N                  -> issue; following '## ...' lines = question
  **Conceptual understandings**         -> bullet block (unit- or issue-level)
  **Key concepts: ...**                 -> key-concept labels
  **N.N Title**                         -> topic (HL-only notes ride in the title)
  bullets (•/▪), AO markers, Diagram:   -> topic content blocks
  **bold content line**                 -> HL-only (per the guide's own legend)

Usage:
    poetry run python scripts/standards/ib_guide_extract.py \
        --guide data/output/markdown/ib_guides/economics_2022.md \
        --out data/output/ib_native/economics/depth.json \
        --units "Introduction to economics,Microeconomics,Macroeconomics,The global economy"
"""
import argparse
import json
import pathlib
import re

TIME_MARKER = re.compile(r"^\*\*Recommended (?:teaching )?time[^*]*\*\*$")
ISSUE_HDR = re.compile(r"^# Real-world issue (\d)$")
TOPIC_HDR = re.compile(r"^\*\*(\d\.\d+)\s+(.+?)\*\*$")
AO_LINE = re.compile(r"^(AO\d(?:,\s*AO\d)*)$")
PAGE_FURNITURE = re.compile(
    r"^(#+ Unit \d.*|Unit \d:.*|\d{1,3}|Economics guide|---|Syllabus(?: content)?|"
    r"\*\*Depth of\*\*|\*\*teaching\*\*|\*\*Diagrams(?: and calculations)?\*\*)$")


def is_bold(ln):
    return ln.startswith("**") and ln.endswith("**")


def unbold(ln):
    return ln.strip("*").strip()


def parse(text, unit_titles):
    lines = [l.strip() for l in text.replace("\xa0", " ").splitlines()]
    units, unit, issue, topic, block = [], None, None, None, None
    mode = None  # None | 'cu' | 'keyconcepts' | 'question'

    def close_block():
        nonlocal block
        if block and (block["text"] or block["bullets"]):
            block["text"] = re.sub(r"\s+", " ", block["text"]).strip()
            topic["blocks"].append(block)
        block = None

    def new_block(hl):
        nonlocal block
        close_block()
        block = {"text": "", "bullets": [], "ao_depth": [], "diagrams": [], "hl_only": hl}

    for ln in lines:
        if not ln:
            continue

        if TIME_MARKER.match(ln):
            close_block()
            topic = issue = None
            unit = {"number": len(units) + 1, "title": unit_titles[len(units)],
                    "time_note": unbold(ln).replace("Recommended", "").strip(": "),
                    "conceptual_understandings": [], "key_concepts": [],
                    "issues": [], "topics": []}
            units.append(unit)
            mode = None
            continue
        if unit is None:
            continue

        m = ISSUE_HDR.match(ln)
        if m:
            close_block()
            topic = None
            issue = {"number": int(m.group(1)), "question": "",
                     "conceptual_understandings": [], "key_concepts": []}
            unit["issues"].append(issue)
            mode = "question"
            continue
        if mode == "question":
            if ln.startswith("## "):
                issue["question"] = (issue["question"] + " " + ln[3:].strip()).strip()
                continue
            mode = None  # fall through: first non-## line ends the question

        if PAGE_FURNITURE.match(ln):
            continue

        m = TOPIC_HDR.match(ln)
        if m:
            close_block()
            title = m.group(2).strip()
            hl_note = ""
            note = re.search(r"\((includes )?HL only[^)]*\)", title)
            if note:
                hl_note = note.group(0).strip("()")
                title = title[:note.start()].strip()
            # a topic spanning pages repeats its header — continue, don't duplicate
            existing = next((t for t in unit["topics"] if t["code"] == m.group(1)), None)
            if existing:
                topic = existing
                topic["hl_note"] = topic["hl_note"] or hl_note
            else:
                topic = {"code": m.group(1), "title": title, "hl_note": hl_note, "blocks": []}
                unit["topics"].append(topic)
            mode = None
            continue

        if unbold(ln) == "Conceptual understandings":
            close_block()
            mode = "cu"
            continue
        if unbold(ln).startswith("Key concepts:"):
            mode = "keyconcepts"
            target = issue if issue else unit
            raw = unbold(ln).removeprefix("Key concepts:")
            target["key_concepts"].extend(
                c.strip() for c in raw.replace(".", "").split(",") if c.strip())
            continue
        if mode == "keyconcepts":
            if is_bold(ln) or TOPIC_HDR.match(ln):
                mode = None
            else:
                target = issue if issue else unit
                target["key_concepts"].extend(
                    c.strip() for c in unbold(ln).replace(".", "").split(",") if c.strip())
                continue

        if mode == "cu":
            target = issue if issue else unit
            if ln in ("•", "▪"):
                target["conceptual_understandings"].append({"text": ""})
            elif TOPIC_HDR.match(ln) or unbold(ln).startswith("Key concepts:"):
                mode = None
                # reprocess key-concepts line inline
                if unbold(ln).startswith("Key concepts:"):
                    raw = unbold(ln).removeprefix("Key concepts:")
                    target["key_concepts"].extend(
                        c.strip() for c in raw.replace(".", "").split(",") if c.strip())
                    mode = "keyconcepts"
                continue
            elif target["conceptual_understandings"]:
                cu = target["conceptual_understandings"][-1]
                cu["text"] = re.sub(r"\s+", " ", cu["text"] + " " + unbold(ln)).strip()
            continue

        if topic is None:
            continue

        # ---- topic content stream ----
        if ln == "•":
            if block is None:
                new_block(False)
            block["bullets"].append({"text": "", "sub": [], "hl_only": False})
            continue
        if ln == "▪":
            if block and block["bullets"]:
                block["bullets"][-1]["sub"].append("")
            continue
        m = AO_LINE.match(ln)
        if m:
            if block is None:
                new_block(False)
            block["ao_depth"] = [a.strip() for a in m.group(1).split(",")]
            continue
        if unbold(ln).startswith(("Diagram:", "Diagrams:")):
            if block is None:
                new_block(is_bold(ln))
            block["diagrams"].append(unbold(ln))
            continue

        hl = is_bold(ln)
        content = unbold(ln)
        if block and block["diagrams"] and content[0].islower():
            # wrapped diagram caption ('...circular flow of income model, with / leakages...')
            block["diagrams"][-1] = re.sub(r"\s+", " ", block["diagrams"][-1] + " " + content)
            continue
        if block and (block["ao_depth"] or block["diagrams"]):
            # AO/diagram column closed the block -> this text starts the next one
            new_block(hl)
            block["text"] = content
            continue
        if block and block["bullets"]:
            b = block["bullets"][-1]
            if b["sub"]:
                b["sub"][-1] = re.sub(r"\s+", " ", b["sub"][-1] + " " + content).strip()
            else:
                b["text"] = re.sub(r"\s+", " ", b["text"] + " " + content).strip()
                b["hl_only"] = b["hl_only"] or hl
            continue
        if block is None:
            new_block(hl)
        block["text"] = (block["text"] + " " + content).strip()
        block["hl_only"] = block["hl_only"] or hl

    close_block()
    return {"units": units}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--units", required=True, help="comma-separated unit titles, in order")
    ap.add_argument("--start", default="# Assessment in the Diploma Programme",
                    help="section header that ends the syllabus content range")
    args = ap.parse_args()

    text = pathlib.Path(args.guide).read_text(encoding="utf-8")
    end = text.find(args.start)
    depth = parse(text[:end if end > 0 else len(text)], args.units.split(","))

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
    n_topics = sum(len(u["topics"]) for u in depth["units"])
    n_issues = sum(len(u["issues"]) for u in depth["units"])
    print(f"wrote {out}: {len(depth['units'])} units, {n_topics} topics, {n_issues} issues")


if __name__ == "__main__":
    main()
