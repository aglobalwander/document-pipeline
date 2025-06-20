# Standards ETL Migration Plan

## Overview
Migrate the standards extraction and processing work from `pipeline-documents` to the main Drupal ETL repository at `/Users/scottwilliams/Documents/Develop Projects/master_projects/drupal/etl_drupal/`.

## Source Structure (pipeline-documents)
```
pipeline-documents/
├── data/output/drupal_prep/         # Processed standards ready for import
│   ├── 01_ela_common_core/          # (empty - already in your CSV)
│   ├── 02_math_common_core/         # 480 standards extracted
│   ├── 03_c3/                       # 324 indicators extracted
│   ├── 04_ngss/                     # 136 performance expectations extracted
│   ├── 05_ncas/                     # 507 standards + EUs/EQs
│   │   ├── dance/                   # 19 standards, 11 EUs, 15 EQs
│   │   ├── music/                   # 427 standards, 25 EUs, 27 EQs
│   │   ├── theatre/                 # 11 standards, 12 EUs, 12 EQs
│   │   ├── visual_arts/             # 50 standards
│   │   └── media_arts/              # (check contents)
│   └── README.md                    # Documentation
└── scripts/                         # Extraction scripts
    ├── extract_ncas_eus_eqs.py
    ├── extract_math_common_core_v2.py
    ├── extract_c3_framework.py
    ├── extract_ngss_standards.py
    ├── map_ncas_to_drupal_hierarchy.py
    ├── split_ncas_by_discipline.py
    └── extract_ap_big_ideas.py      # For future use

```

## Target Structure (etl_drupal)
```
etl_drupal/
├── data/standards/
│   ├── official frameworks/          # Already has source PDFs
│   │   ├── Common Core ELA/
│   │   ├── Common Core Math/
│   │   ├── NCAS/
│   │   ├── NGSS/
│   │   └── Social Studies C3/
│   └── extracted/                   # NEW - Add extracted standards
│       ├── math_common_core/
│       ├── c3_framework/
│       ├── ngss/
│       └── ncas/
└── scripts/standards/               # NEW - Standards-specific scripts
    ├── extractors/                  # Extraction scripts
    ├── mappers/                     # Hierarchy mapping scripts
    └── utils/                       # Shared utilities
```

## Migration Steps

### 1. Create Directory Structure
```bash
# In etl_drupal directory
mkdir -p data/standards/extracted/{math_common_core,c3_framework,ngss,ncas}
mkdir -p scripts/standards/{extractors,mappers,utils}
```

### 2. Copy Processed Data
```bash
# Copy extracted standards data
cp -r pipeline-documents/data/output/drupal_prep/02_math_common_core/* \
      etl_drupal/data/standards/extracted/math_common_core/

cp -r pipeline-documents/data/output/drupal_prep/03_c3/* \
      etl_drupal/data/standards/extracted/c3_framework/

cp -r pipeline-documents/data/output/drupal_prep/04_ngss/* \
      etl_drupal/data/standards/extracted/ngss/

cp -r pipeline-documents/data/output/drupal_prep/05_ncas/* \
      etl_drupal/data/standards/extracted/ncas/
```

### 3. Migrate Scripts
```bash
# Copy extraction scripts
cp pipeline-documents/scripts/extract_*.py \
   etl_drupal/scripts/standards/extractors/

# Copy mapping scripts  
cp pipeline-documents/scripts/map_*.py \
   etl_drupal/scripts/standards/mappers/

# Copy utility scripts
cp pipeline-documents/scripts/split_*.py \
   etl_drupal/scripts/standards/utils/
```

### 4. Update Script Paths
The scripts will need path updates to work in the new location:
- Change `data/output/drupal_prep/` to `data/standards/extracted/`
- Change `data/output/text/standards/` to `data/standards/official frameworks/`

### 5. Create Integration Script
Create a master script in `etl_drupal/scripts/standards/` to:
- Process all frameworks
- Generate unified import files
- Create import documentation

### 6. Documentation
- Copy the README.md and COMPARISON_ANALYSIS.md
- Create a new standards-specific README in `etl_drupal/data/standards/`
- Document the extraction process and data flow

## Benefits of This Structure

1. **Separation of Concerns**: Standards work is clearly separated from other ETL tasks
2. **Reusability**: Scripts can be re-run when standards are updated
3. **Organization**: Clear distinction between source PDFs, extracted data, and import-ready CSVs
4. **Version Control**: Easy to track changes to standards over time
5. **Integration**: Fits well with your existing ETL structure

## Next Steps

1. Review and approve this plan
2. Execute the migration
3. Test scripts in new location
4. Create unified import process
5. Document the complete workflow