# Invariants — pipeline_documents

## Deployment
- Local-only CLI tool; no server deployment
- Poetry environment required (not conda, not venv)
- Processing strategy: Docling (free) by default; APIs only when asked

## Content Architecture
- Loaders: read files of various formats
- Processors: extract content from documents
- Transformers: convert between formats or chunk data
- Output goes to `data/output/` by default

## Dependencies
- Upstream: none (ingests external documents)
- Downstream: knowledge-management
- Python: Poetry-managed (docling, yt-dlp, PyMuPDF, mammoth, markitdown)
- Remote: https://github.com/aglobalwander/document-pipeline.git

## Git
- Branch: main
- Remote: aglobalwander/document-pipeline
- Conventional commits
