#!/usr/bin/env python3
"""
Extract IB course standards from text files.
Creates CSV files for import into Drupal.
Note: This is a basic implementation for IB course guides.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

from doc_processing.utils.ids import generate_unique_id


def extract_course_name(file_path: Path) -> str:
    """Extract course name from filename."""
    name = file_path.stem.replace('_output', '')
    
    # Clean up common IB filename patterns
    name = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '', name)
    name = re.sub(r'_[a-f0-9]+', '', name)
    name = re.sub(r'-guide-en.*', '', name)
    name = re.sub(r'-.*', ' ', name)
    name = re.sub(r'_.*', ' ', name)
    
    # Handle special cases
    if 'd_' in name:
        if 'biolo' in name:
            return 'Biology'
        elif 'chemi' in name:
            return 'Chemistry'
        elif 'physi' in name:
            return 'Physics'
        elif 'ecoso' in name:
            return 'Economics'
        elif 'histx' in name:
            return 'History'
        elif 'philo' in name:
            return 'Philosophy'
        elif 'sport' in name:
            return 'Sports Science'
        elif 'filmx' in name:
            return 'Film'
        elif 'visar' in name:
            return 'Visual Arts'
        elif 'ablan' in name:
            return 'Language B'
        elif 'anlan' in name:
            return 'Language A'
        else:
            return name.title()
    
    # Convert to title case and clean up
    name = ' '.join(word.capitalize() for word in name.split() if word and len(word) > 1)
    return name


def extract_ib_standards(file_path: Path) -> List[Dict]:
    """Extract IB standards from course guide."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    course_name = extract_course_name(file_path)
    standards = []
    lines = content.split('\n')
    
    current_topic = None
    current_section = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detect topic/unit headers
        topic_match = re.match(r'^(Topic|Unit|Theme|Area)\s*(\d+)[:\.]?\s*(.+)', line, re.IGNORECASE)
        if topic_match:
            topic_num = topic_match.group(2)
            topic_title = topic_match.group(3).strip()
            current_topic = f"Topic {topic_num}"
            
            topic_entry = {
                'id': generate_unique_id(f"{course_name}_{current_topic}_{topic_title}", 'IB_TOPIC_'),
                'code': f"IB.{course_name.upper().replace(' ', '_')}.T{topic_num}",
                'course': course_name,
                'topic_number': topic_num,
                'title': f"{current_topic}: {topic_title}",
                'description': topic_title,
                'framework': 'IB',
                'type': 'Topic'
            }
            standards.append(topic_entry)
        
        # Detect subtopic/essential idea patterns
        subtopic_match = re.match(r'^(\d+\.\d+)\s+(.+)', line)
        if subtopic_match and current_topic:
            subtopic_num = subtopic_match.group(1)
            subtopic_text = subtopic_match.group(2).strip()
            
            # Get additional lines if they seem to be part of the subtopic
            j = i + 1
            while j < len(lines) and j < i + 3:
                next_line = lines[j].strip()
                if next_line and not re.match(r'^\d+\.\d+', next_line) and not next_line.startswith('Topic') and len(next_line) > 10:
                    subtopic_text += " " + next_line
                    j += 1
                else:
                    break
            
            subtopic_entry = {
                'id': generate_unique_id(f"{course_name}_{current_topic}_{subtopic_num}_{subtopic_text}", 'IB_SUB_'),
                'code': f"IB.{course_name.upper().replace(' ', '_')}.{current_topic.replace(' ', '')}.{subtopic_num}",
                'course': course_name,
                'topic': current_topic,
                'subtopic_number': subtopic_num,
                'title': f"{subtopic_num}: {subtopic_text[:100]}..." if len(subtopic_text) > 100 else f"{subtopic_num}: {subtopic_text}",
                'description': subtopic_text,
                'framework': 'IB',
                'type': 'Subtopic'
            }
            standards.append(subtopic_entry)
            i = j - 1
        
        # Detect assessment objectives or other structured content
        assessment_match = re.match(r'^(Assessment objective|AO|Objective)\s*(\d+)[:\.]?\s*(.+)', line, re.IGNORECASE)
        if assessment_match:
            obj_num = assessment_match.group(2)
            obj_text = assessment_match.group(3).strip()
            
            obj_entry = {
                'id': generate_unique_id(f"{course_name}_AO{obj_num}_{obj_text}", 'IB_AO_'),
                'code': f"IB.{course_name.upper().replace(' ', '_')}.AO{obj_num}",
                'course': course_name,
                'objective_number': obj_num,
                'title': f"Assessment Objective {obj_num}",
                'description': obj_text,
                'framework': 'IB',
                'type': 'Assessment Objective'
            }
            standards.append(obj_entry)
        
        i += 1
    
    return standards


def create_drupal_hierarchy(standards: List[Dict]) -> List[Dict]:
    """Create hierarchy entries for Drupal."""
    hierarchy_entries = []
    
    # Group by course and type
    courses = {}
    types = {}
    
    for std in standards:
        course = std['course']
        std_type = std['type']
        
        if course not in courses:
            courses[course] = {'count': 0}
        courses[course]['count'] += 1
        
        if std_type not in types:
            types[std_type] = {'count': 0}
        types[std_type]['count'] += 1
    
    # Create course hierarchy entries
    for course, course_data in courses.items():
        hierarchy_entries.append({
            'uuid': f"ib-course-{course.lower().replace(' ', '_')}",
            'title': f"IB {course}",
            'field_standards_framework': 'ib',
            'field_standards_taxonomy': 'course',
            'field_org_level_1': course,
            'status': 'TRUE'
        })
    
    return hierarchy_entries


def process_ib_directory(input_dir: Path, output_dir: Path):
    """Process all IB course guide files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_standards = []
    processed_files = 0
    
    # Process each IB file
    ib_files = list(input_dir.glob("*.txt"))
    print(f"Found {len(ib_files)} IB course files to process")
    
    for file_path in ib_files[:10]:  # Limit to first 10 files for this basic implementation
        course_name = extract_course_name(file_path)
        print(f"Processing: {course_name}")
        
        try:
            standards = extract_ib_standards(file_path)
            all_standards.extend(standards)
            processed_files += 1
            
            print(f"  Found: {len(standards)} items")
            
        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")
    
    if not all_standards:
        print("No standards found.")
        return
    
    # Create hierarchy
    hierarchy_entries = create_drupal_hierarchy(all_standards)
    
    # Write hierarchy CSV
    hierarchy_file = output_dir / 'ib_hierarchy_additions.csv'
    hierarchy_fieldnames = [
        'uuid', 'title', 'field_standards_framework', 'field_standards_taxonomy',
        'field_org_level_1', 'status'
    ]
    
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hierarchy_fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards CSV
    standards_file = output_dir / 'ib_standards_drupal.csv'
    standards_fieldnames = [
        'uuid', 'title', 'body/value', 'field_framework', 'field_course',
        'field_standard_code', 'field_type'
    ]
    
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=standards_fieldnames)
        writer.writeheader()
        
        for std in all_standards:
            writer.writerow({
                'uuid': f"ib-{std['id']}",
                'title': std['title'],
                'body/value': f"<p>{std['description']}</p>",
                'field_framework': 'IB',
                'field_course': std['course'],
                'field_standard_code': std['code'],
                'field_type': std['type']
            })
    
    # Create summary
    by_course = {}
    by_type = {}
    
    for std in all_standards:
        course = std['course']
        std_type = std['type']
        
        if course not in by_course:
            by_course[course] = 0
        by_course[course] += 1
        
        if std_type not in by_type:
            by_type[std_type] = 0
        by_type[std_type] += 1
    
    summary = {
        'total_items': len(all_standards),
        'files_processed': processed_files,
        'hierarchy_entries_created': len(hierarchy_entries),
        'by_course': by_course,
        'by_type': by_type
    }
    
    with open(output_dir / 'ib_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Total items mapped: {len(all_standards)}")
    print(f"  Files processed: {processed_files}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


def main():
    """Main execution function."""
    input_dir = Path("data/output/text/standards/course_guides")
    output_dir = Path("data/output/drupal_prep/11_ib")
    
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        return
    
    process_ib_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()