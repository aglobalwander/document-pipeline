# OCR and PDF processing guide

## Decision rule

Use the smallest local tool that preserves the structure you need:

| Source | First choice | Why |
|---|---|---|
| selectable text, simple layout | PyMuPDF | fast embedded-text extraction |
| scan, tables, columns, mixed layout | Enhanced Docling | local OCR and layout understanding |
| uncertain or mixed collection | Enhanced Docling | reliable local default |
| local extraction demonstrably fails | explicit remote vision path | paid fallback only |

Do not use remembered per-page prices in routing decisions. Provider models and
pricing change; check official pricing immediately before an approved API run.

## Recommended local command

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown
```

Defaults: table extraction, column detection, cache, and all-format output are
enabled. Outputs go under `data/output/text/`, `markdown/`, and `json/`.

Useful controls:

```bash
# One format only
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf \
  --output_format text \
  --no_output_all_formats

# Clear suspect checkpoints
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf \
  --clear_cache

# Disable layout features for a known simple source
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf \
  --no_extract_tables \
  --no_detect_columns
```

## PyMuPDF path

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path document.pdf \
  --pipeline_type text \
  --pdf_processor pymupdf
```

Use this when the PDF has trustworthy selectable text. If the result is empty,
fragmented, or loses important table/column structure, retry with Enhanced
Docling.

## Fallback-chain caveat

The general runner exposes `--pdf_processor_strategy fallback_chain`, but its
configured chain can include paid providers. Inspect the current configuration
before using it. For a routine local run, call `master_docling.py` explicitly.

```bash
poetry run python scripts/document_processing/run_pipeline.py --help
```

## Quality review

Check at least:

- first, middle, and last pages;
- headings and reading order;
- tables, footnotes, and multi-column regions;
- OCR substitutions in names, codes, and numbers;
- output completeness against the source page count.

A successful command or non-empty file does not prove extraction completeness.

## Troubleshooting

- Empty PyMuPDF result: the PDF is probably image-based; use Enhanced Docling.
- Wrong reading order: use Enhanced Docling with column detection enabled.
- Cache reproduces an old error: add `--clear_cache`.
- Memory pressure: process one document at a time and verify available disk.
- Remote API error: stop and verify authorization, provider status, model ID,
  and cost approval; do not silently fall through to another paid provider.
