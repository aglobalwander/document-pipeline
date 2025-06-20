#!/usr/bin/env python3
"""
Process all standards PDFs with PyMuPDF and track which ones need other processors.
"""

import os
import sys
import json
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def process_with_pymupdf(pdf_path: Path, output_dir: Path) -> Tuple[bool, str, Dict]:
    """
    Process a single PDF with PyMuPDF only.
    Returns: (success, error_message, metadata)
    """
    try:
        # Configure pipeline for PyMuPDF only
        config = {
            'pdf_processor_strategy': 'exclusive',
            'pdf_processor': 'pymupdf',
            'default_pdf_processor': 'pymupdf',
            'output_dir': str(output_dir)
        }
        
        pipeline = DocumentPipeline(config)
        
        # Process the document
        result = pipeline.process_document(str(pdf_path))
        
        if result and 'error' not in result:
            # Check if PyMuPDF actually extracted meaningful content
            content = result.get('content', '')
            if len(content.strip()) < 100:
                return False, "Insufficient text extracted", {
                    'content_length': len(content),
                    'pages': result.get('metadata', {}).get('num_pages', 0)
                }
            
            # Save the output
            output_filename = f"{pdf_path.stem}_output.txt"
            output_path = output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, "", {
                'content_length': len(content),
                'pages': result.get('metadata', {}).get('num_pages', 0),
                'output_file': str(output_path)
            }
        else:
            error = result.get('error', 'Unknown error') if result else 'No result returned'
            return False, error, {}
            
    except Exception as e:
        return False, str(e), {}


def main():
    """Process all standards PDFs with PyMuPDF."""
    
    input_base = Path("data/input/pdfs/standards")
    output_base = Path("data/output/text/standards_pymupdf")
    
    if not input_base.exists():
        logger.error(f"Input directory not found: {input_base}")
        sys.exit(1)
    
    # Get all frameworks
    frameworks = [d for d in input_base.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    logger.info(f"Processing {len(frameworks)} frameworks with PyMuPDF")
    logger.info("=" * 70)
    
    # Track results
    all_results = {
        'processing_date': datetime.now().isoformat(),
        'total_pdfs': 0,
        'successful': 0,
        'failed': 0,
        'frameworks': {},
        'failed_pdfs': []
    }
    
    # Process each framework
    for framework_dir in sorted(frameworks):
        framework_name = framework_dir.name
        logger.info(f"\nProcessing {framework_name}...")
        
        # Create output directory
        framework_output = output_base / framework_name
        framework_output.mkdir(parents=True, exist_ok=True)
        
        # Find all PDFs
        pdf_files = list(framework_dir.glob("*.pdf"))
        
        framework_results = {
            'total': len(pdf_files),
            'successful': 0,
            'failed': 0,
            'files': {}
        }
        
        for pdf_path in pdf_files:
            logger.info(f"  Processing: {pdf_path.name}")
            
            success, error, metadata = process_with_pymupdf(pdf_path, framework_output)
            
            all_results['total_pdfs'] += 1
            
            if success:
                all_results['successful'] += 1
                framework_results['successful'] += 1
                framework_results['files'][pdf_path.name] = {
                    'status': 'success',
                    'metadata': metadata
                }
                logger.info(f"    ✅ Success: {metadata.get('content_length', 0)} chars extracted")
            else:
                all_results['failed'] += 1
                framework_results['failed'] += 1
                framework_results['files'][pdf_path.name] = {
                    'status': 'failed',
                    'error': error,
                    'metadata': metadata
                }
                all_results['failed_pdfs'].append({
                    'framework': framework_name,
                    'filename': pdf_path.name,
                    'path': str(pdf_path),
                    'error': error,
                    'metadata': metadata
                })
                logger.warning(f"    ❌ Failed: {error}")
        
        all_results['frameworks'][framework_name] = framework_results
    
    # Save results
    results_path = output_base / 'pymupdf_processing_results.json'
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Create failed PDFs list
    failed_list_path = output_base / 'failed_pdfs_list.txt'
    with open(failed_list_path, 'w') as f:
        f.write("PDFs that PyMuPDF could not process\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total PDFs: {all_results['total_pdfs']}\n")
        f.write(f"Successful: {all_results['successful']} ({all_results['successful']/all_results['total_pdfs']*100:.1f}%)\n")
        f.write(f"Failed: {all_results['failed']} ({all_results['failed']/all_results['total_pdfs']*100:.1f}%)\n")
        f.write("\n" + "=" * 70 + "\n\n")
        
        if all_results['failed_pdfs']:
            f.write("Failed PDFs requiring alternative processing:\n\n")
            
            current_framework = None
            for pdf in all_results['failed_pdfs']:
                if pdf['framework'] != current_framework:
                    current_framework = pdf['framework']
                    f.write(f"\n{current_framework.upper()}\n")
                    f.write("-" * len(current_framework) + "\n")
                
                f.write(f"  • {pdf['filename']}\n")
                f.write(f"    Error: {pdf['error']}\n")
                if pdf.get('metadata'):
                    f.write(f"    Pages: {pdf['metadata'].get('pages', 'Unknown')}\n")
                f.write("\n")
        else:
            f.write("All PDFs were successfully processed with PyMuPDF!\n")
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total PDFs processed: {all_results['total_pdfs']}")
    logger.info(f"Successfully processed: {all_results['successful']} ({all_results['successful']/all_results['total_pdfs']*100:.1f}%)")
    logger.info(f"Failed: {all_results['failed']} ({all_results['failed']/all_results['total_pdfs']*100:.1f}%)")
    logger.info(f"\nResults saved to: {results_path}")
    logger.info(f"Failed PDFs list: {failed_list_path}")
    
    if all_results['failed'] > 0:
        logger.info(f"\nUse fallback processors (Docling, Gemini, GPT-4V) for the {all_results['failed']} failed PDFs")


if __name__ == "__main__":
    main()