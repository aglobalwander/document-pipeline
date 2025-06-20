#!/usr/bin/env python
"""
Batch Processing Script for PDF Ingestion to Weaviate

This script processes a directory of PDF files and ingests them into Weaviate
for semantic search and retrieval.

Usage:
    python batch_process.py --input_dir /path/to/pdfs --output_dir /path/to/output

Optional arguments:
    --weaviate_url URL       Weaviate server URL (default: http://localhost:8080)
    --api_key KEY            OpenAI API key
    --chunk_size SIZE        Chunk size for text splitting (default: 1000)
    --chunk_overlap OVERLAP  Chunk overlap (default: 200)
    --concurrent_files NUM   Number of files to process concurrently (default: 1)
    --concurrent_pages NUM   Number of pages to process concurrently (default: 2)
    --resume                 Resume from last processed file
    --class_name NAME        Weaviate class name for documents (default: Document)
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
import json
import concurrent.futures
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_process.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import document processing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from doc_processing.config import get_settings, ensure_directories_exist
from doc_processing.document_pipeline import DocumentPipeline


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Batch process PDF files and ingest into Weaviate'
    )
    
    parser.add_argument('--input_dir', type=str, required=True,
                        help='Directory containing PDF files')
    
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Directory to save processed files')
    
    parser.add_argument('--weaviate_url', type=str, default='http://localhost:8080',
                        help='Weaviate server URL')
    
    parser.add_argument('--api_key', type=str,
                        help='OpenAI API key (will use env var if not provided)')
    
    parser.add_argument('--chunk_size', type=int, default=1000,
                        help='Chunk size for text splitting')
    
    parser.add_argument('--chunk_overlap', type=int, default=200,
                        help='Chunk overlap for text splitting')
    
    parser.add_argument('--concurrent_files', type=int, default=1,
                        help='Number of files to process concurrently')
    
    parser.add_argument('--concurrent_pages', type=int, default=2,
                        help='Number of pages to process concurrently')
    
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last processed file')
    
    parser.add_argument('--class_name', type=str, default='Document',
                        help='Weaviate class name for documents')
    
    return parser.parse_args()


def get_processed_files(progress_file='progress.json'):
    """Get list of previously processed files."""
    if not os.path.exists(progress_file):
        return set()
    
    try:
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        return set(progress.get('processed_files', []))
    except Exception as e:
        logger.error(f"Error reading progress file: {str(e)}")
        return set()


def update_progress(file_path, success, progress_file='progress.json'):
    """Update progress file with processed file."""
    try:
        # Read existing progress
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress = json.load(f)
        else:
            progress = {'processed_files': [], 'failed_files': []}
        
        # Update progress
        file_path_str = str(file_path)
        if success:
            if file_path_str not in progress['processed_files']:
                progress['processed_files'].append(file_path_str)
        else:
            if file_path_str not in progress['failed_files']:
                progress['failed_files'].append(file_path_str)
        
        # Save progress
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error updating progress file: {str(e)}")


def process_file(file_path, pipeline, output_dir):
    """Process a single PDF file."""
    try:
        logger.info(f"Processing: {file_path}")
        start_time = time.time()
        
        # Process document
        result = pipeline.process_document(file_path)
        
        # Save output
        output_path = Path(output_dir) / f"{Path(file_path).stem}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            # Save a simplified version of the result (without large content)
            simplified = {
                'id': result.get('id'),
                'metadata': result.get('metadata', {}),
                'source_path': result.get('source_path'),
                'num_chunks': len(result.get('chunks', [])),
                'processing_time': time.time() - start_time
            }
            json.dump(simplified, f, indent=2, default=str)
        
        logger.info(f"Completed: {file_path} in {time.time() - start_time:.2f} seconds")
        update_progress(file_path, True)
        return True
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        update_progress(file_path, False)
        return False


def process_directory(args):
    """Process all PDF files in directory."""
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get list of PDF files
    input_dir = Path(args.input_dir)
    pdf_files = list(input_dir.glob('*.pdf'))
    logger.info(f"Found {len(pdf_files)} PDF files in {input_dir}")
    
    if not pdf_files:
        logger.warning("No PDF files found to process")
        return
    
    # Filter already processed files if resuming
    if args.resume:
        processed_files = get_processed_files()
        pdf_files = [f for f in pdf_files if str(f) not in processed_files]
        logger.info(f"Resuming processing with {len(pdf_files)} remaining files")
    
    # Configure pipeline
    pipeline_config = {
        'weaviate_enabled': True,
        'weaviate_config': {
            'url': args.weaviate_url,
            'api_key': args.api_key
        },
        'document_class_name': args.class_name,
        'chunk_class_name': f"{args.class_name}Chunk",
        'pdf_processor_config': {
            'concurrent_pages': args.concurrent_pages,
            'resolution_scale': 2,
            'preserve_page_boundaries': True,
        },
        'chunker_config': {
            'chunk_size': args.chunk_size,
            'chunk_overlap': args.chunk_overlap,
            'chunk_by': 'tokens',
            'preserve_paragraph_boundaries': True
        }
    }
    
    # Create pipeline
    pipeline = DocumentPipeline(pipeline_config)
    pipeline.configure_pdf_to_weaviate_pipeline()
    
    # Process files
    if args.concurrent_files > 1:
        # Process files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrent_files) as executor:
            futures = {executor.submit(process_file, file_path, pipeline, args.output_dir): file_path 
                       for file_path in pdf_files}
            
            # Track progress with tqdm
            with tqdm(total=len(pdf_files), desc="Processing PDFs") as progress_bar:
                for future in concurrent.futures.as_completed(futures):
                    file_path = futures[future]
                    try:
                        success = future.result()
                        progress_bar.update(1)
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}")
    else:
        # Process files sequentially
        for file_path in tqdm(pdf_files, desc="Processing PDFs"):
            process_file(file_path, pipeline, args.output_dir)


def main():
    """Main function."""
    args = parse_arguments()
    
    # Set OpenAI API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    
    # Ensure directories exist
    ensure_directories_exist()
    
    # Process directory
    logger.info("Starting batch processing")
    process_directory(args)
    logger.info("Batch processing complete")


if __name__ == "__main__":
    main()