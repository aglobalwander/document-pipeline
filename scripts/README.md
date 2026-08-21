# Scripts

Run scripts from the repository root through Poetry unless a shell script says
otherwise.

## Primary entry points

```bash
poetry run python scripts/document_processing/run_pipeline.py --help
poetry run python scripts/document_processing/master_docling.py --help
```

- `document_processing/`: general pipeline, Enhanced Docling, MarkItDown, and
  PPTX utilities
- `collections/`: inventory, resumable batches, manifests, and storage fallback
- `pdf_processing/`: focused PyMuPDF analysis and batch tools
- `content_processing/`: heading/chapter splitting
- `standards/`: framework-specific extraction
- `standards_org/`: standards file organization and analysis
- `media/`: YouTube and media diagnostics
- `utilities/`: setup and maintenance helpers
- `shell/`: shell wrappers for standards workflows

Vector-database ingestion is downstream and is not a script category in this
repository.

## Common commands

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown

poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/input \
  --pipeline_type text \
  --recursive

poetry run python scripts/collections/inventory_collection.py \
  --source_dir /absolute/path/collection
```

Check an individual script's `--help` or header before use. Some specialized
standards and collection scripts require source-specific inputs.
