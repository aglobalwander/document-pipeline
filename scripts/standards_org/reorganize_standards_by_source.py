#!/usr/bin/env python3
"""
Reorganize standards text files based on their original PDF directory structure.
"""

import sys
import shutil
from pathlib import Path
import json


def find_original_pdf_path(txt_filename: str, pdf_dirs: list[Path]) -> Path:
    """Find the original PDF path for a given text file."""
    # Remove _output.txt suffix to get original PDF name
    pdf_name = txt_filename.replace("_output.txt", ".pdf")
    
    # Search for this PDF in all directories
    for pdf_dir in pdf_dirs:
        for pdf_path in pdf_dir.rglob("*.pdf"):
            if pdf_path.name == pdf_name:
                return pdf_path
    
    return None


def main():
    """Reorganize text files based on original PDF structure."""
    # Define source directories
    pdf_sources = [
        Path("data/input/pdfs/standards"),
        Path("/Volumes/PortableSSD/data/input/standards_frameworks"),
        Path("/Volumes/PortableSSD/data/input/Subject Briefs")
    ]
    
    # Output directory
    output_base = Path("data/output/text/standards_reorganized")
    
    # Current text files directory
    current_dir = Path("data/output/text/standards")
    
    print("REORGANIZING STANDARDS BY ORIGINAL STRUCTURE")
    print("=" * 70)
    
    # Check which source directories exist
    available_sources = []
    for source in pdf_sources:
        if source.exists():
            available_sources.append(source)
            print(f"✓ Found source: {source}")
        else:
            print(f"✗ Missing source: {source}")
    
    if not available_sources:
        print("\nError: No source directories found!")
        return
    
    print(f"\nScanning text files in: {current_dir}")
    
    # Get all text files
    all_txt_files = list(current_dir.rglob("*_output.txt"))
    print(f"Found {len(all_txt_files)} text files to reorganize")
    
    # Track statistics
    stats = {
        'total': len(all_txt_files),
        'moved': 0,
        'not_found': 0,
        'by_framework': {}
    }
    
    not_found_files = []
    
    # Process each text file
    for i, txt_file in enumerate(all_txt_files, 1):
        if i % 20 == 0:
            print(f"  Processing: {i}/{len(all_txt_files)} files...")
        
        # Find original PDF
        original_pdf = find_original_pdf_path(txt_file.name, available_sources)
        
        if original_pdf:
            # Determine the framework from the original path
            # Get the relative path from the source directory
            for source in available_sources:
                try:
                    rel_path = original_pdf.relative_to(source)
                    
                    # Special handling for Subject Briefs
                    if "Subject Briefs" in str(source):
                        framework = "subject_briefs"
                        output_dir = output_base / framework
                    elif len(rel_path.parts) > 1:
                        # The framework is the first directory in the path
                        framework = rel_path.parts[0]
                        # Create output directory maintaining structure
                        if len(rel_path.parts) > 2:
                            # Has subdirectories
                            output_dir = output_base / Path(*rel_path.parts[:-1])
                        else:
                            # Direct child of framework
                            output_dir = output_base / framework
                    else:
                        # Files directly in the source directory
                        framework = source.name
                        output_dir = output_base / framework
                    
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file to new location
                    dest_path = output_dir / txt_file.name
                    shutil.copy2(txt_file, dest_path)
                    
                    # Update statistics
                    stats['moved'] += 1
                    if framework not in stats['by_framework']:
                        stats['by_framework'][framework] = 0
                    stats['by_framework'][framework] += 1
                    
                    break
                except ValueError:
                    # Not relative to this source, try next
                    continue
        else:
            stats['not_found'] += 1
            not_found_files.append(txt_file.name)
            print(f"\n  ⚠️  Could not find original PDF for: {txt_file.name}")
    
    # Create summary report
    print("\n" + "="*70)
    print("REORGANIZATION COMPLETE")
    print("="*70)
    print(f"Total files processed: {stats['total']}")
    print(f"Successfully reorganized: {stats['moved']}")
    print(f"Original PDF not found: {stats['not_found']}")
    
    print("\nFiles by framework:")
    print("-" * 50)
    for framework, count in sorted(stats['by_framework'].items()):
        print(f"{framework:30} {count:3} files")
    
    if not_found_files:
        print(f"\nFiles without original PDFs ({len(not_found_files)}):")
        for f in not_found_files[:10]:
            print(f"  • {f}")
        if len(not_found_files) > 10:
            print(f"  ... and {len(not_found_files) - 10} more")
    
    # Save reorganization report
    report_path = output_base / "REORGANIZATION_REPORT.json"
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nOutput directory: {output_base}")
    print(f"Report saved to: {report_path}")
    
    # List the new structure
    print("\nNew directory structure:")
    for framework_dir in sorted(output_base.iterdir()):
        if framework_dir.is_dir():
            file_count = len(list(framework_dir.rglob("*.txt")))
            print(f"  {framework_dir.name}/ ({file_count} files)")


if __name__ == "__main__":
    main()