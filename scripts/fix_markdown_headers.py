#!/usr/bin/env python3
"""
Fix missing markdown headers for section numbers.
"""
import re

def fix_section_headers(content):
    """Add ## prefix to lines that are section headers but missing it."""
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Already a header, keep as is
        if stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # Check if this is a section number at the start of a line
        # Pattern: starts with digits.digits followed by space and text
        # Example: "7.10 Instructional Goals and Objectives"
        section_pattern = re.match(r'^(\d+\.\d+)\s+(.+)$', stripped)

        if section_pattern:
            # Check context to confirm it's not part of a list
            prev_line = lines[i-1].strip() if i > 0 else ''
            next_line = lines[i+1].strip() if i < len(lines) - 1 else ''

            # If previous line is blank or is a header/table boundary, this is likely a header
            is_header_context = (
                prev_line == '' or
                prev_line.startswith('#') or
                prev_line.startswith('|') or
                prev_line.startswith('*') or
                prev_line.startswith('Bold =')
            )

            # If next line is blank or starts with list/content, this is likely a header
            next_is_content = (
                next_line == '' or
                next_line.startswith('-') or
                next_line.startswith('∞') or
                next_line.startswith('§') or
                not next_line[0].isdigit() if next_line else True
            )

            if is_header_context and next_is_content:
                # Add ## prefix
                fixed_lines.append(f'## {stripped}')
                continue

        # Keep line as is
        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def main():
    input_file = 'data/output/markdown/SAS Board Policy Manual_2023.09.27_docling_cleaned.md'

    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Fixing section headers...")
    fixed_content = fix_section_headers(content)

    print(f"Writing: {input_file}")
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

    # Count how many were fixed
    original_count = len([l for l in content.split('\n') if re.match(r'^\d+\.\d+\s+', l.strip())])
    fixed_count = len([l for l in fixed_content.split('\n') if re.match(r'^## \d+\.\d+\s+', l.strip())])

    print(f"\nFixed {fixed_count - original_count} section headers")
    print("Done!")


if __name__ == '__main__':
    main()
