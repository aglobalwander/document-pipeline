#!/usr/bin/env python
"""
Flexible Script for Running Document and Media Processing Pipelines

Allows processing single files or directories/URLs with various configurations
and uploading results to Weaviate or saving to files.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import json
import time
import uuid
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse # Import urlparse for URL checking

# Add project root to sys.path to allow importing doc_processing modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.config import get_settings, ensure_directories_exist

# Import Weaviate client getter
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
        description='Run document and media processing pipelines on files, directories, or URLs.'
    )

    parser.add_argument('--input_path', type=str, required=True,
                        help='Path to the input file, directory, or a URL (e.g., YouTube).')
    parser.add_argument('--output_dir', type=str, default='data/output',
                        help='Base directory to save output files (defaults to data/output).')
    parser.add_argument('--pipeline_type', type=str, required=True,
                        choices=['text', 'markdown', 'json', 'hybrid', 'weaviate'],
                        help='Type of pipeline configuration to run.')
    parser.add_argument('--recursive', action='store_true',
                        help='Process directories recursively.')
    parser.add_argument('--output_format', type=str, choices=['txt', 'md', 'json'],
                        help='Explicit output format (default inferred from pipeline_type).')

    # LLM Configuration (used by various processors/transformers)
    parser.add_argument('--llm_provider', type=str, default='openai',
                        choices=['openai', 'gemini', 'anthropic', 'deepseek'],
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

    # Media Processing Configuration
    parser.add_argument('--image_backend', type=str, default='openai', choices=['openai', 'gemini'],
                        help='Backend for image processing (captioning/vision).')
    parser.add_argument('--deepgram_params', type=json.loads, default={},
                        help='JSON string of parameters for the Deepgram API (e.g., \'{"diarize": true}\').')
    # Add arguments for VideoToChunks if needed (e.g., --video_split_strategy)

    # Weaviate Configuration (only relevant for 'weaviate' pipeline_type)
    parser.add_argument('--weaviate_class_prefix', type=str, default='Document',
                        help='Prefix for Weaviate class names (e.g., KnowledgeItem, KnowledgeMain).')
    parser.add_argument('--weaviate_url', type=str,
                        help='Weaviate URL (uses environment variable if not set).')
    parser.add_argument('--weaviate_api_key', type=str,
                        help='Weaviate API key (uses environment variable if not set).')


    return parser.parse_args()

# --- Helper to check if input is a URL ---
def is_url(input_string: str) -> bool:
    """Checks if a string is likely a URL."""
    try:
        result = urlparse(input_string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# --- Main Processing Logic ---
def main():
    """Main execution function."""
    args = parse_arguments()
    settings = get_settings()
    ensure_directories_exist() # Ensure base output dirs exist

    input_path_str = args.input_path
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True) # Ensure specific output dir exists

    inputs_to_process: List[str] = []

    # --- Identify Inputs to Process (Files or URL) ---
    if is_url(input_path_str):
        logger.info(f"Input is a URL: {input_path_str}")
        inputs_to_process = [input_path_str]
    else:
        input_path = Path(input_path_str)
        if input_path.is_file():
            logger.info(f"Input is a file: {input_path}")
            inputs_to_process = [str(input_path)]
        elif input_path.is_dir():
            logger.info(f"Input is a directory: {input_path}")
            pattern = f"**/*" if args.recursive else "*"
            # Define supported extensions for local file processing
            supported_extensions = [
                '.pdf', '.txt', '.md', '.json', '.docx',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', # Image extensions
                '.mp3', '.wav', '.aac', '.flac', # Audio extensions
                '.mp4', '.mov', '.avi', '.mkv', # Video extensions
            ]
            inputs_to_process = [
                str(f) for f in input_path.glob(pattern)
                if f.is_file() and f.suffix.lower() in supported_extensions
            ]
        else:
            logger.error(f"Input path is not a valid file, directory, or URL: {input_path_str}")
            sys.exit(1)

    if not inputs_to_process:
        logger.warning(f"No supported inputs found to process for {input_path_str}")
        sys.exit(0)

    logger.info(f"Found {len(inputs_to_process)} input(s) to process.")

    # --- Initialize Weaviate client if needed ---
    weaviate_client = None
    if args.pipeline_type == 'weaviate':
        try:
            # Pass Weaviate config from args if provided, otherwise rely on env vars/settings
            weaviate_config = {}
            if args.weaviate_url:
                weaviate_config['weaviate_url'] = args.weaviate_url
            if args.weaviate_api_key:
                weaviate_config['weaviate_api_key'] = args.weaviate_api_key

            weaviate_client = get_weaviate_client(config=weaviate_config)
            logger.info("Successfully connected to Weaviate.")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            sys.exit(1)

    # --- Process Inputs ---
    all_results: List[Dict[str, Any]] = []
    for input_item in inputs_to_process:
        logger.info(f"Processing input: {input_item}")

        # Create pipeline configuration dictionary from parsed arguments
        pipeline_config = {
            'pipeline_type': args.pipeline_type,
            'llm_provider': args.llm_provider,
            'llm_model': args.llm_model,
            'api_key': args.api_key,
            'prompt_name': args.prompt_name,
            'ocr_mode': args.ocr_mode,
            'gpt_vision_prompt': args.gpt_vision_prompt,
            'no_page_images': args.no_page_images,
            'image_backend': args.image_backend,
            'deepgram_params': args.deepgram_params,
            # Add other relevant args to config as needed by components
            'weaviate_enabled': args.pipeline_type == 'weaviate', # Explicitly enable weaviate in config
            'weaviate_class_prefix': args.weaviate_class_prefix,
        }

        # Instantiate DocumentPipeline for each input (to ensure a clean pipeline per document/URL)
        pipeline = DocumentPipeline(config=pipeline_config, weaviate_client=weaviate_client)

        try:
            # process_document now returns a List[Dict[str, Any]]
            processed_documents = pipeline.process_document(input_item)
            all_results.extend(processed_documents)

            # --- Handle Output (Save to file if not Weaviate) ---
            if args.pipeline_type != 'weaviate':
                for doc in processed_documents:
                    # Determine output filename and format
                    original_filename = Path(input_item).name if not is_url(input_item) else doc.get('metadata', {}).get('title', 'output')
                    original_stem = Path(original_filename).stem
                    output_format = args.output_format if args.output_format else args.pipeline_type # Use pipeline_type as default output format
                    output_extension = f".{output_format}"

                    # Ensure output directory exists for the specific format
                    format_output_dir = output_dir / output_format
                    format_output_dir.mkdir(parents=True, exist_ok=True)

                    output_filename = f"{original_stem}_output{output_extension}"
                    output_filepath = format_output_dir / output_filename

                    # Save content based on output format
                    content_to_save = ""
                    if output_format == 'json':
                        # For JSON output, save the entire document dictionary
                        content_to_save = json.dumps(doc, indent=2)
                    elif 'content' in doc:
                        # For text/markdown, save the 'content' field
                        content_to_save = doc['content']
                    elif 'text' in doc:
                         # If 'content' is not available, try 'text' (e.g., from chunks)
                         content_to_save = doc['text']
                    else:
                         logger.warning(f"No 'content' or 'text' field found in processed document for {input_item}. Skipping file output.")
                         continue # Skip saving if no content

                    try:
                        with open(output_filepath, 'w', encoding='utf-8') as f:
                            f.write(content_to_save)
                        logger.info(f"Saved output to {output_filepath}")
                    except IOError as e:
                        logger.error(f"Error saving output to {output_filepath}: {e}")

        except Exception as exc:
            logger.error(f"Error processing input {input_item}: {exc}")

    logger.info("Pipeline processing complete.")

    # Note: Weaviate ingestion is now handled within process_document for each document.
    # No need for a separate bulk upload step here unless we change the process_document
    # to return all documents for batching at the script level.

if __name__ == "__main__":
    main()