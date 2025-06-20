#!/usr/bin/env python3
"""
Split NCAS standards by discipline into separate directories.
"""

import csv
import json
import shutil
from pathlib import Path
from collections import defaultdict


def split_ncas_standards():
    """Split NCAS standards, EUs, and EQs by discipline."""
    base_dir = Path("data/output/drupal_prep/05_ncas")
    
    # Read the main standards file
    standards_file = base_dir / "ncas_standards_drupal.csv"
    if not standards_file.exists():
        print(f"Standards file not found: {standards_file}")
        return
    
    # Read all standards
    with open(standards_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_standards = list(reader)
    
    # Group by subject (from field_standard_ref)
    by_discipline = defaultdict(list)
    for std in all_standards:
        # Extract discipline from standard code (e.g., DA:Cr1.1.K -> Dance)
        code = std.get('field_standard_ref', '')
        if ':' in code:
            discipline_code = code.split(':')[0]
            discipline_map = {
                'DA': 'dance',
                'MU': 'music', 
                'TH': 'theatre',
                'VA': 'visual_arts',
                'MA': 'media_arts'
            }
            discipline = discipline_map.get(discipline_code, 'other')
            by_discipline[discipline].append(std)
    
    # Read EUs and EQs
    eus_file = base_dir / "ncas_enduring_understandings.csv"
    eqs_file = base_dir / "ncas_essential_questions.csv"
    
    eus_by_subject = defaultdict(list)
    eqs_by_subject = defaultdict(list)
    
    if eus_file.exists():
        with open(eus_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for eu in reader:
                subject = eu.get('field_subject', '').lower().replace(' ', '_')
                if 'music' in subject:
                    subject = 'music'
                elif 'media' in subject:
                    subject = 'media_arts'
                eus_by_subject[subject].append(eu)
    
    if eqs_file.exists():
        with open(eqs_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for eq in reader:
                subject = eq.get('field_subject', '').lower().replace(' ', '_')
                if 'music' in subject:
                    subject = 'music'
                elif 'media' in subject:
                    subject = 'media_arts'
                eqs_by_subject[subject].append(eq)
    
    # Create hierarchy entries by discipline
    hierarchy_file = base_dir / "ncas_hierarchy_additions.csv"
    hierarchy_by_discipline = defaultdict(list)
    
    if hierarchy_file.exists():
        with open(hierarchy_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            all_hierarchies = list(reader)
            
        # We'll need to analyze which hierarchies belong to which discipline
        # based on the standards that reference them
        hierarchy_ids_by_discipline = defaultdict(set)
        for std in all_standards:
            code = std.get('field_standard_ref', '')
            if ':' in code:
                discipline_code = code.split(':')[0]
                discipline_map = {
                    'DA': 'dance',
                    'MU': 'music',
                    'TH': 'theatre', 
                    'VA': 'visual_arts',
                    'MA': 'media_arts'
                }
                discipline = discipline_map.get(discipline_code, 'other')
                hierarchy_id = std.get('field_standards_hierarchy')
                if hierarchy_id:
                    hierarchy_ids_by_discipline[discipline].add(hierarchy_id)
        
        # Now assign hierarchies to disciplines
        for hierarchy in all_hierarchies:
            h_id = hierarchy.get('ID')
            for discipline, ids in hierarchy_ids_by_discipline.items():
                if h_id in ids:
                    hierarchy_by_discipline[discipline].append(hierarchy)
                    break
    
    # Write files for each discipline
    for discipline, standards in by_discipline.items():
        if not standards:
            continue
            
        disc_dir = base_dir / discipline
        disc_dir.mkdir(exist_ok=True)
        
        print(f"\nProcessing {discipline}: {len(standards)} standards")
        
        # Write standards
        standards_out = disc_dir / f"{discipline}_standards_drupal.csv"
        with open(standards_out, 'w', newline='', encoding='utf-8') as f:
            if standards:
                writer = csv.DictWriter(f, fieldnames=standards[0].keys())
                writer.writeheader()
                writer.writerows(standards)
        
        # Write EUs
        eus = eus_by_subject.get(discipline, [])
        if eus:
            eus_out = disc_dir / f"{discipline}_enduring_understandings.csv"
            with open(eus_out, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=eus[0].keys())
                writer.writeheader()
                writer.writerows(eus)
            print(f"  - {len(eus)} EUs")
        
        # Write EQs
        eqs = eqs_by_subject.get(discipline, [])
        if eqs:
            eqs_out = disc_dir / f"{discipline}_essential_questions.csv"
            with open(eqs_out, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=eqs[0].keys())
                writer.writeheader()
                writer.writerows(eqs)
            print(f"  - {len(eqs)} EQs")
        
        # Write hierarchy additions
        hierarchies = hierarchy_by_discipline.get(discipline, [])
        if hierarchies:
            hierarchy_out = disc_dir / f"{discipline}_hierarchy_additions.csv"
            with open(hierarchy_out, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=hierarchies[0].keys())
                writer.writeheader()
                writer.writerows(hierarchies)
            print(f"  - {len(hierarchies)} hierarchy entries")
        
        # Create discipline summary
        summary = {
            'discipline': discipline,
            'total_standards': len(standards),
            'total_eus': len(eus),
            'total_eqs': len(eqs),
            'hierarchy_entries': len(hierarchies)
        }
        
        with open(disc_dir / f"{discipline}_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
    
    print("\nSplitting complete!")
    
    # Keep the original unified files as well
    print("\nOriginal unified files retained in main directory for reference.")


if __name__ == "__main__":
    split_ncas_standards()