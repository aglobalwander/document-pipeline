#!/usr/bin/env python3
"""Extract syllabus depth from the DP Visual Arts guide (first assessment 2027).

The 2027 guide prints no statement codes. Depth is what the syllabus prints:

  assessment_objectives  the seven bullets under 'Assessment objectives' (lead verb kept)
  core_areas             Create / Connect / Communicate: 'requires learning and teaching about' bullets
  key_terms              'Art-making as inquiry: Key terms' through 'Critical analysis': each term
                         with its printed text
  objective_framework    'Assessment objectives as a framework': Curate ... Synthesize, each with
                         word cloud, definition sentence, guiding questions and printed text

Reads the text layer written by km_text_layer.py, so every item keeps PDF page and bbox.
'page' is the PDF page (1-based), not the printed folio. Figure content is image-only in this
PDF; captions are kept as printed, figure contents are not read.

Usage:
    poetry run python scripts/standards/ib_va_extract.py \
        --layer data/output/km_requests/2026-09-17/p1_ib_guides/<sha>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ib_tok_extract import LEFT_MARGIN, Items, is_furniture, union

CORE_AREAS = ["Create", "Connect", "Communicate"]
STRANDS = ["Curate", "Investigate", "Generate", "Situate", "Refine", "Resolve", "Synthesize"]


def size(r: dict) -> float:
    return max(s["size"] for s in r["spans"])


def all_bold(r: dict) -> bool:
    return all(s["bold"] for s in r["spans"])


def joined(recs: list[dict]) -> str:
    return re.sub(r"\s+", " ", " ".join(r["text"] for r in recs if r["text"] != "•")).strip()


def span(recs: list[dict]) -> dict:
    first = recs[0]["page"]
    out = {"page": first, "bbox": union([r["bbox"] for r in recs if r["page"] == first])}
    later = sorted({r["page"] for r in recs} - {first})
    if later:
        out["continues_on_pages"] = later
    return out


def bullets(recs: list[dict], stop_at_prose: bool = False) -> list[dict]:
    items = Items()
    for r in recs:
        if r["text"] == "•":
            items.start(None)
        elif not items.add(r) and r["bbox"][0] <= LEFT_MARGIN:
            items.close()
            if stop_at_prose and items.items:
                break
    items.close()
    return items.items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True, type=Path)
    args = ap.parse_args()

    source = json.loads((args.layer / "source.json").read_text(encoding="utf-8"))
    recs = [json.loads(l) for l in (args.layer / "text_layer.jsonl").open(encoding="utf-8")]
    recs = [r for r in recs if not is_furniture(r)]

    def index(text: str, min_size: float, start: int = 0) -> int:
        return next(i for i in range(start, len(recs))
                    if recs[i]["text"] == text and size(recs[i]) >= min_size)

    # Assessment objectives: bullets after the 'Students are expected to evidence' stem, to the
    # first line back at the left margin.
    stem = next(i for i, r in enumerate(recs) if r["text"].startswith("Students are expected to evidence"))
    aos = []
    for item in bullets(recs[stem + 1:index("A practice-based syllabus", 17)], stop_at_prose=True):
        item["verb"] = item["text"].split()[0]
        aos.append(item)

    # Core areas.
    core_areas = []
    integrating = index("Integrating the core areas: Art-making as inquiry", 17)
    starts = [index(name, 12.5) for name in CORE_AREAS] + [integrating]
    for name, a, b in zip(CORE_AREAS, starts, starts[1:]):
        body = recs[a + 1:b]
        stem_i = next(i for i, r in enumerate(body) if r["text"].startswith("This core area requires"))
        items = bullets(body[stem_i + 1:], stop_at_prose=True)
        core_areas.append({"title": name, **span([recs[a]]), "stem": body[stem_i]["text"],
                           "learning_and_teaching": items, "text": joined(body)})

    # Key terms: size-14 headings and stand-alone bold titles between the key-terms heading
    # and 'Assessment objectives as a framework'.
    kt_start = index("Art-making as inquiry: Key terms", 12.5)
    framework = index("Assessment objectives as a framework", 17)
    key_terms, cur = [], None
    for r in recs[kt_start + 1:framework]:
        title = size(r) >= 12.5 or (
            all_bold(r) and len(r["text"]) < 60 and not r["text"].endswith((".", ",", ":"))
            and r["bbox"][0] <= LEFT_MARGIN)
        if title:
            cur = {"term": r["text"], **span([r]), "_recs": []}
            key_terms.append(cur)
        elif cur is not None:
            cur["_recs"].append(r)
    for kt in key_terms:
        body = kt.pop("_recs")
        kt["text"] = joined(body)
        kt["bullets"] = bullets(body)

    # Objective framework strands.
    end = index("Engaging, transforming and emerging as artists", 17)
    strand_starts = [index(name, 12.5, framework) for name in STRANDS] + [end]
    strands = []
    for name, a, b in zip(STRANDS, strand_starts, strand_starts[1:]):
        body = recs[a + 1:b]
        wc_i = next(i for i, r in enumerate(body) if r["text"].startswith("Word cloud:"))
        wc = [body[wc_i]]
        j = wc_i + 1
        while j < len(body) and not re.match(rf"To {name.lower()}\b", body[j]["text"]):
            wc.append(body[j])
            j += 1
        definition = []
        while j < len(body):
            definition.append(body[j])
            if body[j]["text"].endswith("."):
                break
            j += 1
        gq = next((i for i, r in enumerate(body) if r["text"] == "Suggested guiding questions"), None)
        questions = bullets(body[gq + 1:], stop_at_prose=True) if gq is not None else []
        strands.append({
            "strand": name, **span([recs[a]]),
            "word_cloud": [w.strip() for w in joined(wc).split(":", 1)[1].split(",")],
            "word_cloud_source": span(wc),
            "definition": joined(definition), "definition_source": span(definition),
            "guiding_questions": questions,
            "text": joined(body),
        })

    out = {"subject": "visual_arts", "source": source,
           "assessment_objectives": {"stem": recs[stem]["text"], "numbered_in_guide": False,
                                     "items": aos},
           "core_areas": core_areas, "key_terms": key_terms, "objective_framework": strands}
    path = args.layer / "depth.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(aos)} AOs; core areas "
          + ", ".join(f"{c['title']} {len(c['learning_and_teaching'])}" for c in core_areas)
          + f"; {len(key_terms)} key terms; strands "
          + ", ".join(f"{s['strand']} {len(s['guiding_questions'])}q" for s in strands))


if __name__ == "__main__":
    main()
