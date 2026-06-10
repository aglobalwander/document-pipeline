#!/usr/bin/env python3
"""Extract a structured skeleton from IB DP subject-brief markdown (sections I-IV).

First caller: DP Economics (2022). The brief markdown shape (from PDF conversion):
- sections delimited by '## I.' .. '## IV.' headers
- bullets render as 'z ' (Zapf dingbat fallback)
- a vertical-text noise block (1-3 char lines) sits inside section II
- the assessment table is flattened: Paper N / description lines / durations / weight

AO -> component alignment is not in the brief; it is parsed from the guide's
"Assessment objectives in practice" tick matrix (--guide).

Usage:
    poetry run python scripts/standards/ib_brief_extract.py \
        --briefs data/output/markdown/ib_briefs/economics_hl_2022.md \
                 data/output/markdown/ib_briefs/economics_sl_2022.md \
        --guide data/output/markdown/ib_guides/economics_2022.md \
        --out data/output/ib_native/economics/skeleton.json --subject economics
"""
import argparse
import json
import pathlib
import re

BULLET = re.compile(r"^z\s+(.+)$")
UNIT_HDR = re.compile(r"\*\*Unit\s+(\d):\s*(.+?)\*\*")
TOPIC = re.compile(r"^(\d\.\d+)\s*(.*)$")
HOURS = re.compile(r"^\*\*(\d+)\*\*$")
AO_HDR = re.compile(r"^\*\*Assessment objective (\d): (.+?)\*\*")
DURATION = re.compile(r"^(\d+ (?:hours?|mins?))$")
WEIGHT = re.compile(r"^(\d{2})$")


def split_sections(text):
    """Return {'I': ..., 'II': ...} keyed by roman numeral of '## N. Title' headers."""
    parts = re.split(r"^## ([IVX]+)\. .*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def collect_bullets(lines, start):
    """Collect one z-bullet starting at lines[start], joining wrapped lines."""
    out = [BULLET.match(lines[start]).group(1).strip()]
    i = start + 1
    while i < len(lines):
        ln = lines[i].strip()
        if not ln or BULLET.match(ln) or ln.startswith(("**", "#", "##")):
            break
        out.append(ln)
        i += 1
    return re.sub(r"\s+", " ", " ".join(out)).strip(), i


def extract_aims(sec1):
    lines = sec1.splitlines()
    aims, in_aims, i = [], False, 0
    while i < len(lines):
        ln = lines[i].strip()
        if "aims" in ln.lower() and ln.startswith("**"):
            in_aims = True
            i += 1
            continue
        if in_aims and BULLET.match(ln):
            aim, i = collect_bullets([l.strip() for l in lines], i)
            aims.append(aim)
            continue
        i += 1
    return aims


def extract_concepts(sec1):
    flat = re.sub(r"\s+", " ", sec1)
    m = re.search(r"nine key concepts \(([^)]+)\)", flat)
    if not m:
        raise SystemExit("key-concepts parenthetical not found in section I")
    raw = m.group(1).replace(" and ", ", ")
    return [{"label": c.strip()} for c in raw.split(",") if c.strip()]


def extract_units(sec2, level):
    """Units with topics and per-level recommended hours. Filters the vertical-text
    noise block (short non-topic lines) by only consuming topic/continuation lines."""
    units, current, open_topic = [], None, None
    for raw in sec2.splitlines():
        ln = raw.strip()
        if not ln or ln == "---":
            continue
        m = UNIT_HDR.search(ln)
        if m:
            current = {"number": int(m.group(1)), "title": m.group(2).strip(),
                       "hours": {level: None}, "topics": []}
            units.append(current)
            open_topic = None
            continue
        if current is None:
            continue
        m = HOURS.match(ln)
        if m and current["hours"][level] is None and current["topics"]:
            current["hours"][level] = int(m.group(1))
            open_topic = None
            continue
        m = TOPIC.match(ln)
        if m:
            open_topic = {"code": m.group(1), "title": m.group(2).strip()}
            current["topics"].append(open_topic)
            continue
        # wrapped topic-title continuation; reject noise (vertical-text fragments,
        # bold table headers, page furniture)
        if (open_topic is not None and not ln.startswith(("**", "#"))
                and len(ln) > 3 and not ln.isupper()):
            open_topic["title"] = re.sub(r"\s+", " ", open_topic["title"] + " " + ln).strip()
        else:
            open_topic = None
    return [u for u in units if u["topics"]]


def extract_aos(sec3, level):
    lines = [l.strip() for l in sec3.splitlines()]
    aos, i = [], 0
    while i < len(lines):
        m = AO_HDR.match(lines[i])
        if not m:
            i += 1
            continue
        ao = {"code": f"AO{m.group(1)}", "title": m.group(2).strip(),
              "grain": "course", "objective_type": "Assessment Objective",
              "bullets": {level: []}}
        i += 1
        while i < len(lines) and not AO_HDR.match(lines[i]) and not lines[i].startswith("**Type of"):
            if BULLET.match(lines[i]):
                b, i = collect_bullets(lines, i)
                ao["bullets"][level].append(b)
            else:
                i += 1
        aos.append(ao)
    return aos


def extract_components(sec3, level):
    """Parse the flattened assessment table: component label, description lines,
    duration fragments, two-digit weight."""
    lines = [l.strip() for l in sec3.splitlines()]
    # table starts at the '**Type of**' header
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("**Type of"))
    except StopIteration:
        raise SystemExit("assessment table header not found in section III")
    comps, current = [], None
    for ln in lines[start:]:
        if not ln or ln.startswith("**") or ln in ("External", "Internal"):
            continue
        if re.match(r"^Paper \d$", ln) or ln == "Portfolio":
            current = {"name": ln, "level": level, "format": [], "duration": [],
                       "weighting_pct": None, "aligned_aos": []}
            comps.append(current)
            continue
        if current is None:
            continue  # the External-total duration/weight rows before Paper 1
        if DURATION.match(ln):
            current["duration"].append(ln)
            continue
        m = WEIGHT.match(ln)
        if m and current["weighting_pct"] is None and current["duration"]:
            current["weighting_pct"] = int(m.group(1))
            continue
        if ln.startswith("## "):
            break
        current["format"].append(ln)
    for c in comps:
        c["format"] = re.sub(r"\s+", " ", " ".join(c["format"])).strip()
        c["duration"] = " ".join(c["duration"])
    # Portfolio weight: the table ends at section IV; weight follows '20 hours'
    return [c for c in comps if c["weighting_pct"]]


def extract_ao_alignment(guide_text):
    """Parse the 'Assessment objectives in practice' tick matrix from the guide.
    Tick columns (Economics 2022): P1 part a, P1 part b, P2, P3 (HL), IA.
    A component aligns to an AO if any of its columns is ticked. The matrix block
    runs from the '**Part a**' column header to the next '# ' page header (the
    command-terms table that follows also lists AOs, so the slice matters)."""
    cols = ["Paper 1", "Paper 1", "Paper 2", "Paper 3", "Portfolio"]
    m = re.search(r"\*\*Part a\*\*.*?(?=^# )", guide_text, re.S | re.M)
    if not m:
        raise SystemExit("AO-in-practice tick matrix not found in guide")
    block = m.group(0)
    align = {}
    for ao_m in re.finditer(r"\*\*(AO\d)[—-](.*?)(?=\*\*AO\d[—-]|\Z)", block, re.S):
        ticks = ao_m.group(2).count("√")
        if ticks == len(cols):
            comps = set(cols)
        elif ticks == len(cols) - 1:
            comps = set(cols[1:])  # first column (Paper 1 part a) unticked — AO3
        else:
            comps = set()
        align[ao_m.group(1)] = comps
    return {comp: sorted(code for code, s in align.items() if comp in s)
            for comp in set(cols)}


def merge_aos(per_level):
    merged = {}
    for level, aos in per_level.items():
        for ao in aos:
            slot = merged.setdefault(ao["code"], {**ao, "bullets": {}})
            slot["bullets"][level] = ao["bullets"][level]
            assert slot["title"] == ao["title"], f"{ao['code']} title differs across levels"
    return [merged[c] for c in sorted(merged)]


def merge_units(per_level):
    merged = {}
    for level, units in per_level.items():
        for u in units:
            slot = merged.setdefault(u["number"], {**u, "hours": {}})
            slot["hours"][level] = u["hours"][level]
            assert slot["title"] == u["title"], f"unit {u['number']} title differs across levels"
            if len(u["topics"]) > len(slot["topics"]):
                slot["topics"] = u["topics"]
    return [merged[n] for n in sorted(merged)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefs", nargs=2, required=True, help="HL brief md, SL brief md")
    ap.add_argument("--guide", required=True, help="full guide md (AO-in-practice matrix)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--edition", type=int, default=2022)
    args = ap.parse_args()

    aims, concepts = None, None
    aos_per_level, units_per_level, components = {}, {}, []
    for path in args.briefs:
        # NBSPs from the PDF conversion break duration/weight parsing ('15\xa0mins')
        text = pathlib.Path(path).read_text(encoding="utf-8").replace("\xa0", " ")
        # the title line reads e.g. 'Economics—higher level' (the DP boilerplate
        # mentions both levels, so match the em-dash title pattern, not bare words)
        level = "HL" if re.search(r"^.*—higher level\s*$", text, re.M) else "SL"
        sec = split_sections(text)
        if aims is None:
            aims, concepts = extract_aims(sec["I"]), extract_concepts(sec["I"])
        units_per_level[level] = extract_units(sec["II"], level)
        aos_per_level[level] = extract_aos(sec["III"], level)
        components.extend(extract_components(sec["III"], level))

    comp_aos = extract_ao_alignment(
        pathlib.Path(args.guide).read_text(encoding="utf-8").replace("\xa0", " "))
    for c in components:
        c["aligned_aos"] = comp_aos.get(c["name"], [])

    skeleton = {
        "subject": args.subject, "edition": args.edition,
        "levels": sorted(units_per_level, reverse=True),
        "aims": aims, "concepts": concepts,
        "assessment_objectives": merge_aos(aos_per_level),
        "units": merge_units(units_per_level),
        "assessment_components": components,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(skeleton, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out}: {len(skeleton['units'])} units, "
          f"{sum(len(u['topics']) for u in skeleton['units'])} topics, "
          f"{len(skeleton['assessment_objectives'])} AOs, "
          f"{len(components)} components, {len(concepts)} concepts")


if __name__ == "__main__":
    main()
