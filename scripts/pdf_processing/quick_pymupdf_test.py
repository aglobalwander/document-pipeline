#!/usr/bin/env python3
"""
Quick test of PyMuPDF on all standards PDFs to identify which ones fail.
"""

import sys
from pathlib import Path
import json
import fitz  # PyMuPDF

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def test_pymupdf(pdf_path):
    """Test if PyMuPDF can extract text from a PDF."""
    try:
        doc = fitz.open(str(pdf_path))
        total_text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            total_text += text
        
        doc.close()
        
        # Check if meaningful text was extracted
        if len(total_text.strip()) < 100:
            return False, "Insufficient text extracted", len(total_text)
        
        return True, "Success", len(total_text)
        
    except Exception as e:
        return False, str(e), 0


def main():
    """Test all PDFs."""
    input_base = Path("data/input/pdfs/standards")
    
    if not input_base.exists():
        print(f"Input directory not found: {input_base}")
        sys.exit(1)
    
    # Get all PDFs
    all_pdfs = list(input_base.rglob("*.pdf"))
    print(f"Found {len(all_pdfs)} PDFs to test\n")
    
    results = {
        'total': len(all_pdfs),
        'successful': 0,
        'failed': 0,
        'failed_pdfs': []
    }
    
    # Test each PDF
    for i, pdf_path in enumerate(all_pdfs, 1):
        print(f"[{i}/{len(all_pdfs)}] Testing: {pdf_path.name}...", end=' ')
        
        success, message, text_length = test_pymupdf(pdf_path)
        
        if success:
            results['successful'] += 1
            print(f"✅ ({text_length} chars)")
        else:
            results['failed'] += 1
            results['failed_pdfs'].append({
                'path': str(pdf_path),
                'name': pdf_path.name,
                'framework': pdf_path.parent.name,
                'error': message,
                'text_length': text_length
            })
            print(f"❌ ({message})")
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total PDFs tested: {results['total']}")
    print(f"Successful: {results['successful']} ({results['successful']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    
    if results['failed_pdfs']:
        print(f"\nFailed PDFs that need alternative processing:")
        print("-"*70)
        
        # Group by framework
        by_framework = {}
        for pdf in results['failed_pdfs']:
            fw = pdf['framework']
            if fw not in by_framework:
                by_framework[fw] = []
            by_framework[fw].append(pdf)
        
        for framework, pdfs in sorted(by_framework.items()):
            print(f"\n{framework.upper()} ({len(pdfs)} files)")
            for pdf in pdfs:
                print(f"  • {pdf['name']}")
                print(f"    Error: {pdf['error']}")
    
    # Save results
    results_path = Path("data/output/pymupdf_test_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_path}")


if __name__ == "__main__":
    main()