# Standards framework PDF processing

Standards PDFs often combine columns, tables, codes, footnotes, and hierarchy.
Preserve the source wording and structure before downstream modeling.

## 1. Keep source authority visible

Record the framework, publisher, edition/date, source URL or file path, and page
range. Extraction output is evidence derived from the official document; it is
not a replacement authority.

## 2. Inventory in place

The pipeline accepts absolute paths, so copying into the repository is optional:

```bash
poetry run python scripts/collections/inventory_collection.py \
  --source_dir /absolute/path/standards
```

For PDF-specific analysis, use the current utility path:

```bash
poetry run python scripts/pdf_processing/analyze_pdfs_for_ocr.py \
  /absolute/path/standards
```

Read the script's help/header before relying on source-specific options.

## 3. Extract locally

For a framework with layout, tables, or scanned pages:

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/framework.pdf \
  --output_dir /absolute/path/processed \
  --output_format markdown
```

For a simple born-digital PDF:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/framework.pdf \
  --output_dir /absolute/path/processed \
  --pipeline_type text \
  --pdf_processor pymupdf
```

For a directory:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/standards \
  --output_dir /absolute/path/processed \
  --pipeline_type text \
  --recursive \
  --pdf_processor enhanced_docling
```

## 4. Verify before structuring

Check:

- statement wording against source pages;
- identifiers and hierarchical parent/child order;
- table row/column alignment;
- cross-references, annotations, and footnotes;
- edition metadata and page coverage.

Do not normalize wording, invent missing parents, or collapse fragmented source
chains during extraction.

## 5. Transform and hand off

After the Markdown/text artifact passes review, use framework-specific scripts
under `scripts/standards/` or `scripts/standards_org/`. These scripts have
source-specific assumptions; inspect their headers and tests first.

Generic JSON conversion is available:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/framework.md \
  --pipeline_type json \
  --output_format json
```

Downstream standards modeling and search/index ingestion belong to their owning
repositories. Keep the official source metadata with every handoff.
