# Scripts Directory

This directory contains command-line tools and utilities for the Document Processing Pipeline. Scripts are organized by their primary function.

## Core Pipeline Scripts

These are the main entry points for document processing:

### `run_pipeline.py`
The primary pipeline execution script with comprehensive options for processing documents.
- Supports all input formats (PDF, DOCX, PPTX, images, audio, video)
- Multiple pipeline types (text, markdown, json, weaviate)
- Batch processing with recursive directory support

### `master_docling.py`
Enhanced Docling processor specifically optimized for PDF processing.
- Uses Docling's native processing capabilities
- Supports multi-format output (text, markdown, JSON)
- Includes caching for resumable operations

### `batch_process.py`
Batch processing utility for handling multiple files with Weaviate integration.
- Process entire directories
- Automatic Weaviate collection management
- Progress tracking and error handling

## Utility Scripts

### Testing & Demo Scripts
- `test_youtube_loader.py` - Test YouTube content extraction
- `test_yt_dlp_standalone.py` - Test YouTube downloader functionality
- `direct_markitdown.py` - Direct MarkitDown conversion demo
- `direct_docx_markitdown.py` - DOCX-specific MarkitDown conversion
- `create_dummy_pptx.py` - Generate test PowerPoint files

### Maintenance & Setup Scripts
- `download_nltk_resources.py` - Download required NLTK dependencies
- `download_punkt_tab.py` - Download specific NLTK tokenizer
- `create_default_template.py` - Create Excel output templates
- `filesize.py` - Find large files in the repository
- `git_lfs_migrate.py` - Migrate large files to Git LFS
- `verify_weaviate_connection.py` - Test Weaviate connectivity
- `check_weaviate_api.py` - Check Weaviate API health
- `setup_weaviate_mcp.py` - Configure Weaviate MCP server

## Project-Specific Scripts

### Adaptive Schools Project
Located in the main scripts directory (consider moving to `projects/adaptive_schools/`):
- `ingest_adaptive_school.py` - Standard pipeline ingestion
- `direct_ingest_adaptive_school.py` - Direct ingestion approach
- `query_adaptive_schools.py` - Query the AdaptiveSchools collection
- `verify_adaptive_schools_collection.py` - Verify collection setup
- `delete_adaptive_schools_collection.py` - Clean up collection
- `summarize_adaptive_schools.py` - Generate collection summaries
- `split_chapters.py` - Split book into chapter files
- `split_cognitive_coaching.py` - Split Cognitive Coaching content
- `split_by_headings.py` - Generic heading-based content splitter

## Usage Examples

### Basic Document Processing
```bash
# Process a single PDF to text
python scripts/run_pipeline.py --input_path document.pdf --pipeline_type text

# Process with enhanced Docling
python scripts/master_docling.py --input_path document.pdf --output_format markdown

# Process a directory recursively
python scripts/run_pipeline.py --input_path /path/to/docs --pipeline_type markdown --recursive
```

### Weaviate Integration
```bash
# Ingest documents to Weaviate
python scripts/batch_process.py --input_dir /path/to/docs --collection MyDocuments

# Verify Weaviate connection
python scripts/verify_weaviate_connection.py

# Query a collection
python scripts/query_adaptive_schools.py --query "search term"
```

### Setup and Maintenance
```bash
# Download required NLTK resources
python scripts/download_nltk_resources.py

# Find large files that should use Git LFS
python scripts/filesize.py

# Set up Weaviate MCP server
python scripts/setup_weaviate_mcp.py
```

## Script Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **Core** | Main pipeline functionality | `run_pipeline.py`, `master_docling.py` |
| **Testing** | Test specific features | `test_youtube_loader.py`, `direct_markitdown.py` |
| **Maintenance** | Setup and repository maintenance | `download_nltk_resources.py`, `git_lfs_migrate.py` |
| **Weaviate** | Vector database operations | `verify_weaviate_connection.py`, `batch_process.py` |
| **Project-Specific** | Custom workflows for specific projects | `ingest_adaptive_school.py`, `split_chapters.py` |

## Adding New Scripts

When adding new scripts, please:
1. Choose the appropriate category
2. Include a docstring describing the script's purpose
3. Add command-line help using `typer` or `argparse`
4. Update this README with the new script's description
5. Consider if it belongs in a subdirectory for better organization

## Future Organization

The scripts directory is planned to be reorganized into subdirectories:
```
scripts/
├── core/           # Main pipeline scripts
├── utilities/      # General utilities
├── testing/        # Test and demo scripts
├── maintenance/    # Setup and maintenance
└── projects/       # Project-specific scripts
```