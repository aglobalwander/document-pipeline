# Incoming Notes to Pipeline Documents

Notes from other repos that this repo needs to act on.

Format per entry:

```
## [FROM: <repo>] [TO: pipeline-documents] [DATE: YYYY-MM-DD] [STATUS: ...]
### Type: <type>
### Priority: <now|next-session|backlog>

**Subject: <one line>**

<body>

### Action Required

- [ ] <step>

Full text: docs/handoff/<dated-file>.md
```

Use a placeholder date in any example: the scanner reads a heading whose date is a real
`YYYY-MM-DD`, so an example dated with its own placeholder stays invisible to it.

Replies to these notes live in `OUTGOING.md` in this same directory. The boundary is fixed: this
repo extracts and transforms, so an extraction is evidence and a received request is neither a canon
row nor an authorization to rule editions, canonize, or crosswalk.

---

## [FROM: knowledge-management] [TO: pipeline-documents] [DATE: 2026-09-17] [STATUS: accepted — P1 (with the Economics skeleton addendum), P2, P3 and P4 returned; P4 needs three rulings]
### Type: working contract + extraction requests
### Priority: now

**Subject: Read sources by sha256 from the one OneDrive store; four extraction requests (IB
guides, NCAS tables, 473 row reads, DP statements)**

Scott approved pipeline-documents as the PDF, OCR and vision specialist, with one OneDrive
store for source documents: `_Standards Frameworks/_curriculum_ontology_sources/`. It holds
108 PDFs, indexed by `MANIFEST.csv` (sha256).

- **Contract.** KM names the document by sha256, the pages, the artifact wanted and its
  acceptance check. You return artifacts under
  `data/output/km_requests/2026-09-17/<request>/<sha>/`, each with a source block (sha, file,
  page, bbox, method, edition marker). Extractions are evidence, not canon.
- **P1.** Economics (2024) `d1a7bcb5…`, Visual Arts (2027) `3ff05912…` and ToK (2022)
  `096f0b28…` are in the store.
  - Briefs are not needed.
  - For ToK, extract what the guide prints: core theme, optional themes, knowledge questions,
    AOs.
- **P2.** NCAS At a Glance tables, 12 documents: printed codes, lettered sub-items, headers,
  page, bbox.
- **P3.** 473 row reads: AP 318, ACTFL 40, DP 39, WIDA 37, GOLD 32, NGSS 7. Printed text,
  page and crop per row.
- **P4.** DP statements under each topic, with level, and the printed AOs, from 23 guides.

Request lists: `knowledge-management/research/standards_frameworks/pipeline_requests_2026-09-17/`

### Action Required

- [x] pipeline-documents: P1 (returned 2026-09-17, including the Economics guide skeleton)
- [x] pipeline-documents: P2 (returned 2026-09-17)
- [x] pipeline-documents: P3 (returned 2026-09-17)
- [x] pipeline-documents: P4 (returned 2026-09-17 — all 22 subjects, 8,252 of 9,272 reference rows
      located as printed with page and bbox; edition labels audited; three rulings requested)
- [ ] KM: acceptance check on each return

Full text: `knowledge-management/docs/handoff/2026-09-17-km-to-pipeline-extraction-contract-and-requests.md`

---

## [FROM: knowledge-management] [TO: pipeline-documents] [DATE: 2026-09-16] [STATUS: superseded by the 2026-09-17 entry — sources now read from the store]
### Type: extraction-re-run
### Priority: next-session

**Subject: Re-run three IB guides — economics skeleton+depth on the FA-2024 guide, depth for visual_arts and theory_of_knowledge — and correct two sweep labels**

KM declines to hand-roll IB guide extraction (`fidelity_sweep/build_economics_*.py` reads the page
grid by hand-measured x-positions) and asks this repo to own the re-run; KM consumes the artifacts.

- **Economics** — full skeleton **and** depth on the first-assessment-**2024** guide
  (`program_frameworks/ib/Economics_2024_official_f527c535.pdf`, sha256 `d1a7bcb5fc89cbb93ba4feb7…`,
  84 pp), replacing the 2022-based pilot. KM's own measurement: 84→84 pages, 73/84 pages
  text-identical, **all 27 numeric codes survive, none added or removed** — a revision, not a
  recode.
- **Visual Arts** — depth for the existing `visual_arts` skeleton (edition 2027 is correct).
- **Theory of Knowledge** — depth for the existing `theory_of_knowledge` skeleton (edition 2022 is
  correct).

Two edition labels in `data/output/ib_native/SWEEP_REPORT.md` must be corrected from the documents:
`dance` 2015 → **2013** (*"First examinations 2013"* in the guide; its brief says 2014) and `film`
2019 → **2023** (*"Second edition, first assessment 2023"* in the guide; its brief says 2019). Both
current values match Hub container titles as they stood before the 2026-09-16 correction, not the
documents — the label-versus-marker failure, now seen in a fourth place.

Every artifact must carry the **source pdf sha256** and the **first-assessment marker read from the
document**, so the pin lives in the artifact rather than in a filename. This matters here rather
than in principle: KM's index reports the archive copy named `Economics (2022).pdf` as
byte-identical to the copy named `Economics_2024_official_f527c535.pdf`.

Accepted 2026-09-16. Blocked on inputs: none of the three guides is held in this working copy
(`data/input/pdfs/ib/` has guides for Economics 2022 and Visual Arts 2017 only, briefs for Economics
HL/SL 2022, ToK 2022 and Visual Arts 2027) and `data/input/**` is gitignored, so none is on the
public remote either. We also found a third defect KM did not raise: `ib_brief_sweep.py` hard-codes
an economics special case and skips it, so the sweep never regenerates economics and its row
describes Hub rather than our artifacts.

### Action Required

- [ ] KM: place the three PDFs where this repo can read them, with sha256 from `MANIFEST.csv`.
- [ ] KM: answer the three open questions — are the 2024 economics **briefs** also revised; is the
      Visual Arts **2027 guide** supplied as a conversion-ready PDF; which artifact shape does KM
      want for ToK (generic theme/topic/understanding depth, or a core shape with knowledge
      questions and no AOs)?
- [ ] pipeline-documents: convert locally with Docling and record the PDF sha256 plus the marker
      read from each document.
- [ ] pipeline-documents: correct the `dance` and `film` labels and remove the hard-coded economics
      skip from the sweep.
- [ ] pipeline-documents: economics 2024 skeleton + depth; `visual_arts` and `theory_of_knowledge`
      depth, each carrying its `source` block.
- [ ] pipeline-documents: report KM's structural measurement as reproduced or not, with the
      code-set diff either way.

Full text: `docs/handoff/2026-09-16-km-request-ib-guide-re-extraction.md`. Our reply:
`docs/handoff/OUTGOING.md` (2026-09-16). Announced by KM in
`knowledge-management/docs/handoff/OUTGOING.md` (2026-09-16 entry, priority `next-session`).