#!/usr/bin/env python3
"""Build the DP Economics skeleton from the guide alone (no briefs).

KM ruled on 2026-09-17 that briefs are summaries, not sources: skeleton and depth come from the
guide. Reads the text layer written by km_text_layer.py, so every item keeps PDF page and bbox:

  aims                   'Economics aims' bullets
  concepts               the 'Key concepts:' line printed in the syllabus
  assessment_objectives  AO1-AO4 with bullets; 'At HL only' items carry levels ["HL"]
  units                  'Syllabus outline' table: unit, topics as printed, SL/HL hours
  internal_assessment_hours, total_teaching_hours   same table
  assessment_components  'Assessment outline—SL' and '—HL' pages

Output keys follow the brief-based skeleton (subject, edition, levels, aims, concepts,
assessment_objectives, units, assessment_components) so consumers can compare the two.

Usage:
    poetry run python scripts/standards/ib_econ_guide_skeleton.py \
        --layer data/output/km_requests/2026-09-17/p1_ib_guides/<sha>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ib_tok_extract import is_furniture
from ib_va_extract import bullets, joined, span

AO_HDR = re.compile(r"^(.+) \((AO\d)\)$")
TOPIC = re.compile(r"^(\d\.\d+) (.+)$")
UNIT = re.compile(r"^Unit (\d): (.+)$")
NOTE = re.compile(r"^(.*?)\s*\(((?:includes |HL only)[^)]*)\)$")
PAPER = re.compile(r"^(Paper \d|Internal assessment) \((.+)\)$")
WEIGHT = re.compile(r"^(\d+)%$")
SL_X, HL_X = 424, 478


def loc(r: dict) -> dict:
    return {"page": r["page"], "bbox": r["bbox"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True, type=Path)
    args = ap.parse_args()

    source = json.loads((args.layer / "source.json").read_text(encoding="utf-8"))
    raw = [json.loads(l) for l in (args.layer / "text_layer.jsonl").open(encoding="utf-8")]
    recs = [r for r in raw if not is_furniture(r)]
    marker = source["edition_marker"]
    edition = int(re.search(r"\d{4}", marker).group()) if marker else None

    def find(pred, start=0):
        return next(i for i in range(start, len(recs)) if pred(recs[i]))

    # Aims.
    a = find(lambda r: r["text"].startswith("The aims of the economics course"))
    aims = bullets(recs[a + 1:], stop_at_prose=True)

    # Key concepts: first 'Key concepts:' line in the syllabus, through the closing full stop.
    k = find(lambda r: r["text"].startswith("Key concepts:"))
    kc = [recs[k]]
    while not kc[-1]["text"].endswith("."):
        kc.append(recs[k + len(kc)])
    concept_text = joined(kc)
    concepts = [{"label": c.strip()} for c in
                concept_text.split(":", 1)[1].rstrip(".").split(",")]

    # Assessment objectives.
    s = find(lambda r: r["text"].startswith("By the end of the economics course"))
    aos, cur, item, hl_block = [], None, None, False

    def close():
        nonlocal item
        if item and item["_recs"]:
            text = joined(item.pop("_recs"))
            hl = hl_block if item["marker"] == "▪" else False
            if text.startswith("At HL only:"):
                rest = text.split(":", 1)[1].strip()
                if not rest:
                    item = None
                    return
                hl = True
            cur["bullets"].append({"text": text, "levels": ["HL"] if hl else ["SL", "HL"],
                                   **item["loc"]})
        item = None

    for r in recs[s + 1:]:
        t = r["text"]
        if t == "Assessment" and r["spans"][0]["bold"]:
            break
        if re.fullmatch(r"\d\.", t):
            continue
        m = AO_HDR.match(t)
        if m:
            close()
            cur = {"code": m.group(2), "title": m.group(1), "printed": t, **loc(r), "bullets": []}
            aos.append(cur)
            hl_block = False
            continue
        if t in ("•", "▪"):
            close()
            if t == "•":
                hl_block = False
            item = {"marker": t, "_recs": [], "loc": loc(r)}
            continue
        if item is not None:
            if not item["_recs"]:
                item["loc"] = loc(r)
            item["_recs"].append(r)
            if item["marker"] == "•" and joined(item["_recs"]) == "At HL only:":
                hl_block = True
    close()

    # Syllabus outline table.
    h = find(lambda r: r["text"] == "Syllabus component")
    end = find(lambda r: r["text"] == "Total teaching hours", h)
    units, unit, topic = [], None, None
    ia_hours, pending_ia, total = None, False, None
    for r in recs[h + 4:end + 3]:
        t, x = r["text"], r["bbox"][0]
        if t in ("Syllabus component", "Teaching hours", "SL", "HL"):
            continue
        if x >= SL_X - 10:
            level = "SL" if abs(x - SL_X) < 20 else "HL"
            target = unit["hours"] if not pending_ia else ia_hours.setdefault("hours", {})
            if r["page"] == recs[end]["page"] and recs.index(r) > end:
                total.setdefault("hours", {})[level] = int(t)
            else:
                target[level] = int(t)
            continue
        if t == "Total teaching hours":
            total = {"printed": t, **loc(r)}
            continue
        m = UNIT.match(t)
        if m:
            unit = {"number": int(m.group(1)), "title": m.group(2), **loc(r), "hours": {},
                    "topics": []}
            units.append(unit)
            topic = None
            continue
        if t == "Internal assessment":
            pending_ia, ia_hours = True, {"printed": t, **loc(r)}
            topic = None
            continue
        if pending_ia:
            ia_hours["component"] = t
            continue
        m = TOPIC.match(t)
        if m:
            topic = {"code": m.group(1), "_recs": [r]}
            unit["topics"].append(topic)
        elif topic is not None:
            topic["_recs"].append(r)
    for u in units:
        for tp in u["topics"]:
            rs = tp.pop("_recs")
            printed = joined(rs)
            body = printed.split(" ", 1)[1]
            n = NOTE.match(body)
            tp.update({"title": n.group(1) if n else body, "hl_note": n.group(2) if n else None,
                       "printed": printed, **span(rs)})

    # Assessment outlines: level from the page title in the unfiltered layer.
    outline_pages = {r["page"]: r["text"].rsplit("—", 1)[1] for r in raw
                     if r["text"] in ("Assessment outline—SL", "Assessment outline—HL")}
    components = []
    for page, level in sorted(outline_pages.items()):
        comp = None
        for r in [r for r in recs if r["page"] == page]:
            t = r["text"]
            m = PAPER.match(t)
            if m:
                comp = {"name": m.group(1), "level": level, "duration": m.group(2),
                        "weighting_pct": None, "aligned_aos": [], "lines": [], **loc(r)}
                components.append(comp)
                continue
            w = WEIGHT.match(t)
            if w and comp is not None and comp["weighting_pct"] is None:
                comp["weighting_pct"] = int(w.group(1))
                comp = None
                continue
            if comp is not None:
                if t.startswith("Assessment objectives:"):
                    comp["aligned_aos"] = re.findall(r"AO\d", t)
                comp["lines"].append(t)
        for c in components:
            if "lines" in c:
                c["description"] = joined([{"text": l} for l in c.pop("lines")])

    out = {
        "subject": "economics", "edition": edition, "levels": ["SL", "HL"],
        "source": source,
        "aims": aims,
        "concepts": concepts, "concepts_source": {"printed": concept_text, **span(kc)},
        "assessment_objectives": aos,
        "units": units,
        "internal_assessment_hours": ia_hours,
        "total_teaching_hours": total,
        "assessment_components": components,
    }
    path = args.layer / "skeleton.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(aims)} aims, {len(concepts)} concepts, {len(aos)} AOs "
          f"({sum(len(a['bullets']) for a in aos)} bullets), {len(units)} units / "
          f"{sum(len(u['topics']) for u in units)} topics, {len(components)} components")


if __name__ == "__main__":
    main()
