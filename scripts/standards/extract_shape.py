#!/usr/bin/env python3
"""
Extract SHAPE America Physical Education standards from text files.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


def generate_unique_id(text: str, prefix: str = "") -> str:
    """Generate a unique ID based on text content."""
    hash_obj = hashlib.md5(text.encode())
    hash_str = hash_obj.hexdigest()[:8]
    return f"{prefix}{hash_str}"


def extract_shape_standards(file_path: Path) -> List[Dict]:
    """Extract SHAPE America PE standards from document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    # First extract the main standards (1-5)
    main_standards = {}
    current_standard = None
    current_grade_level = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detect main standards (e.g., "Standard 1. The physically literate individual...")
        main_standard_match = re.match(r'^Standard (\d+)\.\s*(.+)', line)
        if main_standard_match:
            standard_num = main_standard_match.group(1)
            standard_text = main_standard_match.group(2).strip()
            
            main_standards[standard_num] = {
                'number': standard_num,
                'title': f"Standard {standard_num}",
                'description': standard_text,
                'id': generate_unique_id(f"Standard_{standard_num}_{standard_text}", 'SHAPE_STD_')
            }
            current_standard = standard_num
        
        # Detect grade levels
        grade_match = re.match(r'^(Kindergarten|Grade \d+)$', line)
        if grade_match:
            current_grade_level = grade_match.group(1)
        
        # Detect outcome codes (e.g., "S1.E1.K", "S1.E1.1", etc.)
        outcome_match = re.match(r'^(S\d+\.E\d+(?:\.\w+)?)', line)
        if outcome_match and current_standard:
            outcome_code = outcome_match.group(1)
            
            # Parse the outcome code
            code_parts = outcome_code.split('.')
            if len(code_parts) >= 3:
                standard_part = code_parts[0]  # S1, S2, etc.
                element_part = code_parts[1]   # E1, E2, etc.
                grade_part = code_parts[2] if len(code_parts) > 2 else ''  # K, 1, 2, etc.
                
                standard_number = standard_part[1:]  # Remove 'S'
                element_number = element_part[1:]    # Remove 'E'
                
                # Get outcome text from next line(s)
                outcome_text = ""
                j = i + 1
                while j < len(lines) and j < i + 10:
                    next_line = lines[j].strip()
                    if next_line and not re.match(r'^S\d+\.E\d+', next_line) and not re.match(r'^(Kindergarten|Grade \d+)$', next_line) and not next_line.startswith('Standard') and not next_line.startswith('©'):
                        outcome_text += " " + next_line
                        j += 1
                    else:
                        break
                
                # Clean up the outcome text
                outcome_text = outcome_text.strip()
                # Remove parenthetical references like "(S1.E1.K)"
                outcome_text = re.sub(r'\([S]\d+\.E\d+\.\w+\)', '', outcome_text).strip()
                
                if outcome_text:
                    outcome_entry = {
                        'id': generate_unique_id(f"{outcome_code}_{outcome_text}", 'SHAPE_OUT_'),
                        'code': outcome_code,
                        'standard_number': standard_number,
                        'element_number': element_number,
                        'grade': grade_part,
                        'grade_level': current_grade_level or f"Grade {grade_part}" if grade_part.isdigit() else "Kindergarten" if grade_part == 'K' else grade_part,
                        'title': f"{outcome_code}: {outcome_text[:100]}..." if len(outcome_text) > 100 else f"{outcome_code}: {outcome_text}",
                        'description': outcome_text,
                        'framework': 'SHAPE America',
                        'type': 'Grade-Level Outcome'
                    }
                    
                    standards.append(outcome_entry)
                    i = j - 1
        
        i += 1
    
    # Add main standards to the list
    for std_num, std_data in main_standards.items():
        standard_entry = {
            'id': std_data['id'],
            'code': f"SHAPE.{std_num}",
            'standard_number': std_num,
            'title': std_data['title'],
            'description': std_data['description'],
            'framework': 'SHAPE America',
            'type': 'Standard'
        }
        standards.insert(0, standard_entry)  # Insert at beginning
    
    return standards


def create_drupal_hierarchy(standards: List[Dict]) -> List[Dict]:
    """Create hierarchy entries for Drupal."""
    hierarchy_entries = []
    
    # Group by standard and grade
    main_standards = {}
    grades = {}
    
    for std in standards:
        if std['type'] == 'Standard':
            main_standards[std['standard_number']] = std
        elif std['type'] == 'Grade-Level Outcome':
            grade = std.get('grade_level', '')
            if grade not in grades:
                grades[grade] = {'count': 0}
            grades[grade]['count'] += 1
    
    # Create standard hierarchy entries
    for std_num, std in main_standards.items():
        hierarchy_entries.append({
            'uuid': f"shape-standard-{std_num}",
            'title': f"SHAPE {std['title']}",
            'field_standards_framework': 'shape_america',
            'field_standards_taxonomy': 'standard',
            'field_org_level_1': std['title'],
            'status': 'TRUE'
        })
    
    # Create grade-level hierarchy entries
    for grade, grade_data in grades.items():
        if grade:
            grade_clean = grade.lower().replace(' ', '_').replace('kindergarten', 'k')
            hierarchy_entries.append({
                'uuid': f"shape-grade-{grade_clean}",
                'title': f"SHAPE {grade}",
                'field_standards_framework': 'shape_america',
                'field_standards_taxonomy': 'grade_level',
                'field_org_level_2': grade,
                'status': 'TRUE'
            })
    
    return hierarchy_entries


def process_shape_standards(input_file: Path, output_dir: Path):
    """Process SHAPE standards and create Drupal-ready files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Extracting SHAPE America PE standards...")
    standards = extract_shape_standards(input_file)
    print(f"Found {len(standards)} standards and outcomes")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy
    hierarchy_entries = create_drupal_hierarchy(standards)
    
    # Write hierarchy CSV
    hierarchy_file = output_dir / 'shape_hierarchy_additions.csv'
    hierarchy_fieldnames = [
        'uuid', 'title', 'field_standards_framework', 'field_standards_taxonomy',
        'field_org_level_1', 'field_org_level_2', 'status'
    ]
    
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hierarchy_fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards CSV
    standards_file = output_dir / 'shape_standards_drupal.csv'
    standards_fieldnames = [
        'uuid', 'title', 'body/value', 'field_framework', 'field_standard_number',
        'field_grade_level', 'field_outcome_code', 'field_type'
    ]
    
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=standards_fieldnames)
        writer.writeheader()
        
        for std in standards:
            writer.writerow({
                'uuid': f"shape-{std['id']}",
                'title': std['title'],
                'body/value': f"<p>{std['description']}</p>",
                'field_framework': 'SHAPE America',
                'field_standard_number': std['standard_number'],
                'field_grade_level': std.get('grade_level', ''),
                'field_outcome_code': std['code'],
                'field_type': std['type']
            })
    
    # Create summary
    main_standards_count = len([s for s in standards if s['type'] == 'Standard'])
    outcomes_count = len([s for s in standards if s['type'] == 'Grade-Level Outcome'])
    
    by_standard = {}
    by_grade = {}
    
    for std in standards:
        if std['type'] == 'Grade-Level Outcome':
            std_num = std['standard_number']
            grade = std.get('grade_level', 'Unknown')
            
            if std_num not in by_standard:
                by_standard[std_num] = 0
            by_standard[std_num] += 1
            
            if grade not in by_grade:
                by_grade[grade] = 0
            by_grade[grade] += 1
    
    summary = {
        'total_items': len(standards),
        'main_standards': main_standards_count,
        'grade_level_outcomes': outcomes_count,
        'hierarchy_entries_created': len(hierarchy_entries),
        'outcomes_by_standard': by_standard,
        'outcomes_by_grade': by_grade
    }
    
    with open(output_dir / 'shape_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Total items mapped: {len(standards)}")
    print(f"  Main standards: {main_standards_count}")
    print(f"  Grade-level outcomes: {outcomes_count}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/p.e_/Grade-Level-Outcomes-for-K-12-Physical-Education_output.txt")
    output_dir = Path("data/output/drupal_prep/08_shape")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    process_shape_standards(input_file, output_dir)


if __name__ == "__main__":
    main()