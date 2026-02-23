#!/usr/bin/env python3
"""
Extract Common Core ELA standards from text files to match existing standard.csv format.
Creates CSV files for import into Drupal that follow the exact format of the existing system.
"""

import re
import csv
import json
import uuid
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


def generate_drupal_uuid() -> str:
    """Generate a UUID in the format used by Drupal."""
    return str(uuid.uuid4())


def extract_ela_standards(file_path: Path) -> List[Dict]:
    """Extract ELA standards from Common Core document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    # Current context tracking
    current_strand = None
    current_grade = None
    current_domain = None
    current_cluster = None
    
    # Strand mappings
    strand_mapping = {
        'RL': 'Reading Literature',
        'RI': 'Reading Informational Text', 
        'RF': 'Reading Foundational Skills',
        'W': 'Writing',
        'SL': 'Speaking and Listening',
        'L': 'Language',
        'RST': 'Reading Science and Technical Subjects',
        'RH': 'Reading History/Social Studies',
        'WHST': 'Writing History/Science/Technical Subjects'
    }
    
    # Grade level patterns
    grade_patterns = [
        r'Kindergartners?:',
        r'Grade (\d+) students?:',
        r'Grades? (\d+)-(\d+):',
        r'Grades? (\d+)–(\d+):',
        r'K–5', r'6–12', r'9-10', r'11-12'
    ]
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detect strand headers
        strand_match = re.match(r'^([A-Z]+)\s*$', line)
        if strand_match and strand_match.group(1) in strand_mapping:
            current_strand = strand_match.group(1)
            i += 1
            continue
        
        # Detect strand in section headers
        for strand_code, strand_name in strand_mapping.items():
            if strand_name in line and 'Standards' in line:
                current_strand = strand_code
                # Extract grade level from header
                grade_match = re.search(r'K–5|6–12|9-10|11-12', line)
                if grade_match:
                    current_grade = grade_match.group()
                break
        
        # Detect grade levels
        for pattern in grade_patterns:
            grade_match = re.match(pattern, line)
            if grade_match:
                if 'Kindergarten' in line:
                    current_grade = 'K'
                elif grade_match.groups():
                    current_grade = grade_match.group(1)
                break
        
        # Detect domain/cluster headers
        domain_match = re.match(r'^([A-Z][a-z\s]+[A-Z]?[a-z]*)\s*$', line)
        if domain_match and len(line) < 50 and any(word in line for word in ['Key Ideas', 'Craft', 'Integration', 'Range', 'Text Types', 'Production', 'Research', 'Comprehension', 'Collaboration', 'Presentation', 'Conventions', 'Knowledge', 'Vocabulary']):
            current_domain = domain_match.group(1).strip()
            i += 1
            continue
        
        # Detect standards (numbered statements)
        standard_match = re.match(r'^(\d+)\.\s*(.+)', line)
        if standard_match and current_strand and current_grade:
            standard_num = standard_match.group(1)
            standard_text = standard_match.group(2).strip()
            
            # Collect continuation lines
            j = i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r'^\d+\.', lines[j].strip()) and not any(pat in lines[j] for pat in ['Grade', 'Kindergarten', 'students:']):
                if not re.match(r'^[A-Z][a-z\s]+[A-Z]?[a-z]*\s*$', lines[j].strip()) or len(lines[j].strip()) > 50:
                    standard_text += " " + lines[j].strip()
                else:
                    break
                j += 1
            
            # Create standard code
            if current_grade == 'K':
                standard_code = f"CCSS.ELA-LITERACY.{current_strand}.K.{standard_num}"
            elif '-' in current_grade or '–' in current_grade:
                standard_code = f"CCSS.ELA-LITERACY.{current_strand}.{current_grade}.{standard_num}"
            else:
                standard_code = f"CCSS.ELA-LITERACY.{current_strand}.{current_grade}.{standard_num}"
            
            standard_entry = {
                'id': generate_unique_id(f"{standard_code}_{standard_text}", 'ELA_'),
                'code': standard_code,
                'title': f"{standard_code}: {standard_text[:100]}..." if len(standard_text) > 100 else f"{standard_code}: {standard_text}",
                'description': standard_text,
                'strand': current_strand,
                'strand_name': strand_mapping.get(current_strand, current_strand),
                'grade': current_grade,
                'domain': current_domain or '',
                'number': standard_num,
                'framework': 'Common Core ELA'
            }
            
            standards.append(standard_entry)
            i = j - 1
        
        i += 1
    
    return standards


def create_drupal_hierarchy(standards: List[Dict]) -> List[Dict]:
    """Create hierarchy entries for Drupal."""
    hierarchy_entries = []
    
    # Group by strand and grade for hierarchy
    strands = {}
    grades = {}
    
    for std in standards:
        strand_key = std['strand']
        grade_key = std['grade']
        
        if strand_key not in strands:
            strands[strand_key] = {
                'name': std['strand_name'],
                'code': strand_key,
                'count': 0
            }
        strands[strand_key]['count'] += 1
        
        if grade_key not in grades:
            grades[grade_key] = {'count': 0}
        grades[grade_key]['count'] += 1
    
    # Create strand hierarchy entries
    for strand_code, strand_data in strands.items():
        hierarchy_entries.append({
            'uuid': f"ccela-strand-{strand_code.lower()}",
            'title': f"{strand_data['name']} ({strand_code})",
            'field_standards_framework': 'common_core_ela',
            'field_standards_taxonomy': 'strand',
            'field_org_level_1': strand_data['name'],
            'status': 'TRUE'
        })
    
    # Create grade-level hierarchy entries  
    for grade, grade_data in grades.items():
        hierarchy_entries.append({
            'uuid': f"ccela-grade-{grade.lower().replace('–', '-').replace('-', '_')}",
            'title': f"Grade {grade}",
            'field_standards_framework': 'common_core_ela',
            'field_standards_taxonomy': 'grade_level',
            'field_org_level_2': f"Grade {grade}",
            'status': 'TRUE'
        })
    
    return hierarchy_entries


def process_ela_standards(input_file: Path, output_dir: Path):
    """Process ELA standards and create Drupal-ready files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Extracting Common Core ELA standards...")
    standards = extract_ela_standards(input_file)
    print(f"Found {len(standards)} standards")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy
    hierarchy_entries = create_drupal_hierarchy(standards)
    
    # Write hierarchy CSV
    hierarchy_file = output_dir / 'ela_cc_hierarchy_additions.csv'
    hierarchy_fieldnames = [
        'uuid', 'title', 'field_standards_framework', 'field_standards_taxonomy',
        'field_org_level_1', 'field_org_level_2', 'status'
    ]
    
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hierarchy_fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards CSV
    standards_file = output_dir / 'ela_cc_standards_drupal.csv'
    standards_fieldnames = [
        'uuid', 'title', 'body/value', 'field_framework', 'field_strand',
        'field_grade', 'field_domain', 'field_standard_code', 'field_number'
    ]
    
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=standards_fieldnames)
        writer.writeheader()
        
        for std in standards:
            writer.writerow({
                'uuid': f"ccela-{std['id']}",
                'title': std['title'],
                'body/value': f"<p>{std['description']}</p>",
                'field_framework': 'Common Core ELA',
                'field_strand': std['strand_name'],
                'field_grade': std['grade'],
                'field_domain': std['domain'],
                'field_standard_code': std['code'],
                'field_number': std['number']
            })
    
    # Create summary
    strands = {}
    grades = {}
    for std in standards:
        strand = std['strand_name']
        grade = std['grade']
        if strand not in strands:
            strands[strand] = 0
        strands[strand] += 1
        if grade not in grades:
            grades[grade] = 0
        grades[grade] += 1
    
    summary = {
        'total_standards': len(standards),
        'hierarchy_entries_created': len(hierarchy_entries),
        'strands': strands,
        'grades': grades
    }
    
    with open(output_dir / 'ela_cc_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Standards mapped: {len(standards)}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/common_core/CCSSI_ELA Standards_output.txt")
    output_dir = Path("data/output/drupal_prep/01_ela_common_core")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    process_ela_standards(input_file, output_dir)


if __name__ == "__main__":
    main()