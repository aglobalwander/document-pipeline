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

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P4 follow-ups returned — four hygiene fixes done, Film and SEHS markers resolved, all 838 held rows and the four printed-unit guides enumerated]
### Type: extraction return
### Priority: now

**Subject: printed_heading, qualified codes, canon slugs and the duplicates removed on all 13 statement sets; the spine is built as one extractor, not ten**

Answering the "Still yours" list in `2026-09-17-km-answers-p4-open-questions.md` §Action Required.

**The four fixes, all landed:**

- **`printed_heading`** on **2,331 of 2,331** statement rows (was absent), and on **9,189 of 9,272**
  located rows. Physics is the case you named: its rows now carry `A.1 Kinematics` rather than nothing.
- **`statement_code_qualified`** — the guide's own printed qualifier where it prints one. Chemistry now
  returns `Structure 1.1.1` (73 rows) and `Reactivity 1.1.1` (92), not `1.1.1`. Where no qualifier
  prints, the column is empty rather than guessed: Physics' headings are themselves codes, so it stays
  empty there. The located set also carries a `section_qualifier` from the nearest printed heading above
  the row (3,277 rows); it is the position of the printed heading, not a claim about the code, and the
  statement sets only use the inline form — rule on it if you want it elsewhere.
- **`canon_subject_slug`** on every row, in your canon's own vocabulary, so the 217 rows that did not
  join now do: `mathematics_aa`, `mathematics_ai`, `business_management`.
- **Duplicates: 7 removed, not one.** Yours (`design_technology` `1.1.2`, topic `B1.1`, p46) plus four
  in Global Politics and two in Business Management — each identical in subject, code, text, topic, page
  *and* line, so nothing is lost. The statements set is **13 subjects / 2,331 statements** (was 2,338).
  A statement legitimately printed under two topics keeps both rows.

**Already true, checked rather than changed:** the **nine markers**. Every stored guide's `source.json`
carries the marker read from the document, and all nine agree (CS 2027, DT 2027, ESS 2026, GP 2026,
History 2028, Lang&Lit 2026, Literature 2026, Physics 2025, Psychology 2027). The stale values were in
your `subject_area`, which is yours to correct. The **12 debris and 63 Maths rows are kept** unchanged,
as you asked. P4's headline is unchanged: **8,252 rows located as printed, 0 verbatim failures**.

**Film and SEHS now read a single marker, which they did not before.** You flagged both as carrying no
marker we could read; that was our detector, not the documents, and the cause was twofold. SEHS prints
`First assessment 2026` on **page 7**, outside the pages 1–3 window we scanned; Film prints
`first assessment 2023` and `First assessment 2023` on pages 1–2, which we counted as two markers and
held. The scan window is now eight pages and markers are compared case-insensitively. One rule needed
adding at the same time, because the wider window found the *older* edition in a newer guide: **the
earliest page carrying a marker governs** — `Biology (2028).pdf` prints `First assessment 2028` on
pages 1–2 and a reference to `First assessment 2025` on page 7, and the 2028 edition is the guide. A
hold is now recorded only when one page names different years. Every stored IB guide (28) resolves to a
single marker. The twelve **NCAS At-a-Glance** tables from P2 still read `unresolved`, correctly: those
are tables, not subject guides, and they print no edition marker — do not expect one there.

**The spine (§2) — one extractor, run over everything.** `km_reference_context.py` reads each guide's
own printed headings above each located row; no per-subject grammar was invented and no text is
inferred. It now covers **all 22 subjects**, including your seven unit-grain documents, where the unit
is the whole point:

| document | rows with a printed topic heading above them |
|---|---:|
| Global Politics (2026) | 783 / 789 |
| History (2028) | 1,273 / 1,273 |
| Physics (2025) | 274 / 274 |
| Business Management (2024) | 235 / 235 |
| Mathematics AI (2021) | 1,338 / 1,374 |
| Mathematics AA (2021) | 1,197 / 1,234 |
| Visual Arts (2027) | 213 / 214 |

Artifact: `data/output/km_requests/2026-09-17/p4_dp_statements/statements_arts.csv` —
`pdf_sha256, subject, reference_standard_id, printed_code, reference_text, printed_text, match, page,
bbox, md_line, theme_context, topic_context, context_pages_back`.

**And your 838 held rows, answered by name** — `dp_statements_hold.csv` is a list, not a count, so
`scripts/standards/km_unit_grain_spine.py` walks it and returns the printed unit for each row:

| document | held rows | joined | with a printed heading and topic context |
|---|---:|---:|---:|
| Global Politics (2026) | 402 | 402 | 402 |
| Physics (2025) | 169 | 169 | 169 |
| Business Management (2024) | 123 | 123 | 123 |
| Mathematics AI (2021) | 50 | 50 | 50 |
| Mathematics AA (2021) | 44 | 44 | 44 |
| Visual Arts (2027) | 35 | 35 | 35 |
| History (2028) | 15 | 15 | 15 |

**838 of 838**, every one with the guide's printed heading above it and a printed topic context, and all
838 contexts are distinct from the statement text — units, not echoes. Business Management's read
`Unit 1: Introduction to business management`, Maths AA's `Topic 3— Geometry and trigonometry`,
Physics' `A.1 Kinematics`. The section qualifier is empty for all seven, which is the evidence rather
than a gap: those guides print no per-statement code, which is what makes the rows unit grain.
Artifact: `data/output/km_requests/2026-09-17/p4_dp_statements/statements_unit_grain.csv` (+
`unit_grain_summary.json`). The join is your slug + statement text against our own `statements.csv`
rows — the artifact you measured the holds from. One fix worth recording in the spine's first pass: its
heading rule took wrapped bold lines as headings, so Global Politics topics came out as prose
fragments; it now prefers section-shaped headings and refuses a fragment (unclosed bracket, sentence
left hanging on a connective, lowercase start), and fragment-like topics on the joined rows went
**39 → 0**.

**§2's enumerations, delivered.** Where the guide prints its own unit, that unit wins over the spine,
and all four such guides are now enumerated:

| guide | units | what they are |
|---|---:|---|
| Literature (2026) | 24 | `AoE1`–`AoE3`, their 18 guiding conceptual questions, and the three `Possible links to TOK` lines |
| Language and Literature (2026) | 21 | the three areas and their 18 questions |
| Music (2022) | 5 | `comp-explorectx` p32, `comp-experiment` p37, `comp-present` p39, `comp-contemphl` p42, `comp-total` |
| Dance (2013) | 4 | `comp-ca` and `comp-perf` p23, `comp-wds` p26, `comp-total` |

The match is label-driven against your own canon, so every unit is the guide's printed line with page,
bbox and md_line, and nothing is invented: **54 of 54 codes in scope matched exactly, 0 not found**.
Dance's headings do print as units, so it is included as you allowed. Where a unit prints at body size
rather than as large type — Language and Literature's area titles do — the row says so instead of
pretending otherwise. Artifact: `data/output/km_requests/2026-09-17/p4_dp_statements/printed_units.csv`
(+ `printed_units_summary.json`), from `scripts/standards/km_printed_units.py`.

### Action Required

- [ ] KM: acceptance check on the four fixes (subject slug, qualified code, printed heading, duplicates).
- [ ] KM: rule on the located set's `section_qualifier` — keep it, or restrict it to the inline form.
- [ ] KM: acceptance check on `statements_unit_grain.csv` — 838 rows, one per hold you named, each with
      its printed heading and topic context. Rule on whether that unit is the shape you want keyed.
- [ ] KM: note that the twelve NCAS At-a-Glance tables carry no edition marker by nature, so
      `unresolved` is their correct state rather than a gap to fill.
- [x] pipeline-documents: the printed-unit enumerations for Literature, Language and Literature,
      Music and Dance (54 units, 0 not found).
- [ ] KM: acceptance check on `printed_units.csv` — rule on whether each enumerated unit is the shape
      you want keyed, and on `is_heading` as a signal (it is a type-size fact, not a claim).

Full text: this entry. Context: `docs/handoff/2026-09-17-km-answers-p4-open-questions.md`.

---
## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: Scott's ruling — derived canon codes with no publisher basis are retired]
### Type: decision relay
### Priority: now

**Subject: Retire the canon codes the guide does not print; Biology needs no further relay**

Scott's ruling, 2026-09-17, on the two items KM reserved in the P4 answers.

**1. KM's derived canon codes with no publisher basis are retired.** A code the publisher does not
print cannot be the statement layer's identity — the same class as `code_recovered_from_hub`, and the
reason KM's own heading → canon-code mapping takes the *printed heading* as its evidence. The named
cases are the six composite-code subjects: KM's canon holds `R1.1` for chemistry and `VA2027` for
visual arts, neither of which appears in the guide. This changes none of our returns — we emit codes
as printed, and the retirement is KM's canon work. It authorises no canon edit from this side, and we
are not writing to KM's files.

**2. Biology's edition is already decided and needs no further relay** — it stays on
`Biology (2025).pdf`, the guide KM's request named; the newer `Biology (2028).pdf` was surfaced with
its delta (591 distinct printed codes against 589, additions `A2.3.4` and `C2.1.2`, none dropped, and
KM's 589 rows locating 588 in both editions) and the move was declined. Recorded in that artifact's
`source.json` `edition_decision` block, in the P4 return, and in `CHANGELOG.md`.

### Action Required

- [ ] KM: retire the derived codes that carry no publisher basis, across the six composite-code
      subjects.
- [ ] KM: ratify the statement layer's key once the code carries its printed section qualifier (our
      follow-up, tracked in `INCOMING.md`).

Full text: this entry. Context: `docs/handoff/2026-09-17-km-answers-p4-open-questions.md`.

---
## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P1 addendum — Economics guide skeleton returned]
### Type: extraction return (addendum)
### Priority: now

**Subject: The Economics skeleton, built from the 2024 guide alone (no briefs), is ready.**

**Method.** `scripts/standards/ib_econ_guide_skeleton.py` reads the same PyMuPDF text layer as
`depth.json` (sha `d1a7bcb5…`); no brief. Every item keeps PDF page and bbox.

**Counts.** 3 aims; 9 key concepts; AOs 1–4 with 19 bullets (HL-only bullets flagged); 4 units and
31 topics with SL/HL hours (unit 1 10/10, unit 2 35/70, unit 3 40/75, unit 4 45/65; total 150 SL /
240 HL); 7 assessment components (SL and HL outlines) with duration, weighting and aligned AOs.

Artifact: `data/output/km_requests/2026-09-17/p1_ib_guides/d1a7bcb5…/skeleton.json`. Its keys match
the brief-based skeleton, so the two can be compared. This closes the last open P1 item.

### Action Required

- [ ] KM: acceptance check on the Economics skeleton.

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P2 returned for acceptance]
### Type: extraction return
### Priority: now

**Subject: NCAS At a Glance tables — 12 documents, 2,284 cell items, every code as printed.**

**Method.** PDF text-layer geometry (PyMuPDF), no OCR, no model; each sha verified against
`MANIFEST.csv` first. `scripts/standards/ncas_at_a_glance_extract.py` writes `cells.jsonl` (one
record per cell item: printed column code, letter/inline code, text, page, bbox, row context,
flags) and `summary.json` per sha, plus `SUMMARY.md`.

Codes are never normalised; irregular printed forms are flagged for KM to rule on.

**What the pages print that the request or canon did not expect**

- HS columns use Roman numerals as the band by design (`DA:Cr1.1.I`, `.II`, `.III`); a Roman `I`
  is not a misprint. Music Tech's `MU:Pr4.I.T.Ia` is real, but in the standard position.
- Printed irregularities: Dance `DA:Re.7.1.*`; Visual Arts `VA:Re.7.1.*`, lowercase `Pka`; Theatre
  `TH:Cr2-PK.`, `TH:Cr.1.1.5.`, `TH: Re7.1.-III.`, `TH:Cn11.2.-1.`; Media Arts `(MA:Re9.1.HS.I)`.
- Music at a Glance prints `(MA:Cr3.1.PK)`, a Media Arts prefix, over a Music column; and
  `MU:Pr4.2.5cExplain` with no space.
- **The two Music at a Glance files are not the same edition** (original `MU:Cn10.1.*` vs
  `rev 12-1-16` `MU:Cn10.0.*`); the canon cites the rev copy (234 rows).
- Theatre prints 12 anchor blocks, not 11: `Cn11.1`/`Cn11.2` separately, 156 column codes against
  153 canon rows.

Counts and the full list: `data/output/km_requests/2026-09-17/p2_ncas_at_a_glance/SUMMARY.md`.

### Action Required

- [ ] KM: acceptance check; rule on canonical codes and the duplicate Music editions.

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P3 returned for acceptance]
### Type: extraction return
### Priority: now

**Subject: 473 row reads — 276 read, 91 review, 98 not printed where the row says, 6 absence
regions, 2 not found.**

**Method.** Located by printed key and text in the named sha's own text layer (PyMuPDF), no OCR,
no model; page and crop per read region. `scripts/standards/km_row_reads.py` reader,
`scripts/standards/check_p3_reads.py` acceptance.

| framework | read | review | not_in_document | not_in_named_document | absence_region_read | not_found |
|---|---:|---:|---:|---:|---:|---:|
| AP | 194 | 63 | 59 | 0 | 0 | 2 |
| ACTFL | 1 | 1 | 0 | 38 | 0 | 0 |
| DP | 6 | 26 | 1 | 0 | 6 | 0 |
| WIDA | 37 | 0 | 0 | 0 | 0 | 0 |
| GOLD | 32 | 0 | 0 | 0 | 0 | 0 |
| NGSS | 6 | 1 | 0 | 0 | 0 | 0 |

**Acceptance (`check_p3_reads.py`).** Every token of every text row is printed on that row's own
region pages (presence: PASS), and all 580 referenced crops exist (PASS). Those 580 references
resolve to **542 unique files**; the `crops/` directory holds 548, the extra 6 being superseded
cross-read crops from the DP re-read the ACTFL-only restriction retired, so they are no longer
referenced. The plan's original "contiguous in the word stream" rule was wrong for AP two-column
pages and maths glyphs: it fails 58 correct rows, so acceptance is token-presence plus the crop.

**What the documents showed**

- **Latin (AP, 61 rows: 59 not printed, 2 not found).** The keys and texts come from an earlier
  edition than the named Fall 2025 CED; P3-0297's "Explain…" is printed "Identify…".
- **ACTFL (38 rows).** The benchmark pages are swapped: NOV/IMD keys carry Advanced/Superior text,
  ADV/SUP keys carry Novice/Intermediate text.
- **WIDA (37).** The key is the Language Expectation; canon and Hub texts run into the Language
  Functions and Features table. ELD-SS.1.Argue's canon also absorbs the next page's introduction.
- **GOLD (32).** Confirms your `no_statement` hold: objectives 24–36 print only a title in the
  page 2 list, no dimensions or progressions.
- **AP (63 review).** Equation-bearing Calculus/Precalculus/Statistics statements, where glyph noise
  lowers the match; each has a crop. Image-caption fragments are in the canon, not the statements.
- **NGSS.** Printed wording differs from the canon; HS-LS2-8 is review (the read lost its first word).
- **DP.** Subtotal/front-matter keys are structural claims, not quotations, and stay review. The 6
  ABSENCE rows give the printed region and crop for you to judge. Your markdown line references
  point at KM's own `fidelity_sweep/…/guides_markdown/`, not this repo's markdown.

Counts and notes: `data/output/km_requests/2026-09-17/p3_row_reads/SUMMARY.md`.

### Action Required

- [ ] KM: acceptance check; rule on the Latin edition and the ACTFL level swap.

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P4 — two scoping questions before extraction]
### Type: scoping question
### Priority: now

**Subject: Two answers needed before we build DP statement extraction.**

P4's inputs are read: the 23 guide shas are all in the store, and we can check topic codes against
`dp_canonical.csv` (1,788 rows, 23 subjects, `code`/`parent_code`), which is already on disk here.

1. **Path of the Hub's 9,272-statement DP export.** It is not in the request folder. The closest
   local file, `hub_payloads_ib_2026-09-12/ib_new_statements.csv`, has 554 rows. Without the
   export we can report printed statements and topic-code coverage but not coverage **both ways**.
2. **Scoping for the 10 subjects with no extractor** (dance, film, language_ab_initio,
   language_and_literature, language_b, literature, music, psychology, theatre, visual_arts): how
   many of the 9,272 statements belong to them, and what do you count as a "statement" for arts and
   language guides? Those guides print themes, topics, prescribed questions and taught activities,
   not coded statements. We will not build 10 grammars before this is answered.

### Action Required

- [ ] KM: give the path of the 9,272-statement export.
- [ ] KM: answer the arts/languages scoping question.

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P1 returned for acceptance (Economics skeleton now returned — see the addendum above); P2–P4 accepted]
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

- **Economics skeleton from the 2024 guide — now returned** (see the addendum entry above). Our
  previous skeleton extractor read briefs, which you ruled out; the 2022-brief skeleton and the
  2022 depth have moved out of the live path, to
  `data/output/ib_native/economics/superseded_2022_guide/`.
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
- [x] pipeline-documents: Economics 2024 skeleton from the guide (returned — see the addendum above).
- [x] pipeline-documents: P2 and P3 returned above; P4 scoped, pending KM's two answers.

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

---

## [FROM: pipeline-documents] [TO: flow] [DATE: 2026-09-17] [STATUS: open — question sent; no repo change made]
### Type: runtime-decision-question
### Priority: now

**Subject: Which interpreter does this ecosystem expect for pipeline-documents — 3.10 or 3.14?**

We cannot tell from this repo's own artifacts, so we are asking flow rather than choosing: either
answer changes a dependency, and that is not this repo's call.

- `pyproject.toml` says `python = "^3.10"` (Poetry reads the caret as `>=3.10,<4.0`, so 3.14 is
  allowed), while `youtube-transcript-api` is capped at `python = ">=3.10,<3.14"`; `poetry.lock`
  encodes that as a marker (`python_version < "3.14"`, line 6288), so a 3.14 install *succeeds and
  silently omits the package* instead of failing.
- `README.md:22` and `SYSTEM_MAP.md:5` say "Python 3.10+" with no ceiling, and there is no
  `.python-version` in this repo.
- `flow/ecosystem-map/MAP.yml` records no interpreter or runtime key for this repo or any other, so
  the ecosystem map cannot answer it either.
- Sibling practice points at 3.14: `data_analysis/.python-version` is `3.14.0`, and flow's
  `work_ledger.yml` (2026-09-04) records Studio Lab's `.venv` consolidated "onto its verified
  Python 3.14 venv".
- On Scott's Mac, 2026-09-17, a plain `poetry run` auto-created a 3.14 env (Poetry 2.4.1 takes the
  first satisfying `python3` on `PATH`) that lacks project packages and failed its creation pip
  seed, leaving `poetry run` broken until the 3.10 env was re-activated. Verified after the fix:
  `poetry run pytest -q` → 51 passed, 17 deselected.
- The deciding pin looks vestigial: the live YouTube path is `yt-dlp`
  (`doc_processing/loaders/youtube_loader.py:8`), and `youtube-transcript-api` is imported only by
  `scripts/archive/youtube_adhoc/*`. Not verified: whether those archived scripts stay runnable.

### Action Required

- [ ] flow: rule 3.10 (dependency set unchanged) or 3.14 (relax or drop the archived pin).
- [ ] flow: say whether an interpreter fact belongs in `MAP.yml` (for example an optional
      `runtime: {python: "3.10"}`) or `TOOLING.md`, so agents stop inferring it from `PATH`.
- [ ] pipeline-documents: apply the ruling, re-run `poetry lock`, and confirm the tests.

Full text: `docs/handoff/2026-09-17-flow-interpreter-version-question.md`. Same note filed in flow's
inbox: `flow/docs/handoff/INCOMING.md` (2026-09-17 entry, `[TO: flow]`).

---

## [FROM: pipeline-documents] [TO: flow] [DATE: 2026-09-17] [STATUS: applied — floor raised to 3.13, ceiling held at `<3.14`; evidence below]
### Type: runtime-decision-applied
### Priority: now

**Subject: Narrow applied and the floor raised to 3.13 — constraint diff, lock change and test
result as requested.**

Scott directed the floor raise to 3.13 rather than pinning `.python-version` to 3.10, so the narrow
you asked for was applied as the **ceiling** (`<3.14`) and the **floor** moved 3.10 → 3.13. That is
the only deviation from your status line: `.python-version` is `3.13`, not `3.10`.

**Constraint diff** (`pyproject.toml`)

- `python = "^3.10"` → `python = ">=3.13,<3.14"`, with a four-line comment recording why the
  ceiling is load-bearing (Poetry otherwise selects Homebrew `python3.14`, where
  `youtube-transcript-api` is marker-excluded and the declared set cannot install).
- Classifiers `3.10`/`3.11` → `3.12`/`3.13`.
- `youtube-transcript-api`'s own `python = ">=3.10,<3.14"` pin was **left in place**; on 3.13 it
  installs normally. Its floor is now looser than the project's — if the archived
  `scripts/archive/youtube_adhoc/*` scripts are ever dropped, relaxing that pin is what would allow
  3.14 later.
- New tracked file: `.python-version` = `3.13`.

**Lock change** (`poetry.lock`)

| | before | after |
|---|---|---|
| `[metadata] python-versions` | `"^3.10"` | `">=3.13,<3.14"` |
| `content-hash` | `e57f62c3…` | `dabd2720…` |
| package entries | 197 | 186 |
| `youtube-transcript-api` | marker-gated `python_version < "3.14"` | installs normally (no marker) |

`poetry check --lock` reports no lock inconsistency (only the pre-existing legacy
`[tool.poetry]` metadata deprecation warnings this repo already defers in
`docs/MODEL_ROUTING.md`).

**Test result — matches your expectation exactly**

- `poetry run pytest -q` → **51 passed, 17 deselected** in 18.17s.
- Interpreter in use: **3.13.15** (`poetry env use /opt/homebrew/opt/python@3.13/bin/python3.13`;
  `poetry env list` shows `…py3.13 (Activated)`). `poetry install` completed on 3.13.
- OCR stack intact, no migration: **onnxruntime 1.23.2**, PyMuPDF 1.28.2, yt-dlp 2026.07.04;
  `poetry run python -c "import doc_processing"` → `ready`; `run_pipeline.py --help` renders.
- End-to-end smokes on 3.13, not just imports: `run_pipeline.py --pipeline_type text` on
  `data/input/text/sample_report.txt` saved 812 chars; `master_docling.py` on a 1-page PDF
  (`AI Vendor Due Diligence.pdf`) ran the full Torch/Docling/onnxruntime stack and wrote
  `data/output/markdown/AI Vendor Due Diligence_docling.md` with real headings and table content.
- The current workstream also runs on 3.13: `scripts/standards/check_p3_reads.py` → **P3 acceptance:
  PASS** (473 rows, presence PASS, crops PASS, 83 soft-order rows — identical to the 3.10 result).
- 3.13 is inside support (security support to ~Oct 2029) rather than next month's 3.10 EOL.

**Docs updated in the same patch:** `README.md` (setup), `SYSTEM_MAP.md` (runtime), `AGENTS.md`
(required environment, plus the `poetry env use` recovery command), `docs/MODEL_ROUTING.md` (the
Python row now reads `>=3.13,<3.14` with the reason), `CHANGELOG.md` (new dated Unreleased entry).

**Claim boundary:** verified on Scott's Mac only, from the local Poetry environment — this is not a
CI matrix result and does not assert that every optional extras combination resolves on 3.13.

**Not done, deliberately:** `ecosystem-map/TOOLING.md` was not touched — per-repo interpreter facts
are flow's to record, and per-repo `MAP.yml` keys are contract-governed.

### Action Required

- [ ] flow: record the interpreter fact for pipeline-documents as **Python 3.13** (`>=3.13,<3.14`)
      in `ecosystem-map/TOOLING.md`, and note that `.python-version` pins 3.13 rather than the 3.10
      in your status line.
- [ ] flow: confirm the ruling and close the inbox item (3 actions were open there).

**Correction to this entry (same day).** My earlier note said relaxing the
`youtube-transcript-api` pin was "the single change needed" to open the ceiling above 3.13. That was
wrong, and I checked it before acting on it: **onnxruntime is the gate.** `onnxruntime <=1.23.2`
publishes cp310–cp313 wheels only, so `uv pip compile --python-version 3.14` refuses to resolve the
declared set. onnxruntime publishes cp314 wheels from **1.24.1**, so opening 3.14 means moving the
`onnxruntime` ceiling — plus `torch` (lock holds 2.13.0; cp314 appears at 2.14.0) and `docling-parse`
(lock holds 7.12.0; cp314 only on 7.8.x/7.9.0) — i.e. exactly the OCR migration your ruling avoided.
The `youtube-transcript-api` override stays in place as a second, independent guard; it is not the
unlock. Nothing dependency-wise was changed for this: the pin was left alone rather than edited for
no benefit. Recorded in `docs/MODEL_ROUTING.md`, `README.md`, `SYSTEM_MAP.md` and `CHANGELOG.md`.
- [x] pipeline-documents: narrow applied, `.python-version` added (3.13), lock re-resolved, tests
      returned.

Full text: `docs/handoff/2026-09-17-flow-interpreter-version-question.md` (status now resolved).

---

## [FROM: pipeline-documents] [TO: knowledge-management] [DATE: 2026-09-17] [STATUS: P4 returned — all 22 subjects located; edition labels audited; three rulings needed]
### Type: extraction return
### Priority: now

**Subject: Every statement in your 9,272-row reference located in the guide you named — 8,252 as
printed, and the edition labels are the problem, not the text.**

**Method.** The 23 sha256 named in `p4_dp_guides.csv` were read from the store (bytes verified
against `MANIFEST.csv`; all 23 hash as listed) and their text layers written by
`scripts/standards/km_text_layer.py`. `scripts/standards/km_p4_statements.py --locate` then locates
each reference row in the guide named for its subject, by printed key and text, and returns the
guide's own line(s) with page, bbox and md_line. No OCR, no model. 22 subjects; Economics included
(it is also the P1 guide).

| outcome | rows | |
|---|---:|---|
| `located_exact` | 6,668 | the statement is one printed line |
| `located_adjacent` | 1,584 | printed across a line wrap or a page break |
| `partial` | 945 | region found, statement not contiguous (maths expressions, lists, tables) |
| `not_located` | 12 | not in the document at all |
| `empty_statement_text` | 63 | your row carries no statement text |
| **verbatim failures** | **0** | every returned text re-tokenises against its own page |

**What the documents showed**

1. **Your `subject_area` edition labels are stale, not your text.** Ten disagree with the marker
   printed in the guide you named (Computer Science, Design Technology, ESS, Global Politics,
   History, Language and Literature, Literature, Physics, Psychology, Visual Arts); two guides carry
   no marker we could read (Film, SEHS). The text locates anyway: Computer Science 100%,
   Design Technology 100%, ESS 100%, History 98.1%. So the canon rows match the guides you asked us
   to read, and the labels need the same correction you gave dance (2013) and film (2023).
2. **Visual Arts is the one real edition question.** 19/214 located, 194 partial — but 138 of those
   partials have ≥0.9 of their tokens present in the **2027** guide, so the text is in the document
   and is not printed as contiguous lines. That fits the P1 finding that Visual Arts 2027 prints no
   statement codes (it prints core-area bullets, key terms, word clouds). Only 15 rows are largely
   absent — consistent with your reference being built from the 2017 guide, which you ruled
   superseded. Tell us which edition governs before we treat those 15 as gaps.
3. **12 `not_located` rows are not statements.** Each has 0.0 document coverage and reads as a
   fragment: Global Politics `Col1`/`Col3`, Maths AA `ofAB`, `findingx)`, `(notA)`, Maths AI
   `, wheren = ∑`, Visual Arts `cohesiveness`. This is the same class as the AP image-caption
   fragments in P3 — canon debris, not printed text we failed to find.
4. **63 rows carry empty `statement_text`** (Maths AA 31, Maths AI 30, Literature 1, Language and
   Literature 1). Nothing to locate; listed rather than dropped.
5. **The topic-code acceptance rule does not hold for nine subjects.** 2,525 rows have no
   `dp_canonical` code that prefixes their printed code, concentrated where the canonical layer is
   shaped differently: Maths AI 1,374 (every row), Dance 242 (every row), Visual Arts 214 (every
   row), Chemistry 190 (every row), Psychology 151, Music 125 (every row), Design Technology 87,
   Literature 70 (every row), Language and Literature 63 (every row). For 6,265 rows a canonical
   topic was found, and for 482 the statement is its own canonical row. We list the misses rather
   than coercing them; the acceptance rule ("every statement's topic exists in `dp_canonical`")
   needs a shape ruling for those nine subjects.
6. **AOs.** 647 printed lines carry an `AOn` marker across 14 subjects (AO1–AO4, except Global
   Politics and Psychology, which print AO1–AO3). Nine subjects carry no `AOn` marker in the text
   layer at all (History, Language B, Language ab initio, Language and Literature, Literature,
   Maths AA, Maths AI, Theatre, Visual Arts) — either they print AOs otherwise or the marker is not
   in the layer. Released as printed lines with page and bbox, not as a mapping. Each row carries
   `ao_at_line_start` so definitions are separable from the many assessment lines that merely cite
   an AO (Business Management 231 and Economics 242 such lines).

**Artifacts** under `data/output/km_requests/2026-09-17/p4_dp_statements/`:
`statements_located.jsonl` (one record per reference row: sha, subject, printed_code, printed_text,
page, bbox, md_line, match, coverage, doc_coverage, verbatim, code_in_region), `aos.jsonl`,
`edition_audit.json`, `summary.json`, `SUMMARY.md`.

**One correction on our own first pass.** An earlier run reported 2,265 `not_located`, because the
matcher required all of a statement's rarest tokens on one printed line. Guides wrap statements, so
that was wrong; it also reported 6 "verbatim failures" that were one statement spanning a page
break. Both are fixed — the matcher anchors on the rarest printed token and the span decides, and
the verbatim check now covers every page the span touches — and the figures above are the corrected
ones. The fix is covered by `tests/test_p4_statement_locator.py`.

**Depth reruns (started 2026-09-17, after the return above).** The per-topic artifact KM asked
alongside the statements — topic tree, printed SL/HL/AHL level, guided/linking questions — comes from
rerunning the existing extractors against these same text layers. Eight subjects are done, each read
from the store sha and compared with the existing `data/output/ib_native/<subject>/depth.json`:

| subject | extractor | result |
|---|---|---|
| math_aa, math_ai, history, global_politics | `ib_guide_extract_math.py`, `_history.py`, `_prescribed.py` | **byte-identical** to the existing artifact |
| biology (4/40/549), chemistry (2/22/165), physics (5/24/169), sehs (3/12/66) | `ib_guide_extract_sciences.py` (`--mode`), `_generic.py` | **counts identical**; 1–11 field differences each |

The differences are small and favour the new layers: chemistry's old artifact carried a broken glyph
run (`average kinetic energy ( Ek)  of`) where the guide prints `energy Ek of`; physics differs on one
double space; and the old biology artifact had swallowed the whole *Assessment* section prose into a
lone linking question, which the new layer does not. Counts matched only after two invocation
defects were found and fixed:

- `ib_guide_extract_sciences.py` took `--content-end` at its first occurrence *anywhere*, so the
  guide's earlier mention of the end marker (line 1147, before `--content-start` at 1818) produced an
  empty body and zero units. It now searches after the start and fails loudly if the end is not
  found; its docstring example was the one that did this.
- the SEHS code regex has to require the fourth code segment, or the guide's 29 *topic* headings are
  captured as understandings (94 instead of 66).

**Not yet rerun, with the reason:** `business_management` (the `ib_guide_extract.py` invocation needs
its `--anchor`/`--start` values recovered; a first attempt parsed 0 units), `computer_science`,
`design_technology` and `ess` (each needs its own `--theme-rx`/`--code-rx` recovered: CS and DT print
codes without a dot after the theme letter, ESS numbers its themes 1–8 rather than A–E). Their
invocations will be added here when recovered; no artifact has been written for them.

---

### Action Required

- [ ] KM: acceptance check on the located statements (samples with page+bbox are in
      `statements_located.jsonl`).
- [ ] KM: rule on the stale `subject_area` labels for the ten subjects in point 1.
- [ ] KM: rule which Visual Arts edition governs; if 2027, the 194 partials need a shape decision.
- [ ] KM: confirm whether the 12 debris rows and the 63 empty-text rows stay in your reference.
- [ ] KM: rule on the nine subjects where the topic-code rule cannot hold (point 5).
      **Corrected below:** it is six subjects, not nine, and the codes in question are your Hub
      composite IDs — see correction 1.
- [x] pipeline-documents: the extractor reruns and `ib_depth_to_statements.py` are done — see the
      statements section below (all 12 subjects, 2,303 statements with page and bbox). The
      arts/language shapes still wait on your ruling.

Full text: `docs/handoff/INCOMING.md` (2026-09-17 entry). Counts and tables:
`data/output/km_requests/2026-09-17/p4_dp_statements/SUMMARY.md`.

**Statements with topic, level, page and bbox (the second half of P4).** `depth.json` holds the
topic tree but not where a statement is printed. `scripts/standards/ib_depth_to_statements.py` joins
each artifact to its guide's text layer with the same tested matcher, so every statement carries
topic code, printed level, page, bbox and md_line — the shape your acceptance check needs next to
`statements_located.jsonl`.

- **2,303 statements across all 12 subjects with an extractor**: 1,744 located exactly, 487 across a
  line wrap or page break, 72 partial. Every row carries page, bbox and the guide's own printed
  text; **0 verbatim failures**.
- Per subject: biology 549, ESS 439, Global Politics 402, physics 169, chemistry 165, Design
  Technology 145, Computer Science 136, Business Management 123, SEHS 66, Maths AI 50, Maths AA 44,
  History 15.
- **Level is recorded for 968 of the 2,303; the other 1,335 carry `SL` as a default, not a reading**
  (`level_basis = unrecorded_in_artifact`). Chemistry, Physics, ESS, Design Technology, Global
  Politics and History mark "Additional higher level" in a form the family extractors do not catch,
  so those artifacts hold no HL flag at all — exactly as the pre-existing `ib_native` artifacts do.
  The level column is therefore a printed reading only for the other six subjects; if you need levels
  for the rest, say so and we will extend those grammars rather than infer them.
- Business Management's 123 rows also carry the AOs printed against each block (86 rows), because its
  extractor records `ao_depth`.

Artifacts: `p4_dp_statements/<sha>/statements.csv` and `statements_summary.json` (per subject), plus
`p4_dp_statements/STATEMENTS_SUMMARY.md` for the combined table.

**Two corrections to what we told you above, both from evidence we went and got.**

1. **The topic-code section overstates the problem, and the nine subjects were the wrong ones.** Our
   first check compared the codes literally. When we tolerate the mechanical differences the two
   layers actually use — spacing (`AHL 1.10` against canonical `AHL1.10`), theme name against theme
   letter (`Reactivity 1.1` against `R1.1`), and the reference dropping the theme letter
   (`1.1.1` against `A1.1`) — the misses fall from **2,525 to 236 rows**, and Chemistry,
   Mathematics (AA and AI), Design Technology, Business Management and Economics match entirely.
   The 236 that survive both checks sit in **six subjects only** — Visual Arts 94, Dance 57,
   Music 34, Psychology 24, Literature 14, Language and Literature 13 — and they survive because
   their reference `printed_code` values are Hub composite IDs (`ArtMaking-C13`,
   `CompAnalysis-C10_2`, `Concepts-Bias-Desc`, `Experiment-creator-C1`, `AC-10`), not codes the
   guides print. So the ruling you need is narrower than we implied: not nine subjects, and not a
   canonical-layer shape problem, but what those six references should carry as a code.
2. **Visual Arts is settled, and it is the mirror of the label problem.** The store holds the
   superseded **`Visual Arts (2017).pdf`**, so we read it and located your 214 rows in both editions:

   | guide | lines | your rows located |
   |---|---:|---|
   | Visual Arts (2027) — the guide your request named | 4,350 | 19 / 214 (8.9%) |
   | Visual Arts (2017) — superseded, in the same store | 3,186 | **212 / 214 (99.1%)** |

   So Visual Arts' canon rows are the **2017** record, its `subject_area` label (first assessment
   2017) was **right**, and it is the guide your request named that differs — the opposite of the
   other nine. Ruling wanted: either re-derive the Visual Arts statements from the 2027 guide (we
   hold its P1 depth and its located rows), or keep the 2017 record and label it as that edition.
   Both are one command for us once you say which.

**The other nine label disagreements are the stale ones.** Their content locates in the guide your
request named at 87–100%, so the canon text is from the newer edition and the labels are not. The
markers we read from those documents, for adoption: Computer Science **2027**, Design Technology
**2027**, ESS **2026**, Global Politics **2026**, History **2028**, Language and Literature **2026**,
Literature **2026**, Physics **2025**, Psychology **2027**. Two labels carry a second defect worth
correcting at the same time: Global Politics' label says *Geography*, and ESS' label ends at
last assessment 2025 while the guide we hold prints 2026.

**Still open on our side, and the shape question with it.** The ten arts/language subjects have no
depth artifact, so their statements appear only in `statements_located.jsonl` (located, with page and
bbox) and not in a `statements.csv` with a topic tree. We will not build ten grammars on a guess. Our
proposal, if you want it before you rule: use **your reference as the spine** — for each located row
capture the nearest preceding printed theme and topic headings as its topic context, so you get
"statements under each topic" for those subjects without any per-subject grammar being invented,
and with every row still carrying the guide's own text, page and bbox. It does not pre-empt your
ruling — the topic context is read from the guide's own headings, and the row's identity is still
your reference code.

**Edition decisions (Scott, 2026-09-17), recorded for your side.** The store holds more than one
edition for exactly three subjects, and this repo now applies an edition rule: the newest governs the
extraction, but the choice is surfaced with its evidence first and Scott decides, with the decision
recorded against the sha in that artifact's `source.json`. Outcomes:

- **Biology** — read from `Biology (2025).pdf` (First assessment 2025), the guide your request named.
  `Biology (2028).pdf` (First assessment 2028, 137 pp) was surfaced with its delta and the move was
  declined: 591 distinct printed codes against 589, additions `A2.3.4` and `C2.1.2`, none dropped,
  and your 589 Biology rows locate 588 in *both* editions.
- **Visual Arts** — both editions are kept, each labelled by its own sha and marker: the **2017**
  guide as the basis of your 214 reference rows (212/214 locate there), the **2027** guide as the
  current-edition extraction, now flattened into `statements.csv` like the others (35 statements:
  7 assessment objectives and 28 learning-and-teaching items under Create / Connect / Communicate).
- **Economics** — already read from the newest (2024), which is what P1 returned. For the record, its
  2022 and 2024 files in the store are **not** byte-identical to each other (different sha and byte
  size), so the byte-identity note we relayed earlier from your index does not hold for these two.

None of this changes the returns above: it records which document each artifact was read from.

**Everything we need from you, in one place:** `docs/handoff/2026-09-17-pipeline-to-km-open-questions.md`
— seven asks (the six Hub-composite-code subjects, the arts/language shape, the Visual Arts canon
basis, the nine stale labels, the 12 debris and 63 empty rows, level coverage, and acceptance).

**Answered 2026-09-17.** KM answered all seven asks and landed three repairs — full text:
`docs/handoff/2026-09-17-km-answers-p4-open-questions.md`, detail:
`docs/handoff/2026-09-17-km-dp-repairs-executed.md`. The asks are no longer open; what remains is
ours and is tracked in the `INCOMING.md` entry of the same date. Scott's ruling on the two reserved
items is the entry at the top of this file.