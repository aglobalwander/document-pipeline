#!/usr/bin/env python3
"""Depth extractor for the IB DP 2025 sciences format (Biology / Chemistry / Physics).

Uniform grammar: themed topics '# X N.N Title' (X = theme letter A-D = concept), each
with a theme/level line, '## Guiding questions', numbered understandings ('X.N.N—content
statement' + guidance prose) under '## SL and HL' / '## Additional higher level', and
'## Linking questions'.

Units = the themes (A-D). Each topic's understandings become `understandings` payload
rows scoped to the theme-unit, concept-linked to the theme's concept. Guiding + linking
questions become `questions`.

Usage:
    poetry run python scripts/standards/ib_guide_extract_sciences.py \
        --guide data/output/markdown/ib_guides/biology_2025.md --subject biology \
        --themes "A=Unity and diversity,B=Form and function,C=Interaction and interdependence,D=Continuity and change" \
        --content-start "# A1.1 Water" --content-end "# Collaborative sciences project" \
        --out data/output/ib_native/biology/depth.json
"""
import argparse
import json
import pathlib
import re

TOPIC_HDR = re.compile(r"^# ([A-D])(\d)\.(\d+)\s+(.+)$")
UNDERSTANDING = re.compile(r"^([A-D]\d\.\d+\.\d+)[—-]\s*(.+)$")
FURNITURE = re.compile(r"^(\d{1,3}|[A-Z][\w ]+ guide|---|Syllabus(?: content)?|Syllabus|"
                       r"\*\*Download:.*|Note:.*)$")


def clean(lines):
    return [l.rstrip() for l in lines]


def parse_topic(lines):
    """lines are the body of one topic (after its '# X N.N Title' header)."""
    topic = {"theme_level": "", "guiding_questions": [], "understandings": [],
             "linking_questions": []}
    mode = None
    cur_u = None
    for ln in lines:
        s = ln.strip()
        if not s or FURNITURE.match(s):
            continue
        if s.startswith("## Guiding questions"):
            mode = "gq"
            continue
        if s.startswith("## Linking questions"):
            mode = "lq"
            continue
        if s.startswith("## SL and HL"):
            mode, hl = "u", False
            continue
        if s.startswith("## Additional higher level"):
            mode, hl = "u", True
            continue
        if s.startswith("##"):
            mode = None
            continue
        # theme/level line: first non-bold line before any ## header
        if mode is None and not topic["theme_level"] and "—" in s and not s.startswith("**"):
            topic["theme_level"] = s
            continue
        if mode == "gq":
            if s == "•":
                topic["guiding_questions"].append("")
            elif topic["guiding_questions"] and not s.startswith("#"):
                topic["guiding_questions"][-1] = (topic["guiding_questions"][-1] + " " + s).strip()
        elif mode == "lq":
            if s == "•":
                topic["linking_questions"].append("")
            elif topic["linking_questions"] and not s.startswith("#"):
                topic["linking_questions"][-1] = (topic["linking_questions"][-1] + " " + s).strip()
        elif mode == "u":
            m = UNDERSTANDING.match(s)
            if m:
                cur_u = {"code": m.group(1), "statement": m.group(2).strip(),
                         "guidance": "", "hl_only": hl}
                topic["understandings"].append(cur_u)
            elif cur_u is not None and not s.startswith("**"):
                cur_u["guidance"] = re.sub(r"\s+", " ", cur_u["guidance"] + " " + s).strip()
    topic["guiding_questions"] = [q for q in topic["guiding_questions"] if q]
    topic["linking_questions"] = [q for q in topic["linking_questions"] if q]
    return topic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--themes", required=True, help="A=Label,B=Label,... (theme letter = concept)")
    ap.add_argument("--content-start", required=True)
    ap.add_argument("--content-end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    themes = {}
    for pair in args.themes.split(","):
        k, v = pair.split("=", 1)
        themes[k.strip()] = v.strip()

    raw = pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " ")
    lines = clean(raw.splitlines())
    start = next(i for i, l in enumerate(lines) if l.strip() == args.content_start)
    end = next(i for i, l in enumerate(lines) if l.strip() == args.content_end)
    body = lines[start:end]

    # split into topics
    topic_bounds = [i for i, l in enumerate(body) if TOPIC_HDR.match(l.strip())]
    units = {k: {"theme": k, "title": v, "topics": []} for k, v in themes.items()}
    for idx, ti in enumerate(topic_bounds):
        m = TOPIC_HDR.match(body[ti].strip())
        theme, lvl, num, title = m.group(1), m.group(2), m.group(3), m.group(4).strip()
        stop = topic_bounds[idx + 1] if idx + 1 < len(topic_bounds) else len(body)
        parsed = parse_topic(body[ti + 1:stop])
        parsed["code"] = f"{theme}{lvl}.{num}"
        parsed["title"] = title
        parsed["org_level"] = int(lvl)
        units[theme]["topics"].append(parsed)

    out_units = []
    for k in sorted(units):
        u = units[k]
        if u["topics"]:
            out_units.append(u)
    depth = {"subject": args.subject, "themes": themes, "units": out_units}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
    n_topics = sum(len(u["topics"]) for u in out_units)
    n_und = sum(len(t["understandings"]) for u in out_units for t in u["topics"])
    n_q = sum(len(t["guiding_questions"]) + len(t["linking_questions"])
              for u in out_units for t in u["topics"])
    print(f"wrote {out}: {len(out_units)} theme-units, {n_topics} topics, "
          f"{n_und} understandings, {n_q} questions")


if __name__ == "__main__":
    main()
