# Document Processing Pipeline - User Guide

This guide provides instructions on how to use the document processing pipeline scripts.

## Running the Pipeline (`scripts/run_pipeline.py`)

The `scripts/run_pipeline.py` script allows you to process individual documents or entire directories using various pipeline configurations.

### Basic Usage

Run the script from the main project directory (`pipeline-documents`) using the following command structure:

```bash
python scripts/run_pipeline.py --input_path <path_to_input> --output_dir <path_to_output_dir> --pipeline_type <type> [options]
```

### Key Arguments:

*   `--input_path <path_to_input>`: **(Required)** Path to the single input file (e.g., `data/input/pdfs/sample_test.pdf`, `data/input/text/sample_report.txt`, `data/input/docx/sample_word.docx`) or an input directory (e.g., `data/input/text`). Supported types: `.pdf`, `.txt`, `.md`, `.json`, `.docx`.
*   `--output_dir <path_to_output_dir>`: **(Required)** Path to the directory where output files will be saved (e.g., `data/output/markdown`). The script will create this directory if it doesn't exist. Output filenames are generated automatically based on the input filename and pipeline type.
*   `--pipeline_type <type>`: **(Required)** Specifies the processing pipeline and primary output format. Choose from:
    *   `text`: Plain text extraction (`.txt` output). Suitable for most input types.
    *   `markdown`: Text extraction with Markdown formatting (`.md` output). Suitable for most input types.
    *   `json`: Structured JSON extraction (`.json` output). Best suited for text-based inputs (PDF, TXT, MD, DOCX).
    *   `hybrid`: Runs the hybrid PDF processing (useful if you don't need a specific transformation like Markdown or JSON, defaults to `.txt` output). Primarily for PDF input.
    *   `weaviate`: Processes and prepares data for ingestion into Weaviate collections ('KnowledgeItem' and 'KnowledgeMain'). Refer to [docs/weaviate_layer.md](docs/weaviate_layer.md) for details on Weaviate integration and collection management.
*   `--ocr_mode <mode>`: **(Optional, PDF input only)** Controls the Optical Character Recognition (OCR) method used for PDF files. Choose from:
    *   `hybrid` (Default): Attempts to use Docling if available and suitable, otherwise falls back to the configured LLM's vision capability (e.g., GPT Vision for OpenAI, native PDF for Gemini).
    *   `docling`: Forces the use of Docling (will fall back to the LLM if Docling fails or is unavailable).
    *   `gpt`: Forces the use of the GPT Vision processor (currently assumes OpenAI provider). *Note: This might be less effective if the selected `--llm_provider` is not OpenAI.*
*   `--recursive`: **(Optional, Directory input only)** If specified, the script will process files in subdirectories of the `--input_path`.
*   `--llm_provider <provider>`: **(Optional)** Specify the LLM provider. Defaults to `openai`. Choose from:
    *   `openai`
    *   `gemini`
    *   *(Others TBD)*
*   `--llm_model <model_name>`: **(Optional)** Specify a particular LLM model name to override the default for the selected provider (e.g., `gpt-4o`, `gemini-1.5-flash-latest`).
*   `--api_key <key>`: **(Optional)** Provide the API key directly. If omitted, the script uses the corresponding environment variable (e.g., `OPENAI_API_KEY`, `GOOGLE_API_KEY`).

### Examples:

**1. Process `sample_test.pdf` to Markdown using default hybrid OCR (OpenAI):**

```bash
python scripts/run_pipeline.py --input_path data/input/pdfs/sample_test.pdf --output_dir data/output/markdown --pipeline_type markdown
```
*(Output: `data/output/markdown/sample_test_output.md`)*

**2. Process `sample_test.pdf` to JSON forcing Docling OCR:**

```bash
python scripts/run_pipeline.py --input_path data/input/pdfs/sample_test.pdf --output_dir data/output/json --pipeline_type json --ocr_mode docling
```
*(Output: `data/output/json/sample_test_output.json`)*

**3. Process `sample_test.pdf` to Text using Gemini native PDF processing:**

```bash
python scripts/run_pipeline.py --input_path data/input/pdfs/sample_test.pdf --output_dir data/output/text --pipeline_type text --llm_provider gemini
```
*(Output: `data/output/text/sample_test_output.txt`)*

**4. Process `sample_word.docx` to Markdown (using default OpenAI for transformation):**

```bash
python scripts/run_pipeline.py --input_path data/input/docx/sample_word.docx --output_dir data/output/markdown --pipeline_type markdown
```
*(Output: `data/output/markdown/sample_word_output.md`)*

**5. Process `sample_report.txt` to JSON using Gemini:**

```bash
python scripts/run_pipeline.py --input_path data/input/text/sample_report.txt --output_dir data/output/json --pipeline_type json --llm_provider gemini
```
*(Output: `data/output/json/sample_report_output.json`)*

**6. Process all TXT files in a directory to plain text output:**

```bash
python scripts/run_pipeline.py --input_path data/input/text --output_dir data/output/text_batch --pipeline_type text
```

*(This guide will be expanded as more features are added.)*