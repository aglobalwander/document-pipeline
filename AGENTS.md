# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Document Pipeline Overview

The document processing pipeline is a system that processes various document formats (PDF, DOCX, PPTX, images, audio, video) and transforms them into structured outputs (text, markdown, JSON). It focuses on clean extraction/transform so downstream systems (Milvus, Postgres, etc.) can ingest the outputs as needed.

**Processing Strategy (Scott's Preference):**
- **Default for LLM tasks**: Codex (FREE with subscription) - Interactive, high quality
- **Default for PDFs**: Enhanced Docling (FREE) - Excellent quality, local OCR
- **Batch automation**: Gemini API (cheap) - Only when explicitly requested
- **Other APIs**: Codex API, GPT-4 - Only when explicitly requested

**Workflow**: Extract with Docling/MarkItDown → Transform/structure with Codex

## Environment Setup

**IMPORTANT: Use Poetry environment for all document processing tasks**

The Poetry environment has all required packages installed including:
- yt-dlp (for YouTube downloads)
- PyMuPDF, docling (for FREE PDF processing with OCR)
- anthropic (for optional Codex API integration)
- google-genai (for optional Gemini API integration)
- mammoth, markitdown (for DOCX/PPTX processing)
- langchain, instructor (for LLM integration)
- pandas, openpyxl (for data export)

**For YouTube Processing:**
```bash
# Download YouTube videos with transcripts
poetry run python batch_youtube_download.py

# Process YouTube URL through document pipeline
poetry run python scripts/document_processing/run_pipeline.py --input_path "https://youtube.com/watch?v=..." --pipeline_type markdown --output_format md
```

**For Document Pipeline (PDFs, DOCX, etc):**
```bash
# Recommended: Use enhanced_docling for FREE PDF processing
poetry run python scripts/document_processing/master_docling.py --input_path <pdf_path> --output_format <text|markdown|json>

# Alternative: Use full pipeline with options
poetry run python scripts/document_processing/run_pipeline.py --input_path <path> --pipeline_type <type> --output_format <format>
```

**Note about Conda environments:**
While conda environments are available, they don't have all the required packages:
- `base` (Python 3.10.14) - Limited packages: openpyxl, pandas, tqdm
- `ds-template` (Python 3.12.11) - Limited packages: openpyxl, pandas, tqdm  
- `my-crawler` (Python 3.11.13) - Limited packages: pandas only

The pipeline uses a modular architecture consisting of:
- **Loaders**: Read files of various formats
- **Processors**: Extract content from documents 
- **Transformers**: Convert between formats or chunk the data

## Key Command-Line Tools

### Main Processing Scripts

```bash
# Process a single file with default settings
python scripts/run_pipeline.py --input_path <path_to_file> --pipeline_type <text|markdown|json|structured> --output_format <txt|md|json|csv|xlsx>

# Enhanced Docling processor for PDFs (recommended for most cases)
python scripts/master_docling.py --input_path <path_to_pdf> --output_format <text|markdown|json>

# Process a directory of files 
python scripts/run_pipeline.py --input_path <directory_path> --pipeline_type <type> --recursive
```

### Command-Line Options

#### Common Options
```bash
--input_path               # Path to input file or directory
--output_dir               # Output directory (default: data/output)
--pipeline_type            # Pipeline type: text, markdown, json, structured
--output_format            # Output format: txt, md, json, csv, xlsx
--recursive                # Process directories recursively
```

#### PDF Processing Options
```bash
--ocr_mode <mode>          # OCR mode: enhanced_docling (FREE, default), docling, Codex, gemini, gpt
--extract_tables           # Enable table extraction (default: enabled)
--no_extract_tables        # Disable table extraction
--detect_columns           # Enable column detection (default: enabled)
--no_detect_columns        # Disable column detection
```

**OCR Mode Cost Comparison:**
- `enhanced_docling` (default): **FREE** - Local OCR, excellent quality
- `docling`: **FREE** - Basic Docling without enhancements
- `gemini`: **$0.08-0.30/1M tokens** - Cheap API option (requires GEMINI_API_KEY)
- `Codex`: **$3-15/1M tokens** - High quality (requires ANTHROPIC_API_KEY, opt-in)
- `gpt`: **$2.50-10/1M tokens** - Premium option (requires OPENAI_API_KEY)

#### Docling Options
```bash
--output_all_formats       # Output all formats (text, markdown, JSON) - default: enabled
--no_all_formats           # Disable multi-format output
--use_cache                # Enable processing cache (default: enabled)
--no_cache                 # Disable processing cache
--clear_cache              # Clear existing cache before processing
```

#### LLM Integration Options
```bash
--llm_provider <provider>  # LLM provider: openai, gemini, anthropic (Codex), deepseek, dashscope
--llm_model <model>        # Specific LLM model name
--api_key <key>            # API key for LLM provider
```

**Setting API Keys:**
Add to `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-...     # For Codex (optional)
GEMINI_API_KEY=...               # For Gemini (optional)
OPENAI_API_KEY=sk-...            # For GPT (optional)
```

**Note**: By default, the pipeline uses FREE local processing. API keys are only needed when explicitly using paid options.

## Pipeline Architecture

The pipeline is built around the following components:

1. **DocumentPipeline** (`doc_processing/document_pipeline.py`) - Core orchestration class that:
   - Determines appropriate loaders and processors based on file type
   - Constructs the processing pipeline

2. **BaseLoader** implementations:
   - PDFLoader, DocxLoader, TextLoader, ImageLoader, VideoLoader, AudioLoader, YouTubeLoader

3. **BaseProcessor** implementations:
   - EnhancedDoclingPDFProcessor (FREE, default for PDFs)
   - ClaudePDFProcessor (opt-in, native PDF support)
   - DoclingPDFProcessor, PyMuPDFProcessor (FREE alternatives)
   - GPTPVisionProcessor (paid, page-by-page)
   - MammothDOCXProcessor, MarkItDownPPTXProcessor

4. **BaseTransformer** implementations:
   - TextToMarkdown, TextToJSON, LangChainChunker, InstructorExtractor, JsonToCSV, JsonToExcel

## Development Notes

### Dependencies
The project uses Poetry for dependency management:
```bash
# Install dependencies
poetry install

# Add a new dependency
poetry add package-name
```

### Project Structure
- `doc_processing/` - Core library modules
  - `embedding/` - Shared loader/processor/transformer primitives
  - `loaders/` - File loading components
  - `processors/` - Content extraction components
  - `transformers/` - Format conversion components
  - `templates/` - Prompt templates for LLMs
  - `utils/` - Helper utilities

- `scripts/` - CLI entry points and utilities
- `data/` - Input and output directories
  - `input/` - Source documents organized by type
  - `output/` - Output files organized by format
  - `cache/` - Processing cache for resumable operations

### Key Features

1. **Multi-format Output**: When using the EnhancedDoclingPDFProcessor, the pipeline outputs to:
   - Text: `data/output/text/`
   - Markdown: `data/output/markdown/` 
   - JSON: `data/output/json/`

2. **Processing Cache**: Enables resumable processing of large documents:
   - Caches progress after each page
   - Automatically resumes from last processed page if interrupted

3. **Flexible Pipeline Types**:
   - `text`: Raw text extraction 
   - `markdown`: Formatted markdown output
   - `json`: Structured JSON output
   - `structured`: Instructor-based extraction into custom schemas

4. **LLM Integration**: Can leverage OpenAI, Anthropic (Codex), Gemini, or DeepSeek models for enhanced processing
   - **Codex Integration** (FREE): Use Codex interactively to review/improve outputs
   - **API Integration** (Paid, opt-in): Automated processing with Codex, GPT-4, or Gemini APIs

## Using Pipeline from Other Repos

### Option A: Process files from anywhere (works now)
The pipeline accepts any absolute path - process files from any repo:

```bash
# Process a file from another repo
cd ~/Development/master_projects/pipeline-documents
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path ~/Development/other-repo/docs/document.docx \
  --output_dir ~/Development/other-repo/data/processed \
  --pipeline_type structured

# Or use Codex interactively
# "Process this file: ~/Development/etl_drupal/data/calendar.docx and output structured JSON"
```

### Option B: Install as package (future)
TODO: Make `doc_processing` pip-installable so other repos can import directly:
```python
# Future usage in other repos
from doc_processing import DocumentPipeline
pipeline = DocumentPipeline()
result = pipeline.process("/path/to/any/file.docx")
```

## Typical Workflow

1. **Extract**: Use Docling (PDF) or MarkItDown (DOCX/PPTX) to get raw content
2. **Review**: Check extracted markdown/text for quality
3. **Transform**: Ask Codex to structure the data (normalize dates, categorize, etc.)
4. **Output**: JSON for flexibility, CSV for spreadsheets, or direct to downstream system

## API Access

All credentials at `~/.config/api-keys/.env.master`. See global `api-keys` skill.
By default, the pipeline uses FREE local processing. API keys only needed for paid options.
