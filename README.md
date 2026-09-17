# Document Processing Pipeline

Local-first extraction and transformation for PDF, DOCX, PPTX, text, images,
audio, video, and YouTube URLs. Outputs stay portable—text, Markdown, JSON,
CSV, or XLSX—so downstream repositories can decide how to store and index them.

## Processing defaults

- Use Enhanced Docling for PDFs. It is local, free, and supports OCR, layout,
  tables, caching, and text/Markdown/JSON output.
- Use MarkItDown or Mammoth for Office documents.
- Use Codex interactively for review and one-off structuring.
- Prefer subscription-backed interactive tools for model judgment; never feed
  their OAuth credentials into the Python pipeline.
- Treat every remote API as paid and opt-in. Kimi K3, Gemini, OpenAI, and
  Anthropic are available only when explicitly selected and configured.
- Keep vector database ingestion downstream; this repository ends at clean
  extracted or transformed artifacts.

## Setup

Python 3.13 and Poetry are required. The project floor and ceiling are
`python = ">=3.13,<3.14"` in `pyproject.toml`, and `.python-version` pins 3.13.
The `<3.14` ceiling is deliberate and verified: `onnxruntime <=1.23.2` publishes
cp310–cp313 wheels only, so the OCR stack cannot install on 3.14.

```bash
git clone https://github.com/aglobalwander/document-pipeline.git
cd pipeline-documents
poetry install
poetry run python -c "import doc_processing; print('ready')"
```

Do not use the available Conda environments for pipeline work; they do not
contain the locked dependency set.

## Quick start

Process a PDF with the recommended local path:

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown
```

Process another supported file or a directory:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.docx \
  --pipeline_type markdown \
  --output_format md

poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/collection \
  --pipeline_type text \
  --recursive
```

Inspect the live CLI contracts before scripting an unfamiliar option:

```bash
poetry run python scripts/document_processing/master_docling.py --help
poetry run python scripts/document_processing/run_pipeline.py --help
```

## External collections

Inventory and preview large folders before processing them:

```bash
poetry run python scripts/collections/inventory_collection.py \
  --source_dir /absolute/path/collection

scripts/collections/run_collection_with_storage_fallback.sh \
  --storage auto \
  --source_dir /absolute/path/collection \
  --collection_name my-collection \
  --dry_run
```

Run after reviewing the plan:

```bash
scripts/collections/run_collection_with_storage_fallback.sh \
  --storage auto \
  --source_dir /absolute/path/collection \
  --collection_name my-collection \
  --resume
```

Collection outputs go to
`data/output/collections/{collection_name}/{text,markdown,json}/` unless the
storage wrapper routes them to the external knowledge-hub volume. Status is
recorded in `data/processing_registry.yaml`.

## Optional Kimi K3 transforms

Kimi K3 is supported for paid structured/text transforms through
`--llm_provider kimi`. The Kimi Code subscription CLI is a separate OAuth lane
and does not supply an Open Platform API key to this pipeline.

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/notes.md \
  --pipeline_type json \
  --output_format json \
  --llm_provider kimi \
  --llm_model kimi-k3
```

Credentials load from `~/.config/api-keys/.env.master`. The canonical variable
is `MOONSHOT_API_KEY`; `KIMI_API_KEY` remains a compatibility alias. Never put a
real key in a tracked `.env` or backup file. See [Kimi K3](docs/KIMI_K3.md) for
the API/CLI boundary, current capabilities, and verification commands.

## Architecture

```text
Input -> Loader -> Processor -> Transformer -> Output artifact
```

- `doc_processing/loaders/`: input normalization
- `doc_processing/processors/`: OCR, extraction, transcription, and cleanup
- `doc_processing/transformers/`: Markdown, JSON, chunking, CSV, and XLSX
- `scripts/document_processing/`: main CLI entry points
- `scripts/collections/`: inventory and resumable collection batches
- `data/output/`: generated artifacts (ignored by git)

## Documentation

- [Documentation index](docs/README.md)
- [User guide](docs/USER_GUIDE.md)
- [Command reference](docs/COMMANDS.md)
- [Kimi K3 integration](docs/KIMI_K3.md)
- [Model routing and subscription-first policy](docs/MODEL_ROUTING.md)
- [System map](SYSTEM_MAP.md)
- [Runbook](RUNBOOK.md)
- [Invariants](INVARIANTS.md)

## Verification

```bash
poetry run pytest -q                 # fast unit suite (no fixtures needed)
poetry run pytest -q -m integration  # end-to-end checks; needs data/input fixtures
git diff --check
```

The default run excludes tests marked `integration` because they depend on
sample files under `data/input/` (gitignored) or on network access. Run them
explicitly when those fixtures are present. A green unit run does not prove the
extraction paths worked; it only proves the code loaded and the local contracts
hold.
