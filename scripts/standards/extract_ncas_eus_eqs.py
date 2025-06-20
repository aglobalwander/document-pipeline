#!/usr/bin/env python3
"""
Extract Essential Questions and Enduring Understandings from NCAS standards documents.
Creates CSV files for import into Drupal.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


def generate_unique_id(text: str, prefix: str = "") -> str:
    """Generate a unique ID for an EU or EQ based on its text."""
    # Create a hash of the text for uniqueness
    hash_obj = hashlib.md5(text.encode())
    hash_str = hash_obj.hexdigest()[:8]
    return f"{prefix}{hash_str}"


def extract_ncas_structure(file_path: Path) -> Dict:
    """Extract standards, EUs, and EQs from NCAS document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Data structure to hold results
    results = {
        'anchor_standards': [],
        'enduring_understandings': [],
        'essential_questions': [],
        'standards': [],
        'relationships': []
    }
    
    # Split by pages to process section by section
    pages = content.split('=== Page')
    
    current_anchor = None
    current_eu = None
    current_eq = None
    
    for page in pages:
        lines = page.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Detect Anchor Standard
            anchor_match = re.match(r'^Anchor Standard (\d+):\s*(.+)$', line)
            if anchor_match:
                anchor_num = anchor_match.group(1)
                anchor_text = anchor_match.group(2)
                current_anchor = {
                    'number': anchor_num,
                    'text': anchor_text,
                    'full_text': line
                }
                results['anchor_standards'].append(current_anchor)
                continue
            
            # Detect Enduring Understanding
            if line.startswith('Enduring Understanding:'):
                eu_text = line.replace('Enduring Understanding:', '').strip()
                if not eu_text and i + 1 < len(lines):
                    # EU might be on next line
                    eu_text = lines[i + 1].strip()
                
                if eu_text:
                    eu_id = generate_unique_id(eu_text, 'EU_')
                    current_eu = {
                        'id': eu_id,
                        'text': eu_text,
                        'anchor_standard': current_anchor['number'] if current_anchor else None
                    }
                    results['enduring_understandings'].append(current_eu)
                    
                    # Create relationship
                    if current_anchor:
                        results['relationships'].append({
                            'anchor_standard': current_anchor['number'],
                            'eu_id': eu_id,
                            'type': 'anchor_to_eu'
                        })
                continue
            
            # Detect Essential Questions
            if line.startswith('Essential Question'):
                eq_text = line.replace('Essential Question(s):', '').replace('Essential Question:', '').strip()
                if not eq_text and i + 1 < len(lines):
                    # EQ might be on next line
                    eq_text = lines[i + 1].strip()
                
                if eq_text:
                    # Split multiple questions if they exist
                    questions = re.split(r'\?\s+', eq_text)
                    for question in questions:
                        if question and not question.endswith('?'):
                            question += '?'
                        if question and len(question) > 5:  # Filter out fragments
                            eq_id = generate_unique_id(question, 'EQ_')
                            current_eq = {
                                'id': eq_id,
                                'text': question.strip(),
                                'anchor_standard': current_anchor['number'] if current_anchor else None
                            }
                            results['essential_questions'].append(current_eq)
                            
                            # Create relationship
                            if current_anchor:
                                results['relationships'].append({
                                    'anchor_standard': current_anchor['number'],
                                    'eq_id': eq_id,
                                    'type': 'anchor_to_eq'
                                })
                continue
            
            # Extract specific standards (e.g., VA:Cr1.1.PKa)
            standard_match = re.match(r'^(VA|MU|TH|DA|MA):([A-Za-z0-9\.]+)\s+(.+)', line)
            if standard_match:
                standard_code = f"{standard_match.group(1)}:{standard_match.group(2)}"
                standard_text = standard_match.group(3)
                
                standard_entry = {
                    'code': standard_code,
                    'text': standard_text,
                    'anchor_standard': current_anchor['number'] if current_anchor else None,
                    'eu_ids': [current_eu['id']] if current_eu else [],
                    'eq_ids': [current_eq['id']] if current_eq else []
                }
                results['standards'].append(standard_entry)
    
    return results


def process_ncas_directory(input_dir: Path, output_dir: Path):
    """Process all NCAS documents in a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Aggregate data across all files
    all_eus = []
    all_eqs = []
    all_standards = []
    all_relationships = []
    
    # Track unique EUs and EQs to avoid duplicates
    seen_eus = set()
    seen_eqs = set()
    
    # Process each NCAS file
    ncas_files = list(input_dir.glob("*.txt"))
    print(f"Found {len(ncas_files)} NCAS files to process")
    
    for file_path in ncas_files:
        print(f"Processing: {file_path.name}")
        
        # Extract subject from filename
        subject = file_path.stem.replace('_output', '').replace(' at a Glance', '')
        
        try:
            results = extract_ncas_structure(file_path)
            
            # Process EUs
            for eu in results['enduring_understandings']:
                if eu['text'] not in seen_eus:
                    seen_eus.add(eu['text'])
                    eu['subject'] = subject
                    eu['framework'] = 'NCAS'
                    all_eus.append(eu)
            
            # Process EQs
            for eq in results['essential_questions']:
                if eq['text'] not in seen_eqs:
                    seen_eqs.add(eq['text'])
                    eq['subject'] = subject
                    eq['framework'] = 'NCAS'
                    all_eqs.append(eq)
            
            # Process standards
            for standard in results['standards']:
                standard['subject'] = subject
                standard['framework'] = 'NCAS'
                all_standards.append(standard)
            
            # Collect relationships
            all_relationships.extend(results['relationships'])
            
        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")
    
    # Write CSV files
    write_eus_csv(all_eus, output_dir / 'ncas_enduring_understandings.csv')
    write_eqs_csv(all_eqs, output_dir / 'ncas_essential_questions.csv')
    write_standards_csv(all_standards, output_dir / 'ncas_standards_with_refs.csv')
    
    # Write summary JSON
    summary = {
        'total_eus': len(all_eus),
        'total_eqs': len(all_eqs),
        'total_standards': len(all_standards),
        'subjects': list(set(eu['subject'] for eu in all_eus))
    }
    
    with open(output_dir / 'ncas_extraction_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nExtraction complete!")
    print(f"  Enduring Understandings: {len(all_eus)}")
    print(f"  Essential Questions: {len(all_eqs)}")
    print(f"  Standards: {len(all_standards)}")


def write_eus_csv(eus: List[Dict], output_path: Path):
    """Write Enduring Understandings to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['uuid', 'title', 'body/value', 'field_framework', 'field_subject', 
                        'field_anchor_standard_ref'])
        
        for eu in eus:
            # Generate UUID-style ID
            uuid = f"eu-{eu['id']}"
            title = eu['text'][:100] + '...' if len(eu['text']) > 100 else eu['text']
            body = f"<p>{eu['text']}</p>"
            
            writer.writerow([
                uuid,
                title,
                body,
                'NCAS',
                eu['subject'],
                eu.get('anchor_standard', '')
            ])


def write_eqs_csv(eqs: List[Dict], output_path: Path):
    """Write Essential Questions to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['uuid', 'title', 'body/value', 'field_framework', 'field_subject',
                        'field_anchor_standard_ref'])
        
        for eq in eqs:
            # Generate UUID-style ID
            uuid = f"eq-{eq['id']}"
            title = eq['text']
            body = f"<p>{eq['text']}</p>"
            
            writer.writerow([
                uuid,
                title,
                body,
                'NCAS',
                eq['subject'],
                eq.get('anchor_standard', '')
            ])


def write_standards_csv(standards: List[Dict], output_path: Path):
    """Write standards with EU/EQ references."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['code', 'text', 'framework', 'subject', 'anchor_standard',
                        'eu_references', 'eq_references'])
        
        for standard in standards:
            writer.writerow([
                standard['code'],
                standard['text'],
                standard['framework'],
                standard['subject'],
                standard.get('anchor_standard', ''),
                '|'.join(standard.get('eu_ids', [])),
                '|'.join(standard.get('eq_ids', []))
            ])


def main():
    """Main execution function."""
    input_dir = Path("data/output/text/standards/ncas")
    output_dir = Path("data/output/drupal_import/ncas")
    
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        return
    
    process_ncas_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()