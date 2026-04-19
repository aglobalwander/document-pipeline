# Lazy Import Fixes — Review & Corrections

**Date:** 2026-03-12
**Context:** Changes applied by knowledge-management repo session while processing SAS HR Library documents. Reviewed and corrected in pipeline-documents.

---

## What We Kept (Good Catches)

**1. sys.path fix** (`scripts/document_processing/run_pipeline.py:25`)
The `parent.parent` resolved to `scripts/`, not repo root. Fixed to `parent.parent.parent`. Correct.

**2. Lazy imports in `document_pipeline.py`**
Moving loader/processor/transformer imports into their conditional branches is the right pattern. A PPTX file shouldn't crash because `import fitz` fails. These changes stay.

**3. Lazy imports in `pdf_loader.py`**
The `_ensure_pdf_deps()` pattern with `from __future__ import annotations` is correct. `fitz` and `PIL` are only needed when actually loading a PDF. Stays.

**4. Lazy processor imports in `pdf_processor.py`**
The `_lazy_import_*()` wrapper functions for sub-processor classes are correct. The `_initialize_processors()` lambda-based map is clean. Stays.

---

## What We Fixed on Top of the Original Changes

**1. Dead code in `pdf_processor.py`** — REMOVED

`_ensure_fitz()` and `_ensure_pil()` (plus module-level `_fitz`/`_Image` globals) were defined but never called anywhere in this file. The original `import fitz` and `from PIL import Image` were unused imports in `pdf_processor.py` — fitz/PIL usage happens in the sub-processor files and in `pdf_loader.py`. Removed 28 lines of dead code.

**2. Structural bug in `run_pipeline.py` file-saving logic** — FIXED

The `if/else` block at the output-saving section had two problems:

```python
# BEFORE: file saving trapped inside else branch
if output_dir.name.lower() == args.pipeline_type.lower():
    final_output_dir = output_dir     # sets dir, does nothing else
else:
    final_output_dir = output_dir     # same value — should have been output_dir / pipeline_type
    # ...ALL file saving logic was here...
```

- The `else` branch forgot to append the pipeline type as a subdirectory
- All file-writing code was trapped inside the `else` branch, so matching dir names meant no output was saved

Fixed: moved saving logic out of the branch, and added proper subdirectory creation.

**3. Duplicate imports** — REMOVED

`import os`, `import sys`, `import argparse` appeared twice at the top of `run_pipeline.py`.

**4. Test path fix** — `test_run_pipeline_cli.py` referenced `scripts/run_pipeline.py` (old location). Updated to `scripts/document_processing/run_pipeline.py`.

---

## Lessons for Next Time

These are notes for all of us — same mistakes are easy to repeat across sessions.

### 1. Run `poetry install` first

The root cause was missing deps. The pipeline's `pyproject.toml` + `poetry.lock` declare everything. Running `poetry install` would have resolved the entire chain without source changes. The `pip install` workaround installs packages outside the lockfile and can cause version drift.

### 2. Check if an import is actually used before wrapping it

The `import fitz` and `from PIL import Image` at the top of `pdf_processor.py` were unused imports — they'd been there since the file was created but nothing in that file referenced `fitz` or `Image` directly. The lazy wrappers added for them were equally unused. Quick check: grep the file for the symbol before adding a guard.

### 3. Look at the whole block, not just the interior

The indentation fix for `if content_to_save:` was correct, but the surrounding `if/else` was the real problem. Fixing indentation inside a broken container doesn't fix the container.

### 4. Separate bug fixes from refactoring

Two bugs (sys.path, output saving) got mixed with an architectural change (lazy imports) across 4 files in one uncommitted batch. Smaller commits make it easier to bisect, review, and revert.

### 5. Verify end-to-end

`--help` passing means imports resolve. It doesn't mean the pipeline produces correct output. A single `poetry run python ... --input_path some_file.pdf` would have caught the output-saving bug immediately.

---

## Running the Pipeline from Another Repo

### Step 1: Ensure deps are installed (one time)

```bash
cd ~/Development/_02_platforms/pipeline-documents
poetry install
```

### Step 2: Run with explicit processor selection

The default processor chain includes `enhanced_docling`. For simpler/faster processing, use PyMuPDF:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /path/to/your/file.pdf \
  --output_dir /path/to/output \
  --pipeline_type markdown \
  --output_format md \
  --pdf_processor pymupdf \
  --pdf_processor_strategy exclusive
```

### Step 3: For batch directory processing

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /path/to/directory/ \
  --output_dir /path/to/output \
  --pipeline_type markdown \
  --output_format md \
  --recursive \
  --pdf_processor pymupdf \
  --pdf_processor_strategy exclusive
```

### Avoid

- `pip install` inside the Poetry virtualenv — use `poetry install` or `poetry add`
- Modifying pipeline-documents source files to work around missing deps
- Assuming `--help` means e2e works — test with an actual file
