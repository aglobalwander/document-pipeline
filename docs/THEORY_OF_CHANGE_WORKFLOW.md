# Theory of Change PDF Processing Workflow

**Quick Start Guide for Processing Theory of Change PDFs**

---

## Overview

This workflow processes all PDFs in `data/input/pdfs/theory_of_change/` using a two-phase approach:

1. **Automated Processing**: Batch process all PDFs with enhanced_docling (FREE)
2. **Interactive Review**: Use Claude Code to review and improve outputs (FREE)

**Total Cost**: $0

---

## Step-by-Step Instructions

### Phase 1: Automated Processing

**1. Run the batch processing script:**

```bash
./scripts/process_theory_of_change.sh
```

This will:
- Process all 16 PDFs in the theory_of_change directory
- Generate text, markdown, and JSON outputs
- Create a timestamped processing log
- Display progress and summary

**Expected Output:**
```
data/output/
├── text/                    # Plain text versions
├── markdown/                # Markdown versions (primary)
├── json/                    # JSON structured versions
└── processing_log_<timestamp>.txt
```

**Processing Time**: ~5-10 minutes for all 16 files (depends on PDF complexity)

---

**2. Generate quality metrics:**

After batch processing completes, run:

```bash
poetry run python scripts/generate_quality_metrics.py \
  --log_file data/output/processing_log_<timestamp>.txt
```

Replace `<timestamp>` with the actual timestamp from the log file name.

This will:
- Analyze the processing log
- Check output file sizes
- Detect quality issues
- Generate `processing_summary_<timestamp>.json`

**Expected Output:**
```
QUALITY METRICS SUMMARY
===========================================================
Run ID: 20251115_143022
Total Files: 16
Successful: 15
Failed: 1
Success Rate: 93.8%

⚠ Quality Issues Detected: 2
  Short Outputs (1):
    - making_sense.pdf
  Slow Processing (1):
    - NCCS_BuildingCommunitySchools.pdf
```

---

**3. Generate review checklist:**

```bash
poetry run python scripts/generate_review_checklist.py
```

This automatically finds the latest metrics file and creates:
- `data/output/REVIEW_CHECKLIST.md`

**Expected Output:**
```
✓ Review checklist generated: data/output/REVIEW_CHECKLIST.md

Next Steps:
  1. Open the checklist
  2. Start with priority review items
  3. Use Claude Code to review and improve each file
```

---

### Phase 2: Interactive Review with Claude Code

**1. Open the review checklist:**

```bash
cat data/output/REVIEW_CHECKLIST.md
```

Or open it in your editor.

**2. Start with priority items:**

The checklist prioritizes files with quality issues:
- ⚠️ Short outputs (possible OCR failures)
- ⚠️ Slow processing (complex layouts)
- ❌ Failed processing

**3. Review workflow for each file:**

For each file you want to review:

```bash
# Open the markdown output
cat data/output/markdown/filename_docling.md
```

Then in Claude Code, paste sections and ask:
- "Review this for quality issues and suggest improvements"
- "Fix OCR errors in this section"
- "Restructure this poorly formatted table"
- "Extract key findings from this document"

**4. Save reviewed content:**

Save improved versions as:
```
data/output/markdown/filename_reviewed.md
```

**5. Check off items in the checklist as you complete them**

---

## Example Full Workflow

```bash
# Step 1: Batch process all PDFs
./scripts/process_theory_of_change.sh

# Step 2: Generate quality metrics (use actual timestamp)
poetry run python scripts/generate_quality_metrics.py \
  --log_file data/output/processing_log_20251115_143022.txt

# Step 3: Generate review checklist
poetry run python scripts/generate_review_checklist.py

# Step 4: Open checklist and start reviewing
cat data/output/REVIEW_CHECKLIST.md

# Step 5: Review priority items with Claude Code
# (Interactive process - work through each flagged file)
```

---

## Quality Improvement Between Runs

### Track Improvements

After each run, compare metrics:

```bash
# View latest metrics
cat data/output/processing_summary_*.json | tail -n 50

# Compare success rates, quality flags, processing times
```

### Adjust Settings for Problem Files

If specific files consistently have issues:

```bash
# Reprocess with different settings
poetry run python scripts/document_processing/master_docling.py \
  --input_path "data/input/pdfs/theory_of_change/problematic_file.pdf" \
  --no_extract_tables  # Try without table extraction
```

### Common Adjustments

| Issue | Try This |
|-------|----------|
| Tables not extracting well | `--no_extract_tables` |
| Processing very slow | `--no_cache` |
| Need only markdown | `--no_all_formats` |

---

## File Organization

### Input
```
data/input/pdfs/theory_of_change/
├── 2001_-_Davies_-_Most_Significant_Change_guide.pdf
├── 2001_-_Earl_-_Outcome_Mapping-Building_Learning_and_Reflection.pdf
└── ... (14 more PDFs)
```

### Output
```
data/output/
├── markdown/
│   ├── 2001_-_Davies_-_Most_Significant_Change_guide_docling.md
│   ├── 2001_-_Davies_-_Most_Significant_Change_guide_reviewed.md  ← After review
│   └── ...
├── text/
│   └── ... (text versions)
├── json/
│   └── ... (JSON versions)
├── processing_log_20251115_143022.txt
├── processing_summary_20251115_143022.json
└── REVIEW_CHECKLIST.md
```

---

## Tips for Success

### Batch Processing
- Run during off-hours (takes 5-10 minutes)
- Check the log file if any errors occur
- Processing is resumable (uses caching)

### Quality Metrics
- Focus on files with quality flags first
- Track improvements between runs
- Use metrics to adjust settings

### Claude Code Review
- Work section by section (don't paste entire documents)
- Be specific in your requests
- Save reviewed content incrementally
- Focus on priority items first

---

## Troubleshooting

### "Permission denied" when running scripts
```bash
chmod +x scripts/process_theory_of_change.sh
```

### "poetry not found"
Make sure you're in the project directory:
```bash
cd /Users/scottwilliams/Development/master_projects/pipeline-documents
```

### Processing fails for a specific PDF
Check the log file for error details:
```bash
grep "FAILED" data/output/processing_log_*.txt
```

Then try reprocessing that file manually with different settings.

### No metrics file found
Make sure you ran the batch processing first:
```bash
ls -la data/output/processing_log_*.txt
```

---

## Summary

**Single Command Workflow:**
```bash
# Process everything
./scripts/process_theory_of_change.sh && \
poetry run python scripts/generate_quality_metrics.py --log_file data/output/processing_log_*.txt && \
poetry run python scripts/generate_review_checklist.py

# Then review outputs with Claude Code interactively
```

**Result**: All 16 PDFs converted to high-quality markdown at zero cost!
