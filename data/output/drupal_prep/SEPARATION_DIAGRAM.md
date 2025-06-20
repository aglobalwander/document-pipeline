# Standards Data Separation

## Current Structure in etl_drupal

```
etl_drupal/
└── data/
    └── standards/                           # EXISTING - DO NOT TOUCH
        ├── atlas_04_standards/              # Existing Atlas standards
        ├── atlas_district_standards_complete/# Existing district standards
        ├── schoology_standards_complete/    # Existing Schoology standards
        ├── official frameworks/             # Source PDFs
        └── standard.csv                     # Existing standards CSV
```

## New Structure (Completely Separate)

```
etl_drupal/
└── data/
    ├── standards/                           # EXISTING - UNCHANGED
    └── standards_extracted_2024/            # NEW - SEPARATE DIRECTORY
        ├── processed/                       # Import-ready CSVs
        │   ├── math_common_core/
        │   ├── c3_framework/
        │   ├── ngss/
        │   └── ncas/
        ├── scripts/                         # Processing scripts
        ├── documentation/                   # Process docs
        └── README.md                        # Explains this is separate
```

## Key Points

1. **Complete Separation**: The new `standards_extracted_2024` directory is at the same level as `standards`, not inside it
2. **No Overwrites**: Nothing in the existing `standards/` directory is modified
3. **Clear Naming**: The year in the directory name makes it clear this is a new extraction
4. **Self-Contained**: All scripts, data, and documentation for the new extraction are in one place
5. **Easy to Remove**: If needed, the entire `standards_extracted_2024` directory can be removed without affecting existing data

## Migration Command

To execute the migration, run from the pipeline-documents directory:

```bash
python scripts/migrate_to_drupal_etl.py
```

This will:
- Create the new `standards_extracted_2024` directory structure
- Copy all processed standards data
- Copy all extraction scripts
- Create documentation
- Generate a migration summary

## Benefits

- ✅ No risk to existing data
- ✅ Clear separation of concerns
- ✅ Easy to compare old vs new extractions
- ✅ Can run both systems in parallel
- ✅ Simple to integrate later if desired