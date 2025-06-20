#!/usr/bin/env python3
"""
Extract Math Common Core standards and map to Drupal's 4-level hierarchy.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


# Math Common Core Framework ID from your data
FRAMEWORK_ID = '14783'

# Standard taxonomy type IDs (from your standards_taxonomy.csv)
TAXONOMY_TYPES = {
    'domain': '16468',  # Using Anchor Standard for domains
    'cluster': '16469',  # Using Standard for clusters
    'standard': '16470'  # Using Substandard for individual standards
}

# Grade level mappings
GRADE_LEVELS = {
    'K': 'Kindergarten',
    '1': 'Grade 1',
    '2': 'Grade 2',
    '3': 'Grade 3',
    '4': 'Grade 4',
    '5': 'Grade 5',
    '6': 'Grade 6',
    '7': 'Grade 7',
    '8': 'Grade 8',
    'HS': 'High School'
}

# Domain mappings
DOMAINS = {
    'CC': 'Counting and Cardinality',
    'OA': 'Operations and Algebraic Thinking',
    'NBT': 'Number and Operations in Base Ten',
    'MD': 'Measurement and Data',
    'G': 'Geometry',
    'NF': 'Number and Operations—Fractions',
    'RP': 'Ratios and Proportional Relationships',
    'NS': 'The Number System',
    'EE': 'Expressions and Equations',
    'SP': 'Statistics and Probability',
    'F': 'Functions',
    'A': 'Algebra',
    'N': 'Number and Quantity',
    'S': 'Statistics and Probability'
}


def extract_math_standards_v2(file_path: Path) -> List[Dict]:
    """Extract Math Common Core standards from text file - improved version."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    current_grade = None
    current_domain_code = None
    current_domain_name = None
    current_cluster = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and page markers
        if not line or line.startswith('==='):
            i += 1
            continue
        
        # Detect grade level from context
        if 'KINDERGARTEN' in line:
            current_grade = 'K'
        elif re.search(r'GRADE (\d)', line):
            match = re.search(r'GRADE (\d)', line)
            current_grade = match.group(1)
        elif 'HIGH SCHOOL' in line:
            current_grade = 'HS'
        
        # Detect domain code (e.g., K.CC, 3.NBT)
        domain_code_match = re.match(r'^([K\d]+|HS)\.([A-Z]+)$', line)
        if domain_code_match:
            current_grade = domain_code_match.group(1)
            current_domain_code = domain_code_match.group(2)
            # Look for domain name in previous lines
            if i > 0:
                prev_line = lines[i-1].strip()
                if prev_line and not prev_line.startswith('==='):
                    current_domain_name = prev_line
            i += 1
            continue
        
        # Detect numbered standards (must have current domain)
        if current_domain_code and re.match(r'^\d+\.', line):
            std_match = re.match(r'^(\d+)\.(.*)$', line)
            if std_match:
                std_num = std_match.group(1)
                text = std_match.group(2).strip()
                
                # Continue reading text on next lines
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    # Stop if we hit a new standard, domain, or section
                    if (not next_line or 
                        next_line.startswith('===') or
                        re.match(r'^\d+\.', next_line) or
                        re.match(r'^[a-z]\.', next_line) or
                        re.match(r'^[K\d]+\.', next_line) or
                        any(domain in next_line for domain in DOMAINS.values())):
                        break
                    text += ' ' + next_line
                    j += 1
                
                # Clean up text
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Build standard
                if current_grade and current_domain_code:
                    full_code = f"{current_grade}.{current_domain_code}.{std_num}"
                    
                    standard = {
                        'code': full_code,
                        'grade': current_grade,
                        'domain_code': current_domain_code,
                        'domain_name': current_domain_name or DOMAINS.get(current_domain_code, current_domain_code),
                        'standard_num': std_num,
                        'text': text,
                        'cluster': current_cluster
                    }
                    
                    standards.append(standard)
                
                i = j - 1
        
        # Detect cluster descriptions (italic text before standards)
        elif current_domain_code and not re.match(r'^\d+\.', line) and len(line) > 20:
            # This might be a cluster description
            if not any(keyword in line.lower() for keyword in ['page', 'mathematics', 'overview', 'grade', 'kindergarten']):
                # Check if this looks like a cluster (not a domain name)
                if line not in DOMAINS.values() and not re.match(r'^[K\d]+\.[A-Z]+$', line):
                    current_cluster = line
        
        # Look for sub-standards (a, b, c, etc.)
        elif current_domain_code and re.match(r'^[a-z]\.', line):
            sub_match = re.match(r'^([a-z])\.(.*)$', line)
            if sub_match and standards:
                sub_letter = sub_match.group(1)
                sub_text = sub_match.group(2).strip()
                
                # Continue reading text
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if (not next_line or 
                        next_line.startswith('===') or
                        re.match(r'^[a-z]\.', next_line) or
                        re.match(r'^\d+\.', next_line)):
                        break
                    sub_text += ' ' + next_line
                    j += 1
                
                # Add as a new standard with letter suffix
                last_standard = standards[-1]
                sub_standard = {
                    'code': f"{last_standard['code']}{sub_letter}",
                    'grade': last_standard['grade'],
                    'domain_code': last_standard['domain_code'],
                    'domain_name': last_standard['domain_name'],
                    'standard_num': f"{last_standard['standard_num']}{sub_letter}",
                    'text': sub_text.strip(),
                    'cluster': last_standard['cluster']
                }
                standards.append(sub_standard)
                i = j - 1
        
        i += 1
    
    return standards


def create_hierarchy_entries(standards: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Create hierarchy entries for Math Common Core 4-level structure."""
    hierarchy_entries = []
    standard_entries = []
    
    created_hierarchies = {}
    hierarchy_id_counter = 51000  # Start after NCAS
    
    # Group standards by grade, domain, and cluster
    grouped = {}
    for std in standards:
        grade = GRADE_LEVELS.get(std['grade'], std['grade'])
        domain_name = std['domain_name']
        cluster = std.get('cluster', '')
        
        key = (grade, domain_name, cluster)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(std)
    
    # Create hierarchy entries
    for (grade, domain, cluster), stds in grouped.items():
        # Level 1: Grade Level
        level1_key = f"MathCC_{grade}"
        if level1_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': grade,
                'description': f"Common Core Math Standards for {grade}",
                'parent_tid': '',
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level1_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level1_id = created_hierarchies[level1_key]
        
        # Level 2: Domain
        level2_key = f"{level1_key}_{domain}"
        if level2_key not in created_hierarchies:
            hierarchy_entries.append({
                'ID': hierarchy_id_counter,
                'name': domain,
                'description': '',
                'parent_tid': level1_id,
                'field_associated_framework': FRAMEWORK_ID
            })
            created_hierarchies[level2_key] = hierarchy_id_counter
            hierarchy_id_counter += 1
        level2_id = created_hierarchies[level2_key]
        
        # Level 3: Cluster (if exists)
        if cluster:
            level3_key = f"{level2_key}_{cluster[:30]}"  # Truncate for uniqueness
            if level3_key not in created_hierarchies:
                hierarchy_entries.append({
                    'ID': hierarchy_id_counter,
                    'name': cluster[:100] + '...' if len(cluster) > 100 else cluster,
                    'description': cluster,
                    'parent_tid': level2_id,
                    'field_associated_framework': FRAMEWORK_ID
                })
                created_hierarchies[level3_key] = hierarchy_id_counter
                hierarchy_id_counter += 1
            level3_id = created_hierarchies[level3_key]
            parent_id = level3_id
        else:
            parent_id = level2_id
        
        # Level 4: Individual Standards
        for std in stds:
            std_uuid = f"mathcc-{std['code'].lower().replace('.', '-')}"
            
            standard_entry = {
                'uuid': std_uuid,
                'title': f"CCSS.Math.Content.{std['code']}",
                'body/format': 'basic_html',
                'body/value': f"<p>{std['text']}</p>",
                'field_standards_framework': FRAMEWORK_ID,
                'field_standards_hierarchy': parent_id,
                'field_standards_taxonomy': TAXONOMY_TYPES['standard'],
                'field_org_level_1': grade,
                'field_org_level_2': domain,
                'field_org_level_3': cluster[:100] if cluster else '',
                'field_standard_ref': std['code'],
                'status': 'TRUE'
            }
            
            standard_entries.append(standard_entry)
    
    return hierarchy_entries, standard_entries


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/common_core_math/Math_Standards1_output.txt")
    output_dir = Path("data/output/drupal_prep/02_math_common_core")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract standards
    print("Extracting Math Common Core standards...")
    standards = extract_math_standards_v2(input_file)
    print(f"Found {len(standards)} standards")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy and standard entries
    hierarchy_entries, standard_entries = create_hierarchy_entries(standards)
    
    # Write hierarchy additions
    hierarchy_file = output_dir / 'math_cc_hierarchy_additions.csv'
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'name', 'description', 'parent_tid', 
                                               'field_associated_framework'])
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards
    standards_file = output_dir / 'math_cc_standards_drupal.csv'
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['uuid', 'title', 'body/format', 'body/value', 'field_standards_framework',
                     'field_standards_hierarchy', 'field_standards_taxonomy', 'field_org_level_1',
                     'field_org_level_2', 'field_org_level_3', 'field_standard_ref', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(standard_entries)
    
    # Create summary
    summary = {
        'total_standards': len(standard_entries),
        'hierarchy_entries_created': len(hierarchy_entries),
        'grades': list(set(s['field_org_level_1'] for s in standard_entries)),
        'domains': list(set(s['field_org_level_2'] for s in standard_entries))
    }
    
    with open(output_dir / 'math_cc_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Standards mapped: {len(standard_entries)}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


if __name__ == "__main__":
    main()