#!/usr/bin/env python3
"""
Extract ACTFL World-Readiness Standards for Learning Languages from text files.
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


def extract_actfl_standards(file_path: Path) -> List[Dict]:
    """Extract ACTFL World-Readiness Standards from document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    # The "5 Cs" goal areas
    goal_areas = {
        'COMMUNICATION': {
            'name': 'Communication',
            'description': 'Communicate effectively in more than one language in order to function in a variety of situations and for multiple purposes',
            'standards': {
                'Interpersonal Communication': 'Learners interact and negotiate meaning in spoken, signed, or written conversations to share information, reactions, feelings, and opinions.',
                'Interpretive Communication': 'Learners understand, interpret, and analyze what is heard, read, or viewed on a variety of topics.',
                'Presentational Communication': 'Learners present information, concepts, and ideas to inform, explain, persuade, and narrate on a variety of topics using appropriate media and adapting to various audiences of listeners, readers, or viewers.'
            }
        },
        'CULTURES': {
            'name': 'Cultures',
            'description': 'Interact with cultural competence and understanding',
            'standards': {
                'Relating Cultural Practices to Perspectives': 'Learners use the language to investigate, explain, and reflect on the relationship between the practices and perspectives of the cultures studied.',
                'Relating Cultural Products to Perspectives': 'Learners use the language to investigate, explain, and reflect on the relationship between the products and perspectives of the cultures studied.'
            }
        },
        'CONNECTIONS': {
            'name': 'Connections',
            'description': 'Connect with other disciplines and acquire information and diverse perspectives in order to use the language to function in academic and career related situations',
            'standards': {
                'Making Connections': 'Learners build, reinforce, and expand their knowledge of other disciplines while using the language to develop critical thinking and to solve problems creatively.',
                'Acquiring Information and Diverse Perspectives': 'Learners access and evaluate information and diverse perspectives that are available through the language and its cultures.'
            }
        },
        'COMPARISONS': {
            'name': 'Comparisons',
            'description': 'Develop insight into the nature of language and culture in order to interact with cultural competence',
            'standards': {
                'Language Comparisons': 'Learners use the language to investigate, explain, and reflect on the nature of language through comparisons of the language studied and their own.',
                'Cultural Comparisons': 'Learners use the language to investigate, explain, and reflect on the concept of culture through comparisons of the cultures studied and their own.'
            }
        },
        'COMMUNITIES': {
            'name': 'Communities',
            'description': 'Communicate and interact with cultural competence in order to participate in multilingual communities at home and around the world',
            'standards': {
                'School and Global Communities': 'Learners use the language both within and beyond the classroom to interact and collaborate in their community and the globalized world.',
                'Lifelong Learning': 'Learners set goals and reflect on their progress in using languages for enjoyment, enrichment, and advancement.'
            }
        }
    }
    
    current_goal_area = None
    current_standard = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detect goal areas (COMMUNICATION, CULTURES, etc.)
        if line.upper() in goal_areas:
            current_goal_area = line.upper()
            
            # Add the goal area as a standard
            goal_data = goal_areas[current_goal_area]
            goal_entry = {
                'id': generate_unique_id(f"{current_goal_area}_{goal_data['description']}", 'ACTFL_GOAL_'),
                'code': f"ACTFL.{current_goal_area}",
                'goal_area': current_goal_area,
                'title': f"{goal_data['name']} Goal Area",
                'description': goal_data['description'],
                'framework': 'ACTFL',
                'type': 'Goal Area'
            }
            standards.append(goal_entry)
        
        # Detect standard names within goal areas
        for goal_area_key, goal_area_data in goal_areas.items():
            if current_goal_area == goal_area_key:
                for standard_name, standard_desc in goal_area_data['standards'].items():
                    # Look for the standard name in the current line
                    if standard_name.replace(' ', '') in line.replace(' ', '') or standard_name.split(':')[0].strip() in line:
                        current_standard = standard_name
                        
                        # Create standard code
                        if 'Interpersonal' in standard_name:
                            code_suffix = 'INTER'
                        elif 'Interpretive' in standard_name:
                            code_suffix = 'INTERP'
                        elif 'Presentational' in standard_name:
                            code_suffix = 'PRES'
                        elif 'Practices' in standard_name:
                            code_suffix = 'PRAC'
                        elif 'Products' in standard_name:
                            code_suffix = 'PROD'
                        elif 'Making Connections' in standard_name:
                            code_suffix = 'CONN'
                        elif 'Information' in standard_name:
                            code_suffix = 'INFO'
                        elif 'Language Comparisons' in standard_name:
                            code_suffix = 'LANG'
                        elif 'Cultural Comparisons' in standard_name:
                            code_suffix = 'CULT'
                        elif 'School' in standard_name:
                            code_suffix = 'SCHOOL'
                        elif 'Lifelong' in standard_name:
                            code_suffix = 'LIFE'
                        else:
                            code_suffix = standard_name[:4].upper()
                        
                        standard_entry = {
                            'id': generate_unique_id(f"{current_goal_area}_{standard_name}_{standard_desc}", 'ACTFL_STD_'),
                            'code': f"ACTFL.{current_goal_area}.{code_suffix}",
                            'goal_area': current_goal_area,
                            'goal_area_name': goal_area_data['name'],
                            'title': standard_name,
                            'description': standard_desc,
                            'framework': 'ACTFL',
                            'type': 'Standard'
                        }
                        standards.append(standard_entry)
                        break
        
        i += 1
    
    return standards


def create_drupal_hierarchy(standards: List[Dict]) -> List[Dict]:
    """Create hierarchy entries for Drupal."""
    hierarchy_entries = []
    
    # Group by goal area
    goal_areas = {}
    
    for std in standards:
        goal_area = std['goal_area']
        if goal_area not in goal_areas:
            goal_areas[goal_area] = {
                'name': std.get('goal_area_name', goal_area),
                'standards': 0,
                'goal_areas': 0
            }
        
        if std['type'] == 'Goal Area':
            goal_areas[goal_area]['goal_areas'] += 1
        elif std['type'] == 'Standard':
            goal_areas[goal_area]['standards'] += 1
    
    # Create goal area hierarchy entries
    for goal_code, goal_data in goal_areas.items():
        hierarchy_entries.append({
            'uuid': f"actfl-goal-{goal_code.lower()}",
            'title': f"ACTFL {goal_data['name']}",
            'field_standards_framework': 'actfl',
            'field_standards_taxonomy': 'goal_area',
            'field_org_level_1': goal_data['name'],
            'status': 'TRUE'
        })
    
    return hierarchy_entries


def process_actfl_standards(input_file: Path, output_dir: Path):
    """Process ACTFL standards and create Drupal-ready files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Extracting ACTFL World-Readiness Standards...")
    standards = extract_actfl_standards(input_file)
    print(f"Found {len(standards)} goal areas and standards")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy
    hierarchy_entries = create_drupal_hierarchy(standards)
    
    # Write hierarchy CSV
    hierarchy_file = output_dir / 'actfl_hierarchy_additions.csv'
    hierarchy_fieldnames = [
        'uuid', 'title', 'field_standards_framework', 'field_standards_taxonomy',
        'field_org_level_1', 'status'
    ]
    
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hierarchy_fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards CSV
    standards_file = output_dir / 'actfl_standards_drupal.csv'
    standards_fieldnames = [
        'uuid', 'title', 'body/value', 'field_framework', 'field_goal_area',
        'field_standard_code', 'field_type'
    ]
    
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=standards_fieldnames)
        writer.writeheader()
        
        for std in standards:
            writer.writerow({
                'uuid': f"actfl-{std['id']}",
                'title': std['title'],
                'body/value': f"<p>{std['description']}</p>",
                'field_framework': 'ACTFL',
                'field_goal_area': std.get('goal_area_name', std['goal_area']),
                'field_standard_code': std['code'],
                'field_type': std['type']
            })
    
    # Create summary
    goal_areas_count = len([s for s in standards if s['type'] == 'Goal Area'])
    standards_count = len([s for s in standards if s['type'] == 'Standard'])
    
    by_goal_area = {}
    for std in standards:
        goal_area = std.get('goal_area_name', std['goal_area'])
        if goal_area not in by_goal_area:
            by_goal_area[goal_area] = {'goal_areas': 0, 'standards': 0}
        
        if std['type'] == 'Goal Area':
            by_goal_area[goal_area]['goal_areas'] += 1
        elif std['type'] == 'Standard':
            by_goal_area[goal_area]['standards'] += 1
    
    summary = {
        'total_items': len(standards),
        'goal_areas': goal_areas_count,
        'standards': standards_count,
        'hierarchy_entries_created': len(hierarchy_entries),
        'by_goal_area': by_goal_area
    }
    
    with open(output_dir / 'actfl_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Total items mapped: {len(standards)}")
    print(f"  Goal areas: {goal_areas_count}")
    print(f"  Standards: {standards_count}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/actful/World-ReadinessStandardsforLearningLanguages_output.txt")
    output_dir = Path("data/output/drupal_prep/09_actfl")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    process_actfl_standards(input_file, output_dir)


if __name__ == "__main__":
    main()