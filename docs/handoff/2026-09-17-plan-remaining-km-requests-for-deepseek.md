# Plan: finishing KM requests P2–P4 with a cheaper model

**Date:** 2026-09-17
**For:** a DeepSeek-driven coding agent, with Scott or Claude reviewing at the end
**Request:** `knowledge-management/docs/handoff/2026-09-17-km-to-pipeline-extraction-contract-and-requests.md`

## Addendum — state after the P3 close (2026-09-17, written by the session that closed it)

The plan body below is the handoff as written. Two things in it are now out of date:

- **"Nothing below is committed" is no longer true.** The scripts, the edited sweep files and the
  handoff logs are committed: `ae02b9d` (P1–P3 scripts and handoff plan), `e2ac36d` (P3 cross-read
  restriction to ACTFL, acceptance checker, KM returns), then `273e2a0` (Python floor to 3.13) and
  `6fec8e7` (ceiling-rationale correction).
- **The P3 status counts in the "State at handoff" table are the pre-close numbers.** The returned
  counts are `read 276, review 91, not_in_document 60, not_in_named_document 38,
  absence_region_read 6, not_found 2`. The three DP rows that the ACTFL-only restriction recovered
  moved from `not_in_named_document` into `review` (41 → 38 and 88 → 91).
- **Task 1 is complete**, including the acceptance script and `p3_row_reads/SUMMARY.md`. Note that
  the plan's proposed acceptance rule (contiguous in the word stream) was replaced: it fails 58
  correct rows on AP two-column and maths pages, so acceptance is token-presence plus the crops, with
  order reported as a soft check (83 rows).
- **Task 2 (P4) is not started**: it waits on KM for the Hub's 9,272-statement export path and the
  arts/languages "what counts as a statement" answer.
- Both new scripts now have hermetic tests: `tests/test_p3_row_reads.py` (the acceptance gate's
  PASS/FAIL contract, driven with the page readers patched) and
  `tests/test_ncas_at_a_glance_extract.py` (the NCAS printed-form rules).

One accounting detail for KM's acceptance check on P3: `reads.jsonl` references 580 crops across
473 rows, resolving to **542 unique files, all present**; the `crops/` directory holds 548, the
extra 6 being superseded cross-read crops for P3-0067, P3-0070 and P3-0076 from the DP re-read that
the ACTFL-only restriction retired.

---
## The principle that makes a cheap model safe here

The model writes and fixes **local parsing code**. It never reads a PDF and types out what it
thinks the page says. Every artifact comes from the PDF text layer through PyMuPDF, run locally.
Scripts, not the model's judgment, decide acceptance:

- the text is verbatim in `text_layer.jsonl`;
- the code or topic exists in KM's canon;
- the counts reconcile.

Two consequences:

- **Cost:** DeepSeek tokens go only to writing code and reading short check outputs.
- **Copyright and privacy:** do not paste whole guides or CEDs into DeepSeek prompts. Show it at
  most 60–80 lines of `guide.md` or `text_layer.jsonl` around the structure being parsed. The
  PDFs stay local.

Two cost rules learned in this session:

- **Keep tool output short.** Print counts and 5–10 sample rows, never whole JSON files.
- **Stop fixing heuristics when they plateau.** Mark the rest `review` with a crop and move on.
  Chasing the last few rows cost more than everything before them.

## State at handoff

Nothing below is committed.

**New scripts in `scripts/standards/`:**

| script | purpose |
|---|---|
| `km_text_layer.py` | reads a PDF by sha from the OneDrive store, verifies it, writes `guide.md`, `text_layer.jsonl` and `source.json` |
| `ib_tok_extract.py` | P1, ToK extractor |
| `ib_va_extract.py` | P1, Visual Arts extractor |
| `ib_econ_guide_skeleton.py` | P1, Economics skeleton from the guide |
| `ncas_at_a_glance_extract.py` | P2 |
| `km_row_reads.py` | P3 |

**Edited files:** `ib_brief_sweep.py`, `ib_editions.json`, `scripts/standards/README.md`, and the
handoff logs.

**Outputs** (under `data/output/km_requests/2026-09-17/`, gitignored):

| request | state | reported to KM in OUTGOING? |
|---|---|---|
| P1 | **Done**: Economics depth and skeleton, ToK `tok.json`, Visual Arts `depth.json` | Depth yes; the Economics skeleton not yet |
| P2 | **Done**: `cells.jsonl` per document, plus `SUMMARY.md` | No |
| P3 | **Run**: `reads.jsonl` and `crops/` exist. Statuses: read 276, review 88, `not_in_document` 60, `not_in_named_document` 41, `absence_region_read` 6, `not_found` 2 | No |
| P4 | **Not started** | No |

`poetry run pytest -q` passed (51) before the P2 and P3 scripts were added. Rerun it.

## Task 1: close P3

Small; any model can do it.

1. **Narrow the cross-document re-read.** `km_row_reads.py` `main()` re-reads unread rows in
   other shas of the same framework. Restrict it to `framework == "actfl"`.
   - DP guides share IB boilerplate, so the 3 DP rows marked `not_in_named_document` are false.
   - Rerun `--framework dp`, then merge those rows into `reads.jsonl` or rerun everything, which
     takes about 10 minutes.
2. **Write `p3_row_reads/SUMMARY.md`** from `reads.jsonl`: counts by framework and status, with
   the findings below.
3. **Acceptance script** (`scripts/standards/check_p3_reads.py`): for every `read` row, the
   normalised `printed_text` is a contiguous substring of that sha's text-layer token stream, and
   every `regions[].crop` file exists.

**Findings to report** (already established; do not re-derive):

- **Latin:** 59 rows name the Fall 2025 Latin CED, but their keys (`1.A.i`, `3.F.v`) and texts
  come from an earlier edition. The 2025 CED prints skills 1.A–1.D, 2.A–B and 3.A–B with
  different wording and none of the canon texts; P3-0297's "Explain…" is printed as "Identify…".
- **ACTFL:** 38 rows swap the benchmark pages. NOV/IMD keys carry Advanced/Superior benchmark
  text, which the Novice and Intermediate PDFs do not print. ADV/SUP keys carry Novice/Intermediate
  text. The pairs share one benchmark page each.
- **WIDA:** all 37 read. The key is the Language Expectation. Canon and Hub texts both run on into
  the Language Functions and Features table, and ELD-SS.1.Argue's canon also absorbs the next
  page's "Annotated Language Samples" introduction.
- **GOLD:**
  - All 32 read at the printed objective and dimension headings.
  - Objectives 24–36 print only a title in the page 2 list, with no dimensions or progressions,
    which confirms KM's `no_statement` hold.
- **AP:**
  - **Read (194):** mostly at the printed LO/EK code.
  - **Review (63):** mostly equation-bearing Calculus, Precalculus and Statistics statements,
    where glyph noise lowers the match. Each has a crop for a person to check.
  - **Canon debris:** image-caption fragments ("rces tographs of…") are in the canon, not the
    statements.
- **NGSS:**
  - Printed wording differs from the canon ("…and that their uses…", "ways the parts of
    cells…").
  - HS-LS2-8 is left as review: the read lost its first word.
- **DP:**
  - The descriptive keys (subtotals, front matter) are structural claims, not quotations, and
    most stay review.
  - The 6 ABSENCE rows give the printed table region and crop for KM to judge; they are not a
    verdict.
  - KM's markdown line references point at KM's own
    `fidelity_sweep/hub_source_handoff_2026-09-04/guides_markdown/`, not at this repo's markdown.

## Task 2: P4, DP statements (the big one)

**Goal, per KM:** every statement under each topic, giving the statement code and text as
printed, its topic code as printed in the guide heading, the level (SL, HL or AHL) as printed,
and page and bbox. Also the guide's AOs as printed.

**KM's acceptance:**

- every statement's topic exists in `dp_canonical.csv`, whose `code` and `parent_code` columns
  are per subject;
- coverage is measured both ways against the Hub's 9,272 statements. Ask KM for the path of that
  Hub export; it is not in the request folder.

### 2a. Text layers (no model needed)

```bash
poetry run python scripts/standards/km_text_layer.py --request p4_dp_statements \
  $(tail -n +2 <KM>/pipeline_requests_2026-09-17/p4_dp_guides.csv | cut -d, -f1 | sed 's/^/--sha /')
```

`guide.md` reproduces the page-joined markdown shape the existing IB depth extractors were
written against. Verified on Economics 2022, where it gives an identical `depth.json`.

### 2b. Subjects with an existing extractor (12)

biology, business_management, chemistry, computer_science, design_technology, ess,
global_politics, history, math_aa, math_ai, physics, sehs. Economics is already done in P1.

For each subject:

1. **Find the invocation.**
   - Extractors: `ib_guide_extract_sciences.py`, `_generic.py`, `_math.py`, `_history.py`,
     `_prescribed.py`.
   - Arguments: each script's docstring and `git log -p` for the commit that added its
     `ib_native/<subject>/depth.json`.
   - The model's job here is only to find and record the command.
2. **Rerun it** on `data/output/km_requests/2026-09-17/p4_dp_statements/<sha>/guide.md`.
3. **Diff** against the existing `data/output/ib_native/<subject>/depth.json`.
   - An identical result means the text layer is a faithful input.
   - Any difference is reported rather than "fixed".
4. **Write a shared post-processor, `scripts/standards/ib_depth_to_statements.py`** (the only new
   code in 2b). It flattens `depth.json` into `statements.csv`:
   - columns: `pdf_sha256`, `subject`, `topic_code`, `statement_code`, `statement_text`,
     `level`, `page`, `bbox`, `md_line`;
   - page and bbox come from matching each statement's first line to `text_layer.jsonl`, whose
     `md_line` is exact because `guide.md` and the layer are written together;
   - level comes from what the extractor records (HL-only flags, `AHL` prefixes).

### 2c. Subjects with no extractor (10)

dance, film, language_ab_initio, language_and_literature, language_b, literature, music,
psychology, theatre, visual_arts. Visual Arts already has a P1 depth; reuse it.

1. **Ask KM a scoping question first.** How many of the 9,272 Hub statements belong to these
   subjects, and what does KM count as a "statement" for arts and language guides? These guides
   print themes, topics, prescribed questions and taught activities, not coded statements. Do not
   build 10 grammars before this is answered.
2. **For subjects KM confirms,** one extractor each, following `ib_va_extract.py`: read
   `text_layer.jsonl`, keep page and bbox, and emit what is printed.

### 2d. Checks (scripts, run for every subject)

- **Verbatim:** every `statement_text` normalised is a substring of the sha's token stream.
- **Topic codes:** every `topic_code` is in `dp_canonical.csv` for that subject. List misses; do
  not coerce them.
- **Coverage both ways** against the Hub export, once KM supplies it: statements printed but
  absent from Hub, and Hub statements with no printed match.
- **Counts per subject** into `p4_dp_statements/SUMMARY.md`.

## Task 3: report

Add one OUTGOING entry per request (P1 skeleton addendum, P2, P3, P4), following the 2026-09-17
entry already in `docs/handoff/OUTGOING.md`: counts, rows not read and why, and what the
documents showed that the request assumed wrongly. The P2 findings are in
`p2_ncas_at_a_glance/SUMMARY.md`; the P3 findings are listed above.

## Division of labour

| work | DeepSeek | Claude or Scott |
|---|---|---|
| Finding extractor invocations, writing post-processors and check scripts | yes | spot-check |
| New per-subject grammars for 2c | yes, with 60–80 line excerpts | review sample output against crops |
| Deciding a row is `read` | no (scripts decide) | none |
| Findings wording in OUTGOING | draft | final pass |
| Anything sent to KM as a ruling | no | no (KM rules) |

## Re-running every guide in the store

Yes, but as a cheap local pass, not a re-extraction of everything.

1. **Write text layers for all 108 store PDFs** with `km_text_layer.py`. It is local PyMuPDF with
   no model cost, so the cost is compute time only.
2. **Re-verify every existing artifact** (ib_native skeleton/depth, AP, P1–P3) against its sha's
   text layer with the same verbatim check. Anything that no longer matches is flagged.
3. **Re-extract only where the check fails, the sha changed, or KM names the document.** New
   edition PDFs landing in the store show up as new shas in `MANIFEST.csv`: diff the manifest,
   then run the steps above for the new ones.
4. **Keep the edition marker per sha** in `source.json`, so "most up to date" is decided from the
   printed first-assessment marker, never a filename.
