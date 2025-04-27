# Document Processing Pipeline

A modular Python document processing pipeline for converting various file types (PDF, DOCX, TXT, MD, JSON) to structured formats (Text, Markdown, JSON) and preparing data for vector database integration (e.g., Weaviate). Leverages LLMs like OpenAI and Gemini for advanced processing, including OCR and native PDF understanding.

## 🌟 Features

-   **Modular Architecture**: Easily extendable loaders, processors, and transformers.
-   **Multi-Format Input**: Handles PDF, DOCX, PPTX, TXT, MD, JSON, Audio, Image, and Video files, **including processing directly from YouTube URLs**. If a YouTube video does not have an available transcript, the video file will be downloaded for post-processing.
-   **Advanced Processing**:
    -   **PDFs**: Uses **Docling** for layout-aware text extraction (if available), **OpenAI Vision** for image-based OCR, and **Gemini** for native PDF understanding (text and vision). Hybrid mode intelligently selects the best method (or falls back).
    -   **DOCX**: Uses **Mammoth** to convert Word documents to Markdown with proper formatting.
    -   **PPTX**: Uses **MarkItDown** to convert PowerPoint presentations to Markdown.
    -   **Audio**: Supports transcription.
    -   **Images**: Supports processing and OCR.
    -   **Video**: Supports processing and extraction of audio tracks.
    -   **YouTube**: Download video content directly from YouTube URLs. If a transcript is not available, the video file is provided for post-processing.
-   **LLM Integration**: Abstracted client for OpenAI and Gemini (more can be added).
-   **Output Formats**: Convert documents to plain Text, Markdown, structured JSON, CSV, or Excel.
-   **Flexible Execution**: `scripts/run_pipeline.py` for running pipelines on single files, directories, or **YouTube URLs** with various options. If a YouTube video has no transcript, the downloaded video file path is included in the output metadata.
-   **Weaviate Integration**: Includes a complete modular layer for Weaviate v4 integration, including client connection, collection management, and data ingestion/retrieval. See [docs/weaviate_layer.md](docs/weaviate_layer.md) for detailed documentation.
-   **Jinja Templates**: Flexible prompt and output formatting.
-   **Jupyter Notebooks**: Interactive examples (may need updates).
-   **Command Cheat Sheet**: Quick reference for all pipeline operations available in [COMMANDS.md](docs/COMMANDS.md)

## 📋 Requirements

-   Python 3.9+
-   See `requirements.txt` for specific Python package dependencies (install via `pip install -r requirements.txt`). Key dependencies include:
    -   `google-genai` (for Gemini)
    -   `openai` (for OpenAI)
    -   `PyMuPDF` (for PDF loading)
    -   `python-docx` (for DOCX loading)
    -   `mammoth` (for DOCX to Markdown conversion)
    -   `markdownify` (for HTML to Markdown conversion)
    -   `markitdown[pptx]` (for PPTX to Markdown conversion)
    -   `openpyxl` (for Excel output)
    -   `pandas` (for CSV and Excel processing)
    -   `docling` (Optional, for advanced PDF processing)
    -   `weaviate-client` (Optional, for Weaviate integration)
-   API Keys:
    -   Set environment variables for the LLM providers you intend to use (e.g., `OPENAI_API_KEY`, `GOOGLE_API_KEY`).
    -   Set Weaviate keys if using Weaviate (`WEAVIATE_URL`, `WEAVIATE_API_KEY`).

## 🚀 Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/aglobalwander/document-pipeline.git
    cd document-pipeline
    ```

2.  Create and activate a virtual environment (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you intend to use Docling, ensure its dependencies (like PyTorch) are compatible with your system.*

4.  Set up environment variables:
    *   Create a `.env` file in the project root.
    *   Add your API keys, e.g.:
        ```dotenv
        OPENAI_API_KEY="sk-..."
        GOOGLE_API_KEY="AIza..."
        # WEAVIATE_URL="http://localhost:8080" # If using Weaviate
        # WEAVIATE_API_KEY="..."          # If using Weaviate with auth
        ```

## 📄 Directory Structure (Simplified)

```
document-pipeline/
├── README.md
├── USER_GUIDE.md
├── requirements.txt
├── .gitignore
├── .env            # (Created by user)
├── data/
│   ├── input/      # Sample input files by type (pdfs/, text/, etc.)
│   └── output/     # Default output location (text/, markdown/, json/)
├── doc_processing/
│   ├── __init__.py
│   ├── config.py
│   ├── document_pipeline.py
│   ├── loaders/    # Loads different file types
│   ├── processors/ # Processes document content (e.g., OCR)
│   ├── transformers/ # Transforms content (e.g., to Markdown, JSON)
│   ├── embedding/  # Base classes, Weaviate client/schema
│   ├── llm/        # LLM client implementations (OpenAI, Gemini)
│   ├── models/     # Pydantic schemas
│   ├── templates/  # Jinja templates
│   └── utils/      # Utility functions
├── notebooks/      # Jupyter examples (may need updates)
├── scripts/
│   ├── run_pipeline.py # Main script for running pipelines
│   └── ...             # Other utility scripts
└── tests/          # Unit tests
    └── ...
```

## 🔍 Usage

The primary way to use the pipeline is via the `scripts/run_pipeline.py` script. It can now accept local file paths, directory paths, or **YouTube URLs** as input.

Refer to the **`USER_GUIDE.md`** for detailed instructions and examples on how to use `run_pipeline.py` with different input types, pipeline types, and options (like selecting the LLM provider or OCR mode).

## Specifying Weaviate Collections

When using the `weaviate` pipeline type, you can now specify a target Weaviate collection for data ingestion using the `--collection` flag. This allows you to direct processed documents and chunks into a collection other than the default ones defined internally.

To use a specific collection, you must define its schema in a YAML file within the `weaviate_layer/schemas/` directory. The filename should match the desired collection name (e.g., `MyNewCollection.yaml` for a collection named `MyNewCollection`).

The YAML schema should follow a structure similar to the internal schema definitions, specifying the collection's name, description, properties, and vectorizer configuration.

Example `weaviate_layer/schemas/MyNewCollection.yaml`:

```yaml
name: MyNewCollection
description: A custom collection for specific data.
properties:
  - name: title
    dataType:
      - TEXT
  - name: content
    dataType:
      - TEXT
  - name: custom_field
    dataType:
      - TEXT
vectorizerConfig:
  text2vec-openai:
    model: text-embedding-3-large
```

You can then run the pipeline targeting this collection:

```bash
python scripts/run_pipeline.py --input_path data/input/pdfs/sample_test.pdf --pipeline_type weaviate --collection MyNewCollection
```

If the specified collection does not exist in your Weaviate instance, the pipeline will attempt to create it using the provided YAML schema.

## Word & PowerPoint Support

The pipeline now supports processing Word (DOCX) and PowerPoint (PPTX) files. Specifically, you can now convert DOCX files to Markdown using the `markdown` pipeline type.

```bash
# Word → Markdown
python scripts/run_pipeline.py --input_path data/input/docx/sample_word.docx --pipeline_type markdown
```

```bash
# PowerPoint → Weaviate (slide chunks)
python scripts/run_pipeline.py --input_path data/input/pptx/sample_deck.pptx --pipeline_type weaviate
```

## JSON to CSV/Excel Conversion

You can now convert JSON data to CSV or Excel formats:

```bash
# JSON → CSV
python scripts/run_pipeline.py --input_path data/input/json/sample_data.json --pipeline_type json --output_format csv

# JSON → Excel (with default template)
python scripts/run_pipeline.py --input_path data/input/json/sample_data.json --pipeline_type json --output_format xlsx
```

### Excel Templates

You can customize Excel output using templates:

```bash
# Use a custom Excel template
python scripts/run_pipeline.py --input_path data/input/json/sample_data.json --pipeline_type json --output_format xlsx --excel_template finance
```

Templates are stored in the `report_templates/excel/` directory. The default template provides a blank sheet with a bold header row.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue.

## 📜 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.