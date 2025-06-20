#!/usr/bin/env python3
"""
Test if Subject Briefs PDFs can be processed with PyMuPDF.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
import json


def test_pymupdf(pdf_path):
    """Test if PyMuPDF can extract text from a PDF."""
    try:
        doc = fitz.open(str(pdf_path))
        total_text = ""
        page_count = len(doc)
        
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text()
            total_text += text
        
        doc.close()
        
        # Check if meaningful text was extracted
        text_length = len(total_text.strip())
        if text_length < 100:
            return False, "Insufficient text extracted", text_length, page_count
        
        return True, "Success", text_length, page_count
        
    except Exception as e:
        return False, str(e), 0, 0


def main():
    """Test all Subject Briefs PDFs."""
    briefs_dir = Path("/Volumes/PortableSSD/data/input/Subject Briefs")
    
    if not briefs_dir.exists():
        print(f"Directory not found: {briefs_dir}")
        return
    
    pdfs = list(briefs_dir.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs in Subject Briefs directory\n")
    
    results = {
        'total': len(pdfs),
        'successful': 0,
        'failed': 0,
        'failed_pdfs': []
    }
    
    # Test each PDF
    for i, pdf_path in enumerate(sorted(pdfs), 1):
        print(f"[{i}/{len(pdfs)}] Testing: {pdf_path.name}...", end=' ')
        
        success, message, text_length, page_count = test_pymupdf(pdf_path)
        
        if success:
            results['successful'] += 1
            print(f"✅ ({text_length:,} chars, {page_count} pages)")
        else:
            results['failed'] += 1
            results['failed_pdfs'].append({
                'name': pdf_path.name,
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
        for pdf in results['failed_pdfs']:
            print(f"  • {pdf['name']}")
            print(f"    Error: {pdf['error']}")
    
    # Save results
    results_path = Path("data/output/subject_briefs_pymupdf_test_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_path}")
    
    # Check for known problematic file
    if any(pdf['name'] == 'd_3_gplts_gui_1502_2_e.pdf' for pdf in results['failed_pdfs']):
        print("\nNOTE: d_3_gplts_gui_1502_2_e.pdf failed again - this is the same file that failed in standards processing")


if __name__ == "__main__":
    main()