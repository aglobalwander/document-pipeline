# MarkitDown Direct Conversion Tool

This utility script provides a simple way to convert documents directly to Markdown using the MarkitDown library, bypassing the pipeline's standard processing flow.

## Overview

The `direct_markitdown.py` script is a lightweight wrapper around the MarkItDown library that allows for quick and efficient document conversion to Markdown. It's particularly useful for DOCX files where the direct MarkitDown approach produces cleaner, more compact output with better formatting preservation compared to the pipeline's standard Mammoth-based processor.

## Usage

```bash
# Basic usage - print to stdout
python direct_markitdown.py path/to/document.docx

# Save to file
python direct_markitdown.py path/to/document.docx output.md
```

## Supported File Types

MarkitDown supports a wide range of file formats:

- DOCX (Word)
- PPTX (PowerPoint) 
- XLSX (Excel)
- PDF
- Images (EXIF metadata and OCR)
- Audio (EXIF metadata and speech transcription)
- HTML
- Text-based formats (CSV, JSON, XML)
- ZIP files
- YouTube URLs
- EPubs

## Advantages Over Pipeline Processing

For DOCX files specifically:
- More compact output (typically 3-4x smaller file size)
- Better table formatting and preservation
- Support for embedded images (as base64-encoded content)
- Better handling of complex document structures
- Faster processing for large documents

## Installation Requirements

The script requires the MarkitDown library with appropriate dependencies:

```bash
# Install with all dependencies
pip install 'markitdown[all]'

# Or install with specific dependencies
pip install 'markitdown[docx,pdf]'
```

## Integration with the Pipeline

While this script operates independently of the main pipeline, the outputs can still be used with other pipeline components by:

1. First converting the document: `python direct_markitdown.py input.docx output.md`
2. Then processing the Markdown: `python scripts/run_pipeline.py --input_path output.md --pipeline_type json`

For a detailed comparison of processing approaches, see the DOCX Processing section in the USER_GUIDE.md.