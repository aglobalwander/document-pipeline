# User guide

## Setup and health check

Run from the repository root:

```bash
poetry install
poetry run python -c "import doc_processing, pydantic; print('pipeline ready')"
poetry run python scripts/document_processing/run_pipeline.py --help
```

Use the Poetry environment for every processing command. The local Conda
environments do not contain the complete dependency set.

## Choose the smallest useful workflow

### PDF: recommended local extraction

Enhanced Docling is the default recommendation for PDFs, especially scans,
tables, and complex layouts:

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown
```

It writes under `data/output/{text,markdown,json}/` by default and emits all
three representations unless `--no_output_all_formats` is supplied. The result
cache is enabled by default and lives in `data/cache/`, keyed by file content
plus extraction options, so an unchanged file is not converted twice.

Useful variants:

```bash
# One primary format only
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format json \
  --no_output_all_formats

# Ignore the cached result and convert again
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown \
  --no_cache

# Remove cached results before the run
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --clear_cache

# Speed up a text-layer PDF (skip OCR) and drop table structure
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --no_ocr \
  --no_extract_tables
```

OCR is left to Docling's own per-page decision unless `--ocr` or `--no_ocr` is
given. Page images are off by default because only the GPT vision path consumes
them. `--detect_columns` / `--no_detect_columns` are accepted for compatibility
only; Docling performs layout and column analysis internally.

### PDF: fast embedded text

Use PyMuPDF when a PDF has reliable selectable text and layout reconstruction is
not the priority:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.pdf \
  --pipeline_type text \
  --pdf_processor pymupdf
```

### DOCX, PPTX, text, Markdown, JSON, image, audio, or video

Use the general runner:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.docx \
  --pipeline_type markdown \
  --output_format md
```

For direct DOCX/PPTX conversion with MarkItDown:

```bash
poetry run python scripts/document_processing/direct_markitdown.py \
  /absolute/path/document.docx \
  /absolute/path/output.md
```

### Directories

Directories are non-recursive unless `--recursive` is present:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/collection \
  --pipeline_type text \
  --recursive
```

Supported discovery extensions include PDF, TXT, MD, JSON, DOCX, PPTX, common
image/audio/video formats, and supported URLs.

One pipeline instance (and therefore one set of Docling models) is reused for
every input in a directory run. Audio and video inputs are decoded locally to
WAV bytes; they need an explicitly selected transcription processor before a text
artifact can be written, so the runner reports them instead of writing binary
output.

### YouTube

For a URL through the pipeline:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path "https://youtube.com/watch?v=..." \
  --pipeline_type markdown \
  --output_format md
```

For the repository's batch download workflow:

```bash
poetry run python batch_youtube_download.py
```

Private or restricted videos may require browser cookies.

## Outputs

The general runner writes to a subdirectory matching `pipeline_type` unless the
provided output directory already has that name:

```text
data/output/
├── text/
├── markdown/
├── json/
└── collections/
```

Collection jobs also write a manifest and update
`data/processing_registry.yaml`. Do not edit generated outputs or the registry
while a batch is running.

## Optional remote models

Remote providers are paid, explicit paths. The general runner accepts
`openai`, `gemini`, `anthropic`, `deepseek`, `dashscope`, and `kimi` for the
transform stages that support them.

For one-off review or restructuring, use the active Codex subscription task
instead. See [Model routing](MODEL_ROUTING.md) before choosing a remote API or
another subscription CLI.

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.md \
  --pipeline_type json \
  --output_format json \
  --llm_provider kimi \
  --llm_model kimi-k3
```

Credentials live in `~/.config/api-keys/.env.master` and load at runtime. Do not
pass a key in a recorded shell command or put it in the repository. See
[Kimi K3](KIMI_K3.md) for the subscription CLI versus API boundary.

## Recovery

- Interrupted Docling run: rerun the same command. Finished extractions are
  cached in `data/cache/` by content hash, so work is not repeated.
- Suspect cache: use `--clear_cache`, then rerun.
- Missing import inside `poetry run`: run `poetry install` and verify with the
  health-check command above.
- No content: inspect the source for selectable text and retry with Enhanced
  Docling rather than escalating directly to a paid API.
- Directory finds nothing: verify the extension and add `--recursive` if the
  files are nested.
- Memory pressure in a collection run: pass `--workers 1`; parallel workers each
  hold their own Docling models.
- Noisy first run: Torch/Docling print model-compilation warnings on the first
  conversion. They are expected.

For every option supported by the current code, see [Commands](COMMANDS.md) or
run the two `--help` commands.
