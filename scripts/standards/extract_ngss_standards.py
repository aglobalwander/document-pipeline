#!/usr/bin/env python3
"""
Extract NGSS (Next Generation Science Standards) and map to Drupal's 4-level hierarchy.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


# NGSS Framework ID from your data
FRAMEWORK_ID = '14784'

# Standard taxonomy type IDs
TAXONOMY_TYPES = {
    'topic': '16468',      # Using Anchor Standard for topics
    'dci': '16469',        # Using Standard for disciplinary core ideas
    'standard': '16470'    # Using Substandard for individual performance expectations
}

# Grade level mappings
GRADE_LEVELS = {
    'K': 'Kindergarten',
    '1': 'Grade 1',
    '2': 'Grade 2', 
    '3': 'Grade 3',
    '4': 'Grade 4',
    '5': 'Grade 5',
    'MS': 'Middle School',
    'HS': 'High School'
}

# DCI Category mappings
DCI_CATEGORIES = {
    'PS': 'Physical Sciences',
    'LS': 'Life Sciences',
    'ESS': 'Earth and Space Sciences',
    'ETS': 'Engineering, Technology, and Applications of Science'
}

# Extract full DCI names from the document
DCI_NAMES = {
    'PS1': 'Matter and Its Interactions',
    'PS2': 'Motion and Stability: Forces and Interactions',
    'PS3': 'Energy',
    'PS4': 'Waves and Their Applications in Technologies for Information Transfer',
    'LS1': 'From Molecules to Organisms: Structures and Processes',
    'LS2': 'Ecosystems: Interactions, Energy, and Dynamics',
    'LS3': 'Heredity: Inheritance and Variation of Traits',
    'LS4': 'Biological Evolution: Unity and Diversity',
    'ESS1': "Earth's Place in the Universe",
    'ESS2': "Earth's Systems",
    'ESS3': 'Earth and Human Activity',
    'ETS1': 'Engineering Design',
    'ETS2': 'Links Among Engineering, Technology, Science, and Society'
}


def extract_ngss_standards(file_path: Path) -> List[Dict]:
    """Extract NGSS performance expectations from text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    # Pattern for NGSS codes: K-PS2-1, 1-LS1-1, MS-PS1-1, HS-ESS1-1
    pe_pattern = re.compile(r'^([K\d]+|MS|HS)-(PS|LS|ESS|ETS)(\d+)-(\d+)\.\s*(.+)')
    
    current_topic = None
    current_grade = None
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and page markers
        if not line or line.startswith('==='):
            i += 1
            continue
        
        # Detect topic headers (e.g., "K.Forces and Interactions: Pushes and Pulls")
        topic_match = re.match(r'^([K\d]+|MS|HS)\.(.+)$', line)
        if topic_match and not pe_pattern.match(line):
            grade = topic_match.group(1)
            topic = topic_match.group(2).strip()
            current_grade = grade
            current_topic = topic
        
        # Extract performance expectations
        pe_match = pe_pattern.match(line)
        if pe_match:
            grade = pe_match.group(1)
            dci_category = pe_match.group(2)
            dci_number = pe_match.group(3)
            pe_number = pe_match.group(4)
            text = pe_match.group(5).strip()
            
            # Continue reading if text spans multiple lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Stop if we hit a new PE, clarification, or assessment boundary
                if (not next_line or 
                    pe_pattern.match(next_line) or
                    next_line.startswith('[Clarification') or
                    next_line.startswith('[Assessment') or
                    next_line.startswith('The performance') or
                    next_line.startswith('*The performance') or
                    'Science and Engineering Practices' in next_line or
                    'Disciplinary Core Ideas' in next_line or
                    'Crosscutting Concepts' in next_line):
                    break
                # Skip certain lines
                if ('©' in next_line or 'Achieve, Inc.' in next_line or 
                    re.match(r'^\d+ of \d+$', next_line)):
                    j += 1
                    continue
                text += ' ' + next_line
                j += 1
            
            # Extract clarification statement and assessment boundary if present
            clarification = ''
            assessment_boundary = ''
            
            # Look for clarification and assessment boundary
            k = j
            while k < min(j + 10, len(lines)):
                check_line = lines[k].strip()
                if check_line.startswith('[Clarification Statement:'):
                    clarification = check_line
                    m = k + 1
                    while m < len(lines) and not lines[m].strip().startswith('[') and lines[m].strip():
                        clarification += ' ' + lines[m].strip()
                        m += 1
                    clarification = clarification.replace('[Clarification Statement:', '').replace(']', '').strip()
                elif check_line.startswith('[Assessment Boundary:'):
                    assessment_boundary = check_line
                    m = k + 1
                    while m < len(lines) and not lines[m].strip().startswith('[') and lines[m].strip():
                        assessment_boundary += ' ' + lines[m].strip()
                        m += 1
                    assessment_boundary = assessment_boundary.replace('[Assessment Boundary:', '').replace(']', '').strip()
                k += 1
            
            # Build full code and DCI
            full_code = f"{grade}-{dci_category}{dci_number}-{pe_number}"
            dci_code = f"{dci_category}{dci_number}"
            
            standard = {
                'code': full_code,
                'grade': grade,
                'dci_category': dci_category,
                'dci_code': dci_code,
                'dci_name': DCI_NAMES.get(dci_code, dci_code),
                'pe_number': pe_number,
                'text': text.strip(),
                'topic': current_topic or f"{dci_category} Standards",
                'clarification': clarification,
                'assessment_boundary': assessment_boundary
            }
            
            standards.append(standard)
            i = j - 1
        
        i += 1
    
    return standards


def create_hierarchy_entries(standards: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Create hierarchy entries for NGSS 4-level structure."""
    hierarchy_entries = []
    standard_entries = []
    
    created_hierarchies = {}
    hierarchy_id_counter = 53000  # Start after C3
    
    # Group standards
    grouped = {}
    for std in standards:
        grade_name = GRADE_LEVELS.get(std['grade'], std['grade'])
        dci_category_name = DCI_CATEGORIES.get(std['dci_category'], std['dci_category'])
        topic = std['topic']
        
        # Use topic as the main grouping
        key = (grade_name, topic)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(std)
    
    # Create hierarchy entries
    for (grade_name, topic), stds in grouped.items():
        # Level 1: Grade Level
        level1_key = f"NGSS_{grade_name}"
        if level1_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': grade_name,
                'description': f"NGSS Standards for {grade_name}",
                'parent_tid': '',
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level1_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level1_id = created_hierarchies[level1_key]
        
        # Level 2: Topic
        level2_key = f"{level1_key}_{topic[:30]}"
        if level2_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': topic,
                'description': '',
                'parent_tid': level1_id,
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level2_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level2_id = created_hierarchies[level2_key]
        
        # Group by DCI within topic for Level 3
        dci_groups = {}
        for std in stds:
            dci_key = (std['dci_code'], std['dci_name'])
            if dci_key not in dci_groups:
                dci_groups[dci_key] = []
            dci_groups[dci_key].append(std)
        
        for (dci_code, dci_name), dci_stds in dci_groups.items():
            # Level 3: DCI
            level3_key = f"{level2_key}_{dci_code}"
            if level3_key not in created_hierarchies:
                hierarchy_entries.append({
                    'ID': hierarchy_id_counter,
                    'name': f"{dci_code}: {dci_name}",
                    'description': '',
                    'parent_tid': level2_id,
                    'field_associated_framework': FRAMEWORK_ID
                })
                created_hierarchies[level3_key] = hierarchy_id_counter
                hierarchy_id_counter += 1
            level3_id = created_hierarchies[level3_key]
            
            # Level 4: Individual Performance Expectations
            for std in dci_stds:
                std_uuid = f"ngss-{std['code'].lower()}"
                
                # Build body with clarification and assessment boundary
                body_html = f"<p>{std['text']}</p>"
                if std['clarification']:
                    body_html += f"\n<p><strong>Clarification Statement:</strong> {std['clarification']}</p>"
                if std['assessment_boundary']:
                    body_html += f"\n<p><strong>Assessment Boundary:</strong> {std['assessment_boundary']}</p>"
                
                standard_entry = {
                    'uuid': std_uuid,
                    'title': std['code'],
                    'body/format': 'basic_html',
                    'body/value': body_html,
                    'field_standards_framework': FRAMEWORK_ID,
                    'field_standards_hierarchy': level3_id,
                    'field_standards_taxonomy': TAXONOMY_TYPES['standard'],
                    'field_org_level_1': grade_name,
                    'field_org_level_2': topic,
                    'field_org_level_3': f"{dci_code}: {dci_name}",
                    'field_standard_ref': std['code'],
                    'field_dci': dci_code,  # Add DCI field
                    'status': 'TRUE'
                }
                
                standard_entries.append(standard_entry)
    
    return hierarchy_entries, standard_entries


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/ngss_2/AllTopic_output.txt")
    output_dir = Path("data/output/drupal_prep/04_ngss")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract standards
    print("Extracting NGSS performance expectations...")
    standards = extract_ngss_standards(input_file)
    print(f"Found {len(standards)} performance expectations")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy and standard entries
    hierarchy_entries, standard_entries = create_hierarchy_entries(standards)
    
    # Write hierarchy additions
    hierarchy_file = output_dir / 'ngss_hierarchy_additions.csv'
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'name', 'description', 'parent_tid', 
                                               'field_associated_framework'])
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards
    standards_file = output_dir / 'ngss_standards_drupal.csv'
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['uuid', 'title', 'body/format', 'body/value', 'field_standards_framework',
                     'field_standards_hierarchy', 'field_standards_taxonomy', 'field_org_level_1',
                     'field_org_level_2', 'field_org_level_3', 'field_standard_ref', 'field_dci', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(standard_entries)
    
    # Create summary
    grade_counts = {}
    dci_counts = {}
    for std in standards:
        grade = std['grade']
        dci = std['dci_code']
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
        dci_counts[dci] = dci_counts.get(dci, 0) + 1
    
    summary = {
        'total_standards': len(standard_entries),
        'hierarchy_entries_created': len(hierarchy_entries),
        'grade_levels': list(GRADE_LEVELS.values()),
        'standards_by_grade': grade_counts,
        'standards_by_dci': dci_counts
    }
    
    with open(output_dir / 'ngss_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Standards mapped: {len(standard_entries)}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


if __name__ == "__main__":
    main()