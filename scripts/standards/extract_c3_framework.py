#!/usr/bin/env python3
"""
Extract C3 Framework standards and map to Drupal's 4-level hierarchy.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


# C3 Framework ID from your data
FRAMEWORK_ID = '14785'

# Standard taxonomy type IDs
TAXONOMY_TYPES = {
    'dimension': '16468',  # Using Anchor Standard for dimensions
    'discipline': '16469',  # Using Standard for disciplines
    'indicator': '16470'   # Using Substandard for individual indicators
}

# Grade band mappings
GRADE_BANDS = {
    'K-2': 'Grades K-2',
    '3-5': 'Grades 3-5',
    '6-8': 'Grades 6-8',
    '9-12': 'Grades 9-12'
}

# Dimension mappings
DIMENSIONS = {
    'D1': 'Dimension 1: Developing Questions & Planning Inquiries',
    'D2': 'Dimension 2: Applying Disciplinary Concepts and Tools',
    'D3': 'Dimension 3: Evaluating Sources & Using Evidence',
    'D4': 'Dimension 4: Communicating Conclusions & Taking Informed Action'
}

# Discipline mappings within D2
DISCIPLINES = {
    'Civ': 'Civics',
    'Eco': 'Economics',
    'Geo': 'Geography',
    'His': 'History'
}


def extract_c3_indicators(file_path: Path) -> List[Dict]:
    """Extract C3 Framework indicators from text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    indicators = []
    lines = content.split('\n')
    
    # Pattern for C3 indicators: D#.Discipline.#.Grade-Band
    # Examples: D1.1.K-2, D2.Civ.1.3-5, D3.1.6-8
    pattern = re.compile(r'^(D[1-4])(?:\.([A-Za-z]{3}))?\.(\d+)\.([K0-9]+-[0-9]+)\.\s*(.+)')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        match = pattern.match(line)
        if match:
            dimension = match.group(1)
            discipline = match.group(2) or ''  # Empty for D1, D3, D4
            indicator_num = match.group(3)
            grade_band = match.group(4)
            text = match.group(5)
            
            # Continue reading if text spans multiple lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Stop if we hit a new indicator or empty line
                if not next_line or pattern.match(next_line):
                    break
                # Skip page markers
                if next_line.startswith('===') or 'Framework' in next_line:
                    j += 1
                    continue
                text += ' ' + next_line
                j += 1
            
            # Clean up text
            text = re.sub(r'\s+', ' ', text).strip()
            text = text.replace('­ ', '')  # Remove soft hyphens
            
            # Build full code
            if discipline:
                full_code = f"{dimension}.{discipline}.{indicator_num}.{grade_band}"
            else:
                full_code = f"{dimension}.{indicator_num}.{grade_band}"
            
            indicator = {
                'code': full_code,
                'dimension': dimension,
                'discipline': discipline,
                'indicator_num': indicator_num,
                'grade_band': grade_band,
                'text': text
            }
            
            indicators.append(indicator)
            i = j - 1
        
        i += 1
    
    return indicators


def get_indicator_category(dimension: str, discipline: str, indicator_num: str) -> str:
    """Determine the category/subcategory for an indicator."""
    categories = {
        'D1': {
            '1': 'Constructing Compelling Questions',
            '2': 'Constructing Compelling Questions',
            '3': 'Constructing Supporting Questions',
            '4': 'Constructing Supporting Questions',
            '5': 'Determining Helpful Sources'
        },
        'D2': {
            # These vary by discipline, so we'll use a generic approach
        },
        'D3': {
            '1': 'Gathering and Evaluating Sources',
            '2': 'Gathering and Evaluating Sources',
            '3': 'Gathering and Evaluating Sources',
            '4': 'Developing Claims and Using Evidence'
        },
        'D4': {
            '1': 'Communicating and Critiquing Conclusions',
            '2': 'Communicating and Critiquing Conclusions',
            '3': 'Communicating and Critiquing Conclusions',
            '4': 'Communicating and Critiquing Conclusions',
            '5': 'Communicating and Critiquing Conclusions',
            '6': 'Taking Informed Action',
            '7': 'Taking Informed Action',
            '8': 'Taking Informed Action'
        }
    }
    
    if dimension in categories and indicator_num in categories[dimension]:
        return categories[dimension][indicator_num]
    
    # For D2, return discipline-specific category
    if dimension == 'D2' and discipline:
        return f"{DISCIPLINES.get(discipline, discipline)} Concepts"
    
    return "General Indicators"


def create_hierarchy_entries(indicators: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Create hierarchy entries for C3 Framework 4-level structure."""
    hierarchy_entries = []
    standard_entries = []
    
    created_hierarchies = {}
    hierarchy_id_counter = 52000  # Start after Math Common Core
    
    # Group indicators
    grouped = {}
    for ind in indicators:
        dimension_name = DIMENSIONS.get(ind['dimension'], ind['dimension'])
        discipline_name = DISCIPLINES.get(ind['discipline'], '') if ind['discipline'] else ''
        grade_band_name = GRADE_BANDS.get(ind['grade_band'], ind['grade_band'])
        category = get_indicator_category(ind['dimension'], ind['discipline'], ind['indicator_num'])
        
        # For D2, include discipline in the grouping
        if ind['dimension'] == 'D2' and discipline_name:
            key = (dimension_name, discipline_name, grade_band_name)
        else:
            key = (dimension_name, category, grade_band_name)
        
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(ind)
    
    # Create hierarchy entries
    for key, inds in grouped.items():
        if len(key) == 3:
            dimension_name, subcategory, grade_band = key
        else:
            dimension_name, subcategory, grade_band = key[0], key[1], key[2]
        
        # Level 1: Dimension
        level1_key = f"C3_{dimension_name[:10]}"  # Truncate for uniqueness
        if level1_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': dimension_name,
                'description': '',
                'parent_tid': '',
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level1_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level1_id = created_hierarchies[level1_key]
        
        # Level 2: Subcategory (Discipline for D2, Category for others)
        level2_key = f"{level1_key}_{subcategory[:20]}"
        if level2_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': subcategory,
                'description': '',
                'parent_tid': level1_id,
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level2_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level2_id = created_hierarchies[level2_key]
        
        # Level 3: Grade Band
        level3_key = f"{level2_key}_{grade_band}"
        if level3_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': grade_band,
                'description': '',
                'parent_tid': level2_id,
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level3_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level3_id = created_hierarchies[level3_key]
        
        # Level 4: Individual Indicators
        for ind in inds:
            std_uuid = f"c3-{ind['code'].lower().replace('.', '-')}"
            
            standard_entry = {
                'uuid': std_uuid,
                'title': ind['code'],
                'body/format': 'basic_html',
                'body/value': f"<p>{ind['text']}</p>",
                'field_standards_framework': FRAMEWORK_ID,
                'field_standards_hierarchy': level3_id,
                'field_standards_taxonomy': TAXONOMY_TYPES['indicator'],
                'field_org_level_1': dimension_name,
                'field_org_level_2': subcategory,
                'field_org_level_3': grade_band,
                'field_standard_ref': ind['code'],
                'status': 'TRUE'
            }
            
            standard_entries.append(standard_entry)
    
    return hierarchy_entries, standard_entries


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/c3_framework/Copy of C3-Framework-for-Social-Studies_output.txt")
    output_dir = Path("data/output/drupal_prep/03_c3")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract indicators
    print("Extracting C3 Framework indicators...")
    indicators = extract_c3_indicators(input_file)
    print(f"Found {len(indicators)} indicators")
    
    if not indicators:
        print("No indicators found. Please check the input file format.")
        return
    
    # Create hierarchy and standard entries
    hierarchy_entries, standard_entries = create_hierarchy_entries(indicators)
    
    # Write hierarchy additions
    hierarchy_file = output_dir / 'c3_hierarchy_additions.csv'
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'name', 'description', 'parent_tid', 
                                               'field_associated_framework'])
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards
    standards_file = output_dir / 'c3_standards_drupal.csv'
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['uuid', 'title', 'body/format', 'body/value', 'field_standards_framework',
                     'field_standards_hierarchy', 'field_standards_taxonomy', 'field_org_level_1',
                     'field_org_level_2', 'field_org_level_3', 'field_standard_ref', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(standard_entries)
    
    # Create summary
    dimensions = {}
    for ind in indicators:
        dim = ind['dimension']
        if dim not in dimensions:
            dimensions[dim] = {'count': 0, 'disciplines': set()}
        dimensions[dim]['count'] += 1
        if ind['discipline']:
            dimensions[dim]['disciplines'].add(ind['discipline'])
    
    summary = {
        'total_indicators': len(indicators),
        'hierarchy_entries_created': len(hierarchy_entries),
        'dimensions': {
            dim: {
                'count': data['count'],
                'disciplines': list(data['disciplines'])
            }
            for dim, data in dimensions.items()
        },
        'grade_bands': list(GRADE_BANDS.values())
    }
    
    with open(output_dir / 'c3_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Indicators mapped: {len(standard_entries)}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


if __name__ == "__main__":
    main()