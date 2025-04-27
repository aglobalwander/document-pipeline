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

*   `--input_path <path_to_input>`: **(Required)** Specifies the path to the input. This can be a single file (e.g., `data/input/pdfs/sample_test.pdf`, `data/input/audio/sample.wav`) or a directory containing multiple files (e.g., `data/input/text`). The pipeline supports various file types, including `.pdf`, `.txt`, `.md`, `.json`, `.docx`, audio formats (`.mp3`, `.wav`, `.ogg`, `.m4a`), video formats (`.3gp`, `.flv`, `.mkv`, `.mp4`), and image formats (`.jpg`, `.png`, `.gif`).
*   `--output_dir <path_to_output_dir>`: **(Required)** Specifies the directory where the processed output files will be saved (e.g., `data/output/markdown`). The script automatically creates this directory if it doesn't already exist. Output filenames are generated based on the input filename and the selected `--pipeline_type`.
*   `--pipeline_type <type>`: **(Required)** Defines the processing pipeline to be used and the primary output format. Here's a breakdown of the available pipeline types:
    *   `text`: Extracts plain text content from the input (`.txt` output). This is a versatile option suitable for most input types. For audio and video files, it performs transcription to generate the text. For images, it uses OCR to extract text.
    *   `markdown`: Extracts text and formats it using Markdown syntax (`.md` output). Similar to the `text` pipeline, it supports various input types and applies Markdown formatting where appropriate.
    *   `json`: Extracts structured data from the input and outputs it as a JSON file (`.json` output). This pipeline is most effective with text-based inputs (e.g., PDF, TXT, MD, DOCX) or when extracting data from other formats.
    *   `hybrid`: Performs hybrid PDF processing, which intelligently combines different methods for extracting text and images from PDF files. This is useful when you don't need a specific output format like Markdown or JSON and want the best possible extraction from PDFs. It defaults to `.txt` output.
    *   `weaviate`: Processes the input data and prepares it for ingestion into Weaviate, a vector database. This pipeline creates 'KnowledgeItem' and 'KnowledgeMain' collections in Weaviate. For more information on Weaviate integration and collection management, see [docs/weaviate_layer.md](docs/weaviate_layer.md).
*   `--ocr_mode <mode>`: **(Optional, applies only to PDF and Image input)** Determines the Optical Character Recognition (OCR) method used for processing PDF and image files.
    *   `hybrid` (Default): Attempts to use Docling for OCR if it's available and suitable for the input. If Docling is not available or fails, it falls back to the LLM's built-in vision capabilities (e.g., GPT Vision for OpenAI, native PDF processing for Gemini).
    *   `docling`: Forces the pipeline to use Docling for OCR. If Docling fails or is unavailable, it falls back to the LLM's vision capabilities.
    *   `gpt`: Forces the pipeline to use the GPT Vision processor for OCR. This option assumes you are using the OpenAI provider. *Note: This option might be less effective if you select a different `--llm_provider` that is not OpenAI.*
*   `--recursive`: **(Optional, applies only to Directory input)** When processing a directory specified with `--input_path`, this flag tells the script to recursively process files located in any subdirectories within the input directory.
*   `--llm_provider <provider>`: **(Optional)** Specifies the Large Language Model (LLM) provider to use for processing. The default is `openai`. Available options include:
    *   `openai`: Uses the OpenAI LLM.
    *   `gemini`: Uses the Google Gemini LLM.
    *   *(Others TBD)*: Support for other LLM providers may be added in the future.
*   `--llm_model <model_name>`: **(Optional)** Allows you to override the default LLM model used by the selected provider. For example, you can specify `gpt-4o` for OpenAI or `gemini-1.5-flash-latest` for Gemini.
*   `--api_key <key>`: **(Optional)** Provides the API key for the selected LLM provider directly in the command. If you omit this option, the script will attempt to retrieve the API key from the corresponding environment variable (e.g., `OPENAI_API_KEY` for OpenAI, `GOOGLE_API_KEY` for Gemini).

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

**7. Process `sample.wav` audio file to plain text:**

```bash
python scripts/run_pipeline.py --input_path data/input/audio/sample.wav --output_dir data/output/audio_transcripts --pipeline_type text
```
*(Output: `data/output/audio_transcripts/sample_output.txt` containing the transcript)*


**8. Process `SampleVideo_1280x720_1mb.mp4` video file:**

```bash
python scripts/run_pipeline.py --input_path data/input/video/SampleVideo_1280x720_1mb.mp4 --output_dir data/output/video_processing --pipeline_type text # Or markdown/json depending on desired output
```
*(Note: If the video has an available transcript, it will be extracted. If not, the video file will be downloaded to the output directory for post-processing, and its path will be included in the output metadata.)*

**9. Process `sample_test.pdf` and ingest into Weaviate:**
```bash
# Ensure your Weaviate instance is running and configured via environment variables or .env file
python scripts/run_pipeline.py --input_path data/input/pdfs/sample_test.pdf --pipeline_type weaviate
```
*(Note: Weaviate ingestion does not produce output files in the output_dir by default, as data is sent directly to Weaviate. Ensure your Weaviate client is properly configured via environment variables. You can specify a target collection using the `--collection <CollectionName>` argument; otherwise, it defaults to internal collections like 'KnowledgeMain'.)*
## Troubleshooting

*   **Encoding Errors:** If you encounter encoding errors, especially when processing DOCX files, try specifying the encoding explicitly in the command. For example:

    ```bash
    python scripts/run_pipeline.py --input_path data/input/docx/sample_word.docx --output_dir data/output/markdown --pipeline_type markdown --encoding utf-8
    ```

    If `utf-8` doesn't work, try `latin1` or `cp1252`.

*   **API Key Issues:** Ensure that you have set the correct API key as an environment variable or passed it using the `--api_key` argument. Double-check the API key value and make sure it corresponds to the correct LLM provider.

*   **Weaviate Connection Problems:** If you are having trouble connecting to your Weaviate instance, verify that the `WEAVIATE_URL` and `WEAVIATE_API_KEY` environment variables are set correctly. Also, ensure that your Weaviate instance is running and accessible from your machine.

*   **Docling Errors:** If you encounter errors related to Docling, make sure that you have installed the necessary dependencies and that your system is compatible with Docling. If Docling is not essential, try using the `hybrid` or `gpt` OCR mode instead.

*   **Memory Errors:** If you are processing large files and encounter memory errors, try reducing the chunk size or processing the files in smaller batches.

*   **File Not Found Errors:** Double-check the `--input_path` to ensure that the file or directory exists and is accessible to the script.

*   **Incorrect Output:** If the output is not what you expect, review the selected `--pipeline_type` and any optional arguments you are using. Ensure that the selected pipeline type is appropriate for the input file type and that you are using the correct options for your desired output.