# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Document Pipeline Overview

The document processing pipeline is a system that processes various document formats (PDF, DOCX, PPTX, images, audio, video) and transforms them into structured outputs (text, markdown, JSON). It can also store documents in a vector database (Weaviate) for search and retrieval.

**Cost-Effective Processing Strategy:**
- **Default**: Enhanced Docling (FREE) - Excellent quality for most PDFs
- **Fallback**: Docling → Gemini (FREE or cheap)
- **Optional**: Claude API, GPT-4 (requires API keys, opt-in only)
- **Interactive**: Claude Code (FREE with subscription) - Use for complex cases

See [CLAUDE_CODE_WORKFLOW.md](docs/CLAUDE_CODE_WORKFLOW.md) for detailed cost-saving strategies.

## Environment Setup

**IMPORTANT: Use Poetry environment for all document processing tasks**

The Poetry environment has all required packages installed including:
- yt-dlp (for YouTube downloads)
- PyMuPDF, docling (for FREE PDF processing with OCR)
- anthropic (for optional Claude API integration)
- google-genai (for optional Gemini API integration)
- mammoth, markitdown (for DOCX/PPTX processing)
- weaviate-client (for vector database)
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
- `ds-template` (Python 3.12.11) - Limited packages: openpyxl, pandas, tqdm, weaviate-client  
- `my-crawler` (Python 3.11.13) - Limited packages: pandas only

The pipeline uses a modular architecture consisting of:
- **Loaders**: Read files of various formats
- **Processors**: Extract content from documents 
- **Transformers**: Convert between formats or chunk the data
- **Embedding**: Optional integration with Weaviate for vector search

## Key Command-Line Tools

### Main Processing Scripts

```bash
# Process a single file with default settings
python scripts/run_pipeline.py --input_path <path_to_file> --pipeline_type <text|markdown|json|weaviate> --output_format <txt|md|json|csv|xlsx>

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
--pipeline_type            # Pipeline type: text, markdown, json, weaviate
--output_format            # Output format: txt, md, json, csv, xlsx
--recursive                # Process directories recursively
```

#### PDF Processing Options
```bash
--ocr_mode <mode>          # OCR mode: enhanced_docling (FREE, default), docling, claude, gemini, gpt
--extract_tables           # Enable table extraction (default: enabled)
--no_extract_tables        # Disable table extraction
--detect_columns           # Enable column detection (default: enabled)
--no_detect_columns        # Disable column detection
```

**OCR Mode Cost Comparison:**
- `enhanced_docling` (default): **FREE** - Local OCR, excellent quality
- `docling`: **FREE** - Basic Docling without enhancements
- `gemini`: **$0.08-0.30/1M tokens** - Cheap API option (requires GEMINI_API_KEY)
- `claude`: **$3-15/1M tokens** - High quality (requires ANTHROPIC_API_KEY, opt-in)
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
--llm_provider <provider>  # LLM provider: openai, gemini, anthropic (claude), deepseek
--llm_model <model>        # Specific LLM model name
--api_key <key>            # API key for LLM provider
```

**Setting API Keys:**
Add to `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-...     # For Claude (optional)
GEMINI_API_KEY=...               # For Gemini (optional)
OPENAI_API_KEY=sk-...            # For GPT (optional)
```

**Note**: By default, the pipeline uses FREE local processing. API keys are only needed when explicitly using paid options.

#### Weaviate Options
```bash
--collection <name>        # Target Weaviate collection name
--weaviate_url <url>       # Weaviate URL (uses env var if not set)
--weaviate_api_key <key>   # Weaviate API key (uses env var if not set)
```

## Pipeline Architecture

The pipeline is built around the following components:

1. **DocumentPipeline** (`doc_processing/document_pipeline.py`) - Core orchestration class that:
   - Determines appropriate loaders and processors based on file type
   - Constructs the processing pipeline
   - Handles Weaviate integration when enabled

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
  - `embedding/` - Weaviate integration
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
   - `weaviate`: Vector database storage and retrieval

4. **LLM Integration**: Can leverage OpenAI, Anthropic (Claude), Gemini, or DeepSeek models for enhanced processing
   - **Claude Code Integration** (FREE): Use Claude Code interactively to review/improve outputs
   - **API Integration** (Paid, opt-in): Automated processing with Claude, GPT-4, or Gemini APIs

## Cost-Effective Processing Strategies

### Default Workflow (Zero Cost)
```bash
# Step 1: Process with enhanced_docling (FREE)
poetry run python scripts/document_processing/master_docling.py --input_path document.pdf

# Step 2: Review output
cat data/output/markdown/document_docling.md

# Step 3 (if needed): Ask Claude Code for help
# Open output file and ask: "Can you clean up these OCR errors?"
```

### When to Use Paid APIs
- **Batch processing**: Many documents needing automation → Use Gemini (cheapest)
- **Complex documents**: High accuracy needed → Use Claude API (best quality/cost)
- **Manual review**: Complex interpretation → Use Claude Code (FREE interactive)

See [docs/CLAUDE_CODE_WORKFLOW.md](docs/CLAUDE_CODE_WORKFLOW.md) for detailed examples and workflows.