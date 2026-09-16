#!/usr/bin/env python3
"""
Extract ISTE standards from text files.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

from doc_processing.utils.ids import generate_unique_id


def extract_iste_standards(file_path: Path) -> List[Dict]:
    """Extract ISTE standards from document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    # Section mappings
    section_mapping = {
        'STUDENTS': 'Students',
        'EDUCATORS': 'Educators', 
        'EDUCATION LEADERS': 'Education Leaders',
        'COACHES': 'Coaches'
    }
    
    current_section = None
    current_standard = None
    current_standard_title = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detect section headers
        section_match = re.match(r'^SECTION \d+:\s*([A-Z\s]+)', line)
        if section_match:
            section_name = section_match.group(1).strip()
            if section_name in section_mapping:
                current_section = section_mapping[section_name]
            i += 1
            continue
        
        # Alternative section detection
        for section_key, section_name in section_mapping.items():
            if section_key in line and current_section != section_name:
                current_section = section_name
                break
        
        # Detect main standards (e.g., "1.1. Empowered Learner")
        main_standard_match = re.match(r'^(\d+)\.(\d+)\.\s+(.+)', line)
        if main_standard_match and current_section:
            standard_num = main_standard_match.group(1)
            sub_num = main_standard_match.group(2)
            standard_title = main_standard_match.group(3).strip()
            
            current_standard = f"{standard_num}.{sub_num}"
            current_standard_title = standard_title
            
            # Look for description on next lines
            description = ""
            j = i + 1
            while j < len(lines) and j < i + 10:
                next_line = lines[j].strip()
                if next_line and not re.match(r'^\d+\.\d+\.', next_line) and not next_line.endswith(':'):
                    description += " " + next_line
                    j += 1
                else:
                    break
            
            # Clean up description - stop at "Students:" or "Educators:" etc
            description = description.split(' Students:')[0].split(' Educators:')[0].split(' Education Leaders:')[0].split(' Coaches:')[0].strip()
            
            standard_entry = {
                'id': generate_unique_id(f"{current_standard}_{standard_title}", 'ISTE_'),
                'code': f"ISTE.{current_section.upper().replace(' ', '_')}.{current_standard}",
                'number': current_standard,
                'title': standard_title,
                'description': description,
                'section': current_section,
                'framework': 'ISTE',
                'indicators': []
            }
            
            standards.append(standard_entry)
            i = j - 1
        
        # Detect indicators (e.g., "1.1.a. articulate and set personal learning goals...")
        indicator_match = re.match(r'^(\d+)\.(\d+)\.([a-z])\.\s+(.+)', line)
        if indicator_match and current_section and current_standard:
            ind_num1 = indicator_match.group(1)
            ind_num2 = indicator_match.group(2)
            ind_letter = indicator_match.group(3)
            ind_text = indicator_match.group(4).strip()
            
            # Check if this indicator belongs to current standard
            if f"{ind_num1}.{ind_num2}" == current_standard:
                # Collect continuation lines
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    if next_line and not re.match(r'^\d+\.\d+\.', next_line) and not next_line.startswith('SECTION'):
                        ind_text += " " + next_line
                        j += 1
                    else:
                        break
                
                indicator_entry = {
                    'id': generate_unique_id(f"{current_standard}.{ind_letter}_{ind_text}", 'ISTE_IND_'),
                    'code': f"ISTE.{current_section.upper().replace(' ', '_')}.{current_standard}.{ind_letter}",
                    'number': f"{current_standard}.{ind_letter}",
                    'letter': ind_letter,
                    'text': ind_text,
                    'section': current_section,
                    'standard_title': current_standard_title,
                    'framework': 'ISTE'
                }
                
                # Add to the current standard's indicators
                if standards and standards[-1]['number'] == current_standard:
                    standards[-1]['indicators'].append(indicator_entry)
                
                # Also add as standalone indicator
                standards.append(indicator_entry)
                i = j - 1
        
        i += 1
    
    return standards


def create_drupal_hierarchy(standards: List[Dict]) -> List[Dict]:
    """Create hierarchy entries for Drupal."""
    hierarchy_entries = []
    
    # Group by section
    sections = {}
    main_standards = {}
    
    for std in standards:
        section = std['section']
        if section not in sections:
            sections[section] = {'count': 0}
        sections[section]['count'] += 1
        
        # Track main standards (not indicators)
        if 'indicators' in std:
            main_standards[std['number']] = std
    
    # Create section hierarchy entries
    for section, section_data in sections.items():
        hierarchy_entries.append({
            'uuid': f"iste-section-{section.lower().replace(' ', '_')}",
            'title': f"ISTE {section}",
            'field_standards_framework': 'iste',
            'field_standards_taxonomy': 'section',
            'field_org_level_1': section,
            'status': 'TRUE'
        })
    
    # Create main standard hierarchy entries
    for std_num, std in main_standards.items():
        hierarchy_entries.append({
            'uuid': f"iste-standard-{std_num.replace('.', '_')}",
            'title': f"{std_num}: {std['title']}",
            'field_standards_framework': 'iste',
            'field_standards_taxonomy': 'standard',
            'field_org_level_1': std['section'],
            'field_org_level_2': std['title'],
            'status': 'TRUE'
        })
    
    return hierarchy_entries


def process_iste_standards(input_file: Path, output_dir: Path):
    """Process ISTE standards and create Drupal-ready files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Extracting ISTE standards...")
    standards = extract_iste_standards(input_file)
    print(f"Found {len(standards)} standards and indicators")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy
    hierarchy_entries = create_drupal_hierarchy(standards)
    
    # Write hierarchy CSV
    hierarchy_file = output_dir / 'iste_hierarchy_additions.csv'
    hierarchy_fieldnames = [
        'uuid', 'title', 'field_standards_framework', 'field_standards_taxonomy',
        'field_org_level_1', 'field_org_level_2', 'status'
    ]
    
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hierarchy_fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards CSV
    standards_file = output_dir / 'iste_standards_drupal.csv'
    standards_fieldnames = [
        'uuid', 'title', 'body/value', 'field_framework', 'field_section',
        'field_standard_code', 'field_number', 'field_type'
    ]
    
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=standards_fieldnames)
        writer.writeheader()
        
        for std in standards:
            if 'indicators' in std:
                # Main standard
                description = std['description']
                if std['indicators']:
                    description += "<br><br><strong>Indicators:</strong><ul>"
                    for ind in std['indicators']:
                        description += f"<li>{ind['number']}: {ind['text']}</li>"
                    description += "</ul>"
                
                writer.writerow({
                    'uuid': f"iste-{std['id']}",
                    'title': f"{std['number']}: {std['title']}",
                    'body/value': f"<p>{description}</p>",
                    'field_framework': 'ISTE',
                    'field_section': std['section'],
                    'field_standard_code': std['code'],
                    'field_number': std['number'],
                    'field_type': 'Standard'
                })
            else:
                # Indicator
                writer.writerow({
                    'uuid': f"iste-{std['id']}",
                    'title': f"{std['number']}: {std['text'][:100]}..." if len(std['text']) > 100 else f"{std['number']}: {std['text']}",
                    'body/value': f"<p><strong>{std['standard_title']}</strong></p><p>{std['text']}</p>",
                    'field_framework': 'ISTE',
                    'field_section': std['section'],
                    'field_standard_code': std['code'],
                    'field_number': std['number'],
                    'field_type': 'Indicator'
                })
    
    # Create summary
    sections = {}
    main_standards = 0
    indicators = 0
    
    for std in standards:
        section = std['section']
        if section not in sections:
            sections[section] = {'main_standards': 0, 'indicators': 0}
        
        if 'indicators' in std:
            sections[section]['main_standards'] += 1
            main_standards += 1
        else:
            sections[section]['indicators'] += 1
            indicators += 1
    
    summary = {
        'total_items': len(standards),
        'main_standards': main_standards,
        'indicators': indicators,
        'hierarchy_entries_created': len(hierarchy_entries),
        'sections': sections
    }
    
    with open(output_dir / 'iste_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Standards and indicators mapped: {len(standards)}")
    print(f"  Main standards: {main_standards}")
    print(f"  Indicators: {indicators}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/iste/ISTE-Standards-One-Sheet_Combined_11-22-2021_vF4-1-4_output.txt")
    output_dir = Path("data/output/drupal_prep/06_iste")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    process_iste_standards(input_file, output_dir)


if __name__ == "__main__":
    main()