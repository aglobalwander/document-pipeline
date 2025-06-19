#!/usr/bin/env python3
"""Benchmark PyMuPDF vs other processors."""

import sys
import time
from pathlib import Path
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.processors import PyMuPDFProcessor, EnhancedDoclingPDFProcessor
from doc_processing.processors.pdf_processor import PDFProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def benchmark_processor(processor_name, processor, pdf_path):
    """Benchmark a single processor."""
    document = {
        'source_path': str(pdf_path),
        'metadata': {'filename': pdf_path.name}
    }
    
    start_time = time.time()
    result = processor.process(document)
    end_time = time.time()
    
    processing_time = end_time - start_time
    content_length = len(result.get('content', ''))
    success = content_length > 0 and not result.get('requires_ocr', False)
    
    return {
        'processor': processor_name,
        'time': processing_time,
        'content_length': content_length,
        'success': success,
        'error': result.get('error')
    }


def main():
    """Run benchmarks."""
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = Path("data/input/pdfs/sample_test.pdf")
    
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    logger.info(f"📊 Benchmarking PDF processors on: {pdf_path.name}")
    logger.info("=" * 60)
    
    # Test processors
    processors = [
        ("PyMuPDF", PyMuPDFProcessor()),
        ("Enhanced Docling", EnhancedDoclingPDFProcessor()),
    ]
    
    results = []
    for name, processor in processors:
        logger.info(f"\n🔄 Testing {name}...")
        try:
            result = benchmark_processor(name, processor, pdf_path)
            results.append(result)
            
            if result['success']:
                logger.info(f"✅ Success: {result['content_length']} chars in {result['time']:.2f}s")
            else:
                logger.info(f"❌ Failed: {result['error'] or 'No content extracted'}")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            results.append({
                'processor': name,
                'time': 0,
                'content_length': 0,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📈 PERFORMANCE SUMMARY")
    logger.info("=" * 60)
    
    successful_results = [r for r in results if r['success']]
    
    if len(successful_results) >= 2:
        pymupdf_result = next((r for r in results if r['processor'] == 'PyMuPDF'), None)
        other_results = [r for r in results if r['processor'] != 'PyMuPDF' and r['success']]
        
        if pymupdf_result and pymupdf_result['success'] and other_results:
            for other in other_results:
                speedup = other['time'] / pymupdf_result['time']
                logger.info(f"⚡ PyMuPDF is {speedup:.1f}x faster than {other['processor']}")
                
                # Cost comparison (assuming other processors might use APIs)
                cost_savings = "100%" if other['processor'] in ['GPT-4V', 'Gemini'] else "N/A"
                logger.info(f"💰 Cost savings: {cost_savings}")
    
    # Table format
    logger.info("\n📊 Detailed Results:")
    logger.info(f"{'Processor':<20} {'Time (s)':<10} {'Chars':<10} {'Status':<10}")
    logger.info("-" * 50)
    
    for result in results:
        status = "✅ Success" if result['success'] else "❌ Failed"
        logger.info(f"{result['processor']:<20} {result['time']:<10.2f} {result['content_length']:<10} {status}")
    
    # Test fallback chain
    logger.info("\n" + "=" * 60)
    logger.info("🔗 Testing Fallback Chain Strategy")
    logger.info("=" * 60)
    
    config = {
        'pdf_processor_strategy': 'fallback_chain',
        'active_pdf_processors': ['pymupdf', 'enhanced_docling']
    }
    
    processor = PDFProcessor(config=config)
    document = {
        'source_path': str(pdf_path),
        'metadata': {'filename': pdf_path.name}
    }
    
    start_time = time.time()
    result = processor.process(document)
    end_time = time.time()
    
    logger.info(f"Processor used: {result.get('processor_used', 'unknown')}")
    logger.info(f"Total time: {end_time - start_time:.2f}s")
    logger.info(f"Content extracted: {len(result.get('content', ''))} characters")
    
    if result.get('processor_used') == 'pymupdf':
        logger.info("✨ PyMuPDF handled it instantly - no need for expensive processors!")


if __name__ == "__main__":
    main()