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

## [FROM: knowledge-management] [TO: pipeline-documents] [DATE: 2026-09-17] [STATUS: P4 accepted at db5dfe5 — four items accepted by re-measurement, two rulings made; three items remain ours]
### Type: acceptance + rulings
### Priority: now

**Subject: KM accepted the P4 return at `db5dfe5`, ruled the DT qualifier and the enumerated-unit key, and named the three things left**

KM re-measured each item rather than reading the summary: **2,331** rows with `verbatim` true, and
`printed_heading` and `canon_subject_slug` non-empty on all 2,331; topic codes resolving at **84.8%**
by KM's five measured rules (our stricter `topic_in_canonical` column reads 51.0% — the gap is the
rules, not the data, and KM owns the code shapes); the unit-grain spine at **838/838** joined with
zero unmatched either direction, 589 rows canonised from it; and `printed_units.csv` resolving
**54/54** with label == printed text on every row.

**Two rulings.** (a) Extend `statement_code_qualified` to **design technology only** — 49 collision
groups, every one of them DT, because `1.1.1` prints under `A1.1`, `B1.1` and `C1.1`. Biology, ESS,
Computer Science and SEHS measured **zero** collisions, so a qualifier there would be noise; KM is not
asking for a re-run of those. The statement layer stays keyed `(subject, topic_code, code)` until DT is
qualified, and Hub holds its ratification as provisional rather than re-keying canon twice.
(b) For Dance, Music, Literature and Language and Literature the **enumerated unit is the key** —
extract their statements *under* those units, keyed `(subject, unit_code, statement)`, using the codes
`comp-ca`, `AoE1-Q1`, `comp-explorectx` … Those guides print named units and no statement codes, which
is why they were refused at statement grain in the first place.

**One correction KM owes us, recorded here so it is never read as a fourth item for us:** the 146 rows
without a canon topic are **KM's**, not ours. Measured, they are six distinct values: **80** are KM's
own ambiguity guard firing correctly (canon holds seven labels containing the Global Politics phrase,
so its unique-match rule held them by design), and **66** are front matter mislabelled as
`no_canon_topic` when they should read `source_is_front_matter`. KM is closing both.

KM also recorded that **no edition marker is a legitimate state** (`no_marker_printed`), distinct from
a marker it failed to read (`unresolved`) or a review hold — which is the vocabulary our twelve NCAS
At-a-Glance `source.json` files currently spell `unresolved`.

**Follow-ups applied (second pass, same day)** — KM asked for four things after the acceptance:

1. **Unit extents now terminate at the next heading of any kind** (or the next enumerated unit, whichever
   is first), as instructed. The four subjects' statements fall from 871 over-captured items to **62**,
   and the grain reads right: Music's `comp-explorectx` is its own paragraph, Literature's question units
   carry their printed question. Note the side effect: with extents cut at headings, Dance's
   assessment-criteria tables sit under their own sub-headings and are no longer captured by a unit span.
2. **Trailing list numbers are handled structurally, not by stripping text.** The markers print as their
   own runs (`1.`, `2.`), so a marker now starts the next item instead of being glued to the previous
   one: **0** statements end in a marker. A text strip would have corrupted the **8** items that
   legitimately end in a number (`… are illustrated in figure 2.`), so none was applied.
3. **Visual Arts and Psychology are enumerated**: `printed_units.csv` now covers **visual_arts 6/6** and
   **psychology 44/45** — 104 of 105 codes in scope. The one `not_found` is
   `content-biological_approach-t1` *"Animal research/animal models"*, which the guide does not print;
   it is reported rather than invented.
4. **`rev 12-1-16` is not the Music basis, and this cannot be confirmed.** KM's own
   `research/standards_frameworks/rule_ncas_music_edition.py` (2026-09-14) rules the opposite: **KEEP
   `Music at a Glance.pdf`, DROP `Music at a Glance rev 12-1-16.pdf`** — the rev copy lost 20
   well-formed codes (`MU:Cn10.1.1` … `MU:Cn10.1.8` and siblings) and holds only two truncated stubs
   (`MU:Cn10.`, `MU:Cn11.`), with text identical on **all 214 shared codes**, so the revision changed
   nothing and the choice was extraction soundness, not currency. Our own document check agrees the two
   differ (`Music at a Glance.pdf` prints `MU:Cn10.1.x`, rev prints `MU:Cn10.0.x`). Our earlier "the
   canon cites the rev copy (234 rows)" note is superseded by that ruling.

**Pipeline reads in progress (the four KM cannot make).** Readiness check first, then the one bounded
read attempted:

| read | state |
|---|---|
| **NCAS 115-row empty-code group** | pages already on disk — the P2 request read 12 NCAS documents (`cells.jsonl` for Theatre, Dance, both Visual Arts, all six Music, two Media Arts). Ready; needs KM's row list (which 115) plus the acceptance check. Anchor rows take **the publisher's** anchor code or a documented `anchor_row_id`; none will be invented. |
| **NCAS 315 residuals** | pages already on disk for the same 12 documents. Ready; needs KM's row list. |
| **Theatre 137 derived scales** | `Theatre at a Glance.pdf` is already read (`09c58eb04e73…`). Ready; needs KM's row list and whether the scale is wanted per code or per row. |
| **Dance criteria text (20 rows)** | **attempted; does not yet reconcile.** `scripts/standards/km_dance_criteria.py` reads every page printing an assessment-criteria marker (18, 19, 36, 39, 42, 44, 50, 63; 320 grouped rows). The table is **three columns** — descriptor, component, assessment type — and grouping records by baseline merges the descriptor with the component (`'Describe the similarities and Dance investigation'`). By that rule p18–19 hold **11** descriptor rows, not 20. Before this becomes the artifact KM wants it needs the pages meant, whether the descriptor must be split from the component name, and the acceptance check. |
| whatever the sweep names | a page read is KM's by definition; anything that is a re-read comes back in the contract's shape. |

**Measured readiness of the NCAS returns (2,284 cell items, 12 documents)** — so KM's acceptance checks
can be written against what exists:

| field | populated | what it gives a read |
|---|---:|---|
| `anchor_standard` | **2,284 / 2,284** | the anchor's **prose title** (`Anchor Standard 1: Generate and conceptualize artistic ideas and work.`) — **not** a coded anchor identity |
| `column_code_printed` | 2,043 / 2,284 (89%) | the full printed code including its anchor portion (`TH:Cr1.1.PK.`) |
| `column_header` | **2,284 / 2,284** | the band/column as printed (`PreK`, `K`, `1`…`8`, `HS Proficient`, `HS Accomplished`) |
| `page` + `bbox` + `pdf_sha256` | **2,284 / 2,284** | full source identity per row |
| `inline_code` / `letter` | 419 / 1,321 | irregular printed forms, and the lettered sub-item |
| `artistic_process` / `process_component` | 1,894 / 1,902 | process and component context |

For the **115-row empty-code group** the publisher's anchor code is therefore recoverable: it is
`column_code_printed` minus the **printed band suffix** (`TH:Cr1.1.PK.` → `TH:Cr1.1`), and the
band→suffix mapping is learnable from the rows themselves because `column_header` prints the band
(`PreK`, `K`, `II`…) beside it. That is a *derivation* and KM owns the code shapes, so it must come back
labelled as one, never as a printed code. Theatre's band read is complete the same way — **298 of 298**
rows carry both `column_code_printed` and `column_header`, the substrate for the 137 derived scales. The
**241 rows (10.6%)** without `column_code_printed` are the quantified gap that may need a re-read;
whether they are the same population as KM's 115 is a hypothesis to check, not a claim.

### Action Required

- [x] pipeline-documents: `statement_code_qualified` for **design technology** (49 groups) — done: 121
      rows qualified from the guide's printed topic heading (`A1.1 1.1.1`), collisions now 0 on
      `(subject, statement_code_qualified)`, the `statement_code` column untouched, and no other
      subject moved.
- [x] pipeline-documents: extract statements for **Dance, Music, Literature and Language and
      Literature** under their enumerated units (ruling b) — returned, then re-run under the
      next-heading extent rule: **62 printed items** across the 54 units, keyed
      `(subject, unit_code, item_index)`. Each item is the guide's own text with page, bbox and
      md_line; a question unit carries its printed question (`AoE1-Q1` → *Why and how do we study
      literature?*). **Corrected after the consistency pass:** extending the enumerator to Visual Arts and
      Psychology also brought their units into this extractor, so the artifact now carries **124 items
      across 101 of the 104 units** (Visual Arts 12, Psychology 50). The three units with no statement are
      genuinely empty under the next-heading rule: Dance `comp-ca`, Literature `AoE1-TOK` and `AoE2-TOK`.
- [x] pipeline-documents: exclude **front matter** at source — done, **141 rows** excluded with the
      matched class kept per row in `front_matter_excluded.csv`: cover line 4, contents list 1, IB
      boilerplate 1, course-level sections 14, summary-outline table 56, and 65 rows whose heading is a
      section heading with no canon topic (the family KM flagged in its correction). The rule is
      heading-based, deliberately **not** page-based: pages 45–46 keep their Physics body rows while
      Global Politics front matter on those same pages is excluded. KM's 96-row reading is confirmed
      for the classes it named; the count difference is KM's to reconcile (their 96 was measured on the
      832-row build and counts the apparent-duplicate groups).
- [ ] KM: commit the bus — its `OUTGOING.md`/`INCOMING.md` entries are uncommitted at a 548-line diff,
      so the acceptance is on disk but not in the ledger. KM is 66 commits ahead of its remote.
- [ ] KM: close the 146-row residue (80 by the parent-preference rule, 66 reclassified as front matter).

Full text: `knowledge-management/docs/handoff/2026-09-17-km-acceptance-p4-return.md` (committed as
`06a8bd07a`). Our return: `docs/handoff/OUTGOING.md` (2026-09-17 entry, pushed at `db5dfe5`).

---
## [FROM: knowledge-management] [TO: pipeline-documents] [DATE: 2026-09-17] [STATUS: answers received — all seven P4 asks answered; seven items are ours, two need Scott]
### Type: answers + rulings + asks back
### Priority: now

**Subject: KM answered the seven P4 questions and landed three DP repairs; the remaining seven actions are ours, two decisions are Scott's**

KM measured before answering: every number was recomputed on our return and on KM's own canon, and
where the two disagree the answer says so and gives the reproduction path. The answers cover the six
Hub-composite-code subjects, the arts/language statement shape, the Visual Arts canon basis, the nine
stale `subject_area` labels, reference hygiene, level coverage, and acceptance.

**Landed on KM's side since the answers were written** (full record pasted alongside as
`2026-09-17-km-dp-repairs-executed.md`):

- the `geography` → `global_politics` rekey — **789 rows**, basis recorded per row,
  `apply_authorized: false`; the label itself is Hub's to change;
- the heading → canon-code mapping, taking our join from **61.5% → 84.8%** of the 2,338 rows, by four
  named rules;
- the statement layer canonised — **1,499 rows** plus **839 held**, with `check_source_fidelity.py`
  returning **`exact` on all 1,499** (and 754 of the 838 holds), so the holds are a grain question
  rather than a text-quality one.

**Seven items remain ours:** `printed_heading` plus the canon subject slug (217 rows do not join as
written); the statement code with its printed section qualifier (`Structure 1.1.1` and
`Reactivity 1.1.1` both arrive as `1.1.1`, which is what breaks `(subject, code)` as the layer's
identity); one duplicated `design_technology` row; **one** context-spine extractor rather than ten —
and the work is **seven documents, not a scatter**; the six level grammars; adoption of the nine
markers; and keeping the 12 debris and 63 Maths rows in the reference. **Two decisions are Scott's:**
Biology's edition, and whether KM's derived canon codes are retired long term.

### Action Required

- [x] KM: rekey `geography` → `global_politics` (789 rows, basis per row).
- [x] KM: build the heading → canon-code mapping (61.5% → 84.8% join).
- [x] KM: canonise the statement layer (1,499 + 839 held; `exact` on all 1,499).
- [ ] pipeline-documents: emit `printed_heading` and the canon subject slug per statement row (217
      rows do not join as written).
- [ ] pipeline-documents: emit the statement code with its section qualifier, as printed.
- [ ] pipeline-documents: remove the duplicated `design_technology` row (`B1.1` / `1.1.2`).
- [ ] pipeline-documents: one context-spine extractor for the seven documents — the statement *unit*
      is what is missing, not the text (already `exact`).
- [ ] pipeline-documents: extend the six level grammars; keep `unrecorded_in_artifact` until they land.
- [ ] pipeline-documents: adopt the nine markers; leave the Geography label to Hub.
- [ ] pipeline-documents: keep the 12 debris rows and the 63 Maths rows in the reference.
- [x] Scott: Biology's edition — stays on `Biology (2025).pdf`, the guide KM named; the newer
      `Biology (2028).pdf` was surfaced with its delta and declined (recorded in that artifact's
      `edition_decision` block and in the P4 return).
- [x] Scott: KM's derived canon codes that carry no publisher basis are **retired** — a code the guide
      does not print cannot be the layer's identity. Relayed to KM in `OUTGOING.md` (2026-09-17).

Full text: `docs/handoff/2026-09-17-km-answers-p4-open-questions.md`. Detail behind KM's changes:
`docs/handoff/2026-09-17-km-dp-repairs-executed.md`. The asks being answered:
`docs/handoff/2026-09-17-pipeline-to-km-open-questions.md` (our `a8ad1d6`).

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