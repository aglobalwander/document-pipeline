# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Document Pipeline Overview

The document processing pipeline is a system that processes various document formats (PDF, DOCX, PPTX, images, audio, video) and transforms them into structured outputs (text, markdown, JSON). It can also store documents in a vector database (Weaviate) for search and retrieval.

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
--ocr_mode <mode>          # OCR mode: hybrid, docling, enhanced_docling, gpt
--extract_tables           # Enable table extraction (default: enabled)
--no_extract_tables        # Disable table extraction
--detect_columns           # Enable column detection (default: enabled)
--no_detect_columns        # Disable column detection
```

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
--llm_provider <provider>  # LLM provider: openai, gemini, anthropic, deepseek
--llm_model <model>        # Specific LLM model name
--api_key <key>            # API key for LLM provider
```

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
   - PDFProcessor, EnhancedDoclingPDFProcessor, MammothDOCXProcessor, MarkItDownPPTXProcessor

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

4. **LLM Integration**: Can leverage OpenAI, Anthropic, Gemini, or DeepSeek models for enhanced processing