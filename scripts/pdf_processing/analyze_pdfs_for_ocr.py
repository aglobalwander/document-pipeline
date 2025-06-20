#!/usr/bin/env python3
"""
Analyze PDFs to determine the best OCR method for each document.
Creates an index with recommendations for processing standards framework documents.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import fitz  # PyMuPDF

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.processors import PyMuPDFProcessor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def analyze_pdf_characteristics(pdf_path: Path) -> Dict:
    """Analyze a PDF to determine its characteristics and recommended processing method."""
    try:
        doc = fitz.open(str(pdf_path))
        
        characteristics = {
            'filename': pdf_path.name,
            'path': str(pdf_path),
            'pages': len(doc),
            'has_text': False,
            'text_coverage': 0.0,
            'has_images': False,
            'has_tables': False,
            'is_scanned': False,
            'is_form': False,
            'complexity': 'simple',
            'recommended_processor': 'pymupdf',
            'fallback_processors': ['docling', 'gemini'],
            'notes': []
        }
        
        # Analyze each page
        total_text_length = 0
        pages_with_text = 0
        pages_with_images = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Check for text
            text = page.get_text()
            if len(text.strip()) > 50:
                pages_with_text += 1
                total_text_length += len(text)
            
            # Check for images
            image_list = page.get_images()
            if image_list:
                pages_with_images += 1
            
            # Check for tables (basic heuristic)
            if "table" in text.lower() or "|" in text:
                characteristics['has_tables'] = True
        
        # Store the page count before closing
        total_pages = len(doc)
        doc.close()
        
        # Calculate text coverage
        characteristics['has_text'] = pages_with_text > 0
        characteristics['text_coverage'] = pages_with_text / total_pages if total_pages > 0 else 0
        characteristics['has_images'] = pages_with_images > 0
        
        # Determine if scanned
        if characteristics['text_coverage'] < 0.1:
            characteristics['is_scanned'] = True
            characteristics['notes'].append("Document appears to be scanned (low text coverage)")
        
        # Determine complexity and recommendations
        if characteristics['is_scanned']:
            characteristics['complexity'] = 'complex'
            characteristics['recommended_processor'] = 'docling'
            characteristics['fallback_processors'] = ['enhanced_docling', 'gemini', 'gpt']
            characteristics['notes'].append("Scanned document - OCR required")
            
        elif characteristics['has_tables']:
            characteristics['complexity'] = 'medium'
            characteristics['recommended_processor'] = 'enhanced_docling'
            characteristics['fallback_processors'] = ['docling', 'gemini']
            characteristics['notes'].append("Contains tables - enhanced processing recommended")
            
        elif characteristics['has_images'] and characteristics['text_coverage'] < 0.8:
            characteristics['complexity'] = 'medium'
            characteristics['recommended_processor'] = 'docling'
            characteristics['fallback_processors'] = ['gemini', 'gpt']
            characteristics['notes'].append("Mixed text and images - AI processing may help")
            
        else:
            characteristics['complexity'] = 'simple'
            characteristics['recommended_processor'] = 'pymupdf'
            characteristics['fallback_processors'] = ['docling']
            characteristics['notes'].append("Standard text document - fast extraction possible")
        
        # Add file size
        file_size = pdf_path.stat().st_size / (1024 * 1024)  # MB
        characteristics['size_mb'] = round(file_size, 2)
        
        if file_size > 10:
            characteristics['notes'].append(f"Large file ({file_size:.1f} MB) - consider page-by-page processing")
        
        return characteristics
        
    except Exception as e:
        logger.error(f"Error analyzing {pdf_path}: {str(e)}")
        return {
            'filename': pdf_path.name,
            'path': str(pdf_path),
            'error': str(e),
            'recommended_processor': 'fallback_chain',
            'notes': [f"Error during analysis: {str(e)}"]
        }


def create_processing_index(pdf_directory: Path, output_path: Path = None) -> Dict:
    """Create an index of PDFs with processing recommendations."""
    
    if not pdf_directory.exists():
        logger.error(f"Directory not found: {pdf_directory}")
        return {}
    
    logger.info(f"Analyzing PDFs in: {pdf_directory}")
    
    pdf_files = list(pdf_directory.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    index = {
        'directory': str(pdf_directory),
        'total_files': len(pdf_files),
        'analysis_date': str(Path(__file__).stat().st_mtime),
        'documents': [],
        'summary': {
            'simple': 0,
            'medium': 0,
            'complex': 0,
            'errors': 0
        }
    }
    
    for pdf_path in pdf_files:
        logger.info(f"\nAnalyzing: {pdf_path.name}")
        analysis = analyze_pdf_characteristics(pdf_path)
        index['documents'].append(analysis)
        
        # Update summary
        if 'error' in analysis:
            index['summary']['errors'] += 1
        else:
            index['summary'][analysis['complexity']] += 1
        
        # Log recommendations
        logger.info(f"  - Complexity: {analysis.get('complexity', 'unknown')}")
        logger.info(f"  - Recommended: {analysis.get('recommended_processor', 'unknown')}")
        if analysis.get('notes'):
            for note in analysis['notes']:
                logger.info(f"  - Note: {note}")
    
    # Save index if output path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(index, f, indent=2)
        logger.info(f"\nIndex saved to: {output_path}")
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Total PDFs analyzed: {index['total_files']}")
    logger.info(f"Simple documents: {index['summary']['simple']} (use PyMuPDF)")
    logger.info(f"Medium complexity: {index['summary']['medium']} (use Docling)")
    logger.info(f"Complex documents: {index['summary']['complex']} (use AI/OCR)")
    logger.info(f"Errors: {index['summary']['errors']}")
    
    return index


def create_processing_script(index: Dict, output_path: Path):
    """Generate a bash script to process all PDFs with optimal settings."""
    
    script_lines = [
        "#!/bin/bash",
        "# Auto-generated script to process PDFs with optimal settings",
        f"# Generated from: {index['directory']}",
        f"# Total files: {index['total_files']}",
        "",
        "# Create output directories",
        "mkdir -p data/output/text/standards",
        "mkdir -p data/output/markdown/standards",
        "mkdir -p data/output/json/standards",
        "",
        "# Process each PDF with recommended settings",
        ""
    ]
    
    for doc in index['documents']:
        if 'error' in doc:
            script_lines.append(f"# Skipping {doc['filename']} - analysis error")
            continue
            
        filename = Path(doc['filename']).stem
        processor = doc['recommended_processor']
        
        # Create processing command
        if processor == 'pymupdf':
            cmd = f"python scripts/run_pipeline.py --input_path \"{doc['path']}\" --pipeline_type text --pdf_processor pymupdf --output_dir data/output/text/standards"
        elif processor == 'docling':
            cmd = f"python scripts/master_docling.py --input_path \"{doc['path']}\" --output_format text"
        elif processor == 'enhanced_docling':
            cmd = f"python scripts/master_docling.py --input_path \"{doc['path']}\" --output_all_formats"
        else:
            cmd = f"python scripts/run_pipeline.py --input_path \"{doc['path']}\" --pipeline_type text --pdf_processor_strategy fallback_chain"
        
        script_lines.extend([
            f"echo \"Processing {doc['filename']} with {processor}...\"",
            cmd,
            ""
        ])
    
    # Write script
    with open(output_path, 'w') as f:
        f.write('\n'.join(script_lines))
    
    # Make executable
    os.chmod(output_path, 0o755)
    logger.info(f"\nProcessing script created: {output_path}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze PDFs to determine best OCR method")
    parser.add_argument('pdf_directory', help='Directory containing PDFs to analyze')
    parser.add_argument('--output-index', help='Path to save analysis index JSON', 
                       default='data/output/pdf_analysis_index.json')
    parser.add_argument('--create-script', help='Create processing script', 
                       action='store_true')
    
    args = parser.parse_args()
    
    pdf_dir = Path(args.pdf_directory)
    output_path = Path(args.output_index)
    
    # Create index
    index = create_processing_index(pdf_dir, output_path)
    
    # Create processing script if requested
    if args.create_script and index['documents']:
        script_path = output_path.parent / 'process_standards_pdfs.sh'
        create_processing_script(index, script_path)
        logger.info(f"\nTo process all PDFs, run: bash {script_path}")


if __name__ == "__main__":
    main()