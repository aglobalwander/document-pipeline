# Changelog

## Unreleased - 2026-09-17

### Changed

- Raised the Python floor from 3.10 to 3.13 and narrowed the project constraint to
  `python = ">=3.13,<3.14"` (`pyproject.toml`), added `.python-version` (3.13), and
  re-resolved `poetry.lock` (197 → 186 packages; `[metadata] python-versions` now
  `">=3.13,<3.14"`). 3.10 reaches end-of-life in October 2026; 3.13 is a supported
  interpreter that needs no OCR migration, because `onnxruntime 1.23.2` ships cp313
  wheels. Documented in `README.md`, `SYSTEM_MAP.md`, `AGENTS.md` and
  `docs/MODEL_ROUTING.md`.
- Corrected the reason the `<3.14` ceiling is load-bearing: it is the OCR stack, not
  the archived YouTube scripts. `onnxruntime <=1.23.2` publishes cp310–cp313 wheels
  only, so `uv pip compile --python-version 3.14` cannot resolve the declared set
  (onnxruntime itself publishes cp314 wheels only from 1.24.1). `torch 2.13.0` and
  `docling-parse 7.12.0` would need movement too. Opening 3.14 therefore means moving
  the OCR ceiling — the migration this change deliberately avoided — and is recorded
  rather than attempted. The `youtube-transcript-api` `<3.14` override stays as a
  second, independent guard (it is not, on its own, what blocks 3.14).

### Added

- Hermetic tests for the two P2/P3 scripts that had none, both runnable without the OneDrive
  store: `tests/test_p3_row_reads.py` (21 tests) drives `check_p3_reads.check` with the page
  readers patched, so the acceptance gate's PASS/FAIL contract — token presence, crop existence,
  order-as-a-soft-check, non-text statuses, and the CLI's non-zero exit — is exercised without a
  PDF; `tests/test_ncas_at_a_glance_extract.py` (25 tests) pins the NCAS printed-form rules
  (inline codes kept raw, lettered and `2a`/dash item forms, the Roman-band and irregular-shape
  flags, grade/process/band/furniture recognition). The suite is now 97 passed / 17 deselected.
- P4 delivery, all 22 DP subjects without a per-subject grammar: `scripts/standards/km_p4_statements.py`
  locates every row of KM's 9,272-statement reference in the guide KM named (23 sha256 read and
  verified from the store) and returns the guide's own printed text with page, bbox and md_line.
  Result: 6,668 `located_exact`, 1,584 `located_adjacent`, 945 `partial`, 12 `not_located`,
  63 empty-text rows, **0 verbatim failures**. `--audit` reconciles the reference's `subject_area`
  label with the marker printed in the guide and found ten stale labels (content still matches:
  Computer Science, Design Technology and ESS locate at 100%). `--aos` returns 647 printed lines
  carrying an `AOn` marker across 14 subjects. Two defects found by the new tests and fixed before
  returning: the matcher required a statement on one printed line (which cost 2,253 false
  `not_located` rows) and the verbatim check compared cross-page spans against a single page.
  `tests/test_p4_statement_locator.py` covers the matching rules; the suite is 108 passed.
- Depth reruns against the P4 text layers, 8 of the 12 subjects with an existing extractor:
  `math_aa`, `math_ai`, `history` and `global_politics` reproduce their existing `depth.json`
  byte-identically, and `biology`, `chemistry`, `physics` and `sehs` reproduce the counts exactly
  (4/40/549, 2/22/165, 5/24/169, 3/12/66) with 1–11 small field differences that favour the new
  layer. Fixed `ib_guide_extract_sciences.py`, whose `--content-end` was taken at its first
  occurrence anywhere: the Biology guide mentions the end marker before the content starts, so the
  extractor ran on an empty body and wrote zero units (its own docstring example did this). It now
  searches after the start and fails loudly when the end is missing. `business_management`,
  `computer_science`, `design_technology` and `ess` still need their per-subject invocation
  (`--anchor`/`--start`, `--theme-rx`/`--code-rx`) recovered.
## Unreleased - 2026-09-16

### Fixed

- Removed the import-time `logging.basicConfig(level=DEBUG)` in
  `doc_processing/embedding/base.py`; it ran before every CLI configured logging
  and forced all pipeline runs (and their dependencies) to DEBUG.
- Replaced the per-page Docling "checkpoint" writes, which rewrote the whole
  accumulating page list after every page and were deleted at the end of each
  run, with one result cache entry per (file content hash, options) pair under
  `data/cache/`. The previous early-return path also returned documents without
  `content`.
- `doc_processing/processors/__init__.py` no longer imports docling and the
  provider SDKs eagerly, and `VideoLoader`/`YouTubeLoader` no longer import
  `ffmpeg` at module import time. This repaired test collection
  (`pytest -q` went from 43 collected + 3 errors to 68 collected) and keeps the
  documented lazy-import policy in `document_pipeline.py` true.
- `AudioLoader` was an empty module that `DocumentPipeline` imported for
  `.mp3/.wav/.ogg/.m4a` inputs, so audio processing raised `ImportError`.
  It now decodes audio locally to 16 kHz mono WAV bytes. `VideoLoader` had a
  `NameError` (`data` referenced where the parameter was `document`) and no
  `load()` method, so the video branch raised `AttributeError`; both paths now
  return the documented document shape.
- `--pipeline_type markdown` on plain-text input returned the raw text
  unchanged because `TextToMarkdown` was never wired for text sources. It is now
  applied to `.txt/.md/.json` inputs (local heuristics, no model call), and it
  leaves existing `markdown_content` from Mammoth or Docling untouched.
- Wired `--clear_cache` in `run_pipeline.py` (it was accepted but never acted
  on), and made `--no_page_images` effective: the loader reads
  `generate_page_images`, so the flag previously did nothing while every PDF was
  still rasterised and base64-encoded page by page. Page images are now off
  unless a GPT vision processor is selected.
- Removed the stray per-document `print()` calls in `YouTubeLoader._is_youtube_url`.

### Changed

- `EnhancedDoclingPDFProcessor` builds one Docling `DocumentConverter` per
  processor instance and reuses it for every document instead of rebuilding it
  per file, so model initialisation is paid once per run.
- Docling pipeline options are now configurable and only set when requested:
  `docling_do_ocr`, `docling_images_scale`, `docling_generate_page_images`,
  `docling_do_picture_classification`, `docling_code_enrichment`, and
  `docling_formula_enrichment`, exposed as `--ocr`/`--no_ocr`, `--images_scale`,
  and `--page_images`. The old `DOCLING_USE_EASYOCR`/`DOCLING_ENABLED` module
  level constants in `config.py` were dead code and were removed.
- `run_pipeline.py` reuses one `DocumentPipeline` (and one Docling converter)
  across a directory run and no longer accumulates every processed document in
  memory. Binary WAV content from audio/video inputs is reported instead of
  being written as a text artifact.
- `process_collection.py` now honours the `CONCURRENT_TASKS` and `MAX_RETRIES`
  settings the project already declared: `--workers` (default
  `CONCURRENT_TASKS`) runs extractions in worker processes that each load models
  once, `--retries` (default `MAX_RETRIES`) retries failures, and both are
  recorded in the manifest.
- `ProcessingCache` resolves its directory from `settings.DATA_DIR` instead of
  the current working directory, writes results atomically, and also clears
  stale `.tmp` files.
- Duplicated helpers were consolidated: `sha256_file` (6 copies) now uses
  `doc_processing.utils.file_utils`, and `generate_unique_id` (6 copies in
  `scripts/standards`) uses the new `doc_processing.utils.ids`.
- `--detect_columns`, `--no_merge_hyphenated_words`, `--no_reconstruct_paragraphs`,
  and `--use_llm_cleaning` are still accepted but now warn that no component
  consumes them.

### Added

- `pytest` markers: fixture- and network-dependent tests are marked
  `integration` and deselected by default, so `poetry run pytest -q` is green on
  a fresh clone (51 tests, ~2s). Run the full set with
  `poetry run pytest -q -m integration`.
- `doc_processing/utils/ids.py` and `file_utils.sha256_file`.

### Removed

- Empty placeholder modules that were imported or implied as features:
  `processors/ocr_processor.py`, `processors/text_cleaner.py`,
  `processors/audio_transcription.py`, and the empty `tests/test_{embedding,loaders,processors,transformers}.py`
  (which silently "passed").
- Ten unreferenced ad-hoc YouTube/translation scripts moved to
  `scripts/archive/youtube_adhoc/`; `batch_youtube_download.py` stays because
  the live docs reference it.
- `requirements.txt`, which contradicted `poetry.lock` and listed out-of-scope
  dependencies (Weaviate, Jupyter, NLTK).

### Security

- Untracked `.env.backup` (43 populated credential assignments), which would
  have published the keys on the next push to the public remote, and added it to
  `.gitignore`. The file remains on disk and is not part of any pushed commit.
  Rotate those credentials if the file was ever shared.
- Untracked `data/processing_registry.yaml` and `pymupdf_processing.log` as
  runtime state, and corrected stale `master_projects` paths in the local
  registry.

## Unreleased - 2026-07-20

### Added

- Kimi K3 text, multimodal, and strict JSON Schema client coverage.
- Kimi routing for JSON and structured pipeline transforms.
- Top-level CLI LLM options now propagate into JSON and structured transformers.
- Current Kimi K3 CLI/API integration and capability documentation.

### Changed

- Updated Kimi defaults from Moonshot V1 to `kimi-k3` and the global
  `https://api.moonshot.ai/v1` endpoint.
- Rebuilt the live documentation entry points around the actual Poetry commands
  and current script locations.
- Clarified that local extraction and downstream ingestion are separate stages.
- Declared the test runner and chunk-tokenizer dependencies in Poetry, scoped
  test discovery to `tests/`, and updated the LangChain splitter import.

### Security

- Documented the central credential store and prohibited tracked `.env` backup
  files from being treated as configuration.

## 1.0.0 - 2025-04-27

### Added

- Initial stable release of the Document Processing Pipeline.
- Support for processing PDF, DOCX, PPTX, TXT, MD, JSON, Audio, Image, and Video files.
- Ability to process directly from YouTube URLs.
- Modular architecture with extensible loaders, processors, and transformers.
- Integration with OpenAI and Gemini LLMs for advanced processing (OCR, native PDF).
- Support for various output formats: Text, Markdown, JSON, CSV, Excel.
- Weaviate v4 integration for data ingestion and querying.
- Command-line interface via `scripts/run_pipeline.py`.
- Basic documentation (README.md, USER_GUIDE.md, OVERVIEW.md).
- Modular test suite.
- Configuration management using `pyproject.toml` and environment variables.
- JSON to CSV and JSON to Excel transformers with template support.
- Hybrid OCR mode for intelligent PDF and image processing.
- Troubleshooting section in USER_GUIDE.md.

### Changed

- Reorganized script files from the root directory into the `scripts/` directory.
- Updated README.md to reflect the new directory structure.
- Improved clarity in USER_GUIDE.md regarding Weaviate configuration and removed placeholder text.

### Removed

- Removed HybridPPTXProcessor as MarkItDownPPTXProcessor is used.

### Fixed

- Addressed encoding error handling for DOCX files (as seen in initial user interaction).
