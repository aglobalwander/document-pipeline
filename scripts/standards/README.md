# Standards Extraction Scripts

This directory contains scripts for extracting and processing educational standards from PDF documents that have been converted to text.

## Where the canon and the sources live

Established 2026-09-18 and not ours to change:

- **The canon is knowledge-management's artifact**, not this repo's.
  `_01_hubs/knowledge-management/research/standards_frameworks/<framework>_canonical/output/*.csv`
  (NCAS: `ncas_canonical/output/ncas_canonical.csv`) is the authority, tracked in KM git and built by
  KM's builders (`build_ncas_canonical.py`, `extract_ncas_at_a_glance.py`, …) from the publisher
  documents. KM's `SOURCE_OF_TRUTH.md` names the tiers: SOURCE (the publisher's own material) →
  HUB (the live standard nodes) → KM DECONSTRUCTION.
- **A copy under `_01_hubs/master_data_model_drupal/data_transforming/km_canon_<date>/` is a dated
  delivery snapshot, not the canon.** Check its date before reading any difference from KM's copy as a
  defect. The `km_canon_20260914` snapshot is **16 duplicate-group repairs behind** the canon —
  KM commit `c6de8ccc4` ("the 16-row child rekey", duplicate groups 226 → 210) gave 16 Music child rows
  their own code (`MU:Cr3.1.2a`) where the snapshot still carries two rows both keyed `MU:Cr3.1.2`.
  Snapshot `1af88ffe…`; canon `6c2613b2…`; both 2,000 rows.
- **The official publisher source store is the OneDrive mount**
  `~/Library/CloudStorage/OneDrive-ShanghaiAmericanSchool/2_Models-Frameworks-Research/_Standards Frameworks/_curriculum_ontology_sources`,
  addressed by sha256 through its `MANIFEST.csv`. `km_text_layer.py` reads it and refuses bytes whose
  hash does not match. NCAS rows still migrating onto it are visible in the canon's own provenance:
  1,379 rows cite the Drupal scrape with the basis *"sha256 of ncas.csv … NOT a publisher sha: the text
  was not parsed from the PDF"*.

The boundary is fixed (see `docs/handoff/INCOMING.md`): this repo extracts and transforms, so an
extraction is evidence and a received request is neither a canon row nor an authorization to rule
editions, canonize, or crosswalk.

## Scripts Overview

### Extraction Scripts

#### `extract_ncas_eus_eqs.py`
- Extracts National Core Arts Standards (NCAS) from text files
- Identifies and extracts Enduring Understandings (EUs) and Essential Questions (EQs)
- Creates separate CSV files for standards, EUs, and EQs with proper relationships
- Output: 507 standards, 76 EUs, 130 EQs

#### `extract_math_common_core_v2.py`
- Extracts Math Common Core standards from text files
- Parses complex document structure to identify grade levels, domains, clusters, and standards
- Handles K-8 standards with proper hierarchical organization
- Output: 480 standards
- Note: `extract_math_common_core.py` is the earlier version

#### `extract_c3_framework.py`
- Extracts C3 Framework (Social Studies) indicators
- Organizes by Dimension, Discipline, Grade Band, and Indicator
- Handles all 4 dimensions including Civics, Economics, Geography, History, Psychology, Sociology
- Output: 324 indicators

#### `extract_ngss_standards.py`
- Extracts Next Generation Science Standards (NGSS) performance expectations
- Includes clarification statements and assessment boundaries
- Organizes by Grade, Topic, and Disciplinary Core Idea (DCI)
- Output: 136 performance expectations

#### `extract_ap_big_ideas.py`
- Extracts Advanced Placement (AP) Big Ideas, Enduring Understandings, and Learning Objectives
- Designed for future use (AP standards to be processed last per user request)

### Processing Scripts

#### `ap_pdf_archive.py`
- Preserves current official AP PDFs in an ignored, hash-addressed local archive
- Writes and verifies the tracked `ap_editions.json` source-edition index
- Requires the sealed 40-package manifest and readiness-matrix hashes and
  preserves every observed artifact in a cumulative SHA-addressed history
- Keeps changed official bytes separate from the reviewed baseline and never
  overwrites the legacy flat AP guide directory
- Leaves missing or ambiguous source-edition labels in explicit review states
- Performs no network access; callers provide a complete downloaded directory

#### `km_text_layer.py`
- Reads a KM-requested source by sha256 from the OneDrive source store (`MANIFEST.csv`) and
  refuses bytes whose hash does not match
- Writes `guide.md` (page-joined markdown in the shape the `ib_guide_extract*.py` grammars
  expect), `text_layer.jsonl` (page, bbox, fonts per line) and `source.json` (sha, edition
  markers, method) under `data/output/km_requests/<date>/<request>/<sha256>/`
- PDF text layer via PyMuPDF only: no OCR, no model. On Economics 2022 it reproduces the old guide
  markdown closely enough that `ib_guide_extract.py` returns an identical `depth.json`
- `source.json`'s edition marker reads both registers — IB's `First assessment YYYY` /
  `First examinations YYYY` and AP's `Effective Fall YYYY` — from a **joined** page, because an AP
  course description prints `Effective` on one line and `Fall 2026` on the next. A document that
  prints two editions, as AP Precalculus does in its own title, holds rather than picking one

#### `ib_tok_extract.py`, `ib_va_extract.py`
- Guide-shaped extractors for DP Theory of Knowledge (2022) and Visual Arts (2027), which print
  no statement codes; read `text_layer.jsonl` so every item carries page and bbox

#### `ib_econ_guide_skeleton.py`
- Builds the DP Economics skeleton from the guide alone (aims, key concepts, AOs, syllabus units
  and hours, assessment components), replacing the brief-based sweep for that subject
- Reads `text_layer.jsonl`; every item keeps PDF page and bbox

#### `ncas_at_a_glance_extract.py`
- Reads the 12 NCAS At a Glance PDFs by sha and writes `cells.jsonl` + `summary.json`: printed
  column code, letter/inline code, text, page, bbox, row context and flags
- Never normalises codes; irregular printed forms are flagged for KM to rule on

#### `km_p4_statements.py`
- P4: locates each row of KM's 9,272-statement DP reference in the guide KM named for that subject,
  returning the guide's own printed line(s) with page, bbox and md_line, plus the match state
  (`located_exact`, `located_adjacent`, `partial`, `not_located`, `empty_statement_text`) and, when a
  row is not placed, its coverage against the whole document so an edition gap is distinguishable
  from a matching limit
- `--audit` reconciles the reference's `subject_area` edition label with the first-assessment marker
  read from the document, recording disagreements as label-versus-marker candidates
- `--aos` returns the printed lines carrying an `AOn` marker, with page and bbox, for the guides that
  number their assessment objectives
- Reads only local files (the KM request folder and the text layers written by `km_text_layer.py`);
  no OCR, no model. Misses are listed, never coerced

#### `ib_depth_to_statements.py`
- Flattens a P4 `depth.json` into `statements.csv`: topic code, statement code and text, level,
  the printed AOs where the extractor recorded them, page, bbox, md_line and the guide's own printed
  text for each statement
- Walks every shape the depth artifacts use (`units -> topics -> understandings`, unit-level
  `understandings` for maths, string `items`, Business Management `blocks`, History's top-level
  `concepts` / `focused_study_skills`), so one post-processor covers all families
- Reuses the matcher in `km_p4_statements.py` rather than re-implementing it, and labels `level`
  as `unrecorded_in_artifact` where the artifact holds no HL signal, so a default is never mistaken
  for a printed reading

#### `km_reference_context.py`
- For the subjects with no depth artifact (the ten KM flags `arts_language=yes`), gives each of KM's
  own reference rows its printed topic context: the two nearest headings above the row, read from
  the guide's text layer, so "statements under each topic" is available without inventing a grammar
  per subject
- `--sha` re-locates rows against a different edition's layer first (used for Visual Arts, whose
  rows belong to the 2017 guide rather than the 2027 guide the request named)
- Writes `statements_arts.csv` and `arts_summary.json`; the row keeps the reference's code so KM can
  rule on the shape afterwards

#### `km_row_reads.py`
- Locates each of KM's 473 requested rows by printed key and text in the named sha's text layer,
  with a crop per read region. No OCR, no model
- Re-reads a row across sibling shas only for ACTFL, where the level PDFs share a layout and the
  request mislabels the source; other frameworks' coincidences are boilerplate, not a swapped source

#### `km_dp_printed_read.py`
- R5: for each of KM's 267 derived DP codes, the printed string it stands for, with page and bbox;
  where the guide prints no string for it, an explicit `not_printed` carrying the region read
- Matches **tokens over a window of 1-3 consecutive printed lines**, not per line, because these
  guides wrap a heading or a table cell across lines (Dance prints `AO1.` and `Knowledge and
  understanding` as two lines); a window never crosses a page
- Ranking prefers a line that *is* the label, then a standalone line, then a heading, then the
  tightest run; `occurrences` and `heading` are reported per row, so a two-word label that also
  occurs in prose is visible rather than silently picked
- A `not_printed` row walks the canon's own `parent_code` chain to the nearest ancestor whose label
  locates, so the region the guide *does* print comes back with the row
- Reads only the text layers written by `km_text_layer.py`; no OCR, no model

#### `km_ap_store_edition_index.py`
- What every AP source in the store *is*, from the document's own statement rather than its filename:
  one row per AP entry in `MANIFEST.csv`, with the marker, the page it prints on and the edition year
- Reports where a course is **held in more than one edition** and which of them is the newest, since
  the newest governs the extraction — AP Latin is held at 2020 and 2025
- No body read and no text comparison: the marker is front matter, and nothing here reads a statement

#### `km_r7_ap_edition_markers.py`
- R7: the edition marker each AP course description prints, with the page it prints on; where a
  document states no edition, an explicit `no_marker_printed` with the region read
- No body read and no text comparison: it takes the text layer `km_text_layer.py` wrote from the
  store's hash-verified bytes and reports what the front matter states about its edition
- A document printing two editions (`AP Precalculus`) is a `marker_review_hold`, never a pick

#### `km_ap_prose_adjacency_read.py`
- Ruling A applied: the row's characters against the document's **prose stream** — notation spans
  dropped (KM's font families), and line breaks dropped because these guides split words across
  lines (`pho` / `tographs`)
- Reports presence and adjacency **separately**: `not_adjacent` means every one of the row's words is
  printed and the row is still not contiguous, which is the ruling's case
- Re-measures from the layers R6 already delivered; no source acquisition and no re-read
- `--layers-request` reads a different delivered layer set, and repeatable `--sha-override course=sha`
  points a course at an edition the store holds now: used for AP Latin, whose rows resolve in the
  acquired Fall 2020 course description rather than the Fall 2025 one `ap_editions.json` records

#### `km_r6_printed_text_read.py`
- R6: the printed text with its tokenisation as printed, page and bbox, for KM's 94 rows whose own
  text is damaged — spaces lost inside it, or clipped
- Matches on both sides with **every non-alphanumeric removed**, because the defect being reported
  *is* a lost space: `in one country` and `inonecountry` must meet. Control characters are separators
  (the AP layers emit `\x03` where a space belongs) and are returned as spaces
- When the whole row is not printed, it reports the **longest run of the row that is**, with the
  unmatched head and tail, and only calls it a location when the run is both 40+ characters and 50%+
  of the row — below that the run is incidental prose and the row stays `not_in_document`
- DP documents resolve through KM's `dp_subject_editions.csv`; AP through this repo's
  `ap_editions.json` keyed `ap-<slug>`; a row whose document cannot be resolved says so
- Reads only the text layers written by `km_text_layer.py`; no OCR, no model

#### `check_p3_reads.py`
- Acceptance for P3: every token of a read row's `printed_text` is printed on that row's own region
  pages (presence), and every referenced crop exists. Exits non-zero on either failure
- Reports token order separately (soft): maths glyphs, rubric codes and GOLD heading reconstruction
  legitimately reorder text, so order is not a failure condition

#### `map_ncas_to_drupal_hierarchy.py`
- Maps extracted NCAS standards to Drupal's 4-level hierarchy
- Creates hierarchy entries and standard entries with proper taxonomy references
- Generates CSV files ready for Drupal import

#### `split_ncas_by_discipline.py`
- Splits unified NCAS extraction into separate files by arts discipline
- Creates separate directories for Dance, Music, Theatre, Visual Arts, and Media Arts
- Maintains EU/EQ relationships within each discipline

### Migration Script

#### `migrate_to_drupal_etl.py`
- Migrates all processed standards data to the Drupal ETL repository
- Creates a separate `standards_extracted_2024` directory to avoid conflicts
- Copies all scripts, data, and documentation
- Maintains complete separation from existing standards data

## Usage

All scripts are designed to be run from the pipeline-documents root directory:

```bash
cd /path/to/pipeline-documents
python scripts/standards/extract_ncas_eus_eqs.py
```

## Output Location

Processed data is saved to: `data/output/drupal_prep/`

Each framework has its own numbered directory:
- `01_ela_common_core/` - (empty - already in existing CSV)
- `02_math_common_core/` - Math Common Core standards
- `03_c3/` - C3 Framework indicators
- `04_ngss/` - NGSS performance expectations
- `05_ncas/` - National Core Arts Standards

## Data Flow

1. PDFs are converted to text (using separate document processing pipeline)
2. Extraction scripts parse the text files to identify standards
3. Processing scripts map standards to Drupal's hierarchy structure
4. Migration script moves everything to the Drupal ETL repository

## Notes

- All scripts generate CSV files formatted for Drupal import
- Each framework includes hierarchy additions and standard entries
- NCAS also includes separate entity files for EUs and EQs
- Scripts preserve relationships between standards and supporting concepts
