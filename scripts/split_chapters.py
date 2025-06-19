#!/usr/bin/env python3
"""
Script to split a markdown document into separate chapter files, appendices, references, and index.
"""

import os
import re
import sys

def split_document_by_sections(input_file, output_dir):
    """
    Split a markdown document into separate chapter files, appendices, references, and index.
    
    Args:
        input_file (str): Path to the input markdown file
        output_dir (str): Path to the output directory
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Split content by chapter
    # We'll use regex to find chapter headings and split the content
    chapter_pattern = r'(## Chapter \d+.*?)(?=## Chapter \d+|## Appendix|## References|$)'
    chapters = re.findall(chapter_pattern, content, re.DOTALL)
    
    # Add front matter (content before the first chapter) as chapter 0
    front_matter_pattern = r'^(.*?)(?=## Chapter \d+)'
    front_matter = re.search(front_matter_pattern, content, re.DOTALL)
    if front_matter:
        # Save front matter as chapter 0 (introduction)
        with open(f"{output_dir}/chapter_00_introduction.md", 'w', encoding='utf-8') as f:
            f.write(front_matter.group(1))
        print(f"Saved introduction to {output_dir}/chapter_00_introduction.md")
    
    # Save each chapter to a separate file
    for i, chapter in enumerate(chapters, 1):
        # Extract chapter number and title
        chapter_title_match = re.search(r'## Chapter (\d+)\s*(.*?)$', chapter, re.MULTILINE)
        if chapter_title_match:
            chapter_num = chapter_title_match.group(1)
            chapter_title = chapter_title_match.group(2).strip()
            # Create filename with chapter number and sanitized title
            sanitized_title = re.sub(r'[^\w\s-]', '', chapter_title).strip().replace(' ', '_').lower()
            if sanitized_title:
                filename = f"chapter_{chapter_num.zfill(2)}_{sanitized_title}.md"
            else:
                filename = f"chapter_{chapter_num.zfill(2)}.md"
        else:
            # Fallback if title extraction fails
            filename = f"chapter_{str(i).zfill(2)}.md"
        
        # Write chapter to file
        with open(f"{output_dir}/{filename}", 'w', encoding='utf-8') as f:
            f.write(chapter)
        print(f"Saved chapter {i} to {output_dir}/{filename}")
    
    # Extract and save appendices
    appendix_pattern = r'(## Appendix\s*[A-K].*?)(?=## Appendix|## References|## Index|$)'
    appendices = re.findall(appendix_pattern, content, re.DOTALL)
    
    for i, appendix in enumerate(appendices):
        # Extract appendix letter and title
        appendix_title_match = re.search(r'## Appendix\s*([A-K])\s*(.*?)$', appendix, re.MULTILINE)
        if appendix_title_match:
            appendix_letter = appendix_title_match.group(1)
            appendix_title = appendix_title_match.group(2).strip()
            # Create filename with appendix letter and sanitized title
            sanitized_title = re.sub(r'[^\w\s-]', '', appendix_title).strip().replace(' ', '_').lower()
            if sanitized_title:
                filename = f"appendix_{appendix_letter}_{sanitized_title}.md"
            else:
                filename = f"appendix_{appendix_letter}.md"
        else:
            # Fallback if title extraction fails
            filename = f"appendix_{chr(65+i)}.md"  # A, B, C, ...
        
        # Write appendix to file
        with open(f"{output_dir}/{filename}", 'w', encoding='utf-8') as f:
            f.write(appendix)
        print(f"Saved appendix {appendix_letter if 'appendix_letter' in locals() else chr(65+i)} to {output_dir}/{filename}")
    
    # Extract and save references
    references_pattern = r'(## References.*?)(?=## Appendix|## Index|$)'
    references_match = re.search(references_pattern, content, re.DOTALL)
    if references_match:
        with open(f"{output_dir}/references.md", 'w', encoding='utf-8') as f:
            f.write(references_match.group(1))
        print(f"Saved references to {output_dir}/references.md")
    
    # Extract and save index
    index_pattern = r'(## Index.*?)$'
    index_match = re.search(index_pattern, content, re.DOTALL)
    if index_match:
        with open(f"{output_dir}/index.md", 'w', encoding='utf-8') as f:
            f.write(index_match.group(1))
        print(f"Saved index to {output_dir}/index.md")
    
    print(f"\nSuccessfully split document into {len(chapters)} chapters, {len(appendices)} appendices, references, and index in {output_dir}")

if __name__ == "__main__":
    # Define paths
    input_file = "data/output/markdown/as_docling.md"
    output_dir = "data/output/markdown/adaptive_school_sourcebook"
    
    print(f"Splitting document {input_file} into chapters, appendices, references, and index...")
    split_document_by_sections(input_file, output_dir)
