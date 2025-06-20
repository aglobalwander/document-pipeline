#!/usr/bin/env python3
"""
Organize standards framework PDFs for processing.
Creates proper input/output directory structure.
"""

import os
import sys
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def organize_pdfs(source_dir: Path, target_base: Path = None):
    """
    Organize PDFs into proper structure for pipeline processing.
    
    Creates:
    - data/input/pdfs/standards/[framework_name]/original_files.pdf
    - data/output/text/standards/[framework_name]/
    - data/output/markdown/standards/[framework_name]/
    - data/output/json/standards/[framework_name]/
    """
    
    if target_base is None:
        target_base = Path("data")
    
    # Create directory structure
    input_base = target_base / "input/pdfs/standards"
    output_base = target_base / "output"
    
    # Create output directories
    for format_type in ['text', 'markdown', 'json']:
        (output_base / format_type / 'standards').mkdir(parents=True, exist_ok=True)
    
    # Find all PDFs in source directory
    if source_dir.is_file() and source_dir.suffix.lower() == '.pdf':
        pdf_files = [source_dir]
    else:
        pdf_files = list(source_dir.rglob("*.pdf"))
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    # Organize files by framework (based on directory or filename patterns)
    frameworks = {}
    
    for pdf_path in pdf_files:
        # Try to determine framework from path
        parts = pdf_path.parts
        
        # Look for common framework indicators
        framework = None
        filename_lower = pdf_path.stem.lower()
        
        # Common standards patterns
        if 'ngss' in filename_lower:
            framework = 'ngss'
        elif 'ccss' in filename_lower or 'common_core' in filename_lower:
            framework = 'common_core'
        elif 'c3' in filename_lower:
            framework = 'c3_framework'
        elif 'cas' in filename_lower or 'colorado' in filename_lower:
            framework = 'colorado_standards'
        elif 'teks' in filename_lower or 'texas' in filename_lower:
            framework = 'texas_standards'
        elif 'framework' in filename_lower:
            framework = 'general_framework'
        else:
            # Use parent directory name if available
            if len(parts) > 1:
                framework = parts[-2].lower().replace(' ', '_')
            else:
                framework = 'uncategorized'
        
        if framework not in frameworks:
            frameworks[framework] = []
        frameworks[framework].append(pdf_path)
    
    # Copy files to organized structure
    copied_files = []
    
    for framework, files in frameworks.items():
        framework_input_dir = input_base / framework
        framework_input_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"\nOrganizing {framework} ({len(files)} files):")
        
        for pdf_path in files:
            # Create destination path
            dest_path = framework_input_dir / pdf_path.name
            
            # Copy file if it doesn't exist or is different
            if not dest_path.exists() or dest_path.stat().st_size != pdf_path.stat().st_size:
                shutil.copy2(pdf_path, dest_path)
                logger.info(f"  - Copied: {pdf_path.name}")
                copied_files.append((pdf_path, dest_path))
            else:
                logger.info(f"  - Already exists: {pdf_path.name}")
    
    # Create README for the structure
    readme_path = target_base / "input/pdfs/standards/README.md"
    with open(readme_path, 'w') as f:
        f.write("# Standards Framework PDFs\n\n")
        f.write("This directory contains organized standards framework PDFs.\n\n")
        f.write("## Structure\n\n")
        
        for framework in sorted(frameworks.keys()):
            f.write(f"- `{framework}/` - {len(frameworks[framework])} documents\n")
        
        f.write("\n## Processing\n\n")
        f.write("To analyze these PDFs and determine best OCR method:\n")
        f.write("```bash\n")
        f.write("python scripts/analyze_pdfs_for_ocr.py data/input/pdfs/standards --create-script\n")
        f.write("```\n\n")
        f.write("To process all PDFs:\n")
        f.write("```bash\n")
        f.write("bash data/output/process_standards_pdfs.sh\n")
        f.write("```\n")
    
    logger.info(f"\nOrganization complete!")
    logger.info(f"Input directory: {input_base}")
    logger.info(f"Frameworks organized: {len(frameworks)}")
    logger.info(f"Total files: {sum(len(files) for files in frameworks.values())}")
    logger.info(f"\nNext steps:")
    logger.info(f"1. Run: python scripts/analyze_pdfs_for_ocr.py {input_base} --create-script")
    logger.info(f"2. Review the analysis at: data/output/pdf_analysis_index.json")
    logger.info(f"3. Process PDFs with: bash data/output/process_standards_pdfs.sh")
    
    return frameworks


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Organize standards PDFs for processing")
    parser.add_argument('source_directory', help='Directory containing PDFs to organize')
    parser.add_argument('--target-base', help='Base directory for organized structure (default: data)', 
                       default='data')
    
    args = parser.parse_args()
    
    source_dir = Path(args.source_directory)
    target_base = Path(args.target_base)
    
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)
    
    organize_pdfs(source_dir, target_base)


if __name__ == "__main__":
    main()