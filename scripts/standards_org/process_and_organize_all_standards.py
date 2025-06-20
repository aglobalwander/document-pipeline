#!/usr/bin/env python3
"""
Process new NGSS PDFs and organize all standards text with post-processing.
"""

import sys
import re
import shutil
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


def is_likely_continuation(prev_line: str, curr_line: str) -> bool:
    """Determine if current line is likely a continuation of previous line."""
    if not prev_line or not curr_line:
        return False
    
    # Don't merge if previous line ends with sentence-ending punctuation
    if prev_line.rstrip().endswith(('.', '!', '?', ':', ';')):
        return False
    
    # Don't merge if current line starts with uppercase (likely new sentence)
    # unless previous line ends with specific words that commonly continue
    if curr_line.strip() and curr_line.strip()[0].isupper():
        # Check for common continuing patterns
        prev_words = prev_line.strip().split()
        if prev_words and prev_words[-1].lower() not in ['and', 'or', 'of', 'in', 'to', 'for', 'with']:
            return False
    
    # Don't merge if current line looks like a header/title (all caps, contains colons, etc.)
    if curr_line.strip().isupper() or ':' in curr_line[:20]:
        return False
    
    # Don't merge if line starts with a bullet or number
    if re.match(r'^\s*[\d•\-\*]+[\.\)]\s', curr_line):
        return False
    
    # Don't merge if it's a code/standard identifier (like "VA:Cr1.1.PKa")
    if re.match(r'^[A-Z]+:[A-Za-z0-9\.]+', curr_line.strip()):
        return False
    
    # Merge if previous line ends with hyphen
    if prev_line.rstrip().endswith('-'):
        return True
    
    # Merge if line is short and doesn't start a new logical unit
    if len(curr_line.strip()) < 50:
        return True
    
    return False


def merge_broken_lines(lines: list[str]) -> list[str]:
    """Merge lines that were artificially broken."""
    if not lines:
        return lines
    
    merged = []
    current_paragraph = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines but preserve paragraph breaks
        if not stripped:
            if current_paragraph:
                merged.append(' '.join(current_paragraph))
                current_paragraph = []
            merged.append('')
            continue
        
        # Check if this is a section header (like "=== Page 1 ===")
        if stripped.startswith('===') and stripped.endswith('==='):
            if current_paragraph:
                merged.append(' '.join(current_paragraph))
                current_paragraph = []
            merged.append(line)
            continue
        
        # If we have a previous line, check if current should be merged
        if current_paragraph:
            last_line = current_paragraph[-1]
            
            if is_likely_continuation(last_line, stripped):
                # Remove hyphen if present at end of previous line
                if last_line.endswith('-'):
                    current_paragraph[-1] = last_line[:-1]
                    current_paragraph.append(stripped)
                else:
                    current_paragraph.append(stripped)
            else:
                # Start new paragraph
                merged.append(' '.join(current_paragraph))
                current_paragraph = [stripped]
        else:
            current_paragraph = [stripped]
    
    # Don't forget the last paragraph
    if current_paragraph:
        merged.append(' '.join(current_paragraph))
    
    return merged


def post_process_text(content: str) -> str:
    """Apply post-processing to fix line breaks and clean up text."""
    lines = content.split('\n')
    merged_lines = merge_broken_lines(lines)
    
    cleaned_content = '\n'.join(merged_lines)
    
    # Additional cleanup for specific patterns
    # Fix standards that are split across lines (e.g., "VA:Cr1.1.PKa \nEngage in...")
    cleaned_content = re.sub(r'([A-Z]+:[A-Za-z0-9\.]+)\s*\n+\s*([A-Z][a-z])', r'\1 \2', cleaned_content)
    
    # Remove excessive blank lines (more than 2 consecutive)
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    return cleaned_content


def process_new_ngss_pdfs():
    """Process the new NGSS PDFs."""
    ngss2_dir = Path("/Volumes/PortableSSD/data/input/standards_frameworks/ngss_2")
    pdfs = list(ngss2_dir.glob("*.pdf"))
    
    print(f"Processing {len(pdfs)} new NGSS PDFs...")
    
    results = []
    for pdf_path in pdfs:
        print(f"  Processing: {pdf_path.name}...", end=' ')
        try:
            # Extract text
            content = extract_with_pymupdf(pdf_path)
            
            # Post-process
            cleaned_content = post_process_text(content)
            
            results.append({
                'name': pdf_path.stem,
                'content': cleaned_content,
                'length': len(cleaned_content)
            })
            
            print(f"✅ ({len(cleaned_content):,} chars)")
        except Exception as e:
            print(f"❌ ({str(e)})")
    
    return results


def main():
    """Main function to process and organize all standards."""
    # Create final organized output directory
    final_output_dir = Path("data/output/text/all_standards_cleaned")
    final_output_dir.mkdir(parents=True, exist_ok=True)
    
    print("STANDARDS PROCESSING AND ORGANIZATION")
    print("=" * 70)
    
    # Step 1: Process new NGSS PDFs
    print("\n1. Processing new NGSS PDFs from /Volumes/PortableSSD...")
    new_ngss_results = process_new_ngss_pdfs()
    
    # Save new NGSS files
    ngss_output_dir = final_output_dir / "ngss"
    ngss_output_dir.mkdir(exist_ok=True)
    
    for result in new_ngss_results:
        output_path = ngss_output_dir / f"{result['name']}_output.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result['content'])
    
    # Step 2: Copy and post-process existing PyMuPDF outputs
    print("\n2. Organizing and post-processing ALL existing standards...")
    
    # Always use raw source to get all files
    raw_source = Path("data/output/text/standards_pymupdf")
    print(f"  Processing all files from {raw_source}...")
    
    # Copy all text files, maintaining structure
    total_files = 0
    frameworks = {}
    
    for txt_file in raw_source.rglob("*.txt"):
        # Skip the failed PDFs list
        if "failed_pdfs" in txt_file.name:
            continue
        
        # Determine framework from path
        relative_path = txt_file.relative_to(raw_source)
        if len(relative_path.parts) > 1:
            framework = relative_path.parts[0]
        else:
            framework = "misc"
        
        # Create framework directory
        framework_dir = final_output_dir / framework
        framework_dir.mkdir(exist_ok=True)
        
        # Read and process content
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Post-process to fix line breaks
        content = post_process_text(content)
        
        # Save to organized directory
        output_path = framework_dir / txt_file.name
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Track statistics
        if framework not in frameworks:
            frameworks[framework] = 0
        frameworks[framework] += 1
        total_files += 1
        
        if total_files % 20 == 0:
            print(f"    Processed {total_files} files...")
    
    # Step 3: Create summary report
    print("\n3. Creating summary report...")
    
    summary_path = final_output_dir / "PROCESSING_SUMMARY.txt"
    with open(summary_path, 'w') as f:
        f.write("STANDARDS PROCESSING SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total files processed: {total_files + len(new_ngss_results)}\n\n")
        
        f.write("Files by framework:\n")
        f.write("-" * 50 + "\n")
        
        # Count files in final directory
        for framework_dir in sorted(final_output_dir.iterdir()):
            if framework_dir.is_dir():
                file_count = len(list(framework_dir.glob("*.txt")))
                f.write(f"{framework_dir.name:20} {file_count:3} files\n")
        
        f.write("\n" + "-" * 50 + "\n")
        f.write(f"Output directory: {final_output_dir.absolute()}\n")
        
        # Note about the failed PDF
        f.write("\nNOTE: One PDF failed PyMuPDF processing and requires alternative methods:\n")
        f.write("  - course_guides/d_3_gplts_gui_1502_2_e.pdf (IB Global Politics)\n")
        f.write("  - Recommended: Use Docling or Gemini Vision API\n")
    
    print(f"\n✅ COMPLETE! All standards organized in: {final_output_dir}")
    print(f"   Total files: {total_files + len(new_ngss_results)}")
    print(f"   Summary report: {summary_path}")


if __name__ == "__main__":
    main()