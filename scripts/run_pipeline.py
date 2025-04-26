#!/usr/bin/env python
"""
Flexible Script for Running Document Processing Pipelines

Allows processing single files or directories with various configurations.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import json
import time
from typing import Optional, Dict, Any # Added Dict and Any for type hints

# Add project root to sys.path to allow importing doc_processing modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root)) # Append instead of insert to avoid potential conflicts

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.config import get_settings, ensure_directories_exist
# Import new loaders
from doc_processing.loaders.text_loader import TextLoader
from doc_processing.loaders.markdown_loader import MarkdownLoader
from doc_processing.loaders.json_loader import JSONLoader
from doc_processing.loaders.docx_loader import DocxLoader
from doc_processing.loaders.pdf_loader import PDFLoader # Need this too
from doc_processing.processors.pdf_processor import HybridPDFProcessor # Need this for PDF path
from doc_processing.transformers.text_to_markdown import TextToMarkdown # Need transformers
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import DocumentChunker

# Import the new Weaviate client getter
from weaviate_layer.client import get_weaviate_client

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Log to console
        # Add FileHandler if needed: logging.FileHandler("run_pipeline.log")
    ]
)
logger = logging.getLogger(__name__)

# --- Argument Parsing ---
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run document processing pipelines on files or directories.'
    )

    parser.add_argument('--input_path', type=str, required=True,
                        help='Path to the input file or directory.')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Base directory to save output files.')
    parser.add_argument('--pipeline_type', type=str, required=True,
                        choices=['text', 'markdown', 'json', 'hybrid', 'weaviate'],
                        help='Type of pipeline configuration to run.')
    parser.add_argument('--recursive', action='store_true',
                        help='Process directories recursively.')
    parser.add_argument('--output_format', type=str, choices=['txt', 'md', 'json'],
                        help='Explicit output format (default inferred from pipeline_type).')

    # LLM Configuration
    parser.add_argument('--llm_provider', type=str, default='openai',
                        choices=['openai', 'gemini', 'anthropic', 'deepseek'], # Added 'gemini'
                        help='LLM provider to use.')
    parser.add_argument('--llm_model', type=str,
                        help='Specific LLM model name to override the default.')
    parser.add_argument('--api_key', type=str,
                        help='API key for the selected LLM provider (uses environment variable if not set).')
    parser.add_argument('--prompt_name', type=str,
                        help='Base name of the prompt template file (e.g., "invoice_extraction" for invoice_extraction.j2).')

    # PDF Processing Configuration
    parser.add_argument('--ocr_mode', type=str, default='hybrid', choices=['hybrid', 'docling', 'gpt'],
                        help="OCR mode for PDF processing ('hybrid', 'docling', 'gpt'). Only relevant for PDF inputs.")
    parser.add_argument('--gpt_vision_prompt', type=str,
                        help='Path to a custom Jinja2 template file for GPT Vision OCR.')
    parser.add_argument('--no_page_images', action='store_true',
                        help='Disable PDF page image generation in the loader (saves time if only using Docling).')

    # Weaviate Configuration (only relevant for 'weaviate' pipeline_type)
    # Remove direct URL/API key args as they are handled by weaviate_layer.config
    # parser.add_argument('--weaviate_url', type=str, help='Weaviate instance URL.')
    # parser.add_argument('--weaviate_api_key', type=str, help='Weaviate API key.')
    parser.add_argument('--weaviate_class_prefix', type=str, default='Document',
                        help='Prefix for Weaviate class names (e.g., Document, DocumentChunk).')

    return parser.parse_args()

# --- Helper Functions ---
def get_output_filename(input_path: Path, pipeline_type: str, output_format: Optional[str]) -> str:
    """Determines the output filename based on input and pipeline type."""
    stem = input_path.stem
    if output_format:
        ext = output_format
    elif pipeline_type == 'markdown':
        ext = 'md'
    elif pipeline_type == 'json':
        ext = 'json'
    else: # Default to text for 'text', 'hybrid', 'weaviate'
        ext = 'txt'
    return f"{stem}_output.{ext}"

def save_output(result: Dict[str, Any], output_path: Path, pipeline_type: str):
    """Saves the primary output of the pipeline result to a file."""
    content_to_save = None
    if pipeline_type == 'markdown' and 'markdown' in result:
        content_to_save = result['markdown']
    elif pipeline_type == 'json' and 'json' in result:
        # Save JSON data pretty-printed
        try:
            content_to_save = json.dumps(result['json'], indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to serialize JSON data for {output_path}: {e}")
            content_to_save = f"Error: Failed to serialize JSON - {e}\n\nRaw Data:\n{result.get('json')}"
    elif 'content' in result: # Default to saving 'content' for text, hybrid, weaviate
        content_to_save = result['content']

    if content_to_save is not None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content_to_save)
            logger.info(f"Saved output to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write output file {output_path}: {e}")
    else:
        logger.warning(f"No primary output content found to save for {output_path} (pipeline type: {pipeline_type})")


# --- Main Processing Logic ---
def main():
    """Main execution function."""
    args = parse_arguments()
    settings = get_settings()
    ensure_directories_exist() # Ensure base output dirs exist

    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True) # Ensure specific output dir exists

    # --- Identify Input Files ---
    if input_path.is_file():
        files_to_process = [input_path]
    elif input_path.is_dir():
        pattern = f"**/*" if args.recursive else "*"
        # Simple filter for common document types for now
        supported_extensions = ['.pdf', '.txt', '.md', '.json', '.docx'] # Added .docx
        files_to_process = [
            f for f in input_path.glob(pattern)
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
    else:
        logger.error(f"Input path is not a valid file or directory: {input_path}")
        sys.exit(1)

    if not files_to_process:
        logger.warning(f"No supported files found to process in {input_path}")
        sys.exit(0)

    logger.info(f"Found {len(files_to_process)} file(s) to process.")

    # --- Process Each File ---
    total_start_time = time.time()
    success_count = 0
    fail_count = 0

    # Initialize Weaviate client if needed
    weaviate_client = None
    if args.pipeline_type == 'weaviate':
        try:
            weaviate_client = get_weaviate_client()
            logger.info("Successfully connected to Weaviate.")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            sys.exit(1)

    try: # Use a try...finally block to ensure client is closed
        for file_path in files_to_process:
            logger.info(f"--- Processing file: {file_path.name} ---")
            file_start_time = time.time()
            try:
                # --- Build Pipeline Configuration ---
                pipeline_config = {
                    'weaviate_enabled': args.pipeline_type == 'weaviate',
                    'llm_provider': args.llm_provider,
                    'api_key': args.api_key, # Will be None if not provided, client uses env var
                    'llm_model': args.llm_model, # General model override
                    # PDF Loader specific config
                    'pdf_loader_config': {
                        'generate_page_images': not args.no_page_images
                    },
                    # Hybrid Processor specific config (which contains GPTPVisionProcessor)
                    'pdf_processor_config': {
                         'ocr_mode': args.ocr_mode,
                         'llm_provider': args.llm_provider, # Pass provider choice down
                         'api_key': args.api_key,           # Pass api_key down
                         'vision_model': args.llm_model,    # Pass model override (GPTPVisionProcessor will use this if set)
                         # Pass prompt_name for potential use by GPTPVisionProcessor or Gemini native call
                         'prompt_name': args.prompt_name,
                         # 'gpt_vision_prompt' might become redundant if prompt_name is used, keep for now? Or remove? Let's keep for potential direct template path override.
                         'gpt_vision_prompt': args.gpt_vision_prompt,
                    },
                    # Add other component configs if needed (e.g., chunker for weaviate)
                    'chunker_config': {},
                    'json_transformer_config': {'prompt_name': args.prompt_name}, # Pass prompt_name
                    'markdown_transformer_config': {'prompt_name': args.prompt_name}, # Pass prompt_name (though not used yet)
                }

                # Add Weaviate config if needed (no longer needed here, client is passed directly)
                # if pipeline_config['weaviate_enabled']:
                #      pipeline_config['weaviate_config'] = {
                #          'url': args.weaviate_url or settings.WEAVIATE_URL,
                #          'api_key': args.weaviate_api_key or settings.WEAVIATE_API_KEY,
                #      }
                #      pipeline_config['document_class_name'] = f"{args.weaviate_class_prefix}"
                #      pipeline_config['chunk_class_name'] = f"{args.weaviate_class_prefix}Chunk"

                # Set Weaviate class names in config if enabled
                if pipeline_config['weaviate_enabled']:
                    pipeline_config['document_class_name'] = f"{args.weaviate_class_prefix}"
                    pipeline_config['chunk_class_name'] = f"{args.weaviate_class_prefix}Chunk"

                # Filter out None values from top-level config passed to pipeline
                pipeline_config = {k: v for k, v in pipeline_config.items() if v is not None}

                # --- Instantiate Pipeline ---
                # Pass the Weaviate client to the pipeline
                pipeline = DocumentPipeline(config=pipeline_config, weaviate_client=weaviate_client)

                # --- Determine Loader based on file extension ---
                file_ext = file_path.suffix.lower()
                loader = None
                if file_ext == '.pdf':
                    loader = PDFLoader(pipeline_config.get('pdf_loader_config', {}))
                elif file_ext == '.txt':
                    loader = TextLoader() # Assumes no specific config needed
                elif file_ext == '.md':
                    loader = MarkdownLoader() # Assumes no specific config needed
                elif file_ext == '.json':
                    loader = JSONLoader() # Assumes no specific config needed
                elif file_ext == '.docx':
                    # Ensure python-docx is installed
                    try:
                        loader = DocxLoader() # Assumes no specific config needed
                    except ImportError as e:
                         logger.error(f"Failed to initialize DocxLoader for {file_path.name}: {e}. Make sure 'python-docx' is installed.")
                         fail_count += 1
                         continue # Skip this file
                else:
                    logger.warning(f"Unsupported file type '{file_ext}' for {file_path.name}. Skipping.")
                    fail_count += 1
                    continue # Skip this file

                # --- Configure Pipeline Components ---
                pipeline.pipeline.add_component(loader) # Add loader first

                # Add PDF processor if input is PDF (it handles internal routing now)
                if file_ext == '.pdf':
                     pdf_processor = HybridPDFProcessor(pipeline_config.get('pdf_processor_config', {}))
                     pipeline.pipeline.add_component(pdf_processor)
                # ELSE: For non-PDF files, we might need other processors later (e.g., TextCleaner)

                # Add transformer based on pipeline_type (applied after loader/processor)
                if args.pipeline_type == 'markdown':
                    markdown_transformer = TextToMarkdown(pipeline_config.get('markdown_transformer_config', {}))
                    pipeline.pipeline.add_component(markdown_transformer)
                elif args.pipeline_type == 'json':
                    # Note: JSON input might not make sense for JSON output pipeline unless further transformation is intended
                    if file_ext == '.json':
                         logger.warning(f"Applying JSON pipeline to JSON input file {file_path.name}. Ensure this is intended.")
                    json_transformer = TextToJSON(pipeline_config.get('json_transformer_config', {}))
                    pipeline.pipeline.add_component(json_transformer)
                elif args.pipeline_type == 'weaviate':
                     if not pipeline_config.get('weaviate_enabled'):
                          logger.error("Weaviate pipeline type selected, but Weaviate is not enabled in config.")
                          fail_count += 1
                          continue
                     chunker = DocumentChunker(pipeline_config.get('chunker_config', {}))
                     pipeline.pipeline.add_component(chunker)
                # 'text' and 'hybrid' types primarily rely on the loader (and PDF processor if applicable)

                logger.info(f"Configured pipeline: {[c.__class__.__name__ for c in pipeline.pipeline.components]}")

                # --- Process Document ---
                result = pipeline.process_document(file_path)

                # --- Save Output ---
                if 'error' in result and result['error']:
                     logger.error(f"Pipeline failed for {file_path.name}: {result['error']}")
                     fail_count += 1
                else:
                     output_filename = get_output_filename(file_path, args.pipeline_type, args.output_format)
                     output_path = output_dir / output_filename
                     save_output(result, output_path, args.pipeline_type)
                     success_count += 1

            except Exception as e:
                logger.exception(f"Critical error processing file {file_path.name}: {e}") # Use logger.exception to include traceback
                fail_count += 1

            file_duration = time.time() - file_start_time
            logger.info(f"--- Finished processing {file_path.name} in {file_duration:.2f} seconds ---")

        # --- Summary ---
        total_duration = time.time() - total_start_time
        logger.info("--- Processing Summary ---")
        logger.info(f"Total files processed: {len(files_to_process)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {fail_count}")
        logger.info(f"Total time: {total_duration:.2f} seconds")
        logger.info("--------------------------")

    finally:
        # Ensure the Weaviate client is closed
        if weaviate_client:
            weaviate_client.close()
            logger.info("Weaviate client closed.")

if __name__ == "__main__":
    main()