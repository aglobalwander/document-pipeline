# System map — pipeline-documents

## Runtime

- Python 3.10+ managed by Poetry
- local CLI tooling; no deployed service or HTTP routes
- local PDF stack: Enhanced Docling, Docling, PyMuPDF
- Office stack: MarkItDown, Mammoth, python-pptx, python-docx
- media stack: yt-dlp, FFmpeg wrappers, Deepgram where explicitly configured
- optional LLM APIs: Kimi K3, Gemini, OpenAI, Anthropic, DeepSeek, DashScope
- export stack: pandas, openpyxl, XlsxWriter

## Flow

```text
source -> loader -> processor -> transformer -> portable artifact
```

| Surface | Path | Ownership |
|---|---|---|
| orchestration | `doc_processing/document_pipeline.py` | component selection and execution |
| loaders | `doc_processing/loaders/` | source normalization |
| processors | `doc_processing/processors/` | extraction, OCR, transcription |
| transformers | `doc_processing/transformers/` | Markdown, JSON, chunking, CSV/XLSX |
| model clients | `doc_processing/llm/` | explicit paid API calls |
| primary CLIs | `scripts/document_processing/` | user-facing runners |
| collection jobs | `scripts/collections/` | inventory, resume, manifests |
| runtime state | `data/output/`, `data/cache/` | generated artifacts and checkpoints |

## Boundaries

- Default PDF work stays local through Enhanced Docling.
- Model judgment defaults to interactive subscription tools; Python API clients
  activate only after an explicit provider choice.
- Kimi Code subscription OAuth and Kimi Platform API keys are separate lanes.
- Downstream storage/search systems ingest outputs; this repo does not verify
  their ingestion state.
- `data/processing_registry.yaml` is collection runtime state and may be dirty
  during active work.
