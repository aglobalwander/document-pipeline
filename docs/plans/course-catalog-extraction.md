# SAS Course Catalog Extraction 2026-27

## Source Documents

| Campus | PDF | Pages | Size | Text Extractable |
|--------|-----|------:|-----:|:----------------:|
| PDHS | `data/input/pdfs/division catalogs/670PDHS Course Catalog 2026-27.pdf` | 66 | 9.4 MB | Yes (but two-column layout broke regex) |
| PXHS | `data/input/pdfs/division catalogs/PXHS_Course_Catalog_2026-27.pdf` | 62 | 17.2 MB | No (entirely image-based) |

**Extraction method**: Claude Code vision (multimodal PDF reading). Regex/PyMuPDF extraction failed due to two-column layout interleaving and PXHS being fully image-based.

## Output

**File**: `data/output/json/sas_course_catalogs_2026-27.json`

| Metric | Value |
|--------|-------|
| Total courses | 311 (155 PDHS + 156 PXHS) |
| With descriptions | 299 / 311 (96%) |
| With main_topics + learning_outcomes | 114 (PDHS structured entries) |
| With oral_language / reading / writing | 16 (Chinese Language courses) |

### JSON Schema

```json
{
  "school": "Shanghai American School",
  "academic_year": "2026-27",
  "campuses": ["PDHS", "PXHS"],
  "total_courses": 311,
  "courses": [
    {
      "course_name": "English 9",
      "course_codes": ["HS1000"],
      "credits": 1,
      "grades": "9",
      "department": "English",
      "campus": "PDHS",
      "prerequisites": "None",
      "course_description": "...",
      "main_topics": ["..."],
      "learning_outcomes": ["..."]
    }
  ]
}
```

**Fields per course** (all courses):
- `course_name`, `course_codes`, `credits`, `grades`, `department`, `campus`
- `prerequisites`, `course_description`

**Optional fields** (where catalog provided structured data):
- `main_topics`, `learning_outcomes` — PDHS courses only (114 entries)
- `oral_language`, `reading`, `writing` — Chinese Language courses (16 entries)

### Departments

English, Mathematics, Social Studies, Science, Chinese Language, Global Languages, Visual Arts, Performing Arts, Applied Arts, GTAE Pathway, Physical and Health Education, Elective Courses, Learning Support, Online Learning

## Missing Descriptions (12 PDHS courses)

These appear in the PDHS master course list table but have no individual description page in the catalog PDF:

- Superior Chinese 2
- Advanced Studio Art 1, Advanced Studio Art 2
- Creativity and Design (Inno G9), Innovation & Design (Inno G10)
- Advanced Digital Film Making 1,2,3
- Advanced Contemporary Music
- Orchestra: Advanced
- Theatre Design, Advance Theatre Design
- Dance 1, Dance 2

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/extract_course_catalogs.py` | Master course lists (PDHS_MASTER, PXHS_MASTER) + failed regex functions |
| `scripts/data/pdhs_descriptions.py` | 146 PDHS descriptions (Python dict, 871 lines) |
| `scripts/data/pxhs_descriptions.py` | 155 PXHS descriptions (Python dict, 662 lines) |
| `scripts/build_catalog_json.py` | Merges master lists + descriptions → final JSON. Cross-campus fallback for shared courses. |

**Rebuild**: `poetry run python scripts/build_catalog_json.py`

## Drupal Integration

This JSON is the source data for the Drupal Knowledge Hub course catalog content type. Integration considerations:

- **course_codes** are arrays (some courses span two years with separate Y1/Y2 codes)
- **credits** can be fractional (0.25 for GTAE quarterly, 0.5 for semester courses)
- **grades** is a comma-separated string (e.g. "9,10,11,12")
- **campus** distinguishes PDHS vs PXHS offerings — many courses exist at both campuses with different descriptions
- **main_topics** and **learning_outcomes** are only available for PDHS; PXHS catalog provides paragraph descriptions only
- IB SL/HL pairs are separate entries (different prerequisites and depth of content)
- Some courses appear in multiple departments (IB ESS counts as both Science and Social Studies)

### PowerSchool Cross-Check (TODO)

The `course_codes` field should be validated against PowerSchool's active course list to:
- Confirm codes are current for 2026-27
- Identify any courses in PowerSchool not in the catalog (and vice versa)
- Flag retired or renamed courses

## Provenance

- Extracted: 2026-02-28
- Method: Claude Code multimodal vision reading of catalog PDFs
- Master lists manually transcribed from course list tables (pages 11-14 in both catalogs)
- Descriptions transcribed from course description pages (PDHS pp.14-61, PXHS pp.15-56)
