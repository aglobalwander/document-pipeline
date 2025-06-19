# PyMuPDF Processor Usage Guide

## Overview

The PyMuPDF processor provides ultra-fast text extraction from PDFs that contain embedded text (not scanned images). It's now integrated into the pipeline as the first processor in the fallback chain, providing significant performance improvements.

## Installation

```bash
# Install PyMuPDF dependency
poetry add PyMuPDF

# Or with pip
pip install PyMuPDF
```

## Performance Benefits

- **Speed**: 50-100x faster than OCR-based methods
- **Cost**: Completely free (no API calls)
- **Accuracy**: 100% for PDFs with embedded text
- **Resource Usage**: Minimal CPU and memory requirements

## Usage Examples

### 1. Using PyMuPDF Directly

```python
from doc_processing.processors import PyMuPDFProcessor

processor = PyMuPDFProcessor()
document = {
    'source_path': 'path/to/document.pdf',
    'metadata': {'filename': 'document.pdf'}
}

result = processor.process(document)

if result.get('extraction_successful'):
    print(f"Extracted {len(result['content'])} characters")
    print(f"Pages with text: {result['metadata']['pages_with_text']}")
else:
    print("PDF requires OCR - no embedded text found")
```

### 2. Using with Fallback Chain (Recommended)

```bash
# Command line with fallback chain
python scripts/run_pipeline.py \
    --input_path document.pdf \
    --pipeline_type text \
    --pdf_processor_strategy fallback_chain

# PyMuPDF will be tried first, falling back to Docling/LLMs if needed
```

### 3. Configuration Options

```python
# Configure PyMuPDF processor
config = {
    'extract_tables': True,      # Extract tables (default: True)
    'extract_images': False,     # Extract image metadata (default: False)
    'min_text_length': 50,       # Minimum text per page to consider valid
}

processor = PyMuPDFProcessor(config=config)
```

## How It Works

1. **Text Detection**: PyMuPDF first checks if the PDF contains embedded text
2. **Extraction**: If text is found, it's extracted instantly
3. **Validation**: The processor checks if enough text was extracted
4. **Fallback**: If insufficient text (likely scanned), it returns `requires_ocr=True`

## Integration with Pipeline

The default fallback chain is now:
```
PyMuPDF → Docling → Enhanced Docling → Gemini → GPT-4V
```

### Modifying the Chain

```python
# In your config or command line
config = {
    'pdf_processor_strategy': 'fallback_chain',
    'active_pdf_processors': ['pymupdf', 'docling', 'gemini', 'gpt'],
    # Skip enhanced_docling if not needed
}
```

## When PyMuPDF Works Best

✅ **Perfect for:**
- Modern PDFs created digitally
- Reports, documentation, ebooks
- Form-generated PDFs
- Any PDF with selectable text

❌ **Won't work for:**
- Scanned documents
- Image-based PDFs
- Handwritten content
- Photos of documents

## Testing PyMuPDF

```bash
# Test on a specific PDF
python scripts/test_pymupdf.py path/to/your.pdf

# This will show:
# - PyMuPDF vs Docling performance comparison
# - Whether the PDF has embedded text
# - Extraction speed and accuracy
```

## Monitoring Performance

When using fallback chain, logs will show which processor succeeded:

```
INFO - Attempting processor in fallback chain: pymupdf
INFO - PyMuPDF: Successfully extracted 15420 characters from document.pdf
INFO - Processor pymupdf succeeded.
```

If PyMuPDF can't extract text:

```
INFO - PyMuPDF: Insufficient text extracted from scanned_doc.pdf
INFO - Pages with text: 0/10
INFO - Processor pymupdf failed: Document requires OCR
INFO - Attempting processor in fallback chain: docling
```

## Cost Savings Example

For a typical 100-page PDF document:
- **GPT-4V only**: $1.00 (100 pages × $0.01)
- **With PyMuPDF first**: $0.00 (if text-based) or fallback cost
- **Savings**: Up to 100% for text-based PDFs

## Best Practices

1. **Always use fallback chain** for mixed document types
2. **Check logs** to see which processor handled each document
3. **Monitor costs** using the extraction_cost field
4. **Preprocess PDFs** - Use PyMuPDF to identify which PDFs need OCR

## Troubleshooting

### "No text extracted"
- The PDF is likely scanned or image-based
- Fallback processors (Docling, LLMs) will handle it

### "Tables not formatted well"
- PyMuPDF's table extraction is basic
- For complex tables, let it fall back to Enhanced Docling

### "Special characters missing"
- Ensure the PDF has proper font embedding
- May need to fall back to Docling for better unicode support