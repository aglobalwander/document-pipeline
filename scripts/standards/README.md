# Standards Extraction Scripts

This directory contains scripts for extracting and processing educational standards from PDF documents that have been converted to text.

## Scripts Overview

### Extraction Scripts

#### `extract_ncas_eus_eqs.py`
- Extracts National Core Arts Standards (NCAS) from text files
- Identifies and extracts Enduring Understandings (EUs) and Essential Questions (EQs)
- Creates separate CSV files for standards, EUs, and EQs with proper relationships
- Output: 507 standards, 76 EUs, 130 EQs

#### `extract_math_common_core_v2.py`
- Extracts Math Common Core standards from text files
- Parses complex document structure to identify grade levels, domains, clusters, and standards
- Handles K-8 standards with proper hierarchical organization
- Output: 480 standards
- Note: `extract_math_common_core.py` is the earlier version

#### `extract_c3_framework.py`
- Extracts C3 Framework (Social Studies) indicators
- Organizes by Dimension, Discipline, Grade Band, and Indicator
- Handles all 4 dimensions including Civics, Economics, Geography, History, Psychology, Sociology
- Output: 324 indicators

#### `extract_ngss_standards.py`
- Extracts Next Generation Science Standards (NGSS) performance expectations
- Includes clarification statements and assessment boundaries
- Organizes by Grade, Topic, and Disciplinary Core Idea (DCI)
- Output: 136 performance expectations

#### `extract_ap_big_ideas.py`
- Extracts Advanced Placement (AP) Big Ideas, Enduring Understandings, and Learning Objectives
- Designed for future use (AP standards to be processed last per user request)

### Processing Scripts

#### `map_ncas_to_drupal_hierarchy.py`
- Maps extracted NCAS standards to Drupal's 4-level hierarchy
- Creates hierarchy entries and standard entries with proper taxonomy references
- Generates CSV files ready for Drupal import

#### `split_ncas_by_discipline.py`
- Splits unified NCAS extraction into separate files by arts discipline
- Creates separate directories for Dance, Music, Theatre, Visual Arts, and Media Arts
- Maintains EU/EQ relationships within each discipline

### Migration Script

#### `migrate_to_drupal_etl.py`
- Migrates all processed standards data to the Drupal ETL repository
- Creates a separate `standards_extracted_2024` directory to avoid conflicts
- Copies all scripts, data, and documentation
- Maintains complete separation from existing standards data

## Usage

All scripts are designed to be run from the pipeline-documents root directory:

```bash
cd /path/to/pipeline-documents
python scripts/standards/extract_ncas_eus_eqs.py
```

## Output Location

Processed data is saved to: `data/output/drupal_prep/`

Each framework has its own numbered directory:
- `01_ela_common_core/` - (empty - already in existing CSV)
- `02_math_common_core/` - Math Common Core standards
- `03_c3/` - C3 Framework indicators
- `04_ngss/` - NGSS performance expectations
- `05_ncas/` - National Core Arts Standards

## Data Flow

1. PDFs are converted to text (using separate document processing pipeline)
2. Extraction scripts parse the text files to identify standards
3. Processing scripts map standards to Drupal's hierarchy structure
4. Migration script moves everything to the Drupal ETL repository

## Notes

- All scripts generate CSV files formatted for Drupal import
- Each framework includes hierarchy additions and standard entries
- NCAS also includes separate entity files for EUs and EQs
- Scripts preserve relationships between standards and supporting concepts