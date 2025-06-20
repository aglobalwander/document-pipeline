#!/usr/bin/env python3
"""Test script to demonstrate PyMuPDF processor performance."""

import sys
from pathlib import Path
import time
import logging
from typing import Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.processors import (
    PyMuPDFProcessor, 
    DoclingPDFProcessor,
    PDFProcessor
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_processor(processor_name: str, processor_class, pdf_path: Path) -> Dict:
    """Test a single processor and return results."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {processor_name} on {pdf_path.name}")
    logger.info(f"{'='*60}")
    
    processor = processor_class()
    document = {
        'source_path': str(pdf_path),
        'metadata': {'filename': pdf_path.name}
    }
    
    start_time = time.time()
    try:
        result = processor.process(document)
        processing_time = time.time() - start_time
        
        # Check results
        content = result.get('content', '')
        has_text = len(content) > 100
        requires_ocr = result.get('requires_ocr', False)
        
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Content length: {len(content)} characters")
        logger.info(f"Has extractable text: {has_text}")
        logger.info(f"Requires OCR: {requires_ocr}")
        
        if has_text:
            # Show first 500 characters
            logger.info(f"\nFirst 500 characters of extracted text:")
            logger.info("-" * 40)
            logger.info(content[:500])
            logger.info("-" * 40)
        
        return {
            'processor': processor_name,
            'success': has_text and not requires_ocr,
            'time': processing_time,
            'content_length': len(content),
            'requires_ocr': requires_ocr
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'processor': processor_name,
            'success': False,
            'time': time.time() - start_time,
            'error': str(e)
        }


def test_fallback_chain(pdf_path: Path):
    """Test the fallback chain strategy."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing Fallback Chain on {pdf_path.name}")
    logger.info(f"{'='*60}")
    
    # Configure for fallback chain with PyMuPDF first
    config = {
        'pdf_processor_strategy': 'fallback_chain',
        'active_pdf_processors': ['pymupdf', 'docling', 'enhanced_docling', 'gemini', 'gpt']
    }
    
    processor = PDFProcessor(config=config)
    document = {
        'source_path': str(pdf_path),
        'metadata': {'filename': pdf_path.name}
    }
    
    start_time = time.time()
    result = processor.process(document)
    processing_time = time.time() - start_time
    
    logger.info(f"Processing time: {processing_time:.2f} seconds")
    logger.info(f"Processor used: {result.get('processor_used', 'unknown')}")
    logger.info(f"Content length: {len(result.get('content', ''))} characters")
    
    return result


def main():
    """Run comparison tests."""
    # Get test PDF
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        # Try to find a sample PDF
        possible_paths = [
            Path("data/input/pdfs/sample.pdf"),
            Path("data/input/pdf/sample.pdf"),
            Path("tests/data/sample.pdf"),
        ]
        
        pdf_path = None
        for path in possible_paths:
            if path.exists():
                pdf_path = path
                break
        
        if not pdf_path:
            logger.error("No PDF file specified and no sample PDF found.")
            logger.info("Usage: python test_pymupdf.py <path_to_pdf>")
            sys.exit(1)
    
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Test individual processors
    results = []
    
    # Test PyMuPDF (should be very fast for text PDFs)
    results.append(test_single_processor("PyMuPDF", PyMuPDFProcessor, pdf_path))
    
    # Test Docling for comparison
    results.append(test_single_processor("Docling", DoclingPDFProcessor, pdf_path))
    
    # Test fallback chain
    logger.info("\n" + "="*60)
    logger.info("Testing Fallback Chain Strategy")
    logger.info("="*60)
    fallback_result = test_fallback_chain(pdf_path)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    
    for result in results:
        if result['success']:
            logger.info(f"{result['processor']}: SUCCESS in {result['time']:.2f}s ({result['content_length']} chars)")
        else:
            if 'error' in result:
                logger.info(f"{result['processor']}: FAILED - {result['error']}")
            else:
                logger.info(f"{result['processor']}: REQUIRES OCR")
    
    # Performance comparison
    if all(r['success'] for r in results):
        pymupdf_time = results[0]['time']
        docling_time = results[1]['time']
        speedup = docling_time / pymupdf_time
        logger.info(f"\nPyMuPDF is {speedup:.1f}x faster than Docling for this PDF")


if __name__ == "__main__":
    main()