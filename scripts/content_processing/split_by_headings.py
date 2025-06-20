#!/usr/bin/env python3
"""
Script to split a markdown document into separate files at every ## heading.
"""

import os
import re
import sys

def split_document_by_headings(input_file, output_dir):
    """
    Split a markdown document into separate files at every ## heading.
    
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
    
    # Find all ## headings and their positions
    heading_pattern = r'(?m)^## (.+)$'
    headings = [(m.group(1).strip(), m.start()) for m in re.finditer(heading_pattern, content)]
    
    # Add end of file as the last position
    positions = [pos for _, pos in headings] + [len(content)]
    
    # Extract content before the first heading (if any)
    if headings and headings[0][1] > 0:
        front_matter = content[:headings[0][1]].strip()
        if front_matter:
            with open(f"{output_dir}/00_front_matter.md", 'w', encoding='utf-8') as f:
                f.write(front_matter)
            print(f"Saved front matter to {output_dir}/00_front_matter.md")
    
    # Extract and save each section
    for i in range(len(headings)):
        heading_text = headings[i][0]
        start_pos = headings[i][1]
        end_pos = positions[i + 1]
        
        # Extract section content (including the heading)
        section_content = content[start_pos:end_pos].strip()
        
        # Create a sanitized filename
        sanitized_heading = re.sub(r'[^\w\s-]', '', heading_text).strip().replace(' ', '_').lower()
        if not sanitized_heading:
            sanitized_heading = f"section_{i+1}"
        
        # Add a number prefix to keep files in order
        filename = f"{i+1:02d}_{sanitized_heading}.md"
        
        # Write section to file
        with open(f"{output_dir}/{filename}", 'w', encoding='utf-8') as f:
            f.write(section_content)
        print(f"Saved section '{heading_text}' to {output_dir}/{filename}")
    
    print(f"\nSuccessfully split document into {len(headings)} sections in {output_dir}")

if __name__ == "__main__":
    # Define paths
    input_file = "data/output/markdown/cc_docling.md"
    output_dir = "data/output/markdown/cognitive_coaching_sections"
    
    print(f"Splitting document {input_file} into sections at every ## heading...")
    split_document_by_headings(input_file, output_dir)
