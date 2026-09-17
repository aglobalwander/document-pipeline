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
        --content-start "# A1.1 Water" --content-end "# D4.3 ..." \
        --out data/output/ib_native/biology/depth.json

Both boundaries must be single guide lines, and `--content-end` must occur *after*
`--content-start`: pick the first topic header and the next top-level heading after the last
topic header. (The previous example here named "# Collaborative sciences project", which the
Biology guide prints *earlier*, in its syllabus overview, so the extractor ran on an empty body
and wrote zero units.)
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


PHYS_TOPIC = re.compile(r"^## ([A-E])\.(\d+)\s+(.+)$")
CHEM_TOPIC = re.compile(r"^\*\*(Structure|Reactivity)\s+(\d+)\.(\d+)[—-]\s*(.+?)\*\*$")
CHEM_UND = re.compile(r"^\*\*(Structure|Reactivity)\s+(\d+\.\d+\.\d+)[—-]\s*(.+?)\*\*$")
CHEM_XREF = re.compile(r"^(Structure|Reactivity)\s+\d")


def parse_topic_physics(lines):
    topic = {"theme_level": "", "guiding_questions": [], "understandings": [],
             "linking_questions": []}
    mode, hl = None, False
    for ln in lines:
        s = ln.strip()
        if not s or FURNITURE.match(s):
            continue
        if "no additional higher level content" in s.lower():
            continue
        if s.startswith("**Guiding questions**"):
            mode = "gq"; continue
        if s.startswith("**Understandings**"):
            mode, hl = "u", False; continue
        if s.startswith("**Additional higher level**"):
            mode, hl = "u", True; continue
        if s.startswith("**Linking questions**"):
            mode = "lq"; continue
        if s.startswith("**Guidance**") or s.startswith("**Standard level") \
                or s.startswith("Students should understand"):
            continue
        if s.startswith(("**", "#")):
            mode = None; continue
        if mode == "gq" and s.endswith("?"):
            topic["guiding_questions"].append(s)
        elif mode == "lq" and s.endswith("?"):
            topic["linking_questions"].append(s)
        elif mode == "u":
            if s == "•":
                topic["understandings"].append({"code": "", "statement": "", "guidance": "", "hl_only": hl})
            elif topic["understandings"] and not topic["understandings"][-1]["statement"]:
                topic["understandings"][-1]["statement"] = s
            elif topic["understandings"]:
                topic["understandings"][-1]["statement"] = (topic["understandings"][-1]["statement"] + " " + s).strip()
    topic["understandings"] = [u for u in topic["understandings"] if u["statement"]]
    return topic


def parse_chemistry(body):
    """Chemistry: bold understandings '**Structure 1.1.1—stmt**' + guidance prose;
    inline 'Guiding question:' lines; cross-ref lines are linking questions."""
    units = {"Structure": {"theme": "Structure", "title": "Structure", "topics": []},
             "Reactivity": {"theme": "Reactivity", "title": "Reactivity", "topics": []}}
    cur_topic, cur_u = None, None
    for ln in body:
        s = ln.strip()
        if not s or FURNITURE.match(s):
            continue
        m = CHEM_TOPIC.match(s)
        if m and not CHEM_UND.match(s):
            theme = m.group(1)
            cur_topic = {"code": f"{theme} {m.group(2)}.{m.group(3)}", "title": m.group(4).strip(),
                         "theme_level": "", "guiding_questions": [], "understandings": [],
                         "linking_questions": [], "org_level": int(m.group(2))}
            units[theme]["topics"].append(cur_topic)
            cur_u = None
            continue
        if cur_topic is None:
            continue
        gm = re.match(r"^\*\*Guiding question[s]?:?\s*(.+?)\*\*$", s)
        if gm:
            cur_topic["guiding_questions"].append(gm.group(1).strip())
            continue
        um = CHEM_UND.match(s)
        if um:
            cur_u = {"code": um.group(2), "statement": um.group(3).strip(), "guidance": "",
                     "hl_only": False}
            cur_topic["understandings"].append(cur_u)
            continue
        if CHEM_XREF.match(s) and s.endswith("?"):
            cur_topic["linking_questions"].append(s)
            continue
        if cur_u is not None and not s.startswith(("**", "#")) and not CHEM_XREF.match(s):
            cur_u["guidance"] = re.sub(r"\s+", " ", cur_u["guidance"] + " " + s).strip()
    return [units[k] for k in ("Structure", "Reactivity") if units[k]["topics"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--themes", required=True, help="A=Label,B=Label,... (theme letter = concept)")
    ap.add_argument("--content-start", required=True)
    ap.add_argument("--content-end", required=True)
    ap.add_argument("--mode", default="biology", choices=["biology", "physics", "chemistry"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    themes = {}
    for pair in args.themes.split(","):
        k, v = pair.split("=", 1)
        themes[k.strip()] = v.strip()

    raw = pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " ")
    lines = clean(raw.splitlines())
    start = next(i for i, l in enumerate(lines) if l.strip() == args.content_start)
    # The end boundary must be searched *after* the start: several guides mention the syllabus
    # end marker earlier, in their intro or contents list, and taking the first occurrence
    # anywhere silently produced an empty body (the docstring's biology example did exactly that).
    try:
        end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == args.content_end)
    except StopIteration:
        raise SystemExit(
            f"content-end {args.content_end!r} does not occur after content-start "
            f"{args.content_start!r} (line {start + 1}); check the pair against the guide")
    body = lines[start:end]

    if args.mode == "chemistry":
        out_units = parse_chemistry(body)
        depth = {"subject": args.subject, "themes": themes, "units": out_units}
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
        n_t = sum(len(u["topics"]) for u in out_units)
        n_u = sum(len(t["understandings"]) for u in out_units for t in u["topics"])
        print(f"wrote {args.out}: {len(out_units)} theme-units, {n_t} topics, {n_u} understandings")
        return

    hdr = PHYS_TOPIC if args.mode == "physics" else TOPIC_HDR
    parse_fn = parse_topic_physics if args.mode == "physics" else parse_topic
    topic_bounds = [i for i, l in enumerate(body) if hdr.match(l.strip())]
    units = {k: {"theme": k, "title": v, "topics": []} for k, v in themes.items()}
    for idx, ti in enumerate(topic_bounds):
        m = hdr.match(body[ti].strip())
        if args.mode == "physics":
            theme, num, title = m.group(1), m.group(2), m.group(3).strip()
            lvl = "1"
        else:
            theme, lvl, num, title = m.group(1), m.group(2), m.group(3), m.group(4).strip()
        stop = topic_bounds[idx + 1] if idx + 1 < len(topic_bounds) else len(body)
        parsed = parse_fn(body[ti + 1:stop])
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
