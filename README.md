# Document Processing Pipeline

A powerful, modular document processing framework that transforms various document formats (PDF, DOCX, PPTX, images, audio, video) into structured outputs (text, markdown, JSON). The project now focuses purely on extraction and transformation so you can hand results to whatever downstream system (Milvus, Qdrant, Postgres, etc.) you prefer.

## 🚀 Features

- **Multi-Format Support**: Process PDFs, Word docs, PowerPoints, images, audio, video, and YouTube URLs
- **Flexible Output**: Generate text, markdown, JSON, CSV, or Excel outputs
- **Advanced PDF Processing**: Multiple OCR modes including Docling, GPT-4 Vision, and hybrid approaches
- **Modular Architecture**: Easily extend with custom loaders, processors, and transformers
- **Batch Processing**: Process entire directories with recursive file discovery
- **Resumable Operations**: Processing cache enables resuming interrupted operations
- **LLM Integration**: Leverage OpenAI, Anthropic, Google, or DeepSeek models for enhanced processing

## 📦 Installation

### Prerequisites
- Python 3.8+
- Poetry (recommended) or pip

### Install with Poetry
```bash
git clone https://github.com/yourusername/pipeline-documents.git
cd pipeline-documents
poetry install
```

### Install with pip
```bash
git clone https://github.com/yourusername/pipeline-documents.git
cd pipeline-documents
pip install -e .
```

### Additional Dependencies
```bash
# Download NLTK resources
python scripts/download_nltk_resources.py

# For YouTube processing
pip install yt-dlp

```

## 🚀 Quick Start

### Process a Single PDF
```bash
# Basic text extraction
python scripts/run_pipeline.py --input_path document.pdf --pipeline_type text

# Enhanced PDF processing with Docling
python scripts/master_docling.py --input_path document.pdf --output_format markdown

# Extract to multiple formats
python scripts/master_docling.py --input_path document.pdf --output_all_formats
```

### Process Multiple Files
```bash
# Process all PDFs in a directory
python scripts/run_pipeline.py --input_path /path/to/pdfs --pipeline_type markdown --recursive

# Batch process with optional recursive discovery
python scripts/run_pipeline.py --input_path /path/to/docs --pipeline_type text --recursive
```

### Process External Collections (No Copying)
```bash
# 1) Inventory an external folder first
poetry run python scripts/collections/inventory_collection.py \
  --source_dir "/absolute/path/to/collection"

# 2) Preview processing plan (dry run) with auto storage fallback
scripts/collections/run_collection_with_storage_fallback.sh \
  --storage auto \
  --source_dir "/absolute/path/to/collection" \
  --collection_name "my-collection" \
  --dry_run

# 3) Run full processing (uses /Volumes/My Passport/knowledge-hub when mounted)
scripts/collections/run_collection_with_storage_fallback.sh \
  --storage auto \
  --source_dir "/absolute/path/to/collection" \
  --collection_name "my-collection" \
  --resume
```

Outputs are written under `data/output/collections/{collection_name}/{text,markdown,json}/` with a per-collection `manifest.yaml`.  
Global collection status is tracked in `data/processing_registry.yaml`.  
Use `--resume` to skip files already marked successful with existing outputs.
For large runs, use `scripts/collections/run_collection_with_storage_fallback.sh` so outputs write to an external drive when available and automatically fall back to local paths when not.

## 📖 Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Detailed usage instructions
- **[Command Reference](docs/COMMANDS.md)** - Complete CLI documentation
- **[Overview](docs/OVERVIEW.md)** - Non-technical project overview

## 🏗️ Architecture

The pipeline follows a modular architecture:

```
Input → Loader → Processor → Transformer → Output
```

### Core Components

- **Loaders**: Read various file formats into a common document structure
- **Processors**: Extract and enhance content from documents
- **Transformers**: Convert between formats or chunk documents

### Supported Formats

**Input**: PDF, DOCX, PPTX, TXT, PNG/JPG/JPEG, MP4/AVI/MOV, MP3/WAV, YouTube URLs

**Output**: TXT, MD, JSON, CSV, XLSX

## ⚙️ Configuration

Create a `.env` file for API keys and settings:

```bash
# LLM API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here

# Processing Options
DEFAULT_CHUNK_SIZE=1000
DEFAULT_CHUNK_OVERLAP=200
ENABLE_CACHING=true
```

## 🛠️ Advanced Usage

### Custom Pipeline Configuration
```python
from doc_processing import DocumentPipeline

pipeline = DocumentPipeline(
    pipeline_type="custom",
    ocr_mode="enhanced_docling",
    chunk_size=1500,
    extract_tables=True,
    detect_columns=True
)

result = pipeline.process_document("document.pdf")
```

### Extending the Pipeline
Create custom components by extending base classes:

```python
from doc_processing.base import BaseProcessor

class MyCustomProcessor(BaseProcessor):
    def process(self, document):
        # Custom processing logic
        return enhanced_document
```

## 📊 Performance

- **Caching**: Resume interrupted processing automatically
- **Batch Processing**: Process multiple files concurrently
- **Memory Efficient**: Stream large files without loading entirely into memory
- **Optimized OCR**: Multiple OCR strategies for best accuracy/speed trade-off

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

Built with excellent open-source libraries including:
- [Docling](https://github.com/DS4SD/docling) - Advanced PDF processing
- [LangChain](https://github.com/langchain-ai/langchain) - Document chunking and LLM integration
- [MarkItDown](https://github.com/microsoft/markitdown) - Office document conversion
