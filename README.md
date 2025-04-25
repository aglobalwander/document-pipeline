# Document Processing Pipeline

A modular document processing pipeline for converting various file types (PDF, text, markdown, etc.) to structured formats and integrating with Weaviate for semantic search and retrieval.

## 🌟 Features

- **Modular Architecture**: Easily extendable for different document types and processing needs
- **PDF Processing**: Convert PDFs to text, markdown, or JSON using GPT-4 Vision for high-quality OCR
- **Markdown & JSON Conversion**: Transform documents to structured formats
- **Document Chunking**: Split documents into semantic chunks for embedding and retrieval
- **Weaviate Integration**: Store and search documents and chunks in a vector database
- **Jinja Templates**: Flexible prompt and output formatting with templates
- **Batch Processing**: Process multiple documents with progress tracking
- **Jupyter Notebooks**: Interactive examples for different processing pipelines

## 📋 Requirements

- Python 3.10+
- OpenAI API key (for GPT-4 Vision OCR)
- Weaviate instance (optional, for vector search functionality)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/doc-processing-pipeline.git
cd doc-processing-pipeline
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env to add your API keys
```

## 📄 Directory Structure

```
doc_processing_pipeline/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── notebooks/
│   ├── 01_pdf_to_text_demo.ipynb
│   ├── 02_document_loading_demo.ipynb
│   ├── 03_weaviate_integration_demo.ipynb
│   └── 04_end_to_end_pipeline_demo.ipynb
├── scripts/
│   ├── batch_process.py
│   └── weaviate_operations.py
├── doc_processing/
│   ├── __init__.py
│   ├── config.py
│   ├── document_pipeline.py
│   ├── loaders/
│   ├── processors/
│   ├── transformers/
│   ├── embedding/
│   └── templates/
└── tests/
    └── ...
```

## 🔍 Usage Examples

### Basic PDF to Text Conversion

```python
from doc_processing.document_pipeline import DocumentPipeline

# Configure pipeline
pipeline = DocumentPipeline()
pipeline.configure_pdf_to_text_pipeline()

# Process a PDF file
result = pipeline.process_document("path/to/document.pdf")
print(f"Extracted {len(result['content'])} characters of text")
```

### PDF to Markdown with Custom Templates

```python
from doc_processing.document_pipeline import DocumentPipeline

# Configure pipeline with custom settings
config = {
    'markdown_transformer_config': {
        'generate_toc': True,
        'output_path': 'output/markdown/'
    }
}

# Create and configure pipeline
pipeline = DocumentPipeline(config)
pipeline.configure_pdf_to_markdown_pipeline()

# Process document
result = pipeline.process_document("path/to/document.pdf")
print(f"Markdown saved to: {result.get('markdown_path')}")
```

### Ingesting Documents into Weaviate

```python
from doc_processing.document_pipeline import DocumentPipeline

# Configure pipeline with Weaviate integration
config = {
    'weaviate_enabled': True,
    'weaviate_config': {
        'url': 'http://localhost:8080',
    },
    'chunker_config': {
        'chunk_size': 1000,
        'chunk_overlap': 200,
    }
}

# Create and configure pipeline
pipeline = DocumentPipeline(config)
pipeline.configure_pdf_to_weaviate_pipeline()

# Process document and ingest into Weaviate
result = pipeline.process_document("path/to/document.pdf")
print(f"Ingested document with {len(result['chunks'])} chunks")

# Query similar content
chunks = pipeline.query_similar_chunks("Your search query here", limit=5)
for chunk in chunks:
    print(f"- {chunk['content'][:100]}...")
```

### Batch Processing with Command Line Script

```bash
python scripts/batch_process.py \
    --input_dir data/input/pdfs \
    --output_dir data/output \
    --weaviate_url http://localhost:8080 \
    --chunk_size 1000 \
    --concurrent_files 2
```

## 📓 Jupyter Notebooks

For interactive examples, check out the notebooks in the `notebooks/` directory:

1. **PDF to Text Demo**: Basic conversion of PDFs to text
2. **Document Loading Demo**: Loading various document types
3. **Weaviate Integration Demo**: Storing and querying documents in Weaviate
4. **End-to-End Pipeline Demo**: Complete processing pipeline with analysis

## 🔧 Configuration Options

The pipeline is highly configurable with many options:

### PDF Processor Options
- `model`: Vision model to use (default: 'gpt-4o')
- `max_tokens`: Maximum tokens for API response
- `resolution_scale`: Image scaling factor for OCR quality
- `concurrent_pages`: Number of pages to process concurrently
- `preserve_page_boundaries`: Whether to mark page boundaries in output

### Chunking Options
- `chunk_size`: Size of text chunks (in tokens, characters, etc.)
- `chunk_overlap`: Overlap between chunks
- `chunk_by`: Chunking method ('tokens', 'characters', 'sentences', 'paragraphs')
- `preserve_paragraph_boundaries`: Avoid breaking paragraphs when possible

### Markdown Transformer Options
- `generate_toc`: Whether to generate a table of contents
- `detect_headings`: Automatically detect and format headings
- `extract_metadata`: Include document metadata in output

## 📚 Extending the Pipeline

### Adding a New Document Loader

1. Create a new loader class in the `loaders/` directory
2. Inherit from `BaseDocumentLoader` and implement the `load` method
3. Register the loader in the pipeline configuration

Example:
```python
from doc_processing.loaders.base import BaseDocumentLoader

class CSVLoader(BaseDocumentLoader):
    def load(self, source: str) -> Dict[str, Any]:
        # Implement CSV loading logic
        ...
        return document
```

### Creating Custom Processors

1. Create a new processor class in the `processors/` directory
2. Inherit from `BaseProcessor` and implement the `process` method
3. Add the processor to your pipeline

Example:
```python
from doc_processing.processors.base import BaseProcessor

class TextSummarizer(BaseProcessor):
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        # Implement summarization logic
        ...
        return document
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🧩 Project Components

### Document Loaders

The loaders module handles loading documents from various sources:

- **PDFLoader**: Loads and extracts metadata from PDFs
- **TextLoader**: Loads plain text documents
- **MarkdownLoader**: Loads and parses markdown documents
- **ImageLoader**: Loads images for OCR processing
- **JSONLoader**: Loads structured JSON data

### Document Processors

The processors module transforms document content:

- **GPTVisionPDFProcessor**: Uses GPT-4 Vision for high-quality PDF OCR
- **OCRProcessor**: Basic OCR for images and scanned documents
- **TextCleaner**: Cleans and normalizes extracted text

### Transformers

The transformers module converts content between formats:

- **TextToMarkdown**: Converts text to structured markdown
- **TextToJSON**: Converts text to structured JSON
- **DocumentChunker**: Splits documents into semantic chunks

### Weaviate Integration

The embedding module provides Weaviate vector database integration:

- **WeaviateClient**: Client for interacting with Weaviate
- **SchemaManager**: Manages document and chunk schemas

### Templates

The templates module handles Jinja templates:

- **PromptTemplateManager**: Manages prompt and output templates
- **Prompt templates**: Templates for GPT-4 Vision instructions
- **Output templates**: Templates for formatted outputs

## 🔄 Processing Pipeline

The core of the system is the DocumentPipeline class which orchestrates the processing flow:

1. **Document Loading**: Load document from source
2. **Content Extraction**: Extract text content from document
3. **Transformation**: Convert to desired format (markdown, JSON)
4. **Chunking**: Split into semantic chunks for embedding
5. **Embedding**: Store in vector database for retrieval

## 🛠️ Customization

### Custom Prompts

Create custom GPT-4 Vision prompts in the `templates/prompts` directory:

```jinja
{# Custom prompt template #}
Extract the following information from this PDF page {{ page_number }}:

{% if config.extract_tables %}
- All tables with their data
{% endif %}

{% if config.extract_references %}
- All citations and references
{% endif %}

Please format the extracted content as {{ output_format }}.
```

### Custom Output Formats

Create custom output templates in the `templates/outputs` directory:

```jinja
{# Custom JSON output template #}
{
  "title": "{{ title }}",
  "metadata": {{ metadata | tojson }},
  "content": {{ content | tojson }},
  "sections": [
    {% for section in sections %}
    {
      "heading": "{{ section.heading.text }}",
      "content": {{ section.content | tojson }}
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
```

## 🔗 Integration with LangChain

The document processing pipeline can be integrated with LangChain:

```python
from langchain.document_loaders import PyMuPDFLoader
from langchain.vectorstores import Weaviate
from langchain.embeddings import OpenAIEmbeddings

# Process document with our pipeline
pipeline = DocumentPipeline(config)
result = pipeline.process_document("path/to/document.pdf")

# Use processed chunks with LangChain
documents = [
    Document(page_content=chunk["content"], metadata=chunk["metadata"])
    for chunk in result["chunks"]
]

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = Weaviate.from_documents(
    documents, 
    embeddings,
    weaviate_url="http://localhost:8080"
)

# Query documents
docs = vectorstore.similarity_search("Your query here")
```

## 🚀 Future Enhancements

Planned features for future releases:

- Support for more document types (EPUB, DOCX, HTML)
- Audio and video transcription and processing
- Multi-modal document handling
- Advanced document analysis and summarization
- Web UI for document processing and exploration
- RAG (Retrieval Augmented Generation) integration
- Fine-tuned extraction models for specialized domains

## 📞 Contact

For questions, feedback, or support, please [open an issue](https://github.com/yourusername/doc-processing-pipeline/issues) on GitHub.

---

Happy document processing!