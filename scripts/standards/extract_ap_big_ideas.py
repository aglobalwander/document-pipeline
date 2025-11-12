#!/usr/bin/env python3
"""
Extract Big Ideas, Enduring Understandings, and Learning Objectives from AP course documents.
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


def extract_course_name(file_path: Path) -> str:
    """Extract AP course name from filename."""
    name = file_path.stem.replace('_output', '').replace('ap-', '')
    name = name.replace('-course-and-exam-description', '')
    # Convert to title case
    return ' '.join(word.capitalize() for word in name.split('-'))


def extract_ap_big_ideas(file_path: Path) -> Dict:
    """Extract Big Ideas, EUs, and LOs from AP document."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = {
        'big_ideas': [],
        'enduring_understandings': [],
        'learning_objectives': [],
        'essential_knowledge': [],
        'relationships': []
    }
    
    # Different AP courses use different formats
    # Pattern 1: "BIG IDEA 1: TITLE (CODE)"
    # Pattern 2: "Big Idea 1 (CODE): Title"
    # Pattern 3: "BIG IDEA 1" followed by title on next line
    
    lines = content.split('\n')
    
    current_big_idea = None
    current_eu = None
    current_lo = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Pattern for Big Ideas
        big_idea_match1 = re.match(r'^BIG IDEA (\d+)[:\s]+([A-Z\s]+)(?:\s*\(([A-Z]+)\))?', line)
        big_idea_match2 = re.match(r'^Big Idea (\d+)\s*\(([A-Z]+)\)[:\s]+(.+)', line)
        big_idea_match3 = re.match(r'^BIG IDEA (\d+)$', line)
        
        if big_idea_match1:
            # Extract from pattern 1
            bi_num = big_idea_match1.group(1)
            bi_title = big_idea_match1.group(2).strip()
            bi_code = big_idea_match1.group(3) if big_idea_match1.group(3) else f"BI{bi_num}"
            
            # Look for description on next lines
            description = ""
            j = i + 1
            while j < len(lines) and j < i + 5:
                next_line = lines[j].strip()
                if next_line and not re.match(r'^(BIG IDEA|Enduring Understanding|Learning Objective)', next_line):
                    description += " " + next_line
                    j += 1
                else:
                    break
            
            current_big_idea = {
                'number': bi_num,
                'code': bi_code,
                'title': bi_title,
                'description': description.strip(),
                'id': generate_unique_id(f"{bi_code}_{bi_title}", 'BI_')
            }
            results['big_ideas'].append(current_big_idea)
            i = j
            continue
            
        elif big_idea_match2:
            # Extract from pattern 2
            bi_num = big_idea_match2.group(1)
            bi_code = big_idea_match2.group(2)
            bi_title = big_idea_match2.group(3).strip()
            
            current_big_idea = {
                'number': bi_num,
                'code': bi_code,
                'title': bi_title,
                'description': "",
                'id': generate_unique_id(f"{bi_code}_{bi_title}", 'BI_')
            }
            results['big_ideas'].append(current_big_idea)
            
        elif big_idea_match3:
            # Pattern 3: BIG IDEA followed by number
            bi_num = big_idea_match3.group(1)
            # Look for title and code on next lines
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Try to extract title and code
                title_match = re.match(r'^([^(]+)(?:\s*\(([A-Z]+)\))?', next_line)
                if title_match:
                    bi_title = title_match.group(1).strip()
                    bi_code = title_match.group(2) if title_match.group(2) else f"BI{bi_num}"
                    
                    current_big_idea = {
                        'number': bi_num,
                        'code': bi_code,
                        'title': bi_title,
                        'description': "",
                        'id': generate_unique_id(f"{bi_code}_{bi_title}", 'BI_')
                    }
                    results['big_ideas'].append(current_big_idea)
                    i += 1
        
        # Pattern for Enduring Understandings
        eu_match1 = re.match(r'^Enduring Understanding\s*([0-9A-Z\.\-]+)[:\s]*(.+)?', line)
        eu_match2 = re.match(r'^EU\s*([0-9A-Z\.\-]+)[:\s]*(.+)?', line)
        eu_match3 = re.match(r'^([A-Z]{3})-(\d+\.\d+)[:\s]*(.+)', line)  # e.g., "EVO-1.1: ..."
        
        if eu_match1 or eu_match2 or eu_match3:
            if eu_match1:
                eu_code = eu_match1.group(1)
                eu_text = eu_match1.group(2) if eu_match1.group(2) else ""
            elif eu_match2:
                eu_code = eu_match2.group(1)
                eu_text = eu_match2.group(2) if eu_match2.group(2) else ""
            else:  # eu_match3
                eu_code = f"{eu_match3.group(1)}-{eu_match3.group(2)}"
                eu_text = eu_match3.group(3)
            
            # If text is empty, look on next line
            if not eu_text and i + 1 < len(lines):
                eu_text = lines[i + 1].strip()
                i += 1
            
            if eu_text:
                current_eu = {
                    'code': eu_code,
                    'text': eu_text,
                    'big_idea': current_big_idea['code'] if current_big_idea else None,
                    'id': generate_unique_id(f"{eu_code}_{eu_text}", 'EU_')
                }
                results['enduring_understandings'].append(current_eu)
                
                # Create relationship
                if current_big_idea:
                    results['relationships'].append({
                        'big_idea_id': current_big_idea['id'],
                        'eu_id': current_eu['id'],
                        'type': 'big_idea_to_eu'
                    })
        
        # Pattern for Learning Objectives
        lo_match1 = re.match(r'^Learning Objective\s*([0-9A-Z\.\-]+)[:\s]*(.+)?', line)
        lo_match2 = re.match(r'^LO\s*([0-9A-Z\.\-]+)[:\s]*(.+)?', line)
        lo_match3 = re.match(r'^([A-Z]{3})-(\d+\.\d+\.\d+)[:\s]*(.+)', line)  # e.g., "EVO-1.1.1: ..."
        
        if lo_match1 or lo_match2 or lo_match3:
            if lo_match1:
                lo_code = lo_match1.group(1)
                lo_text = lo_match1.group(2) if lo_match1.group(2) else ""
            elif lo_match2:
                lo_code = lo_match2.group(1)
                lo_text = lo_match2.group(2) if lo_match2.group(2) else ""
            else:  # lo_match3
                lo_code = f"{lo_match3.group(1)}-{lo_match3.group(2)}"
                lo_text = lo_match3.group(3)
            
            # If text is empty, look on next line
            if not lo_text and i + 1 < len(lines):
                lo_text = lines[i + 1].strip()
                i += 1
            
            if lo_text:
                current_lo = {
                    'code': lo_code,
                    'text': lo_text,
                    'eu': current_eu['code'] if current_eu else None,
                    'big_idea': current_big_idea['code'] if current_big_idea else None,
                    'id': generate_unique_id(f"{lo_code}_{lo_text}", 'LO_')
                }
                results['learning_objectives'].append(current_lo)
        
        i += 1
    
    return results


def process_ap_directory(input_dir: Path, output_dir: Path):
    """Process all AP course documents."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Aggregate data
    all_big_ideas = []
    all_eus = []
    all_los = []
    
    # Process each AP file
    ap_files = list(input_dir.glob("ap-*.txt"))
    print(f"Found {len(ap_files)} AP course files to process")
    
    for file_path in ap_files:
        course_name = extract_course_name(file_path)
        print(f"Processing: {course_name}")
        
        try:
            results = extract_ap_big_ideas(file_path)
            
            # Add course info to each item
            for bi in results['big_ideas']:
                bi['course'] = course_name
                bi['framework'] = 'AP'
                all_big_ideas.append(bi)
            
            for eu in results['enduring_understandings']:
                eu['course'] = course_name
                eu['framework'] = 'AP'
                all_eus.append(eu)
            
            for lo in results['learning_objectives']:
                lo['course'] = course_name
                lo['framework'] = 'AP'
                all_los.append(lo)
            
            print(f"  Found: {len(results['big_ideas'])} Big Ideas, "
                  f"{len(results['enduring_understandings'])} EUs, "
                  f"{len(results['learning_objectives'])} LOs")
            
        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")
    
    # Write CSV files
    write_big_ideas_csv(all_big_ideas, output_dir / 'ap_big_ideas.csv')
    write_ap_eus_csv(all_eus, output_dir / 'ap_enduring_understandings.csv')
    write_learning_objectives_csv(all_los, output_dir / 'ap_learning_objectives.csv')
    
    # Write summary
    summary = {
        'total_big_ideas': len(all_big_ideas),
        'total_eus': len(all_eus),
        'total_los': len(all_los),
        'courses': list(set(bi['course'] for bi in all_big_ideas))
    }
    
    with open(output_dir / 'ap_extraction_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nExtraction complete!")
    print(f"  Big Ideas: {len(all_big_ideas)}")
    print(f"  Enduring Understandings: {len(all_eus)}")
    print(f"  Learning Objectives: {len(all_los)}")


def write_big_ideas_csv(big_ideas: List[Dict], output_path: Path):
    """Write Big Ideas to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['uuid', 'title', 'body/value', 'field_framework', 'field_course',
                        'field_code', 'field_number'])
        
        for bi in big_ideas:
            uuid = f"bi-{bi['id']}"
            title = f"{bi['code']}: {bi['title']}"
            body = f"<p><strong>{bi['title']}</strong></p><p>{bi['description']}</p>"
            
            writer.writerow([
                uuid,
                title,
                body,
                'AP',
                bi['course'],
                bi['code'],
                bi['number']
            ])


def write_ap_eus_csv(eus: List[Dict], output_path: Path):
    """Write AP Enduring Understandings to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['uuid', 'title', 'body/value', 'field_framework', 'field_course',
                        'field_code', 'field_big_idea_ref'])
        
        for eu in eus:
            uuid = f"eu-{eu['id']}"
            title = f"{eu['code']}: {eu['text'][:100]}..." if len(eu['text']) > 100 else f"{eu['code']}: {eu['text']}"
            body = f"<p>{eu['text']}</p>"
            
            writer.writerow([
                uuid,
                title,
                body,
                'AP',
                eu['course'],
                eu['code'],
                eu.get('big_idea', '')
            ])


def write_learning_objectives_csv(los: List[Dict], output_path: Path):
    """Write Learning Objectives to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['uuid', 'title', 'body/value', 'field_framework', 'field_course',
                        'field_code', 'field_eu_ref', 'field_big_idea_ref'])
        
        for lo in los:
            uuid = f"lo-{lo['id']}"
            title = f"{lo['code']}: {lo['text'][:100]}..." if len(lo['text']) > 100 else f"{lo['code']}: {lo['text']}"
            body = f"<p>{lo['text']}</p>"
            
            writer.writerow([
                uuid,
                title,
                body,
                'AP',
                lo['course'],
                lo['code'],
                lo.get('eu', ''),
                lo.get('big_idea', '')
            ])


def main():
    """Main execution function."""
    input_dir = Path("data/output/text/standards/ap_guides")
    output_dir = Path("data/output/drupal_prep/10_ap")
    
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        return
    
    process_ap_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()