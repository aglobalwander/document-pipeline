#!/usr/bin/env python3
"""
Test if the new NGSS PDFs can be processed with PyMuPDF.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF


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
    """Test the new NGSS PDFs."""
    ngss2_dir = Path("/Volumes/PortableSSD/data/input/standards_frameworks/ngss_2")
    
    if not ngss2_dir.exists():
        print(f"Directory not found: {ngss2_dir}")
        return
    
    pdfs = list(ngss2_dir.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs in ngss_2 directory\n")
    
    for pdf_path in pdfs:
        print(f"Testing: {pdf_path.name}")
        print("-" * 50)
        
        success, message, text_length, page_count = test_pymupdf(pdf_path)
        
        if success:
            print(f"✅ PyMuPDF can process this file")
            print(f"   Pages: {page_count}")
            print(f"   Extracted text length: {text_length:,} characters")
            
            # Show a sample of the extracted text
            doc = fitz.open(str(pdf_path))
            first_page_text = doc[0].get_text()[:500]
            doc.close()
            
            print(f"   Sample text from first page:")
            print("   " + "-" * 40)
            for line in first_page_text.split('\n')[:10]:
                if line.strip():
                    print(f"   {line.strip()}")
            print("   " + "-" * 40)
        else:
            print(f"❌ PyMuPDF cannot process this file")
            print(f"   Error: {message}")
            print(f"   Recommendation: Use Docling or GPT-4V for this PDF")
        
        print()


if __name__ == "__main__":
    main()