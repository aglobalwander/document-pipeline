#!/usr/bin/env python3
"""
Script to split the Cognitive Coaching markdown document into separate files by parts, chapters, and appendices.
"""

import os
import re
import sys

def split_cognitive_coaching_document(input_file, output_dir):
    """
    Split the Cognitive Coaching markdown document into separate files.
    
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
    
    # Extract front matter (everything before PART 1)
    front_matter_pattern = r'^(.*?)(?=## PART 1)'
    front_matter = re.search(front_matter_pattern, content, re.DOTALL)
    if front_matter:
        with open(f"{output_dir}/00_front_matter.md", 'w', encoding='utf-8') as f:
            f.write(front_matter.group(1))
        print(f"Saved front matter to {output_dir}/00_front_matter.md")
    
    # Extract parts and their chapters
    part_pattern = r'(## PART \d+.*?)(?=## PART \d+|## APPENDICES|## Conclusion|$)'
    parts = re.findall(part_pattern, content, re.DOTALL)
    
    for i, part in enumerate(parts, 1):
        # Extract part number and title
        part_title_match = re.search(r'## PART (\d+): (.*?)$', part, re.MULTILINE)
        if part_title_match:
            part_num = part_title_match.group(1)
            part_title = part_title_match.group(2).strip()
            # Create filename with part number and sanitized title
            sanitized_title = re.sub(r'[^\w\s-]', '', part_title).strip().replace(' ', '_').lower()
            part_filename = f"part_{part_num.zfill(2)}_{sanitized_title}.md"
        else:
            part_filename = f"part_{str(i).zfill(2)}.md"
        
        # Write part to file
        with open(f"{output_dir}/{part_filename}", 'w', encoding='utf-8') as f:
            f.write(part)
        print(f"Saved part {i} to {output_dir}/{part_filename}")
        
        # Extract chapters within this part
        chapter_pattern = r'(## \d+ .*?)(?=## \d+|## PART|## APPENDICES|## Conclusion|$)'
        chapters = re.findall(chapter_pattern, part, re.DOTALL)
        
        for chapter in chapters:
            # Extract chapter number and title
            chapter_title_match = re.search(r'## (\d+) (.*?)$', chapter, re.MULTILINE)
            if chapter_title_match:
                chapter_num = chapter_title_match.group(1)
                chapter_title = chapter_title_match.group(2).strip()
                # Create filename with chapter number and sanitized title
                sanitized_title = re.sub(r'[^\w\s-]', '', chapter_title).strip().replace(' ', '_').lower()
                if sanitized_title:
                    chapter_filename = f"chapter_{chapter_num.zfill(2)}_{sanitized_title}.md"
                else:
                    chapter_filename = f"chapter_{chapter_num.zfill(2)}.md"
            else:
                continue  # Skip if we can't extract chapter info
            
            # Write chapter to file
            with open(f"{output_dir}/{chapter_filename}", 'w', encoding='utf-8') as f:
                f.write(chapter)
            print(f"Saved chapter {chapter_num} to {output_dir}/{chapter_filename}")
    
    # Extract conclusion
    conclusion_pattern = r'(## Conclusion.*?)(?=## APPENDICES|$)'
    conclusion = re.search(conclusion_pattern, content, re.DOTALL)
    if conclusion:
        with open(f"{output_dir}/conclusion.md", 'w', encoding='utf-8') as f:
            f.write(conclusion.group(1))
        print(f"Saved conclusion to {output_dir}/conclusion.md")
    
    # Extract appendices section
    appendices_pattern = r'(## APPENDICES.*?)$'
    appendices_section = re.search(appendices_pattern, content, re.DOTALL)
    if appendices_section:
        # Save the whole appendices section
        with open(f"{output_dir}/appendices.md", 'w', encoding='utf-8') as f:
            f.write(appendices_section.group(1))
        print(f"Saved appendices to {output_dir}/appendices.md")
        
        # Extract appendix list
        appendix_list_pattern = r'- ([A-G]) (.*?)$'
        appendix_list = re.findall(appendix_list_pattern, appendices_section.group(1), re.MULTILINE)
        
        # Create a combined file with all appendices
        with open(f"{output_dir}/all_appendices.md", 'w', encoding='utf-8') as f:
            f.write("# Appendices\n\n")
            for appendix_letter, appendix_title in appendix_list:
                f.write(f"## Appendix {appendix_letter}: {appendix_title}\n\n")
        print(f"Saved combined appendices to {output_dir}/all_appendices.md")
        
        # Also extract other sections from the appendices
        glossary_pattern = r'Glossary of Terms(.*?)(?=References|$)'
        glossary = re.search(glossary_pattern, appendices_section.group(1), re.DOTALL)
        if glossary:
            with open(f"{output_dir}/glossary.md", 'w', encoding='utf-8') as f:
                f.write("# Glossary of Terms\n\n" + glossary.group(1))
            print(f"Saved glossary to {output_dir}/glossary.md")
        
        references_pattern = r'References(.*?)(?=About the Authors|$)'
        references = re.search(references_pattern, appendices_section.group(1), re.DOTALL)
        if references:
            with open(f"{output_dir}/references.md", 'w', encoding='utf-8') as f:
                f.write("# References\n\n" + references.group(1))
            print(f"Saved references to {output_dir}/references.md")
        
        about_authors_pattern = r'About the Authors(.*?)(?=## Tables and Figures|$)'
        about_authors = re.search(about_authors_pattern, appendices_section.group(1), re.DOTALL)
        if about_authors:
            with open(f"{output_dir}/about_authors.md", 'w', encoding='utf-8') as f:
                f.write("# About the Authors\n\n" + about_authors.group(1))
            print(f"Saved about authors to {output_dir}/about_authors.md")
        
        tables_figures_pattern = r'## Tables and Figures(.*?)$'
        tables_figures = re.search(tables_figures_pattern, appendices_section.group(1), re.DOTALL)
        if tables_figures:
            with open(f"{output_dir}/tables_and_figures.md", 'w', encoding='utf-8') as f:
                f.write("# Tables and Figures\n\n" + tables_figures.group(1))
            print(f"Saved tables and figures to {output_dir}/tables_and_figures.md")

if __name__ == "__main__":
    # Define paths
    input_file = "data/output/markdown/cc_docling.md"
    output_dir = "data/output/markdown/cognitive_coaching"
    
    print(f"Splitting document {input_file} into parts, chapters, and appendices...")
    split_cognitive_coaching_document(input_file, output_dir)
