#!/usr/bin/env python3
"""
Map NCAS standards to Drupal's 4-level hierarchy structure.
Creates standards.csv with proper taxonomy references.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


# NCAS Subject to Framework ID mapping (from your standards_frameworks.csv)
FRAMEWORK_IDS = {
    'NCAS': '14786'
}

# NCAS Artistic Processes mapping to Level 1 hierarchy
ARTISTIC_PROCESSES = {
    'Cr': {'name': 'Creating', 'desc': 'Conceiving and developing new artistic ideas and work'},
    'Pr': {'name': 'Performing/Presenting/Producing', 'desc': 'Performing: Realizing artistic ideas and work through interpretation and presentation. Presenting: Interpreting and sharing artistic work. Producing: Realizing and presenting artistic ideas and work'},
    'Re': {'name': 'Responding', 'desc': 'Understanding and evaluating how the arts convey meaning'},
    'Cn': {'name': 'Connecting', 'desc': 'Relating artistic ideas and work with personal meaning and external context'}
}

# Grade level mappings
GRADE_LEVELS = {
    'PK': 'Pre-K',
    'K': 'Kindergarten',
    '1': '1st',
    '2': '2nd', 
    '3': '3rd',
    '4': '4th',
    '5': '5th',
    '6': '6th',
    '7': '7th',
    '8': '8th',
    'I': 'HS Proficient',
    'II': 'HS Accomplished',
    'III': 'HS Advanced'
}

# Standard taxonomy type IDs (from your standards_taxonomy.csv)
TAXONOMY_TYPES = {
    'anchor': '16468',  # Anchor Standard
    'standard': '16469',  # Standard
    'substandard': '16470'  # Substandard
}


def parse_standard_code(code: str) -> Dict:
    """Parse NCAS standard code into components.
    
    Example: DA:Cr1.1.PKa
    - DA = Dance (subject)
    - Cr = Creating (artistic process)
    - 1 = Anchor standard number
    - .1 = Component
    - PK = Grade level
    - a = Subcomponent
    """
    parts = code.split(':')
    if len(parts) != 2:
        return None
    
    subject = parts[0]
    remainder = parts[1]
    
    # Extract artistic process (2 letters)
    process = remainder[:2]
    
    # Split the rest
    rest = remainder[2:]
    
    # Parse anchor standard, component, grade level
    # Format: X.Y.GRADEz where X=anchor, Y=component, GRADE=grade level, z=subcomponent
    import re
    match = re.match(r'(\d+)\.(\d+)\.([A-Za-z0-9]+)([a-z])?', rest)
    
    if match:
        return {
            'subject': subject,
            'process': process,
            'anchor': match.group(1),
            'component': match.group(2),
            'grade': match.group(3),
            'subcomponent': match.group(4) or ''
        }
    
    return None


def get_subject_name(code: str) -> str:
    """Get full subject name from code."""
    mapping = {
        'DA': 'Dance',
        'MU': 'Music',
        'TH': 'Theatre',
        'VA': 'Visual Arts',
        'MA': 'Media Arts'
    }
    return mapping.get(code, code)


def create_hierarchy_entries(standards_data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Create hierarchy entries for the 4-level structure.
    Returns (hierarchy_entries, standard_entries)
    """
    hierarchy_entries = []
    standard_entries = []
    
    # Track what we've already created to avoid duplicates
    created_hierarchies = {}  # Dictionary to map keys to IDs
    hierarchy_id_counter = 50000  # Start with a high number to avoid conflicts
    
    # Group standards by subject and process
    grouped = {}
    for std in standards_data:
        parsed = parse_standard_code(std['code'])
        if not parsed:
            continue
        
        subject = get_subject_name(parsed['subject'])
        process = ARTISTIC_PROCESSES.get(parsed['process'], {}).get('name', parsed['process'])
        anchor_num = parsed['anchor']
        grade = GRADE_LEVELS.get(parsed['grade'], parsed['grade'])
        
        # Create grouping key
        key = (subject, process, anchor_num, grade)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(std)
    
    # Create hierarchy entries and map standards
    for (subject, process, anchor_num, grade), stds in grouped.items():
        # Level 1: Artistic Process (e.g., "Creating")
        level1_key = f"NCAS_{subject}_{process}"
        if level1_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': process,
                'description': ARTISTIC_PROCESSES.get(process[:2], {}).get('desc', ''),
                'parent_tid': '',
                'field_associated_framework': FRAMEWORK_IDS['NCAS']
            })
            created_hierarchies[level1_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level1_id = created_hierarchies[level1_key]
        
        # Level 2: Anchor Standard (e.g., "Anchor Standard 1")
        level2_key = f"{level1_key}_Anchor{anchor_num}"
        if level2_key not in created_hierarchies:
            # Find the anchor standard text from our data
            anchor_text = f"Anchor Standard {anchor_num}"
            for std in stds:
                if std.get('anchor_standard') == anchor_num:
                    # Could look up full anchor text from EU/EQ data if needed
                    break
            
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': f"Anchor Standard {anchor_num}",
                'description': '',
                'parent_tid': level1_id,
                'field_associated_framework': FRAMEWORK_IDS['NCAS']
            })
            created_hierarchies[level2_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level2_id = created_hierarchies[level2_key]
        
        # Level 3: Grade Level (e.g., "Kindergarten")
        level3_key = f"{level2_key}_{grade}"
        if level3_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': grade,
                'description': '',
                'parent_tid': level2_id,
                'field_associated_framework': FRAMEWORK_IDS['NCAS']
            })
            created_hierarchies[level3_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level3_id = created_hierarchies[level3_key]
        
        # Level 4: Individual Standards
        for std in stds:
            parsed = parse_standard_code(std['code'])
            
            # Generate a unique ID for the standard
            std_uuid = f"ncas-{subject.lower()}-{std['code'].lower().replace(':', '-')}"
            
            standard_entry = {
                'uuid': std_uuid,
                'title': std['code'],
                'body/format': 'basic_html',
                'body/value': f"<p>{std['text']}</p>",
                'field_standards_framework': FRAMEWORK_IDS['NCAS'],
                'field_standards_hierarchy': level3_id,
                'field_standards_taxonomy': TAXONOMY_TYPES['standard'],
                'field_org_level_1': process,
                'field_org_level_2': f"Anchor Standard {anchor_num}",
                'field_org_level_3': grade,
                'field_standard_ref': std['code'],
                'field_eu_references': std.get('eu_references', ''),
                'field_eq_references': std.get('eq_references', ''),
                'status': 'TRUE'
            }
            
            standard_entries.append(standard_entry)
    
    return hierarchy_entries, standard_entries


def main():
    """Main execution function."""
    input_file = Path("data/output/drupal_import/ncas/ncas_standards_with_refs.csv")
    output_dir = Path("data/output/drupal_import/ncas")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        print("Please run extract_ncas_eus_eqs.py first")
        return
    
    # Read standards data
    standards_data = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        standards_data = list(reader)
    
    print(f"Processing {len(standards_data)} NCAS standards...")
    
    # Create hierarchy and standard entries
    hierarchy_entries, standard_entries = create_hierarchy_entries(standards_data)
    
    # Write hierarchy additions
    hierarchy_file = output_dir / 'ncas_hierarchy_additions.csv'
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'name', 'description', 'parent_tid', 
                                               'field_associated_framework'])
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards
    standards_file = output_dir / 'ncas_standards_drupal.csv'
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['uuid', 'title', 'body/format', 'body/value', 'field_standards_framework',
                     'field_standards_hierarchy', 'field_standards_taxonomy', 'field_org_level_1',
                     'field_org_level_2', 'field_org_level_3', 'field_standard_ref',
                     'field_eu_references', 'field_eq_references', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(standard_entries)
    
    # Create summary
    summary = {
        'total_standards': len(standard_entries),
        'hierarchy_entries_created': len(hierarchy_entries),
        'subjects': list(set(s['field_org_level_1'] for s in standard_entries if s.get('field_org_level_1')))
    }
    
    with open(output_dir / 'ncas_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Standards mapped: {len(standard_entries)}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


if __name__ == "__main__":
    main()