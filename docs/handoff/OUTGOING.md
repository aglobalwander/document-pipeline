# Outgoing Notes from Pipeline Documents

Notes this repo is sending to other repos.

Entry format (matches the ecosystem convention used by `flow`, `knowledge-management` and
`master_data_model_drupal`):

```
## [FROM: pipeline-documents] [TO: <repo>] [DATE: YYYY-MM-DD] [STATUS: ...]
### Type: <type>
### Priority: <now|next-session|backlog>

**Subject: <one line>**

<body>

### Action Required

- [ ] <step>

Full text: docs/handoff/<dated-file>.md
```

This repo owns extraction and transformation. It does not rule editions, canonize, crosswalk, or
promote its artifacts into canon rows, and an extraction is evidence rather than a canon row.

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P1 returned for acceptance (Economics skeleton open); P2–P4 accepted, not started]
### Type: extraction return + contract acknowledgement
### Priority: now

**Subject: P1 is ready for your acceptance check. We accept the contract and P2–P4, and have
checked all 74 requested sources against the store by sha.**

**Contract.** Accepted as written. We read every source from the store by sha256 and write
nothing to `data/input/`. Every file KM's four request lists name (74 distinct sha256) is in
`MANIFEST.csv`, and its bytes hash to the manifest value: 0 missing, 0 mismatched.

**Method (applies to every P1 artifact).** We read the PDF's own text layer with PyMuPDF
(`scripts/standards/km_text_layer.py`), with no OCR and no model. We did not use Docling here: it
turns the Economics syllabus into tables and drops the bold that marks HL-only content.

- **Checked against the old conversion.** On Economics (2022) the new text layer yields a
  `depth.json` identical to the old one.
- **Positions.** Each line keeps its page and bbox in `text_layer.jsonl`. `page` is the PDF page,
  not the printed folio.
- **Verbatim check.** Every text item below matches the text layer on letters and digits.

Artifacts: `data/output/km_requests/2026-09-17/p1_ib_guides/<sha256>/` (`source.json`,
`text_layer.jsonl`, `guide.md`, plus the files below).

| guide | sha256 | marker read | artifact | counts |
|---|---|---|---|---|
| Economics (2024) | `d1a7bcb5…` | First assessment 2024 | `depth.json` | 4 units, 31 topics, 6 real-world issues, 27 conceptual understandings, 158 blocks (46 HL-only); passes `validate_ib_depth.py` |
| Theory of Knowledge (2022) | `096f0b28…` | First assessment 2022 | `tok.json` | 7 AOs; 15 knowledge-framework KQs; core theme 27 KQs; 5 optional themes and 5 areas of knowledge (125 + 135 KQs), each with 4 core connections |
| Visual Arts (2027) | `3ff05912…` | First assessment 2027 | `depth.json` | 7 AOs; Create 11, Connect 9, Communicate 8 learning-and-teaching items; 14 key terms; 7 AO strands with word cloud, definition and 41 guiding questions |

**Where the documents differ from what the requests assumed**

1. **Economics: 31 topic codes, not 27.** The 2024 guide prints 31 (unit 1: 2, unit 2: 12,
   unit 3: 7, unit 4: 10). The code set, and the entire `depth.json`, is identical to the 2022
   guide's.
   - **Your page measurement reproduces:** 84 → 84 pages, 73 text-identical.
   - **The 11 pages that differ:** 1, 2, 3, 7 and 63 (edition marker, imprint); 64, 67 and 68
     (the SL outline's Paper 2 line now reads "excluding HL extension material"; Paper 2 is the
     same for SL and HL); 70–72
     (markband wording).
   - None of the changes falls on a syllabus page.
2. **ToK prints assessment objectives:** seven unnumbered bullets, not `AO1`–`AO4`. We extracted
   them as printed. Our 09-16 note wrongly said the core had none.
3. **ToK also prints five areas of knowledge**, with the same KQ structure as the themes. We
   included them because the guide prints them.
4. **Some ToK bullets hold two questions.** At least one bullet carries two questions
   (methods and tools, and technology/ethics). We kept each as one item, as printed.
5. **Visual Arts 2027 prints no statement codes.** Its depth is core-area bullets, key terms and
   AO strands, not an `N.N` topic tree.
6. **Visual Arts "Assessment objectives in practice" (figure 2) is image-only.** It maps AOs to
   SL/HL tasks, and the text layer does not carry that mapping. Reading it would need a vision
   pass with a second-method check; tell us if you want one.

**Still open in P1**

- **Economics skeleton from the 2024 guide.** Our skeleton extractor reads briefs, and you ruled
  briefs out. The 2022-brief skeleton and the 2022 depth have moved out of the live path, to
  `data/output/ib_native/economics/superseded_2022_guide/`. A guide-based skeleton (aims, AOs,
  syllabus hours, SL/HL assessment outline) is next.
- **Done from 09-16.** In `ib_editions.json` and the regenerated `SWEEP_REPORT.md`, dance is now
  2013 and film 2023, with notes citing the markers. The hard-coded economics row is gone, and the
  report date is no longer fixed. The regenerated skeletons match the previous ones apart from
  edition and note.

**Notes on P2–P4 before starting**

- **P2 (NCAS).** The At a Glance PDFs have a usable text layer. The high school column codes are
  printed with Roman numerals (for example `DA:Cr1.1.I`, `.II`, `.III` for HS
  Proficient/Accomplished/Advanced), so a Roman `I` is not in itself a misprint. We will report
  each case against its column header.
- **P3 (row reads).**
  - **NGSS:** 7 rows carry no page.
  - **AP:** rows cite markdown line numbers (`… .md L2809`), not PDF pages.
  - **How we will locate them:** by key and printed text in the sha's own text layer, and we will
    report any row we cannot place.

### Action Required

- [ ] KM: acceptance check on the three P1 artifacts.
- [ ] KM: say whether the Visual Arts figure 2 AO-to-task map is wanted (vision read).
- [ ] pipeline-documents: Economics 2024 skeleton from the guide.
- [ ] pipeline-documents: P2, P3, P4, one entry here per request as each lands.

Full text: `knowledge-management/docs/handoff/2026-09-17-km-to-pipeline-extraction-contract-and-requests.md`

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-16] [STATUS: accepted — three IB runs queued, sources not yet held]
### Type: extraction-re-run
### Priority: next-session

**Subject: We accept the three IB guide re-runs and both sweep-label corrections; we need the three source PDFs before extraction.**

Request received (their OUTGOING, 2026-09-16): economics skeleton **and** depth re-run on the
first-assessment-2024 guide, plus depth for `visual_arts` and `theory_of_knowledge`, plus correction
of two edition labels in `SWEEP_REPORT.md`. We accept all of it. Nothing is extracted yet.

**Our side's independent check of the label corrections agrees with KM's, from the documents
themselves** (this repo's converted markdown, not filenames):

- `dance` — guide `ib_guides/dance_2013.md` lines 2/9/166 read *"First examinations 2013"*; the
  briefs read *"First assessments 2014"*. KM rules 2013 from the guide. Our column currently says
  **2015**.
- `film` — guide `ib_guides/film_2023.md` lines 2/7 read *"first assessment 2023"*; the brief reads
  *"First assessments 2019"*. KM rules 2023 from the guide. Our column currently says **2019**.

So the brief and the guide disagree in both cases. We will record the marker **per source document**
and let the guide's marker govern the `edition` field, rather than collapsing the two into one value.

**A third defect KM did not raise, found while checking this:** `ib_brief_sweep.py` hard-codes a
special case for economics (~lines 252–254) and skips it, printing a row that describes the Hub
(*"PILOT (full skeleton+depth in Hub)"*) rather than our artifacts. The sweep therefore never
regenerates economics, and its report title date is hard-coded to `(2026-06-10)`. Both go away in
this work.

**Blocked on inputs.** None of the three requested guides is held in this repo's working copy:
`data/input/pdfs/ib/DP Subject Guides/` contains only `Economics (2022).pdf` and
`Visual Arts (2017).pdf`, and `data/input/**` is gitignored, so none is on the public remote either.
We need `Economics_2024_official_f527c535.pdf` (84 pp), the **Visual Arts 2027 guide** (the 2017
guide stays excluded as superseded) and `TOK (2022).pdf` / `Theory of Knowledge (2022).pdf` (58 pp),
each with its sha256 against KM's `MANIFEST.csv` so we can verify the bytes before reading them.

**On the provenance requirement:** every artifact we write — skeleton and depth — will carry the
source PDF's `pdf_sha256` and the **first-assessment marker read from the document**, plus the
markdown sha it was parsed from, with `marker_resolution_state` recording a hold when a marker is
missing or ambiguous. Field names follow our existing AP precedent (`ap_editions.json`) so the AP
and IB families stay comparable. We take the point that this matters: KM's index reports the archive
copy named `Economics (2022).pdf` as byte-identical to the copy named
`Economics_2024_official_f527c535.pdf`, which is exactly why the edition must be read from bytes and
marker text rather than a filename or a container title.

**Three questions for KM** (details in the full text): whether the 2024 Economics **briefs** are
also revised (the skeleton step needs brief inputs whose markers agree with the guide), whether KM
supplies the Visual Arts **2027 guide** as a conversion-ready PDF, and which artifact shape KM wants
for ToK (generic theme/topic/understanding depth, or a core-specific shape with knowledge questions
and no AOs).

### Action Required

- [ ] KM: place the three PDFs where this repo can read them, with sha256 from `MANIFEST.csv`.
- [ ] KM: answer the three open questions above.
- [ ] pipeline-documents: convert with the local Docling path and record PDF sha + marker per guide.
- [ ] pipeline-documents: regenerate the sweep with `dance` = 2013 and `film` = 2023, and remove the
      hard-coded economics skip.
- [ ] pipeline-documents: Economics 2024 skeleton + depth; Visual Arts and ToK depth.
- [ ] pipeline-documents: report KM's structural measurement (84→84 pp, 73/84 pages text-identical,
      27 numeric codes with none added or removed) as reproduced or not, with the code-set diff.

Full text: `docs/handoff/2026-09-16-km-request-ib-guide-re-extraction.md`