#!/usr/bin/env python3
"""
Extract ISCA Student Standards from text files.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

from doc_processing.utils.ids import generate_unique_id


def extract_isca_standards(file_path: Path) -> List[Dict]:
    """Extract ISCA Student Standards from document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    standards = []
    lines = content.split('\n')
    
    # Domain mappings
    domain_mapping = {
        'SE': 'Social Emotional Development',
        'AC': 'Academic Development', 
        'GP': 'Global Perspective and Identity Development'
    }
    
    current_domain = None
    current_standard = None
    current_competency = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detect domain headers (e.g., "SOCIAL EMOTIONAL DEVELOPMENT DOMAIN")
        for domain_code, domain_name in domain_mapping.items():
            if domain_name.upper() in line.upper() and 'DOMAIN' in line.upper():
                current_domain = domain_code
                break
        
        # Detect standard headers (e.g., "Standard A: Students will understand...")
        standard_match = re.match(r'^Standard ([ABC]):\s*(.+)', line)
        if standard_match:
            standard_letter = standard_match.group(1)
            standard_text = standard_match.group(2).strip()
            current_standard = standard_letter
            
            standard_entry = {
                'id': generate_unique_id(f"{current_domain}:{standard_letter}_{standard_text}", 'ISCA_STD_'),
                'code': f"ISCA.{current_domain}.{standard_letter}",
                'letter': standard_letter,
                'title': f"Standard {standard_letter}",
                'description': standard_text,
                'domain': current_domain,
                'domain_name': domain_mapping.get(current_domain, current_domain),
                'framework': 'ISCA',
                'type': 'Standard'
            }
            
            standards.append(standard_entry)
        
        # Detect competency headers (e.g., "Competency A1 ~ Self Awareness")
        competency_match = re.match(r'^Competency ([ABC]\d+)\s*~\s*(.+)', line)
        if competency_match:
            competency_code = competency_match.group(1)
            competency_title = competency_match.group(2).strip()
            current_competency = competency_code
            
            competency_entry = {
                'id': generate_unique_id(f"{current_domain}:{competency_code}_{competency_title}", 'ISCA_COMP_'),
                'code': f"ISCA.{current_domain}.{competency_code}",
                'competency_code': competency_code,
                'title': f"Competency {competency_code}: {competency_title}",
                'description': competency_title,
                'domain': current_domain,
                'domain_name': domain_mapping.get(current_domain, current_domain),
                'standard': current_standard,
                'framework': 'ISCA',
                'type': 'Competency'
            }
            
            standards.append(competency_entry)
        
        # Detect indicators (e.g., "SE:A1:1")
        indicator_match = re.match(r'^([A-Z]{2}):([ABC]\d+):(\d+)', line)
        if indicator_match:
            domain_code = indicator_match.group(1)
            comp_code = indicator_match.group(2)
            indicator_num = indicator_match.group(3)
            
            # Get indicator text from next line(s)
            indicator_text = ""
            j = i + 1
            while j < len(lines) and j < i + 5:
                next_line = lines[j].strip()
                if next_line and not re.match(r'^[A-Z]{2}:[ABC]\d+:\d+', next_line) and not next_line.startswith('Competency') and not next_line.startswith('Standard'):
                    indicator_text += " " + next_line
                    j += 1
                else:
                    break
            
            if indicator_text:
                indicator_entry = {
                    'id': generate_unique_id(f"{domain_code}:{comp_code}:{indicator_num}_{indicator_text}", 'ISCA_IND_'),
                    'code': f"ISCA.{domain_code}.{comp_code}.{indicator_num}",
                    'indicator_code': f"{domain_code}:{comp_code}:{indicator_num}",
                    'number': indicator_num,
                    'title': f"{domain_code}:{comp_code}:{indicator_num}: {indicator_text[:100]}..." if len(indicator_text) > 100 else f"{domain_code}:{comp_code}:{indicator_num}: {indicator_text}",
                    'description': indicator_text.strip(),
                    'domain': domain_code,
                    'domain_name': domain_mapping.get(domain_code, domain_code),
                    'competency': comp_code,
                    'framework': 'ISCA',
                    'type': 'Indicator'
                }
                
                standards.append(indicator_entry)
                i = j - 1
        
        i += 1
    
    return standards


def create_drupal_hierarchy(standards: List[Dict]) -> List[Dict]:
    """Create hierarchy entries for Drupal."""
    hierarchy_entries = []
    
    # Group by domain, standard, and competency
    domains = {}
    main_standards = {}
    competencies = {}
    
    for std in standards:
        domain = std['domain']
        if domain not in domains:
            domains[domain] = {'name': std['domain_name'], 'count': 0}
        domains[domain]['count'] += 1
        
        if std['type'] == 'Standard':
            main_standards[std['letter']] = std
        elif std['type'] == 'Competency':
            competencies[std['competency_code']] = std
    
    # Create domain hierarchy entries
    for domain_code, domain_data in domains.items():
        hierarchy_entries.append({
            'uuid': f"isca-domain-{domain_code.lower()}",
            'title': f"ISCA {domain_data['name']} ({domain_code})",
            'field_standards_framework': 'isca',
            'field_standards_taxonomy': 'domain',
            'field_org_level_1': domain_data['name'],
            'status': 'TRUE'
        })
    
    # Create standard hierarchy entries
    for std_letter, std in main_standards.items():
        hierarchy_entries.append({
            'uuid': f"isca-standard-{std['domain'].lower()}-{std_letter.lower()}",
            'title': f"ISCA {std['domain']} Standard {std_letter}",
            'field_standards_framework': 'isca',
            'field_standards_taxonomy': 'standard',
            'field_org_level_1': std['domain_name'],
            'field_org_level_2': f"Standard {std_letter}",
            'status': 'TRUE'
        })
    
    # Create competency hierarchy entries
    for comp_code, comp in competencies.items():
        hierarchy_entries.append({
            'uuid': f"isca-competency-{comp['domain'].lower()}-{comp_code.lower()}",
            'title': f"ISCA {comp['domain']} {comp_code}",
            'field_standards_framework': 'isca',
            'field_standards_taxonomy': 'competency',
            'field_org_level_1': comp['domain_name'],
            'field_org_level_2': f"Standard {comp.get('standard', '')}",
            'field_org_level_3': comp['description'],
            'status': 'TRUE'
        })
    
    return hierarchy_entries


def process_isca_standards(input_file: Path, output_dir: Path):
    """Process ISCA standards and create Drupal-ready files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Extracting ISCA Student Standards...")
    standards = extract_isca_standards(input_file)
    print(f"Found {len(standards)} standards, competencies, and indicators")
    
    if not standards:
        print("No standards found. Please check the input file format.")
        return
    
    # Create hierarchy
    hierarchy_entries = create_drupal_hierarchy(standards)
    
    # Write hierarchy CSV
    hierarchy_file = output_dir / 'isca_hierarchy_additions.csv'
    hierarchy_fieldnames = [
        'uuid', 'title', 'field_standards_framework', 'field_standards_taxonomy',
        'field_org_level_1', 'field_org_level_2', 'field_org_level_3', 'status'
    ]
    
    with open(hierarchy_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hierarchy_fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy_entries)
    
    # Write standards CSV
    standards_file = output_dir / 'isca_standards_drupal.csv'
    standards_fieldnames = [
        'uuid', 'title', 'body/value', 'field_framework', 'field_domain',
        'field_standard_code', 'field_type', 'field_competency'
    ]
    
    with open(standards_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=standards_fieldnames)
        writer.writeheader()
        
        for std in standards:
            writer.writerow({
                'uuid': f"isca-{std['id']}",
                'title': std['title'],
                'body/value': f"<p>{std['description']}</p>",
                'field_framework': 'ISCA',
                'field_domain': std['domain_name'],
                'field_standard_code': std['code'],
                'field_type': std['type'],
                'field_competency': std.get('competency', '')
            })
    
    # Create summary
    domains = {}
    types = {'Standard': 0, 'Competency': 0, 'Indicator': 0}
    
    for std in standards:
        domain = std['domain_name']
        if domain not in domains:
            domains[domain] = {'standards': 0, 'competencies': 0, 'indicators': 0}
        
        std_type = std['type'].lower()
        if std_type == 'standard':
            domains[domain]['standards'] += 1
        elif std_type == 'competency':
            domains[domain]['competencies'] += 1
        elif std_type == 'indicator':
            domains[domain]['indicators'] += 1
        
        types[std['type']] += 1
    
    summary = {
        'total_items': len(standards),
        'by_type': types,
        'hierarchy_entries_created': len(hierarchy_entries),
        'domains': domains
    }
    
    with open(output_dir / 'isca_mapping_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nMapping complete!")
    print(f"  Total items mapped: {len(standards)}")
    print(f"  Standards: {types['Standard']}")
    print(f"  Competencies: {types['Competency']}")
    print(f"  Indicators: {types['Indicator']}")
    print(f"  Hierarchy entries: {len(hierarchy_entries)}")
    print(f"  Output files:")
    print(f"    - {hierarchy_file}")
    print(f"    - {standards_file}")


def main():
    """Main execution function."""
    input_file = Path("data/output/text/standards/isca/ISCA Student Standards June 2022_output.txt")
    output_dir = Path("data/output/drupal_prep/07_isca")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    process_isca_standards(input_file, output_dir)


if __name__ == "__main__":
    main()