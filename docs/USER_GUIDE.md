# Document Processing Pipeline User Guide

## Overview
The document processing pipeline provides a flexible system for extracting and transforming content from various document formats (PDF, DOCX, PPTX, etc.) into structured outputs. The pipeline now includes PyMuPDF for ultra-fast text extraction from PDFs, alongside Docling's native processing capabilities for enhanced accuracy and caching support for resumable processing.

## Key Features

### Multi-Format Output
When using the enhanced Docling processor, the pipeline supports output in multiple formats:
- **Primary format**: Specified by `--output_format` (text, markdown, json)
- **Additional formats**: Automatically saved to subdirectories:
  - `data/output/text/`
  - `data/output/markdown/`
  - `data/output/json/`

### Resumable Processing with Caching
The pipeline now includes a caching mechanism that allows processing to be resumed if interrupted:
- Automatically saves progress after each page is processed
- Resumes from the last processed page if the pipeline is restarted
- Maintains document integrity across processing sessions

## Command-Line Options

### Basic Usage
```bash
python scripts/master_docling.py --input_path data/input/pdfs/cc.pdf --output_format text
```

### Format Control Options
- `--output_format`: Specify primary output format (text, markdown, json)
- `--no_all_formats`: Disable additional output formats (default: false)

### Caching Options
- `--use_cache`: Enable processing cache (default: true)
- `--no_cache`: Disable processing cache

### PDF Processing Options
- `--extract_tables`: Enable table extraction (default: true)
- `--no_extract_tables`: Disable table extraction
- `--pdf_processor_strategy`: Choose processing strategy (exclusive, fallback_chain)
- `--pdf_processor`: Specific processor for exclusive strategy (pymupdf, docling, enhanced_docling, gemini, gpt)

## Output Structure
```
data/output/
├── text/              # Text format outputs (.txt)
├── markdown/          # Markdown format outputs (.md)
├── json/              # JSON format outputs (.json)
└── ...                # Other pipeline-specific outputs
```

## Cache Structure
```
data/cache/
└── [document_id].json # Cache files for resumable processing
```

## PDF Processing Strategies

### Available PDF Processors
1. **PyMuPDF** (New!) - Ultra-fast text extraction for PDFs with embedded text
   - Speed: 50-100x faster than OCR methods
   - Cost: Free
   - Best for: Modern PDFs, reports, ebooks with selectable text

2. **Docling** - Advanced document understanding with layout preservation
   - Speed: Moderate
   - Cost: Free (local processing)
   - Best for: Complex layouts, mixed content

3. **Enhanced Docling** - Docling with multi-format output and caching
   - Speed: Moderate
   - Cost: Free (local processing)
   - Best for: When you need text, markdown, and JSON outputs

4. **Gemini** - Google's AI for document processing
   - Speed: Fast
   - Cost: ~$0.0002 per page
   - Best for: When Docling fails, complex documents

5. **GPT-4V** - OpenAI's vision model
   - Speed: Moderate
   - Cost: ~$0.01 per page
   - Best for: Handwritten text, poor quality scans

### Processing Strategies

#### Exclusive Strategy (Default)
Uses only the specified processor:
```bash
python scripts/run_pipeline.py --input_path document.pdf --pipeline_type text --pdf_processor pymupdf
```

#### Fallback Chain Strategy (Recommended)
Tries processors in order until one succeeds:
```bash
python scripts/run_pipeline.py --input_path document.pdf --pipeline_type text --pdf_processor_strategy fallback_chain
```
Default order: PyMuPDF → Docling → Enhanced Docling → Gemini → GPT-4V

## Examples

### Basic Text Output with PyMuPDF (Fastest)
```bash
python scripts/run_pipeline.py --input_path data/input/pdfs/document.pdf --pipeline_type text --pdf_processor pymupdf
```

### Basic Text Output with Docling
```bash
python scripts/master_docling.py --input_path data/input/pdfs/document.pdf --output_format text
```

### Full Multi-Format Output with Caching
```bash
python scripts/master_docling.py --input_path data/input/pdfs/document.pdf --output_format markdown --use_cache
```

### Disable Caching for One-Time Processing
```bash
python scripts/master_docling.py --input_path data/input/pdfs/document.pdf --output_format json --no_cache
```

### Process with Table Extraction Disabled
```bash
python scripts/master_docling.py --input_path data/input/pdfs/document.pdf --output_format text --no_extract_tables
```

## Troubleshooting

### Interrupted Processing
If processing is interrupted, simply run the same command again. The pipeline will automatically resume from the last successfully processed page.

### Cache Issues
If you encounter issues with cached results, simply delete the cache files in the `data/cache/` directory.

### Performance Considerations
- Caching adds minimal overhead but provides significant benefits for large documents
- For small documents or one-time processing, you can disable caching with `--no_cache`

## DOCX Processing

The pipeline supports two methods for converting DOCX files to Markdown:

### Pipeline Approach (MammothDOCXProcessor)
Uses the pipeline's integrated DOCX processor based on the Mammoth library:

```bash
python scripts/run_pipeline.py --input_path data/input/docx/document.docx --pipeline_type markdown
```

Features:
- Integrated with the pipeline's workflow
- Preserves basic document structure (headings, lists, tables)
- Outputs to configured output directories

### Direct MarkitDown Approach
Uses the MarkitDown library directly for more efficient conversion:

```bash
python scripts/direct_markitdown.py data/input/docx/document.docx output.md
```

Features:
- More compact and cleaner output 
- Better table formatting
- Preserves images as base64-encoded content
- Faster processing for large documents

### Comparison
| Feature | Pipeline Approach | Direct MarkitDown |
|---------|-------------------|-------------------|
| Output Size | Larger/more verbose | More compact |
| Table Support | Basic | Enhanced |
| Image Support | Limited | Base64 encoded |
| Integration | Full pipeline features | Standalone |
| Performance | Good | Better |
