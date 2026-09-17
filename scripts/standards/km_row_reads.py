#!/usr/bin/env python3
"""KM request P3 (2026-09-17): read the printed text for named rows, with page, bbox and a crop.

Input: KM's p3_row_reads.csv (request_id, framework, key, sha256, store_file, page_or_ref,
canon_text, hub_text, reason). canon_text and hub_text are search aids, not candidates: the text
returned is always words from this PDF's own text layer.

For each row:
  1. resolve the sha through the store MANIFEST and verify the bytes (km_text_layer.resolve);
  2. turn page_or_ref into expected PDF pages:
       '34', '... .pdf p31'               -> that page (searched with a +/-2 window)
       'ap-x.md L2809'                    -> the '=== Page N ===' marker above line 2809 in KM's
                                             AP source snapshot
       'biology_2025.md L1220-L1225 ...'  -> those lines of KM's guide markdown (fidelity_sweep
                                             handoff) become the search aid; all pages searched
       anything else                      -> whole document
  3. anchor read: find the key's code as printed (e.g. 'LO 1.8.B', 'PIT-1.A.1', 'Unit 4: Learning
     Objective I') and read the column beneath or beside it row by row, stopping at the next code,
     a heading, a large vertical gap or the page end;
  4. if no anchor reads well, align the aid's tokens to the page word stream and keep the densest
     matched run, restricted to the column it sits in.

Scores, both on normalised tokens:
  printed_in_aid  share of the printed words that the aid also has (low = we read the wrong place)
  aid_in_printed  share of the aid's words found in what is printed (low = the aid carries debris,
                  or the printed text is only part of it)
Status 'read' for aids of 20+ tokens when printed_in_aid >= 0.9 and aid_in_printed >= 0.6, or both
>= 0.8; for shorter aids when printed_in_aid >= 0.9 and aid_in_printed >= 0.95; or (anchor reads
only) printed_in_aid >= 0.9 with at least five printed words; 'review' when the better of the two
is >= 0.5; 'not_in_document' when no six-word run of the aid is printed anywhere in the sha;
'not_in_named_document' when the named sha does not print it but another sha of the same framework
in the request does (that read is attached); else 'not_found'. No OCR, no model.

Usage:
    poetry run python scripts/standards/km_row_reads.py --csv <p3_row_reads.csv> [--only P3-0001]
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pymupdf

from km_text_layer import OUT_ROOT, STORE, resolve

KM = Path.home() / "Development/_01_hubs/knowledge-management/research/standards_frameworks"
AP_SNAPSHOTS = KM / "deconstructing_standards/audits/2026-08-16-ap-ib-full-wave/source_snapshots/ap"
IB_GUIDES = KM / "fidelity_sweep/hub_source_handoff_2026-09-04/guides_markdown"  # KM's line numbers
REQUEST = "p3_row_reads"
CODE_START = re.compile(r"^(LO|EK|[A-Z]{2,4}-\d+(\.[A-Z0-9]+)*(\.[ivx]+)?|"
                        r"\d+\.\d+\.[A-Z](\.\d+)?(\.[ivx]+)?|KC-[\w.]+|Unit)$")
HEADING = re.compile(r"^[A-Z][A-Z&/]{3,}$")


def norm(tok: str) -> str:
    tok = unicodedata.normalize("NFKC", tok).replace("’", "'").replace("‘", "'")
    return re.sub(r"[^0-9a-z]", "", tok.lower())


def tokens(text: str) -> list[str]:
    return [t for t in (norm(w) for w in re.split(r"[\s/–—-]+", text)) if t]


@lru_cache(maxsize=None)
def document(sha: str) -> tuple[dict, pymupdf.Document]:
    row, data = resolve(sha, STORE)
    return row, pymupdf.open(stream=data, filetype="pdf")


def furniture_free(page: pymupdf.Page) -> list[tuple]:
    """Words minus running headers/footers (top/bottom 6% of the page) and the
    'continued on next page' marker, which are page furniture rather than row text."""
    h = page.rect.height
    words = [w for w in page.get_text("words", sort=False) if h * 0.06 < w[3] and w[1] < h * 0.94]
    drop = set()
    for i in range(len(words) - 3):
        if [w[4].lower() for w in words[i:i + 4]] == ["continued", "on", "next", "page"]:
            drop.update(range(i, i + 4))
    return [w for i, w in enumerate(words) if i not in drop]


@lru_cache(maxsize=None)
def page_words(sha: str, pno: int) -> list[dict]:
    _, doc = document(sha)
    out = []
    for i, w in enumerate(furniture_free(doc[pno - 1])):
        for piece in re.split(r"(?<=[/–—-])|(?=[–—])", w[4]):
            if norm(piece):
                out.append({"text": w[4], "piece": piece, "tok": norm(piece), "page": pno,
                            "bbox": [round(v, 1) for v in w[:4]], "wid": (pno, i)})
    return out


@lru_cache(maxsize=None)
def page_rows(sha: str, pno: int) -> list[list[dict]]:
    """Whole words grouped into visual rows (top-to-bottom, left-to-right)."""
    _, doc = document(sha)
    words = sorted(({"text": w[4], "bbox": [round(v, 1) for v in w[:4]], "page": pno}
                    for w in furniture_free(doc[pno - 1])),
                   key=lambda w: (w["bbox"][3], w["bbox"][0]))
    rows: list[list[dict]] = []
    for w in words:
        if rows and abs(rows[-1][0]["bbox"][3] - w["bbox"][3]) <= 2.5:
            rows[-1].append(w)
        else:
            rows.append([w])
    for r in rows:
        r.sort(key=lambda w: w["bbox"][0])
    return rows


def ref_pages_and_aid(ref: str, subject: str = "") -> tuple[list[int] | None, str | None, str]:
    ref = ref.strip()
    if re.fullmatch(r"\d+", ref):
        return [int(ref)], None, "page_or_ref page number"
    m = re.match(r"^(ap-[\w-]+\.md) L(\d+)", ref)
    if m:
        path = AP_SNAPSHOTS / m.group(1)
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            for i in range(int(m.group(2)) - 1, -1, -1):
                mk = re.match(r"=== Page (\d+) ===", lines[i])
                if mk:
                    return [int(mk.group(1))], None, f"page marker above {m.group(1)} L{m.group(2)}"
        return None, None, f"{m.group(1)} not found; searched all pages"
    m = re.search(r"\.pdf (?:sha256 \S+ )?pp?\.?(\d+)", ref)
    if m:
        return [int(m.group(1))], None, f"PDF page p{m.group(1)} named in page_or_ref"
    m = re.match(r"^([\w]+\.md) L(\d+)(?:-L?(\d+))?", ref) or \
        re.search(r"([\w]+_\d{4}\.md) (?:lines? )?(\d+)(?:-(\d+))?", ref)
    if not m and subject and re.search(r"\bmd (\d+)(?:-(\d+))?", ref):
        mm = re.search(r"\bmd (\d+)(?:-(\d+))?", ref)
        hits = sorted(IB_GUIDES.glob(f"{subject}_*.md")) or sorted(IB_GUIDES.glob(f"{subject}.md"))
        if hits:
            m = re.match(r"(\S+) (\d+)(?: (\d+))?$", f"{hits[0].name} {mm.group(1)} {mm.group(2) or ''}".strip())
    if m:
        path = IB_GUIDES / m.group(1)
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            a, b = int(m.group(2)), int(m.group(3) or m.group(2))
            aid = " ".join(re.sub(r"<br>|[|*#]", " ", l).strip() for l in lines[a - 1:b])
            return None, aid, (f"aid = KM guide markdown {m.group(1)} L{a}-L{b}; that markdown has no "
                               "page breaks, so all pages were searched")
        return None, None, f"{m.group(1)} not found; searched all pages"
    return None, None, "no usable page in page_or_ref; searched all pages"


def score(printed: str, aid_toks: list[str]) -> tuple[float, float]:
    pt = tokens(printed)
    if not pt or not aid_toks:
        return 0.0, 0.0
    sm = difflib.SequenceMatcher(None, pt, aid_toks, autojunk=False)
    same = sum(b.size for b in sm.get_matching_blocks())
    return round(same / len(pt), 3), round(same / len(aid_toks), 3)


def status_for(p_in_a: float, a_in_p: float, aid_len: int = 99) -> str:
    if aid_len < 20:  # a short aid must be printed nearly whole: one wrong word matters
        if p_in_a >= 0.9 and a_in_p >= 0.95:
            return "read"
    elif (p_in_a >= 0.9 and a_in_p >= 0.6) or (p_in_a >= 0.8 and a_in_p >= 0.8):
        return "read"
    return "review" if max(p_in_a, a_in_p) >= 0.5 else "not_found"


def code_of(key: str) -> list[str]:
    tail = key.split("|", 1)[-1].strip()
    m = re.match(r"^Unit (\d+): Learning Objective ([A-Z])$", tail)
    if m:
        return ["Unit", f"{m.group(1)}:", "Learning", "Objective", m.group(2)]
    tail = re.sub(r"^LO\s+", "", tail)
    return [tail] if re.search(r"\d", tail) and " " not in tail else []


@lru_cache(maxsize=None)
def page_edges(sha: str, pno: int) -> list[float]:
    """Recurring left edges of text runs on the page (column starts)."""
    counts: Counter = Counter()
    for row in page_rows(sha, pno):
        prev = None
        for w in row:
            if prev is None or w["bbox"][0] - prev["bbox"][2] > 5:
                counts[round(w["bbox"][0] / 3) * 3] += 1
            prev = w
    return sorted(x for x, n in counts.items() if n >= 3)


def anchor_reads(sha: str, pno: int, code: list[str]) -> list[dict]:
    """Every place on the page where the code is printed, with the column text read after it."""
    rows = page_rows(sha, pno)
    edges = page_edges(sha, pno)
    width = document(sha)[1][pno - 1].rect.width
    found = []
    for ri, row in enumerate(rows):
        texts = [w["text"].rstrip(":.,") if len(code) == 1 else w["text"] for w in row]
        for wi in range(len(row) - len(code) + 1):
            if len(code) == 1:
                hit = texts[wi] == code[0]
            else:
                hit = [t.rstrip() for t in texts[wi:wi + len(code)]] == code
            if not hit:
                continue
            anchor = row[wi + len(code) - 1]
            label = wi - 1 if wi and row[wi - 1]["text"] in ("LO", "EK", "EU", "LO:", "EK:") else wi
            left = row[label]["bbox"][0]
            words, colx, right = [], None, None
            same_row = row[wi + len(code):]
            if same_row and same_row[0]["bbox"][0] - anchor["bbox"][2] < 14 \
                    and not CODE_START.match(same_row[0]["text"].rstrip(":.")):
                colx = same_row[0]["bbox"][0]
                right = next((e for e in edges if e > colx + 30), width)
                words += [w for w in same_row if w["bbox"][0] < right - 3]
            last_bottom = anchor["bbox"][3]
            line_h = anchor["bbox"][3] - anchor["bbox"][1]
            for nxt in rows[ri + 1:]:
                if min(w["bbox"][1] for w in nxt) - last_bottom > 6 * line_h:
                    break
                if colx is None:
                    start = [w for w in nxt if left - 6 <= w["bbox"][0] <= left + 40]
                    if not start:
                        continue
                    colx = start[0]["bbox"][0]
                    right = next((e for e in edges if e > colx + 30), width)
                run = [w for w in nxt if colx - 4 <= w["bbox"][0] < right - 3]
                if not run:
                    continue  # another column's line (offset baseline); keep looking below
                if min(w["bbox"][1] for w in run) - last_bottom > 2.6 * line_h:
                    break  # vertical gap inside the column: the statement has ended
                t0 = run[0]["text"].rstrip(":.")
                if words and abs(run[0]["bbox"][0] - colx) <= 6 and (CODE_START.match(t0) or HEADING.match(t0)):
                    break
                words += run
                last_bottom = max(w["bbox"][3] for w in run)
            if words:
                found.append({"anchor": " ".join(w["text"] for w in row[wi:wi + len(code)]),
                              "anchor_bbox": anchor["bbox"], "column": [colx, right],
                              "words": words})
    return found


def aid_gaps(printed: str, aid_toks: list[str]) -> int:
    """Aid tokens skipped inside the stretch the printed words align to (dropped words)."""
    sm = difflib.SequenceMatcher(None, tokens(printed), aid_toks, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    return sum(max(0, (b2.b - (b1.b + b1.size)) - (b2.a - (b1.a + b1.size)))
               for b1, b2 in zip(blocks, blocks[1:]))


def align(aid_toks: list[str], words: list[dict]) -> tuple[int, int, int, set[int]] | None:
    doc_toks = [w["tok"] for w in words]
    sm = difflib.SequenceMatcher(None, aid_toks, doc_toks, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    if not blocks:
        return None
    best = None
    for i, seed in enumerate(blocks):
        run = [seed]
        for b in blocks[i + 1:]:
            last = run[-1]
            if b.b - (last.b + last.size) <= 8 and 0 <= b.a - (last.a + last.size) <= 12:
                run.append(b)
            elif b.b > last.b + last.size + 8:
                break
        matched = sum(b.size for b in run)
        if best is None or matched > best[0]:
            best = (matched, run)
    matched, run = best
    return run[0].b, run[-1].b + run[-1].size, matched, {b.a + k for b in run for k in range(b.size)}


def alignment_read(sha: str, pages: list[int], aid_toks: list[str]) -> list[dict] | None:
    best = None
    for p in pages:
        words = [w for q in (p, p + 1) if q <= document(sha)[1].page_count for w in page_words(sha, q)]
        res = align(aid_toks, words)
        if not res:
            continue
        start, end, matched, _ = res
        span = words[start:end]
        hits = [w for w in span if w["tok"] in set(aid_toks)]
        if hits:  # restrict to the column the run sits in, re-sorted by line
            x0 = min(w["bbox"][0] for w in hits) - 4
            x1 = max(w["bbox"][2] for w in hits) + 4
            col = sorted((w for w in words if x0 <= (w["bbox"][0] + w["bbox"][2]) / 2 <= x1),
                         key=lambda w: (w["page"], round(w["bbox"][3] / 3), w["bbox"][0]))
            res2 = align(aid_toks, col)
            if res2 and res2[2] >= matched:
                span, matched = col[res2[0]:res2[1]], res2[2]
        if best is None or matched > best[0]:
            best = (matched, span)
    if not best:
        return None
    out, seen = [], set()
    for w in best[1]:
        if w["wid"] not in seen:
            out.append({"text": w["text"], "bbox": w["bbox"], "page": w["page"]})
            seen.add(w["wid"])
    return out


def emit(out: dict, words: list[dict], aid_toks: list[str], crops: Path, rid: str, method: str) -> dict:
    _, doc = document(out["pdf_sha256"])
    printed = " ".join(w["text"] for w in words)
    p_in_a, a_in_p = score(printed, aid_toks)
    regions = []
    for p in sorted({w["page"] for w in words}):
        boxes = [w["bbox"] for w in words if w["page"] == p]
        bbox = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes)]
        crop = crops / f"{rid}_p{p}.png"
        clip = (pymupdf.Rect(bbox) + (-6, -6, 6, 6)) & doc[p - 1].rect
        doc[p - 1].get_pixmap(dpi=150, clip=clip).save(crop)
        regions.append({"page": p, "bbox": bbox, "crop": str(crop.relative_to(crops.parent))})
    status = status_for(p_in_a, a_in_p, len(aid_toks))
    gaps = aid_gaps(printed, aid_toks) if aid_toks else 0
    if status == "read" and gaps > 2:
        status = "review"  # the printed run skips words the aid has inside the same stretch
    aid_set = set(tokens(printed))
    out.update(status=status, read_method=method,
               printed_text=printed if status != "not_found" else None,
               candidate_text=printed if status == "not_found" else None,
               regions=regions, printed_in_aid=p_in_a, aid_in_printed=a_in_p, aid_words_skipped=gaps,
               aid_tokens_not_printed=[t for t in aid_toks if t not in aid_set][:40])
    return out


def gold_read(r: dict, out: dict, crops: Path) -> dict | None:
    """GOLD objectives: read the printed heading for the key's number (and dimension letter).

    Page 2 lists objectives as 'N. title' with lettered dimensions; objective pages print
    'Objective N' + title, then dimension headings 'a. ...' at the left margin."""
    m = re.match(r"^GOLD\.(\d+)([a-z])?$", r["key"])
    ref = r["page_or_ref"].strip()
    if not m or not ref.isdigit():
        return None
    n, letter, page = m.group(1), m.group(2), int(ref)
    sha = r["sha256"]
    doc = document(sha)[1]

    def row_words_right(rows, row, start_w, gap=22):
        """Words to the right of start_w on its visual line (tolerating a small baseline shift)."""
        y = (start_w["bbox"][1] + start_w["bbox"][3]) / 2
        line = sorted((w for rr in rows for w in rr
                       if abs((w["bbox"][1] + w["bbox"][3]) / 2 - y) < 6 and w["bbox"][0] > start_w["bbox"][0]),
                      key=lambda w: w["bbox"][0])
        run, last = [], start_w
        for w in line:
            if w["bbox"][0] - last["bbox"][2] > gap or re.fullmatch(r"\d+\.", w["text"]):
                break
            run.append(w)
            last = w
        return run

    if page == 2 or not any("Objective" == w["text"] for rr in page_rows(sha, page) for w in rr):
        rows = page_rows(sha, page)
        for row in rows:
            for w in row:
                if w["text"] == f"{n}.":
                    words = [w] + row_words_right(rows, row, w)
                    x_title = words[1]["bbox"][0] if len(words) > 1 else w["bbox"][2]
                    last_b = max(x["bbox"][3] for x in words)
                    for rr in rows[rows.index(row) + 1:]:
                        cont = [x for x in rr if abs(x["bbox"][0] - (x_title + 18)) < 4 or abs(x["bbox"][0] - x_title) < 4]
                        if not cont or cont[0]["bbox"][1] - last_b > 8:
                            if rr[0]["bbox"][1] - last_b > 20:
                                break
                            continue
                        if re.fullmatch(r"\d+\.", cont[0]["text"]) or any(
                                re.fullmatch(r"\d+\.", x["text"]) and x_title - 30 <= x["bbox"][0] < cont[0]["bbox"][0]
                                for x in rr):
                            break  # the next numbered objective begins on this line
                        seg = [cont[0]]
                        for x in rr[rr.index(cont[0]) + 1:]:
                            if x["bbox"][0] - seg[-1]["bbox"][2] > 22 or re.fullmatch(r"\d+\.", x["text"]):
                                break
                            seg.append(x)
                        if re.fullmatch(r"[a-z]\.", seg[0]["text"]) or abs(seg[0]["bbox"][0] - x_title) < 4:
                            words += seg
                            last_b = max(x["bbox"][3] for x in seg)
                    out["anchor"] = {"text": f"{n}.", "page": page, "bbox": w["bbox"]}
                    res = emit(out, words, [], crops, r["request_id"], "gold_list_entry")
                    res.update(status="read", printed_text=" ".join(x["text"] for x in words),
                               candidate_text=None,
                               note="read at the printed objective number in the objectives list; "
                                    "canon_text is empty or a KM note, so there is no aid to score")
                    return res
        return None

    for p in [q for q in range(page - 2, page + 3) if 1 <= q <= doc.page_count]:
        rows = page_rows(sha, p)
        for row in rows:
            for i, w in enumerate(row[:-1]):
                if w["text"] == "Objective" and row[i + 1]["text"] == n:
                    head = [w, row[i + 1]] + row_words_right(rows, row, row[i + 1], gap=40)
                    words = list(head)
                    # dimension headings at the left margin until the next objective
                    for q in range(p, min(p + 4, doc.page_count) + 1):
                        stop = False
                        for rr in page_rows(sha, q):
                            if q == p and rr[0]["bbox"][1] <= head[0]["bbox"][3]:
                                continue
                            if rr[0]["text"] == "Objective" and len(rr) > 1 and rr[1]["text"] != n:
                                stop = True
                                break
                            if re.fullmatch(r"[a-z]\.", rr[0]["text"]) and rr[0]["bbox"][0] < 60:
                                if letter and rr[0]["text"] != f"{letter}.":
                                    continue
                                seg = [rr[0]]
                                for x in rr[1:]:
                                    if x["bbox"][0] - seg[-1]["bbox"][2] > 22:
                                        break
                                    seg.append(x)
                                words += seg
                        if stop:
                            break
                    out["anchor"] = {"text": f"Objective {n}", "page": p, "bbox": w["bbox"]}
                    res = emit(out, words, [], crops, r["request_id"], "gold_objective_heading")
                    res.update(status="read", printed_text=" ".join(x["text"] for x in words),
                               candidate_text=None,
                               note="objective heading and dimension headings as printed; canon_text is "
                                    "a KM note, not a quotation, so there is no aid to score"
                                    + ("; dimension letter selected" if letter else ""))
                    return res
    return None


def read_row(r: dict, crops: Path) -> dict:
    sha = r["sha256"]
    meta, doc = document(sha)
    pages, md_aid, page_basis = ref_pages_and_aid(r["page_or_ref"], r["key"].split("|")[0])
    aid_source = ("markdown lines named in page_or_ref" if md_aid else "canon_text"
                  if r["canon_text"].strip() else "hub_text" if r["hub_text"].strip() else None)
    aid = md_aid or r["canon_text"].strip() or r["hub_text"].strip()
    if r["framework"] == "wida":
        # The key is a Language Expectation ('Construct ... that' plus its bullets). Both aids run
        # on into the Language Functions and Features table, so search with the expectation only.
        if "Language Functions and Features" in r["hub_text"]:
            aid, aid_source = r["hub_text"].split("Language Functions and Features")[0], \
                "hub_text up to 'Language Functions and Features'"
        elif "through…" in aid:
            aid, aid_source = aid.split("through…")[0], f"{aid_source} up to the first 'through…'"
    out = {"request_id": r["request_id"], "framework": r["framework"], "key": r["key"],
           "pdf_sha256": sha, "file": meta["file"], "page_or_ref": r["page_or_ref"],
           "reason": r["reason"], "page_basis": page_basis, "aid_source": aid_source,
           "method": f"pdf text layer (PyMuPDF {pymupdf.VersionBind}); no OCR, no model"}
    if r["framework"] == "gold":
        res = gold_read(r, dict(out), crops)
        if res:
            return res
    aid_toks = tokens(aid) if aid else []
    near = sorted({q for p in (pages or []) for q in range(p - 2, p + 3) if 1 <= q <= doc.page_count},
                  key=lambda q: abs(q - pages[0]))
    everywhere = list(range(1, doc.page_count + 1))

    # 1. anchor on the printed code
    code = code_of(r["key"])
    if code:
        cands = []
        for scope in ([near, everywhere] if near else [everywhere]):
            for p in scope:
                for a in anchor_reads(sha, p, code):
                    s = score(" ".join(w["text"] for w in a["words"]), aid_toks) if aid_toks else (0, 0)
                    cands.append((s[0] + s[1], p, a))
            if cands:
                break  # anchors near the named page win; the whole document is a fallback
        if cands:
            _, p, a = max(cands, key=lambda c: c[0])
            out["anchor"] = {"text": a["anchor"], "page": p, "bbox": a["anchor_bbox"],
                             "occurrences": len(cands)}
            if aid_toks:
                res = emit(dict(out), a["words"], aid_toks, crops, r["request_id"], "anchor")
                text = res["printed_text"] or res["candidate_text"] or ""
                if res["status"] != "read" and res["printed_in_aid"] >= 0.9 \
                        and len(tokens(text)) >= 5 and aid_gaps(text, aid_toks) <= 2:
                    # The printed code anchors the place and every printed word is in the aid:
                    # what the aid has beyond it is debris, not missing text.
                    res.update(status="read", printed_text=res["printed_text"] or res["candidate_text"],
                               candidate_text=None,
                               note="read at the printed code; the aid carries extra tokens not "
                                    "printed with this code (aid_tokens_not_printed)")
                if res["status"] == "read":
                    return res
            else:
                return emit(out, a["words"], [], crops, r["request_id"], "anchor")

    if not aid_toks:
        out.update(status="no_search_aid", printed_text=None)
        return out

    # 2. token alignment
    words = alignment_read(sha, near, aid_toks) if near else None
    if words is None or score(" ".join(w["text"] for w in words), aid_toks)[1] < 0.5:
        if near:
            out["page_basis"] += "; weak near the expected page, searched all pages"
        words = alignment_read(sha, everywhere, aid_toks) or words
    if not words:
        out.update(status="not_found", printed_text=None)
        return out
    res = emit(out, words, aid_toks, crops, r["request_id"], "alignment")
    if "ABSENCE" in r["key"] and res.get("regions"):
        res.update(status="absence_region_read", printed_text=res.get("printed_text") or res.get("candidate_text"),
                   candidate_text=None,
                   note="KM's row asserts that something is not printed. The region its markdown "
                        "lines name is read and cropped here so the absence can be judged on the page; "
                        "this is not a verdict on the absence")
        return res
    mathematical = re.match(r"^(precalculus|calculus|statistics|mathematics)", r["key"])
    if res["status"] != "read" and res["aid_in_printed"] < 0.8 and not mathematical \
            and not phrase_in_document(sha, aid_toks):
        # (equation-bearing statements lose their word runs to glyph noise, so they stay 'review')
        res.update(status="not_in_document", printed_text=None,
                   note="no 6-word run of the search aid is printed anywhere in this sha's text "
                        "layer; candidate_text is the closest partial alignment")
        res["candidate_text"] = res.get("candidate_text") or " ".join(w["text"] for w in words)
    return res


@lru_cache(maxsize=None)
def document_token_text(sha: str) -> str:
    _, doc = document(sha)
    return " " + " ".join(w["tok"] for p in range(1, doc.page_count + 1) for w in page_words(sha, p)) + " "


def phrase_in_document(sha: str, aid_toks: list[str], n: int = 6) -> bool:
    text = document_token_text(sha)
    grams = [" " + " ".join(aid_toks[i:i + n]) + " " for i in range(max(1, len(aid_toks) - n + 1))]
    return any(g in text for g in grams)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--framework", action="append", default=[])
    ap.add_argument("--date", default="2026-09-17")
    args = ap.parse_args()
    rows = list(csv.DictReader(args.csv.open(newline="", encoding="utf-8")))
    if args.only:
        rows = [r for r in rows if r["request_id"] in set(args.only)]
    if args.framework:
        rows = [r for r in rows if r["framework"] in set(args.framework)]
    out_dir = OUT_ROOT / args.date / REQUEST
    crops = out_dir / "crops"
    crops.mkdir(parents=True, exist_ok=True)
    results = [read_row(r, crops) for r in rows]
    # A row not read in its named sha is re-read in the other shas of the same framework named in
    # this request, when at least 75% of the aid's 5-word runs are printed there. The named-sha
    # result stays the row's status; the other-document read is attached as evidence.
    #
    # Restricted to ACTFL: its NOV/IMD/ADV/SUP benchmark PDFs share one layout and the request
    # mislabels which level a row belongs to, so a row absent from its named sha is genuinely
    # found in a sibling. In every other framework the aid coincides through shared boilerplate or
    # an overlapping sibling guide (DP Mathematics AA vs AI), where "not in the named document" is
    # a false finding rather than a swapped source.
    by_fw: dict[str, set[str]] = {}
    for r in rows:
        if r["framework"] != "actfl":
            continue
        by_fw.setdefault(r["framework"], set()).add(r["sha256"])
    for r, res in zip(rows, results):
        if res["status"] == "read" or r["framework"] != "actfl":
            continue
        aid = r["canon_text"].strip() or r["hub_text"].strip()
        toks = tokens(aid)
        if len(toks) < 5:
            continue
        for other in sorted(by_fw[r["framework"]] - {r["sha256"]}):
            text = document_token_text(other)
            grams = [" " + " ".join(toks[i:i + 5]) + " " for i in range(len(toks) - 4)]
            if sum(g in text for g in grams) / len(grams) < 0.75:
                continue
            alt = read_row({**r, "sha256": other, "request_id": r["request_id"] + "_other",
                            "page_or_ref": ""}, crops)
            res.setdefault("printed_in_other_documents", []).append(
                {k: alt.get(k) for k in ("pdf_sha256", "file", "status", "printed_text", "regions",
                                         "printed_in_aid", "aid_in_printed", "read_method")})
            if res["status"] != "read":
                res["status"] = "not_in_named_document"
                res["candidate_text"] = res.get("printed_text") or res.get("candidate_text")
                res["printed_text"] = None
                res["note"] = ("the aid is not printed in the named sha; see printed_in_other_documents")
    name = "reads.jsonl" if not (args.only or args.framework) else "reads_subset.jsonl"
    with open(out_dir / name, "w", encoding="utf-8") as fh:
        for res in results:
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
    print(Counter((x["framework"], x["status"]) for x in results))


if __name__ == "__main__":
    main()
