#!/usr/bin/env python3
"""
Analyze standards framework PDFs to determine which processing method they need.
This script checks PDFs without processing them to help decide next steps.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import fitz  # PyMuPDF
from collections import defaultdict
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def analyze_pdf_quick(pdf_path: Path) -> Dict:
    """Quick analysis of a PDF to determine processing needs."""
    try:
        doc = fitz.open(str(pdf_path))
        
        # Basic info
        page_count = len(doc)
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        
        # Sample first few pages for text content
        sample_pages = min(5, page_count)  # Check first 5 pages
        text_samples = []
        has_images = False
        total_text_length = 0
        
        for i in range(sample_pages):
            page = doc[i]
            text = page.get_text()
            text_length = len(text.strip())
            total_text_length += text_length
            
            if text_length > 50:
                text_samples.append(text[:200])  # First 200 chars
            
            # Check for images
            if page.get_images():
                has_images = True
        
        doc.close()
        
        # Determine processing needs
        avg_text_per_page = total_text_length / sample_pages if sample_pages > 0 else 0
        
        # Classification logic
        if avg_text_per_page > 500:
            # Good amount of embedded text
            method = "PyMuPDF"
            confidence = "High"
            reason = "Embedded text detected (avg {:.0f} chars/page)".format(avg_text_per_page)
            
        elif avg_text_per_page > 100:
            # Some text but might need enhancement
            method = "Docling"
            confidence = "Medium"
            reason = "Partial text detected, may have complex layout"
            
        elif has_images and avg_text_per_page < 100:
            # Likely scanned
            method = "Gemini/GPT-4V"
            confidence = "High"
            reason = "Appears to be scanned (images with little text)"
            
        else:
            # Unknown or problematic
            method = "Fallback Chain"
            confidence = "Low"
            reason = "Unclear content type, needs full analysis"
        
        return {
            'filename': pdf_path.name,
            'pages': page_count,
            'size_mb': round(file_size_mb, 2),
            'method': method,
            'confidence': confidence,
            'reason': reason,
            'avg_text_per_page': int(avg_text_per_page),
            'has_images': has_images,
            'sample_text': text_samples[0][:100] if text_samples else "No text found"
        }
        
    except Exception as e:
        return {
            'filename': pdf_path.name,
            'error': str(e),
            'method': "Error - Needs Manual Review",
            'confidence': "N/A",
            'reason': f"Analysis failed: {str(e)}"
        }


def analyze_framework(framework_dir: Path) -> List[Dict]:
    """Analyze all PDFs in a framework directory."""
    pdf_files = list(framework_dir.glob("*.pdf"))
    results = []
    
    for pdf_path in pdf_files:
        result = analyze_pdf_quick(pdf_path)
        results.append(result)
    
    return results


def main():
    """Main analysis function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze standards PDFs to determine processing needs")
    parser.add_argument('--input-dir', default='data/input/pdfs/standards',
                       help='Input directory with organized standards')
    parser.add_argument('--output', default='data/output/standards_analysis.json',
                       help='Output file for analysis results')
    parser.add_argument('--frameworks', nargs='+',
                       help='Specific frameworks to analyze (default: all)')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Get frameworks to analyze
    if args.frameworks:
        framework_dirs = [input_dir / fw for fw in args.frameworks if (input_dir / fw).exists()]
    else:
        framework_dirs = [d for d in input_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    logger.info("PDF Analysis for Standards Frameworks")
    logger.info("=" * 70)
    logger.info("This analysis determines which processing method each PDF needs:\n")
    logger.info("- PyMuPDF: Fast extraction for PDFs with embedded text")
    logger.info("- Docling: For complex layouts, tables, multi-column")
    logger.info("- Gemini/GPT-4V: For scanned documents needing OCR")
    logger.info("- Fallback Chain: When automatic detection fails\n")
    
    # Analyze each framework
    all_results = {}
    method_counts = defaultdict(int)
    total_pages = 0
    total_size = 0
    
    for framework_dir in sorted(framework_dirs):
        framework_name = framework_dir.name
        logger.info(f"\nAnalyzing {framework_name}...")
        
        results = analyze_framework(framework_dir)
        all_results[framework_name] = results
        
        # Count methods and stats
        for result in results:
            if 'error' not in result:
                method_counts[result['method']] += 1
                total_pages += result.get('pages', 0)
                total_size += result.get('size_mb', 0)
    
    # Display results by framework
    logger.info("\n" + "=" * 70)
    logger.info("ANALYSIS RESULTS BY FRAMEWORK")
    logger.info("=" * 70)
    
    for framework, results in all_results.items():
        logger.info(f"\n{framework.upper()} ({len(results)} files)")
        logger.info("-" * 50)
        
        # Group by method
        by_method = defaultdict(list)
        for result in results:
            by_method[result.get('method', 'Unknown')].append(result)
        
        for method, pdfs in by_method.items():
            logger.info(f"\n  {method} ({len(pdfs)} files):")
            for pdf in pdfs[:3]:  # Show first 3
                logger.info(f"    - {pdf['filename'][:40]:<40} {pdf.get('reason', '')}")
            if len(pdfs) > 3:
                logger.info(f"    ... and {len(pdfs) - 3} more")
    
    # Overall summary
    logger.info("\n" + "=" * 70)
    logger.info("OVERALL SUMMARY")
    logger.info("=" * 70)
    
    total_files = sum(len(results) for results in all_results.values())
    logger.info(f"Total PDFs analyzed: {total_files}")
    logger.info(f"Total pages: {total_pages:,}")
    logger.info(f"Total size: {total_size:.1f} MB")
    logger.info(f"\nProcessing methods needed:")
    
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_files * 100) if total_files > 0 else 0
        logger.info(f"  - {method:<20} {count:>3} files ({percentage:>5.1f}%)")
    
    # Cost estimation
    logger.info(f"\nCost Estimation (rough):")
    
    # Estimate pages per method
    pages_by_method = defaultdict(int)
    for framework, results in all_results.items():
        for result in results:
            if 'error' not in result:
                pages_by_method[result['method']] += result.get('pages', 0)
    
    pymupdf_pages = pages_by_method.get('PyMuPDF', 0)
    docling_pages = pages_by_method.get('Docling', 0)
    ai_pages = pages_by_method.get('Gemini/GPT-4V', 0)
    
    logger.info(f"  - PyMuPDF: {pymupdf_pages:,} pages (Free)")
    logger.info(f"  - Docling: {docling_pages:,} pages (Free)")
    logger.info(f"  - Gemini/GPT-4V: {ai_pages:,} pages")
    logger.info(f"    • Gemini cost: ~${ai_pages * 0.0002:.2f}")
    logger.info(f"    • GPT-4V cost: ~${ai_pages * 0.01:.2f}")
    
    # Recommendations
    logger.info(f"\nRECOMMENDATIONS:")
    logger.info(f"1. Start with PyMuPDF files ({method_counts.get('PyMuPDF', 0)} files) - these will process quickly")
    logger.info(f"2. Use Docling for complex layouts ({method_counts.get('Docling', 0)} files)")
    logger.info(f"3. Consider Gemini over GPT-4V for scanned docs to save ~98% on costs")
    logger.info(f"4. Use fallback chain for uncertain files ({method_counts.get('Fallback Chain', 0)} files)")
    
    # Save detailed results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_files': total_files,
                'total_pages': total_pages,
                'total_size_mb': round(total_size, 2),
                'method_counts': dict(method_counts),
                'pages_by_method': dict(pages_by_method)
            },
            'frameworks': all_results
        }, f, indent=2)
    
    logger.info(f"\nDetailed analysis saved to: {output_path}")
    
    # Create processing recommendations script
    script_path = output_path.parent / 'recommended_processing.sh'
    with open(script_path, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Recommended processing order based on analysis\n\n")
        
        # Process PyMuPDF files first
        f.write("# Step 1: Process PyMuPDF files (fastest)\n")
        for framework, results in all_results.items():
            pymupdf_files = [r for r in results if r.get('method') == 'PyMuPDF']
            if pymupdf_files:
                f.write(f"./process_single_framework.sh {framework} # {len(pymupdf_files)} PyMuPDF files\n")
        
        f.write("\n# Step 2: Process Docling files\n")
        for framework, results in all_results.items():
            docling_files = [r for r in results if r.get('method') == 'Docling']
            if docling_files:
                f.write(f"./process_single_framework.sh {framework} # {len(docling_files)} Docling files\n")
    
    os.chmod(script_path, 0o755)
    logger.info(f"Processing recommendations script created: {script_path}")


if __name__ == "__main__":
    main()