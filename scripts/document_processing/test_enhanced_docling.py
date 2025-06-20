#!/usr/bin/env python
"""
Test script for the Enhanced Docling PDF Processor.

This script demonstrates the Docling processor with multi-format output capabilities.
It processes a PDF file and outputs the extracted text in text, markdown, and JSON formats.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path

# Add project root to sys.path to allow importing doc_processing modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from doc_processing.processors.enhanced_docling_processor import EnhancedDoclingPDFProcessor
from doc_processing.loaders.pdf_loader import PDFLoader

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Test the Enhanced Docling PDF Processor with multi-format output capabilities.'
    )

    parser.add_argument('--input_path', type=str, default='data/input/pdfs/as_1.pdf',
                        help='Path to the input PDF file (default: data/input/pdfs/as_1.pdf).')
    parser.add_argument('--output_dir', type=str, default='data/output',
                        help='Directory to save output files (default: data/output).')
    parser.add_argument('--output_format', type=str, default='text', choices=['text', 'markdown', 'json'],
                        help='Primary output format (default: text).')
    parser.add_argument('--no_all_formats', action='store_true',
                        help='Disable output of all formats (text, markdown, JSON).')
    parser.add_argument('--extract_tables', action='store_true', default=True,
                        help='Enable table extraction (default: enabled).')
    parser.add_argument('--no_extract_tables', action='store_true',
                        help='Disable table extraction.')

    return parser.parse_args()

def main():
    """Main execution function."""
    args = parse_arguments()
    
    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    # Create configuration for the processor
    processor_config = {
        'docling_extract_tables': False if args.no_extract_tables else args.extract_tables,
        'output_format': args.output_format,
        'output_all_formats': not args.no_all_formats,
    }
    
    # Load the PDF file
    logger.info(f"Loading PDF file: {input_path}")
    pdf_loader = PDFLoader()
    document = pdf_loader.load(str(input_path))
    
    # Process the document with the Enhanced Docling processor
    logger.info("Processing document with Docling processor")
    processor = EnhancedDoclingPDFProcessor(config=processor_config)
    processed_document = processor.process(document)
    
    # Save the primary output format
    primary_format_ext = '.txt' if args.output_format == 'text' else '.md' if args.output_format == 'markdown' else '.json'
    primary_output_filename = f"{input_path.stem}_docling{primary_format_ext}"
    primary_output_path = output_dir / args.output_format / primary_output_filename
    
    # Create output subdirectories
    (output_dir / args.output_format).mkdir(parents=True, exist_ok=True)
    
    # Add debug information about the content
    content = processed_document.get('content', '')
    content_length = len(content) if content else 0
    logger.info(f"Primary content ({args.output_format}) length: {content_length} characters")
    if content_length > 0:
        logger.info(f"Content starts with: {content[:100]}...")
    else:
        logger.warning("Content is empty!")
    
    # Save the primary format
    logger.info(f"Saving {args.output_format} output to: {primary_output_path}")
    with open(primary_output_path, 'w', encoding='utf-8') as f:
        f.write(content if content else "No content was generated.")
    
    # Save all formats if requested
    if not args.no_all_formats:
        # Save text format
        if args.output_format != 'text' and 'text_content' in processed_document:
            text_output_path = output_dir / 'text' / f"{input_path.stem}_docling.txt"
            (output_dir / 'text').mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving text output to: {text_output_path}")
            with open(text_output_path, 'w', encoding='utf-8') as f:
                f.write(processed_document['text_content'])
        
        # Save markdown format
        if args.output_format != 'markdown' and 'markdown_content' in processed_document:
            markdown_output_path = output_dir / 'markdown' / f"{input_path.stem}_docling.md"
            (output_dir / 'markdown').mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving markdown output to: {markdown_output_path}")
            with open(markdown_output_path, 'w', encoding='utf-8') as f:
                f.write(processed_document['markdown_content'])
        
        # Save JSON format
        if args.output_format != 'json' and 'json_content' in processed_document:
            json_output_path = output_dir / 'json' / f"{input_path.stem}_docling.json"
            (output_dir / 'json').mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving JSON output to: {json_output_path}")
            with open(json_output_path, 'w', encoding='utf-8') as f:
                f.write(processed_document['json_content'])
    
    logger.info("Processing complete")
    
    # Print a summary of the processing
    logger.info("\nProcessing Summary:")
    logger.info(f"  Input file: {input_path}")
    logger.info(f"  Primary output format: {args.output_format}")
    logger.info(f"  Primary output file: {primary_output_path}")
    logger.info(f"  All formats output: {'Disabled' if args.no_all_formats else 'Enabled'}")
    logger.info(f"  Table extraction: {'Enabled' if processor_config['docling_extract_tables'] else 'Disabled'}")
    
    # Print a sample of the processed text
    sample_length = min(500, len(content))
    logger.info(f"\nSample of processed text (first {sample_length} characters):")
    logger.info("-" * 80)
    logger.info(content[:sample_length] + "...")
    logger.info("-" * 80)

if __name__ == "__main__":
    main()
