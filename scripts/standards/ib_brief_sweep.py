#!/usr/bin/env python3
"""Skeleton sweep across all current-edition DP subject briefs.

Tolerant, per-slot extraction with confidence flags — no hard validator. The
sweep's job is breadth (stand up every subject's skeleton + harvest concepts +
record per-family structure quirks); precision lands in the per-family depth
waves. Driven by scripts/standards/ib_editions.json.

Brief eras the parser tolerates:
  - 'z'-bullet era (Economics/BM 2022-24): '**Assessment objective N: Title**'
  - '•'-bullet era (sciences 2025+): '**Assessment objective N**' + imperative line
  - matrix/prose AO models (History 2028): raw section captured, ao_confidence=low

Usage:
    poetry run python scripts/standards/ib_brief_sweep.py \
        [--only subject1,subject2] [--editions scripts/standards/ib_editions.json]

Outputs: data/output/ib_native/<subject>/skeleton.json + data/output/ib_native/SWEEP_REPORT.md
"""
import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
BRIEFS = ROOT / "data/output/markdown/ib_briefs"
OUT = ROOT / "data/output/ib_native"

BULLET = re.compile(r"^(?:z|•|\d{1,2}\.)\s+(.+)$")
AO_TITLED = re.compile(r"^\*\*Assessment objective (\d):\s*(.+?)\*\*$")
AO_BARE = re.compile(r"^\*\*Assessment objective (\d)\*\*$")
HOURS_BOLD = re.compile(r"^\*\*(\d{1,3})\*\*$")


def split_sections(text):
    parts = re.split(r"^## ([IVX]+)\. .*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def clean_lines(sec):
    return [l.strip() for l in sec.splitlines() if l.strip()]


def collect_bullet(lines, i):
    out = [BULLET.match(lines[i]).group(1).strip()]
    i += 1
    while i < len(lines):
        ln = lines[i]
        if BULLET.match(ln) or ln.startswith(("**", "#", "##")) or ln == "---":
            break
        out.append(ln)
        i += 1
    return re.sub(r"\s+", " ", " ".join(out)).strip(), i


def extract_aims(sec1):
    lines = clean_lines(sec1)
    aims, in_aims, i = [], False, 0
    while i < len(lines):
        ln = lines[i]
        low = ln.lower()
        if "aims" in low and ("enable students" in low or low.rstrip("*").endswith("to:")
                              or "aims of" in low):
            in_aims = True
            i += 1
            continue
        if in_aims:
            if BULLET.match(ln):
                aim, i = collect_bullet(lines, i)
                aims.append(aim)
                continue
            if aims and (ln.startswith("#") or ln == "---"):
                break
        i += 1
    return aims, ("high" if len(aims) >= 3 else "low")


def extract_concepts(sec1, sec2):
    """Key/course concepts parentheticals or 'Key concepts' lead-ins, both sections."""
    found = []
    for sec in (sec1, sec2):
        flat = re.sub(r"\s+", " ", sec)
        for m in re.finditer(r"(?:key |course )?concepts(?:[^.()]{0,80})?\(([^)]{10,300})\)",
                             flat, re.I):
            raw = m.group(1)
            if raw.count(",") >= 2:
                parts = re.split(r",| and ", raw)
                found.extend(p.strip() for p in parts if 0 < len(p.strip()) <= 40)
        for m in re.finditer(r"\*\*Key concepts?\*\*[:\s]*([^*#]{10,300})", sec):
            parts = re.split(r",|;| and ", m.group(1))
            found.extend(p.strip(" .\n") for p in parts if 0 < len(p.strip(" .\n")) <= 40)
        for m in re.finditer(r"[Cc]oncepts such as ([^*#]{10,200}?)(?:\bare\b|\.|\*)", flat):
            parts = re.split(r",| and ", m.group(1))
            found.extend(p.strip() for p in parts if 0 < len(p.strip()) <= 40)
    dedup = list(dict.fromkeys(c.lower() for c in found if not any(ch.isdigit() for ch in c)))
    return dedup, ("high" if 3 <= len(dedup) <= 12 else ("none" if not dedup else "low"))


def extract_aos(sec3):
    lines = clean_lines(sec3)
    aos, i = [], 0
    while i < len(lines):
        m = AO_TITLED.match(lines[i]) or AO_BARE.match(lines[i])
        if not m:
            i += 1
            continue
        code = f"AO{m.group(1)}"
        title = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else ""
        i += 1
        bullets, desc = [], []
        while i < len(lines) and not (AO_TITLED.match(lines[i]) or AO_BARE.match(lines[i])):
            ln = lines[i]
            if ln.startswith(("**Type of", "## Assessment at a glance", "**Element**")) \
                    or ln.startswith("**About the IB"):
                break
            if BULLET.match(ln):
                b, i = collect_bullet(lines, i)
                bullets.append(b)
                continue
            if not ln.startswith(("#", "---", "©")) and len(ln) > 2 and not ln.isdigit():
                desc.append(ln)
            i += 1
        if not title and desc:
            title = re.sub(r"\s+", " ", " ".join(desc[:2])).strip().rstrip(":")
        if not any(a["code"] == code for a in aos):
            aos.append({"code": code, "title": title, "bullets": bullets})
    conf = "high" if len(aos) >= 3 else ("none" if not aos else "low")
    return aos, conf


def extract_components(sec3):
    """Assessment table rows: component label followed (within a few lines) by a
    weight percent. Works for both inline tables and 'Assessment at a glance'."""
    lines = clean_lines(sec3)
    comps, current = [], None
    pending_weight_gap = 0
    for ln in lines:
        name = None
        un = ln.strip("*").strip()
        if re.match(r"^Paper \d[A-B]?$", un) or un in (
                "Portfolio", "Internal assessment", "External assessment portfolio",
                "Individual oral", "Higher level essay", "Written assignment",
                "Exploration", "Solo theatre piece", "Collaborative project",
                "Production proposal", "Research presentation", "Comparative study",
                "Process portfolio", "Exhibition", "Composing", "Performing",
                "Exploring music in context", "Experimenting with music",
                "Presenting music", "The contemporary music-maker",
                "Scientific investigation", "Collaborative sciences project", "Essay"):
            name = un
        if name:
            current = {"name": name, "detail": [], "weighting_pct": None}
            comps.append(current)
            pending_weight_gap = 0
            continue
        if current is None:
            continue
        pending_weight_gap += 1
        m = re.match(r"^(\d{1,2}(?:\.\d)?)%?$", un)
        if m and current["weighting_pct"] is None and pending_weight_gap <= 10:
            v = float(m.group(1))
            if 5 <= v <= 80:
                current["weighting_pct"] = v
                continue
        if len(current["detail"]) < 6 and not ln.startswith(("#", "---")) and len(un) > 2:
            current["detail"].append(un)
    for c in comps:
        c["detail"] = re.sub(r"\s+", " ", " ".join(c["detail"]))[:300]
    conf = "high" if comps and sum(1 for c in comps if c["weighting_pct"]) >= 2 else \
        ("none" if not comps else "low")
    return comps, conf


def extract_curriculum_rows(sec2):
    """(label, hours) pairs from the section-II component/hours table."""
    lines = clean_lines(sec2)
    rows, label_buf = [], []
    for ln in lines:
        m = HOURS_BOLD.match(ln)
        if m and label_buf:
            label = re.sub(r"\s+", " ", " ".join(l.strip("*") for l in label_buf[-3:])).strip()
            rows.append({"label": label[:160], "hours": int(m.group(1))})
            label_buf = []
            continue
        if ln.startswith("**") and not HOURS_BOLD.match(ln):
            label_buf.append(ln)
        elif re.match(r"^\d\.\d+", ln) or (label_buf and not ln.startswith(("#", "---"))):
            continue
    conf = "high" if len(rows) >= 2 else ("none" if not rows else "low")
    return rows, conf


def detect_levels(text, n_briefs):
    if n_briefs == 2:
        return ["SL", "HL"]
    has_hl = bool(re.search(r"\bHL\b", text))
    has_sl = bool(re.search(r"\bSL\b", text))
    return (["SL", "HL"] if (has_hl and has_sl) else (["HL"] if has_hl else ["SL"]))


def sweep_subject(slug, meta):
    merged = {"subject": slug, "family": meta["family"], "edition": meta["edition"],
              "status": meta["status"], "note": meta.get("note", ""),
              "briefs": meta["briefs"], "levels": [],
              "aims": [], "concepts": [], "assessment_objectives": [],
              "assessment_components": [], "curriculum_rows": [],
              "confidence": {}}
    for brief in meta["briefs"]:
        text = (BRIEFS / brief).read_text(encoding="utf-8").replace("\xa0", " ")
        sec = split_sections(text)
        if "I" not in sec or "III" not in sec:
            merged["confidence"]["sections"] = "FAILED"
            continue
        s1, s2, s3 = sec.get("I", ""), sec.get("II", ""), sec.get("III", "")
        if not merged["aims"]:
            merged["aims"], merged["confidence"]["aims"] = extract_aims(s1)
        if not merged["concepts"]:
            merged["concepts"], merged["confidence"]["concepts"] = extract_concepts(s1, s2)
        if not merged["assessment_objectives"]:
            merged["assessment_objectives"], merged["confidence"]["aos"] = extract_aos(s3)
        comps, cconf = extract_components(s3)
        level = "HL" if re.search(r"—higher level\s*$", text, re.M) else \
            ("SL" if re.search(r"—standard level\s*$", text, re.M) else "both")
        for c in comps:
            c["level"] = level
        merged["assessment_components"].extend(comps)
        merged["confidence"]["components"] = cconf
        if not merged["curriculum_rows"]:
            merged["curriculum_rows"], merged["confidence"]["curriculum"] = \
                extract_curriculum_rows(s2)
        merged["levels"] = detect_levels(text, len(meta["briefs"])) \
            if not merged["levels"] else merged["levels"]
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--editions", default=str(pathlib.Path(__file__).parent / "ib_editions.json"))
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    editions = json.load(open(args.editions))["subjects"]
    only = set(filter(None, args.only.split(",")))

    report = ["# DP brief skeleton sweep — coverage report (2026-06-10)", "",
              "| subject | family | ed. | aims | concepts | AOs | components | curric | note |",
              "|---|---|---|---|---|---|---|---|---|"]
    for slug, meta in editions.items():
        if only and slug not in only:
            continue
        if not meta["briefs"]:
            report.append(f"| {slug} | {meta['family']} | {meta['edition']} | — | — | — | — | — | NO BRIEF: {meta.get('note','')} |")
            continue
        if slug == "economics":
            report.append(f"| economics | individuals_societies | 2022 | done | done | done | done | done | PILOT (full skeleton+depth in Hub) |")
            continue
        sk = sweep_subject(slug, meta)
        out = OUT / slug / "skeleton.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(sk, indent=1, ensure_ascii=False), encoding="utf-8")
        c = sk["confidence"]
        report.append(
            f"| {slug} | {sk['family']} | {sk['edition']} | "
            f"{len(sk['aims'])} ({c.get('aims','-')}) | "
            f"{len(sk['concepts'])} ({c.get('concepts','-')}) | "
            f"{len(sk['assessment_objectives'])} ({c.get('aos','-')}) | "
            f"{len(sk['assessment_components'])} ({c.get('components','-')}) | "
            f"{len(sk['curriculum_rows'])} ({c.get('curriculum','-')}) | {sk['note']} |")
    (OUT / "SWEEP_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
