#!/usr/bin/env python3
"""
Fix markdown formatting issues in the converted Board Policy Manual.
"""
import re
import sys

def fix_markdown(content):
    """Fix all identified formatting issues."""

    # Fix OCR errors
    content = re.sub(r'Last editedE September IUc IOIC', 'Last edited: September 27, 2023', content)
    content = re.sub(r'Last edited: September IUc IOIC', 'Last edited: September 27, 2023', content)

    # Fix incorrect apostrophes and quotes (common OCR errors)
    content = content.replace('Õ', "'")  # Replace incorrect apostrophe
    content = content.replace('È', '"')  # Replace incorrect quote
    content = content.replace('É', '"')  # Replace incorrect quote

    # Fix HTML entities
    content = content.replace('&amp;', '&')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')

    # Standardize section symbols - keep original symbols as they appear to be intentional
    # § for adopted policies, ∞ for others

    # Fix missing section headers (lines that look like headers but aren't marked)
    # Match lines that are all caps or look like headers but don't have ##
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip if already a header
        if stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # Check if this looks like a missing header
        # Pattern: Short line (< 80 chars), Title Case or ALL CAPS, not in a list
        if (len(stripped) > 0 and
            len(stripped) < 80 and
            not stripped.startswith(('- ', '* ', '∞', '§', '|')) and
            not stripped[0].isdigit() and
            (stripped.isupper() or (stripped[0].isupper() and ' ' in stripped))):

            # Check context - if previous line is blank and next line is content, likely a header
            prev_blank = i == 0 or lines[i-1].strip() == ''
            next_has_content = i < len(lines) - 1 and lines[i+1].strip() != ''

            # Special case: Section numbers like "8.80 Student Employment by the School"
            if re.match(r'^\d+\.\d+\s+[A-Z]', stripped):
                fixed_lines.append(f'## {stripped}')
                continue

        fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    # Clean up excessive blank lines (more than 2 consecutive)
    content = re.sub(r'\n\n\n+', '\n\n', content)

    # Fix broken table structures - simplify complex tables
    # Tables with duplicate columns need manual review, but we can clean up obvious issues
    content = re.sub(r'\|\s*\|\s*\|', '|', content)  # Remove empty table cells

    return content


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'data/output/markdown/SAS Board Policy Manual_2023.09.27_docling.md'
    output_file = input_file.replace('.md', '_cleaned.md')

    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Fixing formatting issues...")
    fixed_content = fix_markdown(content)

    print(f"Writing: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

    print("Done! Created cleaned version.")

    # Report statistics
    original_lines = len(content.split('\n'))
    fixed_lines = len(fixed_content.split('\n'))

    print(f"\nStatistics:")
    print(f"  Original lines: {original_lines}")
    print(f"  Fixed lines: {fixed_lines}")
    print(f"  OCR apostrophe fixes: {content.count('Õ')}")
    print(f"  HTML entity fixes: {content.count('&amp;')}")


if __name__ == '__main__':
    main()
