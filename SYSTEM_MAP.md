# System Map — pipeline_documents

## Stack
- Python 3.x (Poetry)
- Docling, MarkItDown, PyMuPDF (PDF processing)
- yt-dlp (YouTube downloads)
- anthropic, google-genai (optional API integration)
- pandas, openpyxl (data export)

## Module Inventory
| Module | Type | Path | Purpose |
|--------|------|------|---------|
| doc_processing/ | library | doc_processing/ | Core document processing pipeline |
| cli/ | entrypoint | cli/ | Command-line interface |
| scripts/ | automation | scripts/ | Pipeline runners (run_pipeline.py, master_docling.py) |
| data/ | data | data/ | Input/output document storage |
| docs/ | docs | docs/ | Pipeline documentation |

## Key Services & Routes
- Services: none (CLI tooling)
- Routes: none
- YouTube downloaders: batch_youtube_download.py, download_transcript.py, etc.

## Integrations
- Feeds into: knowledge-management (document ingestion)
- Optional APIs: Claude API, Gemini API (only when explicitly requested)
- Default: Docling for PDFs (free, local OCR), Claude Code for LLM tasks

## Key Paths
- Metadata root: `_02_platforms/pipeline-documents`
- Scripts: `scripts/document_processing/`
- CLI: `cli/`
- Output: `data/output/`
