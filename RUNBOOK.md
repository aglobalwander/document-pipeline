# Runbook — pipeline_documents

## Local Setup
```bash
cd _02_platforms/pipeline-documents
poetry install
```

## Process Documents
```bash
# PDF processing (recommended: enhanced Docling, free)
poetry run python scripts/document_processing/master_docling.py \
  --input_path <pdf> --output_format markdown

# Full pipeline with options
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path <path> --pipeline_type markdown --output_format md

# YouTube transcript download
poetry run python batch_youtube_download.py
```

## Common Commands
```bash
poetry run python scripts/document_processing/run_pipeline.py --help
poetry run python scripts/document_processing/master_docling.py --help
```

## Known Issues
- Conda environments lack required packages; always use Poetry
- YouTube downloads may require browser cookies for private videos
