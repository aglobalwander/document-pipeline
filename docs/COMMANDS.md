# Command reference

Run every Python entry point from the repository root through Poetry.

## Environment

```bash
poetry install
poetry run python -c "import doc_processing; print('ready')"
poetry run pytest -q
```

## Enhanced Docling PDF runner

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path INPUT.pdf \
  [--output_dir data/output] \
  [--output_format text|markdown|json] \
  [--output_all_formats|--no_output_all_formats] \
  [--extract_tables|--no_extract_tables] \
  [--detect_columns|--no_detect_columns] \
  [--use_cache|--no_cache] \
  [--clear_cache]
```

Defaults: primary format `text`, output directory `data/output`, all formats
enabled, tables enabled, column detection enabled, and cache enabled.

Examples:

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path report.pdf \
  --output_format markdown

poetry run python scripts/document_processing/master_docling.py \
  --input_path report.pdf \
  --output_dir /absolute/path/processed \
  --output_format json \
  --no_output_all_formats
```

## General pipeline runner

Required arguments:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path PATH_OR_URL \
  --pipeline_type text|markdown|json|structured
```

Common options:

| Option | Values or effect |
|---|---|
| `--output_dir` | base output directory; default `data/output` |
| `--output_format` | `txt`, `md`, `json`, `csv`, `xlsx` |
| `--recursive` | recurse through an input directory |
| `--pptx_strategy` | `hybrid` |
| `--llm_provider` | explicit paid API opt-in: `openai`, `gemini`, `anthropic`, `deepseek`, `dashscope`, `kimi`; no default |
| `--llm_model` | explicit provider model ID |
| `--prompt_name` | prompt template base name |
| `--pdf_processor_strategy` | `exclusive`, `fallback_chain` |
| `--pdf_processor` | `pymupdf`, `docling`, `enhanced_docling`, `gpt`, `gemini`, `claude` |
| `--ocr_mode` | `hybrid`, `docling`, `enhanced_docling`, `gpt` |
| `--image_backend` | `local` (default), `openai`, `gemini` |
| `--deepgram_params` | JSON object, such as `'{"diarize": true}'` |
| `--use_cache` / `--no_cache` | control processing cache |
| `--clear_cache` | clear checkpoints before processing |
| `--no_page_images` | skip PDF page-image generation |

The live parser remains authoritative:

```bash
poetry run python scripts/document_processing/run_pipeline.py --help
```

Examples:

```bash
# PDF with embedded text
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path report.pdf \
  --pipeline_type text \
  --pdf_processor pymupdf

# DOCX to Markdown
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path report.docx \
  --pipeline_type markdown \
  --output_format md

# Recursive directory
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/documents \
  --pipeline_type text \
  --recursive

# YouTube URL
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path "https://youtu.be/example" \
  --pipeline_type markdown \
  --output_format md

# Paid Kimi K3 structured transform
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path notes.md \
  --pipeline_type json \
  --output_format json \
  --llm_provider kimi \
  --llm_model kimi-k3

# Paid OpenAI Responses transform with explicit reasoning controls
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path notes.md \
  --pipeline_type json \
  --output_format json \
  --llm_provider openai \
  --reasoning_effort medium \
  --text_verbosity low
```

## Direct MarkItDown

```bash
poetry run python scripts/document_processing/direct_markitdown.py \
  INPUT.docx \
  OUTPUT.md
```

If no output path is supplied, the script prints Markdown to stdout.

## Collections

```bash
poetry run python scripts/collections/inventory_collection.py \
  --source_dir /absolute/path/collection

scripts/collections/run_collection_with_storage_fallback.sh \
  --storage auto \
  --source_dir /absolute/path/collection \
  --collection_name collection-name \
  --dry_run

scripts/collections/run_collection_with_storage_fallback.sh \
  --storage auto \
  --source_dir /absolute/path/collection \
  --collection_name collection-name \
  --resume
```

## Diagnostics

```bash
poetry env info
poetry check
poetry run python scripts/document_processing/run_pipeline.py --help
poetry run python scripts/document_processing/master_docling.py --help
poetry run pytest -q tests/test_kimi_client.py
git diff --check
```

Do not use undocumented `just` targets, nonexistent `-r` aliases, or root-level
`run_pipeline.py` paths. They are not part of the current CLI contract.
