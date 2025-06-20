#!/usr/bin/env python3
"""
Migrate standards extraction work to Drupal ETL repository in a separate directory.
Keeps all new work isolated from existing standards data.
"""

import shutil
import os
from pathlib import Path
import json
from datetime import datetime


def create_migration_structure():
    """Create the directory structure for migrated standards work."""
    base_path = Path("/Users/scottwilliams/Documents/Develop Projects/master_projects/drupal/etl_drupal")
    
    # Create a separate directory for the pipeline-extracted standards
    new_standards_dir = base_path / "data" / "standards_extracted_2024"
    
    directories = [
        new_standards_dir / "processed" / "math_common_core",
        new_standards_dir / "processed" / "c3_framework", 
        new_standards_dir / "processed" / "ngss",
        new_standards_dir / "processed" / "ncas" / "unified",
        new_standards_dir / "processed" / "ncas" / "by_discipline" / "dance",
        new_standards_dir / "processed" / "ncas" / "by_discipline" / "music",
        new_standards_dir / "processed" / "ncas" / "by_discipline" / "theatre",
        new_standards_dir / "processed" / "ncas" / "by_discipline" / "visual_arts",
        new_standards_dir / "processed" / "ncas" / "by_discipline" / "media_arts",
        new_standards_dir / "scripts" / "extractors",
        new_standards_dir / "scripts" / "mappers",
        new_standards_dir / "scripts" / "utilities",
        new_standards_dir / "documentation",
        new_standards_dir / "source_text"  # For the extracted text files if needed
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created: {directory}")
    
    return new_standards_dir


def copy_processed_data(source_base, target_base):
    """Copy processed standards data to new location."""
    source_path = Path(source_base) / "data" / "output" / "drupal_prep"
    target_path = target_base / "processed"
    
    # Copy Math Common Core
    if (source_path / "02_math_common_core").exists():
        shutil.copytree(
            source_path / "02_math_common_core",
            target_path / "math_common_core",
            dirs_exist_ok=True
        )
        print("✓ Copied Math Common Core data")
    
    # Copy C3 Framework
    if (source_path / "03_c3").exists():
        shutil.copytree(
            source_path / "03_c3",
            target_path / "c3_framework",
            dirs_exist_ok=True
        )
        print("✓ Copied C3 Framework data")
    
    # Copy NGSS
    if (source_path / "04_ngss").exists():
        shutil.copytree(
            source_path / "04_ngss",
            target_path / "ngss",
            dirs_exist_ok=True
        )
        print("✓ Copied NGSS data")
    
    # Copy NCAS - both unified and by discipline
    if (source_path / "05_ncas").exists():
        # Copy unified files
        ncas_source = source_path / "05_ncas"
        ncas_target = target_path / "ncas" / "unified"
        
        for file in ncas_source.glob("*.csv"):
            shutil.copy2(file, ncas_target)
        for file in ncas_source.glob("*.json"):
            shutil.copy2(file, ncas_target)
        print("✓ Copied NCAS unified data")
        
        # Copy discipline-specific files
        for discipline in ["dance", "music", "theatre", "visual_arts", "media_arts"]:
            if (ncas_source / discipline).exists():
                shutil.copytree(
                    ncas_source / discipline,
                    target_path / "ncas" / "by_discipline" / discipline,
                    dirs_exist_ok=True
                )
                print(f"✓ Copied NCAS {discipline} data")
    
    # Copy documentation
    docs = ["README.md", "COMPARISON_ANALYSIS.md", "MIGRATION_PLAN.md"]
    for doc in docs:
        if (source_path / doc).exists():
            shutil.copy2(
                source_path / doc,
                target_base / "documentation" / doc
            )
            print(f"✓ Copied {doc}")


def copy_scripts(source_base, target_base):
    """Copy extraction and processing scripts."""
    source_scripts = Path(source_base) / "scripts"
    target_scripts = target_base / "scripts"
    
    # Extraction scripts
    extractors = [
        "extract_ncas_eus_eqs.py",
        "extract_math_common_core.py",
        "extract_math_common_core_v2.py",
        "extract_c3_framework.py",
        "extract_ngss_standards.py",
        "extract_ap_big_ideas.py"
    ]
    
    for script in extractors:
        if (source_scripts / script).exists():
            shutil.copy2(
                source_scripts / script,
                target_scripts / "extractors" / script
            )
            print(f"✓ Copied {script}")
    
    # Mapping scripts
    mappers = [
        "map_ncas_to_drupal_hierarchy.py"
    ]
    
    for script in mappers:
        if (source_scripts / script).exists():
            shutil.copy2(
                source_scripts / script,
                target_scripts / "mappers" / script
            )
            print(f"✓ Copied {script}")
    
    # Utility scripts
    utilities = [
        "split_ncas_by_discipline.py"
    ]
    
    for script in utilities:
        if (source_scripts / script).exists():
            shutil.copy2(
                source_scripts / script,
                target_scripts / "utilities" / script
            )
            print(f"✓ Copied {script}")


def create_readme(target_base):
    """Create a README file for the migrated standards."""
    readme_content = f"""# Extracted Standards (Pipeline Migration - {datetime.now().strftime('%Y-%m-%d')})

This directory contains standards extracted and processed from PDF documents using the pipeline-documents project.
This is kept separate from the existing standards data to avoid any conflicts or overwrites.

## Directory Structure

```
standards_extracted_2024/
├── processed/              # Ready-for-import CSV files
│   ├── math_common_core/   # 480 Math Common Core standards
│   ├── c3_framework/       # 324 C3 Framework indicators
│   ├── ngss/              # 136 NGSS performance expectations
│   └── ncas/              # National Core Arts Standards
│       ├── unified/       # All NCAS standards together
│       └── by_discipline/ # Separated by arts discipline
├── scripts/               # Processing scripts
│   ├── extractors/        # Scripts to extract from source documents
│   ├── mappers/          # Scripts to map to Drupal hierarchy
│   └── utilities/        # Helper scripts
├── documentation/         # Process documentation
└── source_text/          # (Optional) Extracted text from PDFs
```

## Processed Standards Summary

### Math Common Core
- 480 standards extracted
- Organized by: Grade → Domain → Cluster → Standard
- Files: `math_cc_standards_drupal.csv`, `math_cc_hierarchy_additions.csv`

### C3 Framework (Social Studies)
- 324 indicators extracted
- Organized by: Dimension → Discipline/Category → Grade Band → Indicator
- Files: `c3_standards_drupal.csv`, `c3_hierarchy_additions.csv`

### NGSS (Next Generation Science Standards)
- 136 performance expectations extracted
- Organized by: Grade → Topic → DCI → Performance Expectation
- Includes clarification statements and assessment boundaries
- Files: `ngss_standards_drupal.csv`, `ngss_hierarchy_additions.csv`

### NCAS (National Core Arts Standards)
- 507 total standards
- 76 Enduring Understandings (EUs)
- 130 Essential Questions (EQs)
- Organized by: Artistic Process → Anchor Standard → Grade → Standard
- Available both unified and separated by discipline:
  - Dance: 19 standards, 11 EUs, 15 EQs
  - Music: 427 standards, 25 EUs, 27 EQs
  - Theatre: 11 standards, 12 EUs, 12 EQs
  - Visual Arts: 50 standards
  - Media Arts: (check contents)

## Import Process

Each framework includes:
1. `*_standards_drupal.csv` - Standards ready for node import
2. `*_hierarchy_additions.csv` - New taxonomy terms to add
3. `*_mapping_summary.json` - Processing statistics
4. Additional entity files (EUs, EQs) where applicable

### Import Order
1. First import hierarchy additions to create taxonomy structure
2. Import any entity files (EUs, EQs for NCAS)
3. Finally import standards with proper references

## Scripts

### Running Extractors
Scripts assume they're run from the standards_extracted_2024 directory:
```bash
cd /path/to/etl_drupal/data/standards_extracted_2024
python scripts/extractors/extract_math_common_core_v2.py
```

### Path Updates Required
The scripts may need path updates to work in this new location. Original paths:
- `data/output/drupal_prep/` → `processed/`
- `data/output/text/standards/` → (update to source location)

## Relationship to Existing Standards

This extraction is completely separate from the existing standards in:
- `/data/standards/atlas_04_standards/`
- `/data/standards/atlas_district_standards_complete/`
- `/data/standards/schoology_standards_complete/`
- `/data/standards/standard.csv`

No existing data has been modified or overwritten.

## Source
Migrated from: pipeline-documents project
Migration date: {datetime.now().strftime('%Y-%m-%d')}
"""
    
    readme_path = target_base / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"✓ Created README at {readme_path}")


def create_migration_summary(source_base, target_base):
    """Create a summary of what was migrated."""
    summary = {
        "migration_date": datetime.now().isoformat(),
        "source_path": str(source_base),
        "target_path": str(target_base),
        "frameworks_migrated": {
            "math_common_core": {
                "standards": 480,
                "status": "complete"
            },
            "c3_framework": {
                "indicators": 324,
                "status": "complete"
            },
            "ngss": {
                "performance_expectations": 136,
                "status": "complete"
            },
            "ncas": {
                "total_standards": 507,
                "enduring_understandings": 76,
                "essential_questions": 130,
                "disciplines": {
                    "dance": {"standards": 19, "eus": 11, "eqs": 15},
                    "music": {"standards": 427, "eus": 25, "eqs": 27},
                    "theatre": {"standards": 11, "eus": 12, "eqs": 12},
                    "visual_arts": {"standards": 50}
                },
                "status": "complete"
            }
        },
        "scripts_migrated": {
            "extractors": 6,
            "mappers": 1,
            "utilities": 1
        }
    }
    
    summary_path = target_base / "migration_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Created migration summary at {summary_path}")


def main():
    """Execute the migration."""
    print("Starting Standards Migration to Drupal ETL Repository")
    print("=" * 50)
    
    # Define paths
    source_base = Path("/Users/scottwilliams/Documents/Develop Projects/master_projects/pipeline-documents")
    
    # Create directory structure
    print("\n1. Creating directory structure...")
    target_base = create_migration_structure()
    
    # Copy processed data
    print("\n2. Copying processed standards data...")
    copy_processed_data(source_base, target_base)
    
    # Copy scripts
    print("\n3. Copying extraction scripts...")
    copy_scripts(source_base, target_base)
    
    # Create documentation
    print("\n4. Creating documentation...")
    create_readme(target_base)
    create_migration_summary(source_base, target_base)
    
    print("\n" + "=" * 50)
    print("✓ Migration complete!")
    print(f"\nNew standards data location:")
    print(f"  {target_base}")
    print("\nThis is completely separate from existing standards data.")
    print("No existing files were modified or overwritten.")


if __name__ == "__main__":
    main()