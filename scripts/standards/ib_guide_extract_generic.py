#!/usr/bin/env python3
"""Configurable depth extractor for DP guides built on BOLD understanding statements.

Covers the 2026/2027-era sciences-family grammars (SEHS, Computer Science, Design
Technology): theme sections, topic subsections, and understandings expressed as bold
headers ('**<code> <statement>**', code regex supplied) followed by guidance prose
and/or bullet sub-content. HL flagged by '(HL only)' in the header or a preceding
'**Additional higher level' marker.

Themes become units (concept-linkable in the payload step). Everything is captured
under its theme; topic codes ride on each understanding.

Usage:
    poetry run python scripts/standards/ib_guide_extract_generic.py \
        --guide <md> --subject sehs \
        --themes "A=...,B=...,C=...,D=..." \
        --theme-rx "^# ([A-E])\\. (.+)$" \
        --code-rx "^\\*\\*([A-E]\\.\\d+\\.\\d+(?:\\.\\d+)?)[—-]?\\s*(.+?)\\*\\*$" \
        --content-start "# A." --content-end "# ..." \
        --out data/output/ib_native/sehs/depth.json
"""
import argparse
import json
import pathlib
import re

FURNITURE = re.compile(r"^(\d{1,3}|[A-Z][\w ,]+ guide|---|Syllabus(?: content)?|Syllabus|"
                       r"\*\*Download:.*|Note:.*|Tool \d.*|Inquiry \d.*)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--themes", required=True)
    ap.add_argument("--theme-rx", required=True)
    ap.add_argument("--code-rx", required=True)
    ap.add_argument("--standalone-rx", default="",
                    help="code-on-its-own-line regex; statement follows on bold lines")
    ap.add_argument("--content-start", required=True)
    ap.add_argument("--content-end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    themes = {}
    for pair in args.themes.split(","):
        k, v = pair.split("=", 1)
        themes[k.strip()] = v.strip()
    theme_rx = re.compile(args.theme_rx)
    code_rx = re.compile(args.code_rx)
    standalone_rx = re.compile(args.standalone_rx) if args.standalone_rx else None
    topic_rx = re.compile(r"^(?:#+\s*|\*\*)([A-E]\d?\.?\d*)\s+(.+?)\*?\*?$")
    awaiting_statement = False

    raw = pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " ")
    lines = raw.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == args.content_start.strip())
    try:
        end = next(i for i in range(start + 1, len(lines))
                   if lines[i].strip() == args.content_end.strip())
    except StopIteration:
        end = len(lines)
    body = lines[start:end]

    units = {k: {"theme": k, "title": v, "topics": [], "_topic_index": {}}
             for k, v in themes.items()}
    cur_theme = cur_topic = cur_u = None
    hl_section = False

    def get_topic(theme, code, title):
        u = units[theme]
        if code not in u["_topic_index"]:
            t = {"code": code, "title": title, "understandings": [],
                 "guiding_questions": [], "linking_questions": []}
            u["topics"].append(t)
            u["_topic_index"][code] = t
        return u["_topic_index"][code]

    for ln in body:
        s = ln.strip()
        if not s or FURNITURE.match(s):
            continue
        tm = theme_rx.match(s)
        if tm:
            cur_theme = tm.group(1)
            cur_topic = cur_u = None
            hl_section = False
            continue
        if cur_theme is None or cur_theme not in units:
            continue
        if "additional higher level" in s.lower():
            hl_section = True
            continue
        if standalone_rx and cur_topic is not None:
            sm = standalone_rx.match(s)
            if sm:
                cur_u = {"code": sm.group(1), "statement": "", "guidance": "",
                         "hl_only": hl_section}
                cur_topic["understandings"].append(cur_u)
                awaiting_statement = True
                continue
            if awaiting_statement and s.startswith("**") and s.endswith("**"):
                frag = s.strip("*").strip()
                cur_u["statement"] = (cur_u["statement"] + " " + frag).strip()
                continue
            if awaiting_statement:
                awaiting_statement = False
        cm = code_rx.match(s)
        if cm:
            code = cm.group(1)
            statement = cm.group(2).strip()
            hl = hl_section or "(HL only)" in s or "(HL)" in statement
            statement = re.sub(r"\s*\(HL only\)\s*", "", statement).strip()
            topic_code = ".".join(code.split(".")[:2]) if "." in code else code
            cur_topic = get_topic(cur_theme, topic_code, "")
            cur_u = {"code": code, "statement": statement, "guidance": "", "hl_only": hl}
            cur_topic["understandings"].append(cur_u)
            continue
        # topic header (no understanding code)
        tpm = topic_rx.match(s)
        if tpm and not cm and (s.startswith("#") or (s.startswith("**") and s.endswith("**"))):
            code = tpm.group(1)
            cur_topic = get_topic(cur_theme, code, tpm.group(2).strip())
            cur_u = None
            hl_section = "additional higher level" in s.lower()
            continue
        if re.match(r"^\*\*Linking question", s, re.I):
            cur_u = None
            continue
        if s.endswith("?") and cur_topic is not None and re.match(r"^[A-E0-9]", s):
            cur_topic["linking_questions"].append(s)
            continue
        # guidance / sub-content for the open understanding
        if cur_u is not None and s not in ("•", "▪") and not s.startswith(("**", "#")):
            cur_u["guidance"] = re.sub(r"\s+", " ", cur_u["guidance"] + " " + s).strip()

    out_units = []
    for k in sorted(units):
        u = units[k]
        u.pop("_topic_index", None)
        if u["topics"]:
            out_units.append(u)
    depth = {"subject": args.subject, "themes": themes, "units": out_units}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(depth, indent=1, ensure_ascii=False), encoding="utf-8")
    n_t = sum(len(u["topics"]) for u in out_units)
    n_u = sum(len(t["understandings"]) for u in out_units for t in u["topics"])
    n_hl = sum(1 for u in out_units for t in u["topics"] for x in t["understandings"] if x["hl_only"])
    print(f"wrote {out}: {len(out_units)} theme-units, {n_t} topics, "
          f"{n_u} understandings ({n_hl} HL)")


if __name__ == "__main__":
    main()
