# Theory of Change PDF Processing Design

**Date**: 2025-11-15
**Status**: Approved
**Goal**: Process 16 theory of change PDFs to markdown with quality tracking and iterative improvement

---

## Requirements Summary

### Primary Goal
One-time batch conversion of 16 PDFs in `data/input/pdfs/theory_of_change/` to markdown format.

### Quality Requirements
- **Level**: Automated processing sufficient (some OCR errors acceptable)
- **Focus**: Output quality and process reliability
- **Workflow**: Two-phase approach (automated processing → structured review)

### Improvement Goals
- Track output quality across runs
- Track process reliability (success/failure rates)
- Enable data-driven configuration tuning

---

## Architecture Overview

### Two-Phase Workflow

**Phase 1: Automated Docling Processing**
- Batch process all PDFs using enhanced_docling processor
- Generate text, markdown, and JSON outputs
- Log processing status and metrics
- 100% automated, zero cost

**Phase 2: Structured Claude Code Review**
- Use generated checklist to track review progress
- Interactive cleanup with Claude Code for quality issues
- Focus review time on flagged/problematic files
- Free with Claude subscription

---

## Component Design

### 1. Batch Processing Script

**File**: `scripts/process_theory_of_change.sh`

**Purpose**: Process all PDFs in the theory_of_change directory sequentially

**Key Features**:
- Loops through all PDF files
- Calls master_docling.py for each file
- Logs processing status with timestamps
- Tracks success/failure for each file
- Generates comprehensive processing log

**Example Command**:
```bash
#!/bin/bash
INPUT_DIR="data/input/pdfs/theory_of_change"
LOG_FILE="data/output/processing_log_$(date +%Y%m%d_%H%M%S).txt"

for pdf in "$INPUT_DIR"/*.pdf; do
    filename=$(basename "$pdf")
    echo "Processing: $filename" | tee -a "$LOG_FILE"

    poetry run python scripts/document_processing/master_docling.py \
        --input_path "$pdf" 2>&1 | tee -a "$LOG_FILE"

    # Track status
    if [ $? -eq 0 ]; then
        echo "✓ SUCCESS: $filename" | tee -a "$LOG_FILE"
    else
        echo "✗ FAILED: $filename" | tee -a "$LOG_FILE"
    fi
done
```

**Outputs**:
- `data/output/text/` - Plain text versions
- `data/output/markdown/` - Markdown versions (primary)
- `data/output/json/` - JSON structured versions
- `data/output/processing_log_*.txt` - Processing log

---

### 2. Quality Metrics Tracker

**File**: `scripts/generate_quality_metrics.py`

**Purpose**: Analyze processing logs and outputs to generate quality metrics

**Metrics Tracked**:
1. **Processing Success Rate**: Files processed without errors
2. **Output Size Analysis**: Detect unusually short outputs (possible failures)
3. **Error Patterns**: Common issues (table extraction, column detection)
4. **Processing Time**: Identify slow files needing special handling

**Output Format** (`data/output/processing_summary.json`):
```json
{
  "run_date": "2025-11-15",
  "run_id": "20251115_143022",
  "total_files": 16,
  "successful": 15,
  "failed": 1,
  "avg_processing_time_seconds": 23.4,
  "quality_flags": {
    "short_outputs": ["making_sense.pdf"],
    "processing_errors": [],
    "slow_processing": ["NCCS_BuildingCommunitySchools.pdf"]
  },
  "file_details": [
    {
      "filename": "2001_-_Davies_-_Most_Significant_Change_guide.pdf",
      "status": "success",
      "processing_time": 45.2,
      "output_size_chars": 125000,
      "num_pages": 52
    }
  ]
}
```

**Usage**:
```bash
# After running batch processing
poetry run python scripts/generate_quality_metrics.py \
  --log_file data/output/processing_log_20251115_143022.txt \
  --output_dir data/output/markdown
```

---

### 3. Review Checklist Generator

**File**: `scripts/generate_review_checklist.py`

**Purpose**: Create interactive markdown checklist for Claude Code review workflow

**Output** (`data/output/REVIEW_CHECKLIST.md`):
```markdown
# Theory of Change PDF Review Checklist

**Generated**: 2025-11-15 14:30:22
**Total Files**: 16
**Flagged for Review**: 3

## How to Use This Checklist with Claude Code

1. Open a markdown file: `data/output/markdown/[filename]_docling.md`
2. Ask Claude Code: "Review this for quality issues and suggest improvements"
3. Work interactively with Claude Code to clean up content
4. Check off the item below when complete
5. Save improved version with `_reviewed.md` suffix

## Priority Review (Quality Issues Detected)

- [ ] **making_sense.pdf** ⚠️ Short output (possible OCR failure)
- [ ] **NCCS_BuildingCommunitySchools.pdf** ⚠️ Slow processing (complex layout)

## Standard Review (Optional)

- [ ] 2001_-_Davies_-_Most_Significant_Change_guide.pdf
- [ ] 2001_-_Earl_-_Outcome_Mapping-Building_Learning_and_Reflection.pdf
...
```

**Usage**:
```bash
poetry run python scripts/generate_review_checklist.py \
  --metrics_file data/output/processing_summary.json \
  --output_file data/output/REVIEW_CHECKLIST.md
```

---

## Configuration & Tuning

### Default Settings (Optimal for Most Cases)

The `master_docling.py` script uses these defaults:
- `--extract_tables` (enabled) - Good for academic papers with tables
- `--detect_columns` (enabled) - Handles multi-column layouts
- `--output_all_formats` (enabled) - Generates text, markdown, JSON
- `--use_cache` (enabled) - Resumable processing if interrupted

### Tuning Based on Quality Metrics

| Quality Issue Detected | Configuration Adjustment |
|------------------------|--------------------------|
| Tables not extracting properly | Try `--no_extract_tables` for specific files |
| Multi-column layout garbled | Already using `--detect_columns` (optimal) |
| Processing interrupted | Cache automatically resumes from last page |
| Processing too slow | Use `--no_cache` if resumability not needed |
| Need only markdown | Use `--no_all_formats` to skip text/JSON |

### Iterative Improvement Workflow

```bash
# Run 1: Process with defaults
./scripts/process_theory_of_change.sh

# Generate metrics
poetry run python scripts/generate_quality_metrics.py --log_file data/output/processing_log_*.txt

# Review metrics, identify issues

# Run 2: Reprocess problematic files with adjusted settings
poetry run python scripts/document_processing/master_docling.py \
  --input_path "data/input/pdfs/theory_of_change/problematic_file.pdf" \
  --no_extract_tables  # Example adjustment
```

---

## Data Flow

```
theory_of_change/*.pdf
    ↓
process_theory_of_change.sh
    ↓
master_docling.py (enhanced_docling processor)
    ↓
├── data/output/text/*.txt
├── data/output/markdown/*.md      ← Primary output
├── data/output/json/*.json
└── data/output/processing_log.txt
    ↓
generate_quality_metrics.py
    ↓
processing_summary.json
    ↓
generate_review_checklist.py
    ↓
REVIEW_CHECKLIST.md
    ↓
Manual review with Claude Code
    ↓
data/output/markdown/*_reviewed.md  ← Final output
```

---

## Success Criteria

### Phase 1 Success
- ✓ All 16 PDFs processed without script errors
- ✓ Markdown files generated for each PDF
- ✓ Processing log captures all activity
- ✓ Quality metrics generated

### Phase 2 Success
- ✓ Review checklist generated with prioritized items
- ✓ Quality issues identified and flagged
- ✓ Interactive review workflow documented

### Iterative Improvement Success
- ✓ Quality metrics improve between runs (fewer flags)
- ✓ Processing reliability increases (higher success rate)
- ✓ Data-driven configuration adjustments documented

---

## Cost Analysis

**Total Cost**: $0

- Enhanced Docling processing: FREE (local OCR)
- Claude Code review: FREE (with Claude subscription)
- No API keys required
- No external services needed

---

## Future Enhancements (Optional)

### Quality Improvements
- Add OCR confidence scoring
- Implement automated markdown formatting cleanup
- Add table structure validation

### Workflow Improvements
- Parallel processing for faster batch runs
- Automated diff generation between runs
- Integration with version control for reviewed files

### Advanced Features
- Structured data extraction (theory of change models)
- Cross-document analysis and linking
- Weaviate integration for semantic search

---

## Notes

### Why Enhanced Docling?
- Free and open-source
- Built-in table extraction
- Multi-column detection
- Native markdown export
- Caching support for large documents
- High quality for academic papers

### Why Not Claude API?
- Not needed for "good enough" quality requirement
- Would cost $3-15 per million tokens
- Interactive Claude Code review provides same quality benefit for $0
- Keeps human in the loop for quality control

### File Naming Convention
- Input: `original_filename.pdf`
- Output: `original_filename_docling.md`
- Reviewed: `original_filename_reviewed.md`
