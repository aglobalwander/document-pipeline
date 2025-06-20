# Drupal Standards Import Files

This directory contains all standards frameworks prepared for import into Drupal 11. Each framework is organized in its own numbered directory for sequential processing.

## Directory Structure

```
drupal_prep/
├── 01_ela_common_core/     # English Language Arts Common Core
├── 02_math_common_core/    # Mathematics Common Core
├── 03_c3/                  # College, Career, and Civic Life (C3) Framework
├── 04_ngss/                # Next Generation Science Standards
├── 05_ncas/                # National Core Arts Standards
│   ├── dance/              # Dance standards (if separated)
│   ├── music/              # Music standards (if separated)
│   ├── theatre/            # Theatre standards (if separated)
│   ├── visual_arts/        # Visual Arts standards (if separated)
│   └── media_arts/         # Media Arts standards (if separated)
├── 06_iste/                # International Society for Technology in Education
├── 07_isca/                # (To be confirmed)
├── 08_shape/               # Society of Health and Physical Educators
├── 09_actfl/               # American Council on Teaching of Foreign Languages
├── 10_ap/                  # Advanced Placement (to be done last)
└── 11_ib/                  # International Baccalaureate (to be done last)
```

## File Types

Each framework directory should contain:

1. **Standards Files**
   - `{framework}_standards_drupal.csv` - Main standards nodes
   - `{framework}_hierarchy_additions.csv` - New hierarchy entries to add

2. **Entity Files** (where applicable)
   - `{framework}_essential_questions.csv` - EQ entities
   - `{framework}_enduring_understandings.csv` - EU entities
   - `{framework}_big_ideas.csv` - Big Ideas entities

3. **Supporting Files**
   - `{framework}_mapping_summary.json` - Processing summary
   - `{framework}_extraction_summary.json` - Extraction details

## Import Order

Import should follow this sequence:

1. **Taxonomy Updates** - Import hierarchy_additions.csv first
2. **Entity Creation** - Import EUs, EQs, and Big Ideas
3. **Standards Import** - Import standards with references last

## Field Mappings

### Standards CSV Fields
- `uuid` - Unique identifier
- `title` - Standard code/number
- `body/format` - Always "basic_html"
- `body/value` - Standard text in HTML
- `field_standards_framework` - Framework ID reference
- `field_standards_hierarchy` - Hierarchy term ID
- `field_standards_taxonomy` - Standard type (anchor/standard/substandard)
- `field_org_level_1` through `field_org_level_4` - Organization levels
- `field_standard_ref` - Original standard code
- `field_eu_references` - EU entity references
- `field_eq_references` - EQ entity references
- `status` - Publication status (TRUE/FALSE)

### Entity CSV Fields (EUs/EQs/Big Ideas)
- `uuid` - Unique identifier
- `title` - Short title
- `body/value` - Full text in HTML
- `field_framework` - Framework name
- `field_subject` - Subject area
- `field_anchor_standard_ref` - Reference to anchor standard

## Processing Status

### Newly Processed (in drupal_prep)
- [x] NCAS - Complete (507 standards, 76 EUs, 130 EQs)
- [x] Math Common Core - Complete (480 standards)
- [x] C3 - Complete (324 indicators)
- [x] NGSS - Complete (136 performance expectations from ngss_2 folder)
  - Organized by Grade → Topic → DCI
  - Includes clarification statements and assessment boundaries

### Already in Existing CSV (comparison)
- [x] ELA Common Core - In existing CSV
- [x] NGSS - In existing CSV (208 standards) vs new extraction (136 PEs)
- [x] ISTE - In existing CSV (35 standards)
- [x] ISCA - In existing CSV (166 standards)
- [x] SHAPE - In existing CSV (1,379 standards)
- [ ] ACTFL - Only 1 standard in CSV (needs documents)

### To Be Done Last
- [ ] AP (Advanced Placement)
- [ ] IB (International Baccalaureate)