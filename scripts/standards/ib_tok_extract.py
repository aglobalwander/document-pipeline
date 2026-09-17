#!/usr/bin/env python3
"""Extract what the DP Theory of Knowledge guide (first assessment 2022) prints.

Reads the text layer written by km_text_layer.py (text_layer.jsonl + source.json) rather than
markdown, so every item keeps its PDF page and bbox. Shape follows the guide, not a subject
template:

  assessment_objectives   the unnumbered bullets under 'Assessment objectives'
  knowledge_framework     'Examples of knowledge questions' page: KQs per element
  themes                  core theme, five optional themes, five areas of knowledge; each with
                          its example knowledge questions per element (scope, perspectives,
                          methods and tools, ethics) and 'Making connections to the core theme'

Page furniture (running page titles, footers, page numbers) is dropped by position.
'page' is the PDF page (1-based), not the printed folio.

Usage:
    poetry run python scripts/standards/ib_tok_extract.py \
        --layer data/output/km_requests/2026-09-17/p1_ib_guides/<sha>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CORE = "Core theme: Knowledge and the knower"
OPTIONAL = ["Knowledge and technology", "Knowledge and language", "Knowledge and politics",
            "Knowledge and religion", "Knowledge and indigenous societies"]
AOK = ["History", "The human sciences", "The natural sciences", "The arts", "Mathematics"]
ELEMENT = re.compile(r"^(Scope|Perspectives|Methods and [Tt]ools|Ethics)\s*(•)?$")
LEFT_MARGIN = 90  # body prose starts at x=85; table and bullet text sit further right
CONNECTION_ELEMENT = re.compile(r"\((scope|perspectives|methods and tools|ethics)\)$")


def is_furniture(rec: dict) -> bool:
    y0, y1 = rec["bbox"][1], rec["bbox"][3]
    size = max(s["size"] for s in rec["spans"])
    return y1 < 70 or y0 > 790 or (size >= 18.5 and size < 19.5 and y0 < 110)


def union(boxes: list[list[float]]) -> list[float]:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


class Items:
    """Accumulate bullet items; continuation lines sit at or right of the first text line."""

    def __init__(self):
        self.items: list[dict] = []
        self.open: dict | None = None

    def start(self, element: str | None, dest: list[dict] | None = None):
        self.close()
        self.open = {"element": element, "parts": [], "anchors": [],
                     "dest": self.items if dest is None else dest}

    def add(self, rec: dict) -> bool:
        if self.open is None:
            return False
        if self.open["parts"] and rec["bbox"][0] < self.open["anchors"][0]["bbox"][0] - 2:
            self.close()
            return False
        self.open["parts"].append(rec["text"])
        self.open["anchors"].append(rec)
        return True

    def close(self):
        if self.open and self.open["parts"]:
            pages = sorted({a["page"] for a in self.open["anchors"]})
            item = {"text": re.sub(r"\s+", " ", " ".join(self.open["parts"])).strip(),
                    "page": pages[0],
                    "bbox": union([a["bbox"] for a in self.open["anchors"]
                                   if a["page"] == pages[0]])}
            if len(pages) > 1:
                item["continues_on_pages"] = pages[1:]
            if self.open["element"] is not None:
                item["element"] = self.open["element"]
            self.open["dest"].append(item)
        self.open = None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True, type=Path)
    args = ap.parse_args()

    source = json.loads((args.layer / "source.json").read_text(encoding="utf-8"))
    recs = [json.loads(l) for l in (args.layer / "text_layer.jsonl").open(encoding="utf-8")]
    recs = [r for r in recs if not is_furniture(r)]

    def big(r):
        return max(s["size"] for s in r["spans"]) >= 17

    # Assessment objectives: bullets after the 'Having completed the TOK course' stem, up to
    # the 'Course elements' table.
    aos = Items()
    ao_stem = None
    mode = None
    for r in recs:
        if r["text"].startswith("Having completed the TOK course"):
            ao_stem, mode = r, "ao"
            continue
        if mode == "ao":
            if r["text"] == "Course elements" or big(r):
                break
            if r["text"] == "•":
                aos.start(None)
            else:
                aos.add(r)
    aos.close()

    sections: list[dict] = []
    framework = None
    cur = None
    items = Items()
    element = None
    stage = None  # None | 'intro' | 'kq' | 'connections'

    for r in recs:
        t = r["text"]
        if big(r):
            items.close()
            element = None
            if t in [CORE, *OPTIONAL, *AOK, "Examples of knowledge questions"]:
                kind = ("knowledge_framework" if t == "Examples of knowledge questions" else
                        "core" if t == CORE else "optional" if t in OPTIONAL else
                        "area_of_knowledge")
                cur = {"kind": kind, "title": t, "page": r["page"], "bbox": r["bbox"],
                       "knowledge_questions": [], "core_connections": []}
                if kind == "knowledge_framework":
                    framework, stage = cur, "kq"
                else:
                    sections.append(cur)
                    stage = "intro"
            else:  # any other section heading ends the current one
                cur, stage = None, None
            continue
        if cur is None:
            continue
        if t == "Examples of knowledge questions":
            if stage != "kq":  # repeated as a table header on continuation pages
                items.close()
                stage = "kq"
            continue
        if t == "Making connections to the core theme":
            items.close()
            stage, element = "connections", None
            continue
        m = ELEMENT.match(t)
        if m and stage != "connections":
            items.close()
            stage, element = "kq", m.group(1).lower()
            if m.group(2):
                items.start(element, cur["knowledge_questions"])
            continue
        if stage not in ("kq", "connections"):
            continue
        dest = cur["knowledge_questions"] if stage == "kq" else cur["core_connections"]
        if t == "•":
            items.start(element if stage == "kq" else None, dest)
            continue
        if not items.add(r) and r["bbox"][0] <= LEFT_MARGIN and cur["kind"] != "knowledge_framework":
            # prose at the left margin ends a question table or connections list
            stage = "intro"
    items.close()

    for s in sections:
        for c in s["core_connections"]:
            m = CONNECTION_ELEMENT.search(c["text"])
            c["element"] = m.group(1) if m else None

    out = {
        "subject": "theory_of_knowledge",
        "source": source,
        "assessment_objectives": {
            "stem": ao_stem["text"] if ao_stem else None,
            "numbered_in_guide": False,
            "items": aos.items,
        },
        "knowledge_framework": framework,
        "themes": sections,
    }
    path = args.layer / "tok.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(aos.items)} AOs; "
          + "; ".join(f"{s['title']} {len(s['knowledge_questions'])} KQ/"
                      f"{len(s['core_connections'])} conn" for s in sections))


if __name__ == "__main__":
    main()
