# Document Processing Pipeline

A modular Python document processing pipeline for converting various file types (PDF, DOCX, TXT, MD, JSON) to structured formats (Text, Markdown, JSON) and preparing data for vector database integration (e.g., Weaviate). Leverages LLMs like OpenAI and Gemini for advanced processing, including OCR and native PDF understanding.

## 🌟 Features

-   **Modular Architecture**: Easily extendable loaders, processors, and transformers.
-   **Multi-Format Input**: Handles PDF, DOCX, TXT, MD, JSON, Audio, Image, and Video files.
-   **Advanced Processing**:
    -   **PDFs**: Uses **Docling** for layout-aware text extraction (if available), **OpenAI Vision** for image-based OCR, and **Gemini** for native PDF understanding (text and vision). Hybrid mode intelligently selects the best method (or falls back).
    -   **Audio**: Supports transcription (e.g., via Deepgram).
    -   **Images**: Supports processing and OCR.
    -   **Video**: Supports processing and transcription of audio tracks.
-   **LLM Integration**: Abstracted client for OpenAI and Gemini (more can be added).
-   **Output Formats**: Convert documents to plain Text, Markdown, or structured JSON.
-   **Flexible Execution**: `scripts/run_pipeline.py` for running pipelines on single files or directories with various options.
-   **Weaviate Integration**: Includes a complete modular layer for Weaviate v4 integration, including client connection, collection management, and data ingestion/retrieval. See [docs/weaviate_layer.md](docs/weaviate_layer.md) for detailed documentation.
-   **Jinja Templates**: Flexible prompt and output formatting.
-   **Jupyter Notebooks**: Interactive examples (may need updates).

## 📋 Requirements

-   Python 3.9+
-   See `requirements.txt` for specific Python package dependencies (install via `pip install -r requirements.txt`). Key dependencies include:
    -   `google-genai` (for Gemini)
    -   `openai` (for OpenAI)
    -   `PyMuPDF` (for PDF loading)
    -   `python-docx` (for DOCX loading)
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

The primary way to use the pipeline is via the `scripts/run_pipeline.py` script.

Refer to the **`USER_GUIDE.md`** for detailed instructions and examples on how to use `run_pipeline.py` with different file types, pipeline types, and options (like selecting the LLM provider or OCR mode).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue.

## 📜 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.