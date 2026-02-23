# Pipeline Documents Command Cheat Sheet

This is a comprehensive reference for all commands available in the pipeline-documents repository. Use this guide to quickly find the right command for your document processing needs, from simple one-off operations to multi-format ETL batches.

⸻

## 0. Conventions

```bash
python run_pipeline.py ...          # Flexible ETL runner (files/dirs/URLs)
just ...                            # Optional shortcuts (add to Justfile)
```

**Prerequisites**: 
- Execute from repo root with active virtualenv
- Required API keys set in environment variables (OpenAI, Gemini, Deepgram)

⸻

## 1. Quick Ingest Commands

| Action | Command |
|--------|---------|
| Process single PDF → Markdown | `python run_pipeline.py --input_path docs/intro.pdf --pipeline_type markdown` |
| Process PDF with PyMuPDF (fastest) | `python run_pipeline.py --input_path docs/intro.pdf --pipeline_type text --pdf_processor pymupdf` |
| Process PDF with fallback chain | `python run_pipeline.py --input_path docs/intro.pdf --pipeline_type text --pdf_processor_strategy fallback_chain` |
| Process folder (non-recursive) | `python run_pipeline.py --input_path data/pdfs --pipeline_type text` |
| Process folder recursively | `python run_pipeline.py --input_path data/pdfs -r --pipeline_type text` |
| Image processing with Gemini | `python run_pipeline.py --input_path data/images -r --pipeline_type text --image_backend gemini` |
| Deepgram diarization | `python run_pipeline.py --input_path data/audio -r --pipeline_type text --deepgram_params '{"diarize": true}'` |
| YouTube ingestion | `python run_pipeline.py --input_path https://youtu.be/abcd1234 --pipeline_type text` |

⸻

## 2. Format Transforms

| Conversion | Command |
|------------|---------|
| Markdown → JSON | `python run_pipeline.py --input_path notes/readme.md --pipeline_type json --output_format json` |
| TXT → Markdown | `python run_pipeline.py --input_path data/txt -r --pipeline_type markdown` |
| DOCX → Text | `python run_pipeline.py --input_path docs/report.docx --pipeline_type text` |
| DOCX → Markdown (pipeline) | `python run_pipeline.py --input_path docs/report.docx --pipeline_type markdown` |
| DOCX → Markdown (direct MarkitDown) | `python -c "from markitdown import MarkItDown; md = MarkItDown(); result = md.convert('docs/report.docx'); print(result.text_content)"` |
| JSON → CSV | `python run_pipeline.py --input_path data/json/invoice.json --pipeline_type json --output_format csv` |
| JSON → Excel | `python run_pipeline.py --input_path data/json/invoice.json --pipeline_type json --output_format xlsx` |

⸻

## 5. PDF Processing Strategies

### Available PDF Processors

| Processor | Speed | Cost | Best For |
|-----------|-------|------|----------|
| PyMuPDF | 50-100x faster | Free | Modern PDFs with embedded text |
| Docling | Moderate | Free | Complex layouts, mixed content |
| Enhanced Docling | Moderate | Free | Multi-format output (text/md/json) |
| Gemini | Fast | ~$0.0002/page | When Docling fails |
| GPT-4V | Moderate | ~$0.01/page | Handwritten text, poor scans |

### Exclusive Strategy (Use specific processor)
```bash
# Use only PyMuPDF (fastest)
python run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor pymupdf

# Use only Docling
python run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor docling

# Use only Gemini
python run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor gemini
```

### Fallback Chain Strategy (Recommended)
```bash
# Try processors in order: PyMuPDF → Docling → Enhanced Docling → Gemini → GPT-4V
python run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor_strategy fallback_chain

# Configure custom fallback order via environment
export PDF_FALLBACK_ORDER='["pymupdf", "gemini", "gpt"]'
python run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor_strategy fallback_chain
```

⸻

## 6. Maintenance & Diagnostics

```bash
# Find large files (10MB or larger)
python tools/find_large_files.py 10M

# List the 15 largest directories in the repo
python tools/du_top.py --top 15

# Run test suite (excludes slow tests)
just test  # Alias for: pytest -m "not slow"
```

⸻

## 7. Justfile Shortcuts

```bash
# View all shortcuts
just -l

# Process PDF to Markdown
just pdf-md path=docs/intro.pdf

```

⸻

## 8. Advanced Options

### PPTX Processing

```bash
# Process PowerPoint with hybrid strategy (PDF + speaker notes)
python run_pipeline.py --input_path slides/team_deck.pptx \
                      --pipeline_type markdown \
                      --pptx_strategy hybrid
```

### Excel Output Options

```bash
# Use a custom Excel template
python run_pipeline.py --input_path data/json/invoice.json \
                      --pipeline_type json \
                      --output_format xlsx \
                      --excel_template finance

# Specify a custom template directory
python run_pipeline.py --input_path data/json/invoice.json \
                      --pipeline_type json \
                      --output_format xlsx \
                      --excel_template_dir /path/to/templates
```

### CSV Output Options

```bash
# Merge multiple JSON files into a single CSV
python run_pipeline.py --input_path data/json \
                      --pipeline_type json \
                      --output_format csv \
                      --merge_csv
```

### Direct MarkitDown Conversion Script

```bash
# Create a reusable script for direct MarkitDown conversion
cat << 'EOF' > scripts/direct_markitdown.py
#!/usr/bin/env python
"""Convert files to Markdown using MarkitDown library directly."""

import os
import sys
from pathlib import Path

def main():
    """Convert file to Markdown using MarkitDown library directly."""
    if len(sys.argv) < 2:
        print("Usage: python direct_markitdown.py <input_file> [output_file]")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # Import MarkitDown
        from markitdown import MarkItDown
        
        # Initialize MarkItDown converter
        print(f"Converting {input_path} to Markdown...")
        md = MarkItDown(enable_plugins=False)
        
        # Convert the file
        result = md.convert(input_path)
        
        # Save result to file or print to stdout
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.text_content)
            print(f"Conversion successful! Output saved to {output_path}")
        else:
            print(result.text_content)
        
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Try installing with: pip install 'markitdown[all]'")
        sys.exit(1)
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x scripts/direct_markitdown.py

# Usage examples:
# python scripts/direct_markitdown.py docs/report.docx output.md
# python scripts/direct_markitdown.py docs/slides.pptx > slides.md
```

## 9. Future Enhancements

- [ ] Add `pipeline chunk promote` – copies extracted files into long-term storage
- [ ] Implement `cleanup_tmp` – nightly job to delete tmp_* older than 14 days
- [ ] Auto-infer pipeline type from MIME / extension (pipeline_type auto)
- [ ] Add `just ingest-youtube <url>` – wrapper for video transcription path

*Last updated: 2025-05-15*
