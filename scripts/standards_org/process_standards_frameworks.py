#!/usr/bin/env python3
"""
Process standards framework PDFs with optimal settings.
Uses fallback chain strategy for robust processing.
"""

import os
import sys
from pathlib import Path
import logging
import argparse
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def process_framework(framework_dir: Path, output_base: Path, pipeline_type: str = 'text'):
    """Process all PDFs in a framework directory."""
    
    framework_name = framework_dir.name
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing framework: {framework_name}")
    logger.info(f"{'='*60}")
    
    # Find all PDFs in framework
    pdf_files = list(framework_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {framework_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDFs")
    
    # Create output directory for this framework
    framework_output = output_base / framework_name
    framework_output.mkdir(parents=True, exist_ok=True)
    
    # Configure pipeline with fallback chain
    config = {
        'pdf_processor_strategy': 'fallback_chain',
        'active_pdf_processors': ['pymupdf', 'docling', 'enhanced_docling', 'gemini', 'gpt'],
        'use_cache': True,
        'output_dir': str(framework_output),
        'extract_tables': True,
        'detect_columns': True
    }
    
    pipeline = DocumentPipeline(config)
    
    # Process each PDF
    success_count = 0
    failed_files = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        try:
            # Configure pipeline based on type
            if pipeline_type == 'text':
                pipeline.configure_pdf_to_text_pipeline()
            elif pipeline_type == 'markdown':
                pipeline.configure_pdf_to_markdown_pipeline()
            elif pipeline_type == 'json':
                pipeline.configure_pdf_to_json_pipeline()
            
            # Process the document
            result = pipeline.process_document(str(pdf_path))
            
            if result and 'error' not in result:
                logger.info(f"✅ Success: {pdf_path.name}")
                if 'processor_used' in result:
                    logger.info(f"   Used processor: {result['processor_used']}")
                success_count += 1
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                logger.error(f"❌ Failed: {pdf_path.name} - {error_msg}")
                failed_files.append((pdf_path.name, error_msg))
                
        except Exception as e:
            logger.error(f"❌ Exception processing {pdf_path.name}: {str(e)}")
            failed_files.append((pdf_path.name, str(e)))
    
    # Summary for this framework
    logger.info(f"\n{framework_name} Summary:")
    logger.info(f"  - Processed: {success_count}/{len(pdf_files)} successfully")
    if failed_files:
        logger.info(f"  - Failed files:")
        for filename, error in failed_files:
            logger.info(f"    - {filename}: {error}")
    
    return success_count, len(pdf_files), failed_files


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Process standards framework PDFs")
    parser.add_argument('--input-dir', default='data/input/pdfs/standards',
                       help='Input directory with organized standards')
    parser.add_argument('--output-dir', default='data/output/text/standards',
                       help='Output directory for processed files')
    parser.add_argument('--pipeline-type', choices=['text', 'markdown', 'json'],
                       default='text', help='Output format')
    parser.add_argument('--frameworks', nargs='+', 
                       help='Specific frameworks to process (default: all)')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip PDFs that already have output files')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        logger.info("Have you run organize_standards_pdfs.py first?")
        sys.exit(1)
    
    # Get list of frameworks to process
    if args.frameworks:
        framework_dirs = [input_dir / fw for fw in args.frameworks if (input_dir / fw).exists()]
    else:
        framework_dirs = [d for d in input_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    logger.info(f"Processing {len(framework_dirs)} frameworks")
    logger.info(f"Output directory: {output_dir}")
    
    # Process each framework
    total_success = 0
    total_files = 0
    all_failed = []
    
    for framework_dir in sorted(framework_dirs):
        success, total, failed = process_framework(framework_dir, output_dir, args.pipeline_type)
        total_success += success
        total_files += total
        all_failed.extend([(framework_dir.name, f, e) for f, e in failed])
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("FINAL SUMMARY")
    logger.info("="*60)
    logger.info(f"Total frameworks processed: {len(framework_dirs)}")
    logger.info(f"Total PDFs processed: {total_success}/{total_files} ({total_success/total_files*100:.1f}%)")
    
    if all_failed:
        logger.info(f"\nFailed files by framework:")
        current_framework = None
        for framework, filename, error in all_failed:
            if framework != current_framework:
                logger.info(f"\n{framework}:")
                current_framework = framework
            logger.info(f"  - {filename}: {error[:100]}...")
    
    # Create summary file
    summary_path = output_dir / 'processing_summary.txt'
    with open(summary_path, 'w') as f:
        f.write(f"Standards Framework Processing Summary\n")
        f.write(f"{'='*50}\n")
        f.write(f"Total frameworks: {len(framework_dirs)}\n")
        f.write(f"Total PDFs: {total_files}\n")
        f.write(f"Successfully processed: {total_success}\n")
        f.write(f"Failed: {len(all_failed)}\n")
        f.write(f"Success rate: {total_success/total_files*100:.1f}%\n")
        
        if all_failed:
            f.write(f"\nFailed Files:\n")
            for framework, filename, error in all_failed:
                f.write(f"{framework}/{filename}: {error}\n")
    
    logger.info(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()