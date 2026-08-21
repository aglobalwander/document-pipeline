# PyMuPDF processor usage

PyMuPDF is the fast path for PDFs with embedded, selectable text. It is local
and free, but it is not OCR and does not guarantee correct reading order for
complex layouts.

## Command

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.pdf \
  --pipeline_type text \
  --pdf_processor pymupdf
```

## Direct use

```python
from doc_processing.processors.pymupdf_processor import PyMuPDFProcessor

processor = PyMuPDFProcessor()
result = processor.process(
    {
        "source_path": "/absolute/path/document.pdf",
        "metadata": {"filename": "document.pdf"},
    }
)
print(result.get("content", ""))
```

## Good fits

- digitally generated reports and ebooks;
- forms with embedded text;
- quick corpus triage where plain text is enough.

## Poor fits

- scanned or photographed pages;
- handwriting;
- tables or multi-column layouts where reading order matters;
- PDFs with broken font maps or copy protection.

## Escalation

If the output is empty or structurally poor, use the recommended Enhanced
Docling path:

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown
```

Review the artifact; do not infer accuracy from speed or character count alone.
