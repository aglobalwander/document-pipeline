#!/usr/bin/env python3
"""
Complete processing of remaining PDFs with PyMuPDF.
This script directly uses PyMuPDF to avoid pipeline overhead.
"""

import sys
import json
from pathlib import Path
import fitz  # PyMuPDF

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def extract_with_pymupdf(pdf_path: Path) -> str:
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    extracted_text = ["=== DOCUMENT TEXT ===\n"]
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            extracted_text.append(f"\n=== Page {page_num + 1} ===\n{text}")
    
    doc.close()
    return ''.join(extracted_text)


def main():
    """Process remaining PDFs."""
    input_base = Path("data/input/pdfs/standards")
    output_base = Path("data/output/text/standards_pymupdf")
    
    # Get all PDFs
    all_pdfs = list(input_base.rglob("*.pdf"))
    print(f"Total PDFs found: {len(all_pdfs)}")
    
    # Get already processed files
    processed_files = set()
    for txt_file in output_base.rglob("*_output.txt"):
        # Reconstruct the original PDF name
        pdf_name = txt_file.stem.replace("_output", "") + ".pdf"
        processed_files.add(pdf_name)
    
    print(f"Already processed: {len(processed_files)} files")
    
    # Find PDFs that need processing
    remaining_pdfs = []
    for pdf_path in all_pdfs:
        if pdf_path.name not in processed_files:
            # Also check if it's the one that failed
            if pdf_path.name != "d_3_gplts_gui_1502_2_e.pdf":
                remaining_pdfs.append(pdf_path)
    
    print(f"Remaining to process: {len(remaining_pdfs)} files")
    
    if not remaining_pdfs:
        print("All PDFs have been processed!")
        return
    
    # Process remaining PDFs
    successful = 0
    failed = 0
    
    for i, pdf_path in enumerate(remaining_pdfs, 1):
        framework_name = pdf_path.parent.name
        framework_output = output_base / framework_name
        framework_output.mkdir(parents=True, exist_ok=True)
        
        output_path = framework_output / f"{pdf_path.stem}_output.txt"
        
        print(f"[{i}/{len(remaining_pdfs)}] Processing: {framework_name}/{pdf_path.name}...", end=' ')
        
        try:
            # Extract text
            content = extract_with_pymupdf(pdf_path)
            
            # Check if meaningful text was extracted
            if len(content.replace("=== DOCUMENT TEXT ===", "").replace("=== Page", "").strip()) < 100:
                print(f"❌ (Insufficient text)")
                failed += 1
                continue
            
            # Save the output
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ ({len(content)} chars)")
            successful += 1
            
        except Exception as e:
            print(f"❌ ({str(e)})")
            failed += 1
    
    # Print summary
    print("\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    print(f"Total processed: {len(remaining_pdfs)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nTotal PyMuPDF processed files now: {len(processed_files) + successful}")


if __name__ == "__main__":
    main()