#!/usr/bin/env python3
"""Simple test to verify PyMuPDF extraction."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.processors.pymupdf_processor import PyMuPDFProcessor
from doc_processing.processors.pdf_processor import PDFProcessor


def test_pymupdf_direct():
    """Test PyMuPDF directly."""
    pdf_path = Path("data/input/pdfs/sample_test.pdf")
    
    processor = PyMuPDFProcessor()
    document = {
        'source_path': str(pdf_path),
        'metadata': {'filename': pdf_path.name}
    }
    
    result = processor.process(document)
    
    print(f"Extraction successful: {result.get('extraction_successful', False)}")
    print(f"Content length: {len(result.get('content', ''))}")
    print(f"Requires OCR: {result.get('requires_ocr', False)}")
    
    if result.get('content'):
        print("\nFirst 300 characters:")
        print(result['content'][:300])


def test_fallback_with_pymupdf():
    """Test fallback chain with PyMuPDF included."""
    pdf_path = Path("data/input/pdfs/sample_test.pdf")
    
    # Configure to use PyMuPDF in fallback chain
    config = {
        'pdf_processor_strategy': 'fallback_chain',
        'active_pdf_processors': ['pymupdf', 'docling'],  # Only PyMuPDF and Docling
    }
    
    processor = PDFProcessor(config=config)
    document = {
        'source_path': str(pdf_path),
        'metadata': {'filename': pdf_path.name}
    }
    
    result = processor.process(document)
    
    print(f"\nFallback chain result:")
    print(f"Processor used: {result.get('processor_used', 'unknown')}")
    print(f"Content length: {len(result.get('content', ''))}")
    print(f"Has error: {'error' in result}")


if __name__ == "__main__":
    print("Testing PyMuPDF directly...")
    test_pymupdf_direct()
    
    print("\n" + "="*60 + "\n")
    
    print("Testing fallback chain with PyMuPDF...")
    test_fallback_with_pymupdf()