# Pipeline Documents - Scripts Directory

This directory contains all scripts for the document processing pipeline, organized by functionality.

## Directory Structure

### 📁 `pdf_processing/`
Scripts for processing PDF files using PyMuPDF and other PDF tools.
- PDF analysis and OCR detection
- Batch PDF processing
- PyMuPDF utilities and benchmarks

### 📁 `document_processing/`
Core document processing scripts using various processors.
- `run_pipeline.py` - Main pipeline execution script
- `master_docling.py` - Enhanced Docling processor
- `batch_process.py` - Batch document processing
- MarkItDown processors for DOCX files

### 📁 `vector_db/` (archived)
Legacy scripts for vector database operations (moved to the knowledge-management repo once Milvus became the source of truth).

### 📁 `content_processing/`
Scripts for processing and organizing document content.
- Split documents by headings or chapters
- Content summarization
- Specialized processors (e.g., Cognitive Coaching)

### 📁 `standards/`
Educational standards extraction scripts.
- Extract standards from various frameworks (NCAS, Common Core, C3, NGSS)
- Map standards to Drupal hierarchy
- Extract related entities (EUs, EQs, Big Ideas)

### 📁 `standards_org/`
Scripts for organizing standards files and directories.
- Analyze and organize standards PDFs
- Process standards by framework
- Test standards processing

### 📁 `utilities/`
Helper scripts and utilities.
- NLTK resource downloads
- File size management
- Git LFS migration
- Template creation

### 📁 `media/`
Scripts for processing media files.
- YouTube video processing
- Audio/video extraction utilities

### 📁 `archive/`
Deprecated or old scripts kept for reference.

## Main Entry Points

1. **Document Processing Pipeline**
   ```bash
   python document_processing/run_pipeline.py --input_path <file> --pipeline_type <type> --output_format <format>
   ```

2. **Enhanced Docling Processing**
   ```bash
   python document_processing/master_docling.py --input_path <pdf> --output_format <format>
   ```

3. **Batch PDF Processing**
   ```bash
   python pdf_processing/batch_process_pymupdf.py
   ```

## Script Categories

### Core Processing
- `run_pipeline.py` - Main pipeline orchestrator
- `master_docling.py` - Enhanced PDF processing
- `batch_process.py` - Batch file processing

### Standards Extraction
- See `/standards/README.md` for detailed information

### Database Operations
- Vector database ingestion and search now live in `/knowledge-management`
- Use the JSON/Markdown outputs from this repo as inputs to those pipelines

### Content Organization
- Document splitting by structure
- Content summarization
- Chapter/section extraction

## Usage Notes

1. Most scripts should be run from the project root directory
2. Check individual script headers for specific requirements
3. Ensure environment variables are set for API keys (OpenAI, Anthropic, Gemini, etc.)
4. See `../docs/` for detailed documentation

## Recent Updates

- Reorganized all scripts into categorical directories (2024-06-20)
- Moved standards extraction scripts to dedicated directory
- Cleaned up root scripts directory
- Added comprehensive documentation
