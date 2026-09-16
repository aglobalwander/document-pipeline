# KM → pipeline-documents — re-extraction request for three IB guides

**Date:** 2026-09-16
**From:** knowledge-management
**To:** pipeline_documents (`_02_platforms/pipeline-documents`)
**Status:** request received in this repo — not started
**Claim class:** `source_summary` for the findings below; this is a work request, not a claim about outcomes.
**Full text as sent by KM:** `_01_hubs/knowledge-management/docs/handoff/2026-09-16-km-request-ib-guide-re-extraction.md`
**Announced in KM's OUTGOING:** `knowledge-management/docs/handoff/OUTGOING.md` (2026-09-16 entry,
`[TO: pipeline-documents]`, priority `next-session`)
**Our reply record:** `docs/handoff/OUTGOING.md` (2026-09-16 entry, `[TO: knowledge-management]`)

## Why this repo owns the re-run

This repository owns extraction and transformation; KM owns source meaning, edition rulings,
canon, crosswalk and ontology. KM already ruled this way once (`2026-09-13-deconstruction-inbox.md`)
when it accepted an existing verified extraction rather than re-deriving it. KM's own
`fidelity_sweep/build_economics_*.py` reads the page grid by hand-measured x-positions
(~131/161/190) — a specialist extraction duplicated in the wrong repo. **This repo re-runs;
KM consumes.**

Neither side promotes the other's output: an extraction is evidence, not a canon row, and a canon
row is not an extraction.

## The three requested runs

| # | subject | work | source identity (per KM) | current state here |
|---|---|---|---|---|
| 1 | `economics` | full **skeleton and depth**, re-run on the **first assessment 2024** guide, replacing the 2022-based pilot | `program_frameworks/ib/Economics_2024_official_f527c535.pdf`, sha256 `d1a7bcb5fc89cbb93ba4feb7…`, 84 pp | `economics/skeleton.json` + `economics/depth.json` exist, both derived from `economics_2022.md` |
| 2 | `visual_arts` | **depth** (skeleton exists; edition 2027 is correct) | edition pair; only `Visual Arts (2027).pdf` is canon-cited | `visual_arts/skeleton.json` only — no depth |
| 3 | `theory_of_knowledge` | **depth** (skeleton exists; edition 2022 is correct) | `program_frameworks/ib/elsa_share_2026-09-02/TOK (2022).pdf`, 58 pp, *First assessment 2022*; archived 2026-09-16 as `Theory of Knowledge (2022).pdf` | `theory_of_knowledge/skeleton.json` only — no depth |

KM's independent measurement of run 1 (not ours, and not a substitute for it): 84 → 84 pages,
**73/84 pages text-identical**, **all 27 numeric codes survive — none added, none removed**. That
makes the 2024 guide a *revision, not a recode*, so the depth re-run should come out
**code-stable and text-moved**. A different code set is a signal worth a second look, not an
automatic pass.

## The two sweep-label corrections (both confirmed here)

`data/output/ib_native/SWEEP_REPORT.md` and `scripts/standards/ib_editions.json` carry two edition
values that do not match the markers printed in the documents:

| subject | current value | must become | marker evidence (verified in this repo) |
|---|---|---|---|
| `dance` | `2015` — note reads *"2013 guide (FA 2015) still in force"* | **2013** | guide `ib_guides/dance_2013.md` lines 2, 9, 166: *"First examinations 2013"*; briefs `ib_briefs/dance_hl.md` / `dance_sl.md` line 24: *"First assessments 2014"* |
| `film` | `2019` — note reads *"FA-2019 syllabus, 2023 print"* | **2023** | guide `ib_guides/film_2023.md` lines 2, 7: *"first assessment 2023"*; line 14: *"First assessment 2023) published April 2021"*; brief `ib_briefs/film.md` line 25: *"First assessments 2019"* |

Two notes for the executor:

- **The briefs and guides disagree for both subjects** (dance 2014 vs 2013; film 2019 vs 2023). KM
  rules from the guide. Do not collapse the two into one value: record the marker **per source
  document** and let the guide's marker govern the `edition` field. This is the failure mode the
  request is really about.
- KM reports the cause as structural: both wrong values match **Hub container titles as they stood
  before 2026-09-16** (Hub's old titles were `DP Dance (2015)` and `DP Film (2019)`), not the
  documents. `visual_arts` 2027, `theory_of_knowledge` 2022 and `economics` 2022 are *correct* in
  our column — only dance and film change.

There is also a third, self-contained defect in the same file: `ib_brief_sweep.py` **hard-codes a
special case for economics** and `continue`s past it (around lines 252–254), printing
`| economics | … | 2022 | done | … | PILOT (full skeleton+depth in Hub) |`. So the sweep never
regenerates economics, and the report's economics row is a claim about the Hub, not about our
## Provenance contract — the pin goes in the artifact

KM's requirement: each artifact carries the **source pdf sha256** and the **first-assessment marker
read from the document**, *"so the pin lives in the artifact and not in a filename."* This is not
cosmetic. KM's source index reports that the archive copy named `Economics (2022).pdf` is
**byte-identical** to the `elsa_share` copy named `Economics_2024_official_f527c535.pdf`. Filenames
and Hub titles have now produced a wrong edition label in four places; only bytes plus the marker
settle it.

Every artifact written by these runs — each `skeleton.json`, each `depth.json` — must carry a
`source` block, and every source document it read must carry its own entry. Field names follow the
existing AP precedent in `scripts/standards/ap_editions.json` (`sha256`,
`detected_effective_labels`, `label_detection_source`, `label_resolution_state`) so the AP and IB
families stay comparable.

```json
{
  "source": {
    "pdf_path": "data/input/pdfs/ib/DP Subject Guides/Economics (2024).pdf",
    "pdf_sha256": "<64-hex sha256 of the PDF bytes actually read>",
    "pdf_pages": 84,
    "edition_marker": "First assessment 2024",
    "detected_markers": ["First assessment 2024"],
    "marker_detection_source": "pdf_text_pages_1_through_3",
    "marker_resolution_state": "single_detected_marker",
    "derived_edition": 2024,
    "guide_markdown_path": "data/output/markdown/ib_guides/economics_2024.md",
    "guide_markdown_sha256": "<64-hex sha256 of the markdown actually parsed>"
  }
}
```

Rules:

1. `derived_edition` is **parsed from the marker**, never copied from a filename, a Hub title, or
   `ib_editions.json`. If the parsed value disagrees with the manifest, stop and report the
   disagreement rather than silently writing either value.
2. Record the marker **verbatim**. The ToK guide says *"First assessment 2022"*; the economics brief
   says *"First assessments 2022—last assessments 2029"*. Keep the literal text and say which
   document it came from.
3. Multi-source artifacts (skeleton = briefs + guide) list every document:
   `"source_documents": [{"role": "guide", "path": …, "sha256": …, "edition_marker": …, "marker_location": "line 12"}, {"role": "brief_hl", …}]`.
4. Amended artifacts must not silently retain the old pin. When `economics/depth.json` is replaced,
   the 2022 pin goes with it and the 2022 artifact stays recoverable from git history rather than
   remaining a live file that claims to be current.
5. Where a marker cannot be read, write `null` plus `marker_resolution_state: "unresolved"` and say
   so in the report. The AP archive's own rule is that a file with no detected label, or more than
   one, records a **review hold** instead of choosing one to match a baseline.

## Required inputs — not in this repo yet

Verified inventory here (`data/input/pdfs/ib/`): guides for **Economics (2022)** and **Visual Arts
(2017)** only; briefs for Economics HL/SL (2022), Theory of Knowledge (2022), Visual Arts (2027).
**None of the three requested guides is present in this repo's working copy, and `data/input/**` is
gitignored so none is on the public remote either.**

| run | PDF to obtain | expected marker |
|---|---|---|
| 1 | `Economics_2024_official_f527c535.pdf` (84 pp) | First assessment 2024 |
| 2 | `Visual Arts (2027).pdf` guide — the 2017 guide is superseded and stays excluded | First assessment 2027 |
| 3 | `TOK (2022).pdf` / `Theory of Knowledge (2022).pdf` (58 pp) | First assessment 2022 |

Source of record: KM's `docs/handoff/2026-09-16-km-subject-guide-path-and-source-index.md` (sealed
archive, `MANIFEST.csv` indexed by `directory, file, sha256, bytes, copied_from`; 107/107 after the
2026-09-16 reconciliation) and `research/standards_frameworks/program_frameworks/ib/SOURCE_INDEX.md`.
Confirm each received PDF's sha256 against KM's manifest **before** extracting, and record it.

## Execution plan

Local-first throughout: Docling for PDF → Markdown, then the existing extractors. No paid API is
involved, and none may be switched on by implication.

```bash
# 0. Obtain the three PDFs from KM's archive and verify bytes against MANIFEST.csv.
#    Place under data/input/pdfs/ib/DP Subject Guides/ (gitignored, as now).

# 1. Convert PDF -> Markdown with the recommended local path, one file at a time.
poetry run python scripts/document_processing/master_docling.py \
  --input_path 'data/input/pdfs/ib/DP Subject Guides/Economics (2024).pdf' \
  --output_format markdown
#    then place the result at data/output/markdown/ib_guides/economics_2024.md
#    (same for visual_arts_2027.md and theory_of_knowledge_2022.md)

# 2. Record each PDF's sha256 and the first-assessment marker read from its bytes.

# 3. scripts/standards/ib_editions.json
#    - economics: edition 2024, guide economics_2024.md, drop the PILOT note
#    - visual_arts: guide visual_arts_2027.md ; theory_of_knowledge: guide theory_of_knowledge_2022.md
#    - dance: edition 2013 ; film: edition 2023 ; notes rewritten to cite the markers

# 4. Remove the hard-coded economics skip in ib_brief_sweep.py (~lines 252-254) and regenerate
#    breadth: SWEEP_REPORT.md + every skeleton.json
poetry run python scripts/standards/ib_brief_sweep.py

# 5. Economics skeleton (pilot grammar)
poetry run python scripts/standards/ib_brief_extract.py \
  --briefs data/output/markdown/ib_briefs/economics_hl_2024.md \
           data/output/markdown/ib_briefs/economics_sl_2024.md \
  --guide data/output/markdown/ib_guides/economics_2024.md \
  --out data/output/ib_native/economics/skeleton.json --subject economics

# 6. Economics depth (2022-era grammar)
poetry run python scripts/standards/ib_guide_extract.py \
  --guide data/output/markdown/ib_guides/economics_2024.md \
  --out data/output/ib_native/economics/depth.json \
  --units "Introduction to economics,Microeconomics,Macroeconomics,The global economy"

# 7. Visual Arts + ToK depth — ib_guide_extract_generic.py (--themes / --theme-rx / --code-rx /
#    --content-start / --content-end), or a new family grammar if arts/core does not fit the
#    bold-understanding shape.
```

Steps 5–7 assume the 2024 economics guide still matches the 2022-era shapes the grammars encode
(recommended-time unit openers, real-world-issue headers, `N.N` topics). KM measured a revision
rather than a recode, so that is likely — verify against the document and state which grammar was
used. `theory_of_knowledge` is a **core** subject (no AOs, not the taught-subject unit shape):
expect to extend the generic grammar or add a core grammar rather than forcing it.

## Acceptance checks

- [ ] `economics` skeleton and depth are derived from the 2024 guide; the 2022-derived pilot no
      longer occupies the live path.
- [ ] KM's structural measurement reproduces: 84 → 84 pages, 73/84 pages text-identical, and
      **27 numeric codes with none added and none removed**. Report the code-set diff either way.
- [ ] `visual_arts` and `theory_of_knowledge` each have a `depth.json` carrying a `source` block.
- [ ] `SWEEP_REPORT.md` shows `dance` = 2013 and `film` = 2023 with notes that cite the markers, and
      the report's date is regenerated rather than the stale `(2026-06-10)`.
- [ ] The economics special case is gone from `ib_brief_sweep.py`, and re-running the sweep
      reproduces every skeleton, economics included.
- [ ] Every artifact's `edition` equals its document's marker, and every artifact carries
      `pdf_sha256` for the bytes it read.
- [ ] `validate_ib_skeleton.py` / `validate_ib_depth.py` are currently **hard-coded to the Economics
      2022 contract** (AO1–4, units `[1,2,3,4]`, ≥28 topics, nine named concepts, Paper 3 HL, six
      real-world issues). Those assertions will fail on a revised guide or another subject, so
      generalize them per subject or add per-subject contracts. A validator that cannot express the
      new shape is not evidence that the new shape is wrong.
- [ ] `poetry run pytest -q` stays green. The extraction runs are not covered by the default suite,
      so report them as run outcomes, not as test outcomes.

## Boundaries

- This repo extracts and transforms. It does not rule editions, canonize, crosswalk, or promote its
  output into canon rows.
- Nothing here authorizes a paid model call, remote ingestion, or a Hub/Drupal write.
- A clean extraction is evidence about the document bytes read. It does not prove downstream
  ingestion, indexing, or canon acceptance.
- KM reports `economics_2022.md` and `visual_arts_2017.md` as **STALE** in KM's terms. Keep
  `visual_arts_2017.md` excluded, and do not let the 2022 economics markdown quietly remain the live
  input for an artifact labelled current.

## Open questions for KM

1. Are the 2024 economics **briefs** (`Economics HL` / `Economics SL`) also revised, or only the
   guide? The skeleton step needs brief inputs whose markers agree with the guide's, and the only
   briefs on disk here are the 2022 pair.
2. Does KM supply the Visual Arts 2027 **guide** as a conversion-ready PDF, or only the 2027 brief
   already present here? Depth cannot be produced from a brief.
3. For ToK, which artifact shape does KM want to consume — the generic theme/topic/understanding
   depth, or a core-specific shape (themes plus knowledge questions, no AOs)?

## References

- KM request (authoritative): `_01_hubs/knowledge-management/docs/handoff/2026-09-16-km-request-ib-guide-re-extraction.md`
- KM source index and sealed archive: `knowledge-management/docs/handoff/2026-09-16-km-subject-guide-path-and-source-index.md`
- KM import instruction for the IB edition carriers: `knowledge-management/docs/handoff/2026-09-16-km-import-instruction-ib-editions.md`
- Our reply record: `docs/handoff/OUTGOING.md` (2026-09-16 entry)
- Manifest and sweep: `scripts/standards/ib_editions.json`, `scripts/standards/ib_brief_sweep.py`,
  `data/output/ib_native/SWEEP_REPORT.md`
- Extractors: `scripts/standards/ib_brief_extract.py`, `ib_guide_extract.py`,
  `ib_guide_extract_generic.py`
- Validators: `scripts/standards/validate_ib_skeleton.py`, `validate_ib_depth.py`
- Provenance precedent (AP family): `scripts/standards/ap_editions.json`,
  `docs/guides/STANDARDS_PDF_PROCESSING.md`
artifacts. The report's title date is hard-coded to `(2026-06-10)` as well.