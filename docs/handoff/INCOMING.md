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

Replies to these notes live in `OUTGOING.md` in this same directory. The boundary is fixed: this
repo extracts and transforms, so an extraction is evidence and a received request is neither a canon
row nor an authorization to rule editions, canonize, or crosswalk.

---

## [FROM: knowledge-management] [TO: pipeline-documents] [DATE: 2026-09-16] [STATUS: open — accepted, blocked on source PDFs]
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