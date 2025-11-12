#!/usr/bin/env python3
"""
Convert cleaned markdown to structured JSON format.
"""
import json
import re
from pathlib import Path


def parse_markdown_to_json(content):
    """Parse markdown content into structured JSON."""

    lines = content.split('\n')

    # Document structure
    document = {
        "title": "Shanghai American School Policy Manual",
        "last_revised": "September 27, 2023",
        "sections": [],
        "metadata": {
            "source": "SAS Board Policy Manual_2023.09.27.pdf",
            "format": "markdown",
            "conversion_method": "enhanced_docling",
            "processed": True,
            "cleaned": True
        }
    }

    current_section = None
    current_subsection = None
    current_policy = None
    current_content = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines when accumulating content
        if not stripped:
            if current_content and current_content[-1] != '':
                current_content.append('')
            continue

        # Section header (e.g., "## Section 1.00 SCHOOL ESTABLISHMENT")
        section_match = re.match(r'^##\s+Section\s+(\d+\.\d+)\s+(.+)$', stripped)
        if section_match:
            # Save previous content
            if current_policy and current_content:
                current_policy['content'] = '\n'.join(current_content).strip()
                current_content = []

            # Create new section
            current_section = {
                "section_number": section_match.group(1),
                "section_title": section_match.group(2),
                "subsections": []
            }
            document["sections"].append(current_section)
            current_subsection = None
            current_policy = None
            continue

        # Subsection header (e.g., "## 1.10 School Governance")
        subsection_match = re.match(r'^##\s+(\d+\.\d+)\s+(.+)$', stripped)
        if subsection_match:
            # Save previous content
            if current_policy and current_content:
                current_policy['content'] = '\n'.join(current_content).strip()
                current_content = []

            # Create new subsection
            current_subsection = {
                "subsection_number": subsection_match.group(1),
                "subsection_title": subsection_match.group(2),
                "policies": []
            }

            if current_section:
                current_section["subsections"].append(current_subsection)
            current_policy = None
            continue

        # Policy item in list (e.g., "- § 1.101 Role of Articles of Association")
        policy_match = re.match(r'^-\s+([§∞])\s+(\d+\.\d+\w*)\s+(.+)$', stripped)
        if policy_match:
            # Save previous policy content
            if current_policy and current_content:
                current_policy['content'] = '\n'.join(current_content).strip()
                current_content = []

            # Create new policy
            symbol = policy_match.group(1)
            status = "adopted" if symbol == "§" else "pending"

            current_policy = {
                "policy_number": policy_match.group(2),
                "policy_title": policy_match.group(3),
                "status": status,
                "content": ""
            }

            if current_subsection:
                current_subsection["policies"].append(current_policy)
            continue

        # Special headers like "Adopted:", "Revised:", etc.
        if stripped in ["Adopted:", "Revised:", "Cross Reference:", "File:"]:
            if current_content and current_content[-1] != '':
                current_content.append('')
            current_content.append(f"**{stripped}**")
            continue

        # Table of contents markers - skip
        if stripped.startswith("Bold =") or stripped.startswith("* Italic ="):
            continue

        if stripped.startswith("Last revised:") or stripped.startswith("Last edited:"):
            continue

        # Regular content line
        current_content.append(stripped)

    # Save final content
    if current_policy and current_content:
        current_policy['content'] = '\n'.join(current_content).strip()

    return document


def main():
    input_file = Path('data/output/markdown/SAS Board Policy Manual_2023.09.27_docling_cleaned.md')
    output_file = Path('data/output/json/SAS Board Policy Manual_2023.09.27_docling_cleaned.json')

    print(f"Reading: {input_file}")
    content = input_file.read_text(encoding='utf-8')

    print("Parsing markdown to JSON...")
    document = parse_markdown_to_json(content)

    # Add statistics
    total_sections = len(document["sections"])
    total_subsections = sum(len(s["subsections"]) for s in document["sections"])
    total_policies = sum(
        len(sub["policies"])
        for s in document["sections"]
        for sub in s["subsections"]
    )

    document["metadata"]["statistics"] = {
        "total_sections": total_sections,
        "total_subsections": total_subsections,
        "total_policies": total_policies
    }

    print(f"Writing: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    print(f"\nStatistics:")
    print(f"  Total sections: {total_sections}")
    print(f"  Total subsections: {total_subsections}")
    print(f"  Total policies: {total_policies}")
    print(f"\nJSON file created successfully!")


if __name__ == '__main__':
    main()
