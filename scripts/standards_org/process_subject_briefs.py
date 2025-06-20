#!/usr/bin/env python3
"""
Process Subject Briefs PDFs with PyMuPDF and add to standards directory.
"""

import sys
import re
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
    
    # Don't merge if it's a code/standard identifier
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
    # Fix standards that are split across lines
    cleaned_content = re.sub(r'([A-Z]+:[A-Za-z0-9\.]+)\s*\n+\s*([A-Z][a-z])', r'\1 \2', cleaned_content)
    
    # Remove excessive blank lines (more than 2 consecutive)
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    return cleaned_content


def main():
    """Process all Subject Briefs PDFs."""
    briefs_dir = Path("/Volumes/PortableSSD/data/input/Subject Briefs")
    output_dir = Path("data/output/text/standards/subject_briefs")
    
    if not briefs_dir.exists():
        print(f"Directory not found: {briefs_dir}")
        return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDFs
    pdfs = list(briefs_dir.glob("*.pdf"))
    print(f"Processing {len(pdfs)} Subject Briefs PDFs...")
    print("=" * 70)
    
    successful = 0
    failed = 0
    failed_list = []
    
    for i, pdf_path in enumerate(sorted(pdfs), 1):
        # Skip the known problematic file
        if pdf_path.name == "d_3_gplts_gui_1502_2_e.pdf":
            print(f"[{i}/{len(pdfs)}] Skipping: {pdf_path.name} (known PyMuPDF failure)")
            failed += 1
            failed_list.append(pdf_path.name)
            continue
        
        print(f"[{i}/{len(pdfs)}] Processing: {pdf_path.name}...", end=' ')
        
        try:
            # Extract text
            content = extract_with_pymupdf(pdf_path)
            
            # Check if meaningful text was extracted
            if len(content.replace("=== DOCUMENT TEXT ===", "").replace("=== Page", "").strip()) < 100:
                print(f"❌ (Insufficient text)")
                failed += 1
                failed_list.append(pdf_path.name)
                continue
            
            # Post-process to fix line breaks
            cleaned_content = post_process_text(content)
            
            # Save the output
            output_path = output_dir / f"{pdf_path.stem}_output.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            print(f"✅ ({len(cleaned_content):,} chars)")
            successful += 1
            
        except Exception as e:
            print(f"❌ ({str(e)})")
            failed += 1
            failed_list.append(pdf_path.name)
        
        # Progress indicator
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(pdfs)} files processed...")
    
    # Update the summary file
    summary_path = Path("data/output/text/standards/PROCESSING_SUMMARY.txt")
    
    # Read existing summary
    with open(summary_path, 'r') as f:
        summary_content = f.read()
    
    # Update the summary with new information
    updated_lines = []
    for line in summary_content.split('\n'):
        if line.startswith("Total files processed:"):
            # Extract current count and add new files
            current_count = int(line.split(':')[1].strip())
            new_count = current_count + successful
            updated_lines.append(f"Total files processed: {new_count}")
        else:
            updated_lines.append(line)
    
    # Add subject_briefs to the framework list if not already there
    if "subject_briefs" not in summary_content:
        # Find the line before the separator
        for i, line in enumerate(updated_lines):
            if line.startswith("--------------------------------------------------"):
                # Insert before the separator
                updated_lines.insert(i, f"subject_briefs        {successful:3} files")
                break
    
    # Write updated summary
    with open(summary_path, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    # Print final summary
    print("\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    print(f"Total Subject Briefs PDFs: {len(pdfs)}")
    print(f"Successfully processed: {successful}")
    print(f"Failed/Skipped: {failed}")
    
    if failed_list:
        print(f"\nFailed PDFs:")
        for pdf in failed_list:
            print(f"  • {pdf}")
    
    print(f"\nOutput directory: {output_dir}")
    print(f"Updated summary: {summary_path}")


if __name__ == "__main__":
    main()