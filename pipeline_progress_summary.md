# Pipeline Progress Summary & Bug Fixes (as of 2025-04-25)

## 1. Functionality Achieved:

*   **LLM Abstraction:** Successfully refactored the LLM interaction into a base client (`BaseLLMClient`) and a concrete implementation (`OpenAIClient`), allowing for easier integration of different LLM providers in the future.
*   **PDF Loader Image Generation:** Confirmed the `PDFLoader` correctly generates base64-encoded images for each page, enabling visual processing by multimodal models.
*   **Core Pipeline Configurations Tested:** The `DocumentPipeline` class can be configured and run for the following basic transformations using `data/input/pdfs/sample_test.pdf`:
    *   `pdf_to_text`: Extracts text content (using `HybridPDFProcessor` with GPT Vision fallback initially, Docling confirmed working later).
    *   `pdf_to_markdown`: Extracts text and applies basic Markdown formatting (using `TextToMarkdown` transformer).
    *   `pdf_to_json`: Extracts text and attempts structured JSON extraction (using `TextToJSON` transformer).
*   **Flexible Execution Script (`scripts/run_pipeline.py`):**
    *   Created a command-line script to run different pipeline configurations (`text`, `markdown`, `json`, `hybrid`, `weaviate`).
    *   Supports processing single files or directories (non-recursively by default, recursively with `--recursive`).
    *   Allows specifying the output directory.
    *   Allows selecting the OCR mode for PDF processing (`hybrid`, `docling`, `gpt`) via `--ocr_mode`.
    *   Handles saving the primary output (text, markdown, or JSON) to the specified directory.
*   **Docling Integration:** Successfully integrated the `docling` library into the `HybridPDFProcessor`. The processor can now correctly invoke Docling when `--ocr_mode docling` is specified in the `run_pipeline.py` script.

## 2. Key Bugs Fixed:

*   **Initial OpenAI Quota Error:** Resolved by updating the default model in `OpenAIClient` to one available under the current quota (e.g., `gpt-4.1`).
*   **`run_pipeline.py` Import Errors:**
    *   `NameError: name 'Optional' is not defined`: Fixed by adding `from typing import Optional` to the script imports.
    *   `NameError: name 'Dict' is not defined`: Fixed by adding `Dict` to the `typing` import (`from typing import Optional, Dict, Any`).
*   **`TextToMarkdown` Template Error:**
    *   `jinja2.exceptions.UndefinedError: 'now' is undefined`: Fixed by adding `now = datetime.datetime.now()` to the context passed to the Jinja2 template in `TextToMarkdown.transform`.
    *   `TypeError: 'datetime.datetime' object is not callable`: Fixed by changing `{{ now().strftime(...) }}` to `{{ now.strftime(...) }}` in `doc_processing/templates/outputs/markdown_template.j2`.
*   **Docling Import Issues:**
    *   **Initial Diagnosis:** Script reported "Docling library not found" despite direct command-line import working.
    *   **Incorrect Import Pattern:** Identified and corrected the import from `docling.models.convert_document` to `docling.document_converter.DocumentConverter`.
    *   **Module-Level Import Conflict:** Resolved issues caused by top-level `docling` imports interfering with `sys.path` modifications by moving the `DocumentConverter` import inside the relevant method (`_process_with_docling`).
*   **Docling Page Number Error:**
    *   `AttributeError: 'int' object has no attribute 'page_number'`: Handled by adding a `hasattr` check and fallback logic when iterating through `docling_doc.pages` in `HybridPDFProcessor._process_with_docling`.
*   **Weaviate Schema and Collection Creation Errors:**
    *   **Incompatible Sharding Configuration:** Resolved `AttributeError` by removing unsupported parameters (`key`, `strategy`, `function`) from `Configure.sharding()` in schema definitions (`KnowledgeItemSchema`, `KnowledgeMainSchema`).
    *   **Missing Configuration Attributes:** Resolved `AttributeError` by adding missing attributes (`inverted_index_config`, `multi_tenancy_config`, `replication_config`, `sharding_config`) to all relevant schema classes (`AudioItemSchema`, `AudioChunkSchema`, `ImageItemSchema`, `VideoItemSchema`, `VideoChunkSchema`).
    *   Successfully ran integration tests (`pytest -m integration`) after applying fixes.