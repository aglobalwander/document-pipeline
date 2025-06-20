#!/usr/bin/env python3
"""
Post-process PyMuPDF output to fix line break issues.
Merges lines that were artificially broken in the PDF layout.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


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


def merge_broken_lines(lines: List[str]) -> List[str]:
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


def process_file(input_path: Path, output_path: Path = None) -> None:
    """Process a single file to fix line breaks."""
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    merged_lines = merge_broken_lines(lines)
    
    cleaned_content = '\n'.join(merged_lines)
    
    # Additional cleanup for specific patterns
    # Fix standards that are split across lines (e.g., "VA:Cr1.1.PKa \nEngage in...")
    cleaned_content = re.sub(r'([A-Z]+:[A-Za-z0-9\.]+)\s*\n+\s*([A-Z][a-z])', r'\1 \2', cleaned_content)
    
    # Remove excessive blank lines (more than 2 consecutive)
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"  Saved to: {output_path}")


def process_directory(input_dir: Path, output_dir: Path = None) -> None:
    """Process all text files in a directory."""
    if output_dir is None:
        output_dir = input_dir.parent / f"{input_dir.name}_cleaned"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    txt_files = list(input_dir.rglob("*.txt"))
    print(f"Found {len(txt_files)} text files to process")
    
    for txt_file in txt_files:
        # Maintain directory structure
        relative_path = txt_file.relative_to(input_dir)
        output_path = output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        process_file(txt_file, output_path)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python post_process_pymupdf_output.py <input_file_or_directory> [output_path]")
        print("\nExamples:")
        print("  python post_process_pymupdf_output.py data/output/text/standards_pymupdf/")
        print("  python post_process_pymupdf_output.py data/output/text/standards_pymupdf/ncas/Visual Arts at a Glance rev_output.txt")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not input_path.exists():
        print(f"Error: {input_path} does not exist")
        sys.exit(1)
    
    if input_path.is_file():
        process_file(input_path, output_path)
    elif input_path.is_dir():
        process_directory(input_path, output_path)
    else:
        print(f"Error: {input_path} is neither a file nor a directory")
        sys.exit(1)
    
    print("\nPost-processing complete!")


if __name__ == "__main__":
    main()