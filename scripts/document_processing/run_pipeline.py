#!/usr/bin/env python
"""
Flexible Script for Running Document and Media Processing Pipelines

Allows processing single files or directories/URLs with various configurations
and saving results to files.
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
# parent chain: run_pipeline.py -> document_processing/ -> scripts/ -> (repo root)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.config import get_settings, ensure_directories_exist

# Import Weaviate client getter and collection management function
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
                        choices=['text', 'markdown', 'json', 'structured'],
                        help='Type of pipeline configuration to run.')
    parser.add_argument('--recursive', action='store_true',
                        help='Process directories recursively.')
    parser.add_argument('--output_format', type=str, choices=['txt', 'md', 'json', 'csv', 'xlsx'],
                        help='Explicit output format (default inferred from pipeline_type).')

    # PPTX Configuration
    parser.add_argument('--pptx_strategy', type=str, default='hybrid', choices=['hybrid'],
                        help='Processing strategy for PPTX files (e.g., "hybrid").')

    # Excel and CSV configuration
    parser.add_argument('--excel_template', type=str, default='default',
                        help='Name of Excel template in report_templates/excel/ (without .xlsx extension)')
    parser.add_argument('--excel_template_dir', type=str, default='report_templates/excel',
                        help='Directory containing Excel templates')
    parser.add_argument('--merge_csv', action='store_true',
                        help='Merge multiple CSV outputs into a single file')

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
    parser.add_argument('--ocr_mode', type=str, default='hybrid', choices=['hybrid', 'docling', 'enhanced_docling', 'gpt'],
                        help="OCR mode for PDF processing ('hybrid', 'docling', 'enhanced_docling', 'gpt'). Only relevant for PDF inputs.")
    parser.add_argument('--show_progress_bar', action='store_true', default=True,
                        help="Show progress bar when processing multi-page documents.")
    parser.add_argument('--no_progress_bar', action='store_true',
                        help="Disable progress bar when processing multi-page documents.")
    
    # Enhanced Docling Configuration
    parser.add_argument('--output_all_formats', action='store_true', default=True,
                        help="Output all available formats (text, markdown, JSON) when using enhanced_docling processor.")
    parser.add_argument('--no_output_all_formats', action='store_true',
                        help="Disable multi-format output when using enhanced_docling processor.")
    parser.add_argument('--use_cache', action='store_true', default=True,
                        help="Enable processing cache for resumable document processing.")
    parser.add_argument('--no_cache', action='store_false', dest='use_cache',
                        help="Disable processing cache.")
    parser.add_argument('--clear_cache', action='store_true',
                        help="Clear existing cache before processing.")
    parser.add_argument('--detect_columns', action='store_true', default=True,
                        help="Enable column detection for multi-column PDFs (for enhanced_docling processor).")
    parser.add_argument('--no_detect_columns', action='store_true',
                        help="Disable column detection for multi-column PDFs (for enhanced_docling processor).")
    parser.add_argument('--merge_hyphenated_words', action='store_true', default=True,
                        help="Merge hyphenated words that span multiple lines (for enhanced_docling processor).")
    parser.add_argument('--no_merge_hyphenated_words', action='store_true',
                        help="Disable merging of hyphenated words (for enhanced_docling processor).")
    parser.add_argument('--reconstruct_paragraphs', action='store_true', default=True,
                        help="Reconstruct paragraphs from individual lines (for enhanced_docling processor).")
    parser.add_argument('--no_reconstruct_paragraphs', action='store_true',
                        help="Disable paragraph reconstruction (for enhanced_docling processor).")
    parser.add_argument('--use_llm_cleaning', action='store_true',
                        help="Use LLM-based cleaning for improved text flow (for enhanced_docling processor).")
    parser.add_argument('--pdf_processor_strategy', type=str, choices=['exclusive', 'fallback_chain'],
                        help="Strategy for PDF processing: 'exclusive' (use one processor) or 'fallback_chain' (try multiple in order)")
    parser.add_argument('--pdf_processor', type=str, choices=['pymupdf', 'docling', 'enhanced_docling', 'gpt', 'gemini'],
                        help="Default PDF processor to use (for 'exclusive' strategy)")
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
                '.pdf', '.txt', '.md', '.json', '.docx', '.pptx',
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
            # Add new configuration options
            'excel_template': args.excel_template,
            'excel_template_dir': args.excel_template_dir,
            'merge_csv': args.merge_csv,
            'output_format': args.output_format,
            
            # Progress bar configuration
            'show_progress_bar': args.show_progress_bar if hasattr(args, 'show_progress_bar') else True,
            
            # Enhanced Docling configuration
            'output_all_formats': args.output_all_formats if hasattr(args, 'output_all_formats') else True,
            'detect_columns': args.detect_columns if hasattr(args, 'detect_columns') else True,
            'merge_hyphenated_words': args.merge_hyphenated_words if hasattr(args, 'merge_hyphenated_words') else True,
            'reconstruct_paragraphs': args.reconstruct_paragraphs if hasattr(args, 'reconstruct_paragraphs') else True,
            'use_llm_cleaning': args.use_llm_cleaning,
            
            # Caching configuration
            'use_cache': args.use_cache if hasattr(args, 'use_cache') else True,
            'clear_cache': args.clear_cache if hasattr(args, 'clear_cache') else False,
        }
        
        # Add PDF processor configuration
        # Map ocr_mode to default_pdf_processor if pdf_processor is not explicitly specified
        if args.pdf_processor:
            pipeline_config['default_pdf_processor'] = args.pdf_processor
        elif args.ocr_mode:
            # Map ocr_mode to default_pdf_processor
            if args.ocr_mode == 'gpt':
                pipeline_config['default_pdf_processor'] = 'gpt'
            elif args.ocr_mode == 'docling':
                pipeline_config['default_pdf_processor'] = 'docling'
            elif args.ocr_mode == 'enhanced_docling':
                pipeline_config['default_pdf_processor'] = 'enhanced_docling'
            elif args.ocr_mode == 'hybrid':
                # For hybrid mode, use fallback chain strategy with docling as first choice
                pipeline_config['pdf_processor_strategy'] = 'fallback_chain'
                pipeline_config['active_pdf_processors'] = ['pymupdf', 'docling', 'enhanced_docling', 'gpt', 'gemini']
        
        # Set pdf_processor_strategy if specified
        if args.pdf_processor_strategy:
            pipeline_config['pdf_processor_strategy'] = args.pdf_processor_strategy

        # Instantiate DocumentPipeline for each input (to ensure a clean pipeline per document/URL)
        pipeline = DocumentPipeline(config=pipeline_config)

        try:
            # process_document returns a single dictionary
            processed_document = pipeline.process_document(input_item)
            all_results.append(processed_document) # Append the single dict to results

            # --- Handle Output (Save to file) ---
            doc = processed_document
            # Determine output filename and format
            # Use metadata from the processed doc if available, otherwise derive from input_item
            metadata = doc.get('metadata', {})
            original_filename = Path(input_item).name if not is_url(input_item) else metadata.get('title', 'output')
            original_stem = Path(original_filename).stem
            output_format = args.output_format if args.output_format else args.pipeline_type
            # Map 'text' format to '.txt' extension, otherwise use the format directly
            output_extension = ".txt" if output_format == 'text' else f".{output_format}"

            # Determine final output directory — add pipeline_type subdirectory
            # unless the output_dir already ends with it (e.g., data/output/text)
            if output_dir.name.lower() == args.pipeline_type.lower():
                final_output_dir = output_dir
            else:
                final_output_dir = output_dir / args.pipeline_type
            final_output_dir.mkdir(parents=True, exist_ok=True)

            output_filename = f"{original_stem}_output{output_extension}"
            output_filepath = final_output_dir / output_filename

            # Save content based on output format
            content_to_save = ""
            logger.info(f"Document keys: {list(doc.keys())}")

            if output_format == 'json':
                content_to_save = json.dumps(doc, indent=2)
            elif output_format == 'markdown':
                if 'content' in doc:
                    content_to_save = doc['content']
                elif 'markdown' in doc:
                    content_to_save = doc['markdown']
            elif 'content' in doc:
                content_to_save = doc['content']
            elif 'text' in doc:
                content_to_save = doc['text']
            else:
                logger.warning(f"No 'content' or 'text' field found in processed document for {input_item}. Skipping file output.")

            if content_to_save:
                try:
                    logger.info(f"Saving {len(content_to_save)} chars to {output_filepath}")
                    with open(output_filepath, 'w', encoding='utf-8') as f:
                        f.write(content_to_save)
                    logger.info(f"Saved output to {output_filepath}")
                except IOError as e:
                    logger.error(f"Error saving output to {output_filepath}: {e}")
                    raise
            else:
                logger.warning(f"No content found to save for {input_item} to {output_filepath}")

            # Handle multi-format output from EnhancedDoclingPDFProcessor
            if pipeline_config.get('output_all_formats', False) and doc.get('processing_method') == 'docling':
                if 'text_content' in doc and output_format != 'text':
                    text_output_dir = output_dir / 'text'
                    text_output_dir.mkdir(parents=True, exist_ok=True)
                    text_output_path = text_output_dir / f"{original_stem}_output.txt"
                    with open(text_output_path, 'w', encoding='utf-8') as f:
                        f.write(doc['text_content'])
                    logger.info(f"Saved additional text format to {text_output_path}")

                if 'markdown_content' in doc and output_format != 'markdown':
                    md_output_dir = output_dir / 'markdown'
                    md_output_dir.mkdir(parents=True, exist_ok=True)
                    md_output_path = md_output_dir / f"{original_stem}_output.md"
                    with open(md_output_path, 'w', encoding='utf-8') as f:
                        f.write(doc['markdown_content'])
                    logger.info(f"Saved additional markdown format to {md_output_path}")

                if 'json_content' in doc and output_format != 'json':
                    json_output_dir = output_dir / 'json'
                    json_output_dir.mkdir(parents=True, exist_ok=True)
                    json_output_path = json_output_dir / f"{original_stem}_output.json"
                    with open(json_output_path, 'w', encoding='utf-8') as f:
                        f.write(doc['json_content'])
                    logger.info(f"Saved additional JSON format to {json_output_path}")

        except Exception as exc:
            logger.error(f"Error processing input {input_item}: {exc}")

    logger.info("Pipeline processing complete.")

    # Note: Weaviate ingestion is now handled within process_document for each document.
    # No need for a separate bulk upload step here unless we change the process_document
    # to return all documents for batching at the script level.

if __name__ == "__main__":
    main()
