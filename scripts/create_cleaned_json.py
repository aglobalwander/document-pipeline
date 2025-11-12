#!/usr/bin/env python3
"""
Create JSON in the same format as docling output, but from cleaned markdown.
"""
import json
from pathlib import Path


def main():
    input_file = Path('data/output/markdown/SAS Board Policy Manual_2023.09.27_docling_cleaned.md')
    output_file = Path('data/output/json/SAS Board Policy Manual_2023.09.27_docling_cleaned.json')

    print(f"Reading: {input_file}")
    content = input_file.read_text(encoding='utf-8')

    # Create JSON in same format as original docling output
    document = {
        "metadata": {
            "filename": "SAS Board Policy Manual_2023.09.27.pdf",
            "num_pages": 435,
            "processing": {
                "method": "enhanced_docling",
                "cleaned": True,
                "fixes_applied": [
                    "OCR error corrections (267 fixes)",
                    "HTML entity decoding (24 fixes)",
                    "Missing section headers (280 fixes)",
                    "Excessive blank line removal",
                    "Character encoding fixes"
                ]
            }
        },
        "content": content
    }

    print(f"Writing: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    # Get file size
    file_size_kb = output_file.stat().st_size / 1024

    print(f"\nJSON created successfully!")
    print(f"  File size: {file_size_kb:.1f} KB")
    print(f"  Content length: {len(content):,} characters")


if __name__ == '__main__':
    main()
