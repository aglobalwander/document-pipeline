# Standards Framework PDF Processing Guide

This guide explains how to process standards framework PDFs (NGSS, Common Core, state standards, etc.) using the pipeline-documents system.

## Overview

Standards framework documents often have unique characteristics:
- Complex layouts with multiple columns
- Tables, charts, and diagrams
- Mixed text and scanned content
- Hierarchical numbering systems
- Cross-references and annotations

The pipeline provides tools to analyze and process these documents optimally.

## Step 1: Organize Your PDFs

### Option A: Copy PDFs to the Pipeline Directory

```bash
# Copy your PDFs to the input directory
cp /path/to/your/standards/*.pdf data/input/pdfs/standards/

# Or organize by framework
cp /path/to/ngss/*.pdf data/input/pdfs/standards/ngss/
cp /path/to/common_core/*.pdf data/input/pdfs/standards/common_core/
```

### Option B: Process PDFs from Their Current Location

You can process PDFs directly from any location:

```bash
# Process a single PDF
python scripts/run_pipeline.py --input_path /path/to/standards/ngss.pdf --pipeline_type text

# Process entire directory
python scripts/run_pipeline.py --input_path /path/to/standards/ --pipeline_type text --recursive
```

### Option C: Use the Organization Script

```bash
# Automatically organize PDFs by detected framework
python scripts/organize_standards_pdfs.py /path/to/your/standards/

# This creates:
# - data/input/pdfs/standards/ngss/
# - data/input/pdfs/standards/common_core/
# - data/input/pdfs/standards/[other_frameworks]/
```

## Step 2: Analyze PDFs to Determine Best Processing Method

Run the analysis script to create an index of your PDFs:

```bash
# Analyze PDFs and create index
python scripts/analyze_pdfs_for_ocr.py data/input/pdfs/standards/

# Include script generation
python scripts/analyze_pdfs_for_ocr.py data/input/pdfs/standards/ --create-script
```

This generates:
1. `data/output/pdf_analysis_index.json` - Analysis results for each PDF
2. `data/output/process_standards_pdfs.sh` - Custom processing script

### Understanding the Analysis

The analyzer checks each PDF for:
- **Text coverage**: How much embedded text vs images
- **Complexity**: Simple, medium, or complex layout
- **Tables**: Presence of structured data
- **Scan quality**: Whether it's a scanned document

Based on these factors, it recommends:
- **PyMuPDF**: For modern PDFs with embedded text (fastest)
- **Docling**: For complex layouts and tables
- **Enhanced Docling**: For documents needing multiple output formats
- **Gemini/GPT-4V**: For scanned or handwritten content

## Step 3: Process the PDFs

### Option A: Use the Generated Script

```bash
# Run the auto-generated processing script
bash data/output/process_standards_pdfs.sh
```

### Option B: Process Individually with Recommended Settings

Based on the analysis, process each type appropriately:

#### For Simple PDFs (embedded text):
```bash
python scripts/run_pipeline.py \
    --input_path data/input/pdfs/standards/framework.pdf \
    --pipeline_type text \
    --pdf_processor pymupdf \
    --output_dir data/output/text/standards/
```

#### For Complex PDFs (tables, mixed content):
```bash
python scripts/master_docling.py \
    --input_path data/input/pdfs/standards/complex_framework.pdf \
    --output_all_formats \
    --use_cache
```

#### For Scanned PDFs:
```bash
python scripts/run_pipeline.py \
    --input_path data/input/pdfs/standards/scanned_doc.pdf \
    --pipeline_type text \
    --pdf_processor_strategy fallback_chain \
    --output_dir data/output/text/standards/
```

### Option C: Batch Process with Fallback Chain

Process all PDFs using intelligent fallback:

```bash
# Process all standards with automatic method selection
python scripts/run_pipeline.py \
    --input_path data/input/pdfs/standards/ \
    --pipeline_type text \
    --pdf_processor_strategy fallback_chain \
    --recursive \
    --output_dir data/output/text/standards/
```

## Step 4: Output Structure

After processing, your outputs will be organized as:

```
data/output/
├── text/standards/
│   ├── ngss/
│   │   ├── ngss_k12_standards.txt
│   │   └── ngss_appendices.txt
│   ├── common_core/
│   │   ├── ccss_math.txt
│   │   └── ccss_ela.txt
│   └── [framework]/
├── markdown/standards/
│   └── [same structure with .md files]
└── json/standards/
    └── [same structure with .json files]
```

## Step 5: Working with Processed Standards

### Loading Processed Text
```python
from pathlib import Path

# Read processed standard
standard_path = Path("data/output/text/standards/ngss/ngss_k12_standards.txt")
with open(standard_path, 'r') as f:
    content = f.read()

# Search for specific grade level
grade_3_standards = [line for line in content.split('\n') if '3-' in line]
```

### Converting to Structured Format
```python
# Convert to JSON for better structure
python scripts/run_pipeline.py \
    --input_path data/output/text/standards/ngss/ngss_k12_standards.txt \
    --pipeline_type json \
    --output_format json
```

### Ingesting to Weaviate for Search
```python
# Create searchable standards database
python scripts/run_pipeline.py \
    --input_path data/output/text/standards/ \
    --pipeline_type weaviate \
    --collection StandardsFrameworks \
    --recursive
```

## Tips for Standards Documents

### 1. Handling Multi-Column Layouts
Standards often use multi-column layouts. Docling handles these well:
```bash
python scripts/master_docling.py \
    --input_path multi_column_standard.pdf \
    --detect_columns \
    --output_format markdown
```

### 2. Preserving Hierarchical Structure
For standards with numbering (K.CC.1, 1.NBT.2, etc.):
```bash
python scripts/run_pipeline.py \
    --input_path standard.pdf \
    --pipeline_type json \
    --preserve_structure
```

### 3. Extracting Specific Sections
For large framework documents:
```python
# Process specific page ranges
from doc_processing.document_pipeline import DocumentPipeline

config = {
    'page_range': (10, 50),  # Pages 10-50
    'pdf_processor': 'enhanced_docling'
}
pipeline = DocumentPipeline(config)
```

### 4. Handling Tables and Rubrics
Many standards include assessment rubrics:
```bash
python scripts/master_docling.py \
    --input_path rubric_standard.pdf \
    --extract_tables \
    --output_format json
```

## Common Issues and Solutions

### Issue: Poor OCR Quality
**Solution**: Use preprocessing and higher resolution
```bash
python scripts/run_pipeline.py \
    --input_path scanned_standard.pdf \
    --pipeline_type text \
    --pdf_processor gemini \
    --preprocessing true
```

### Issue: Mixed Quality Pages
**Solution**: Use page-level processing
```bash
python scripts/master_docling.py \
    --input_path mixed_quality.pdf \
    --use_cache \
    --fallback_on_error
```

### Issue: Large Files Timeout
**Solution**: Enable caching and batch processing
```bash
python scripts/master_docling.py \
    --input_path large_framework.pdf \
    --use_cache \
    --batch_size 10
```

## Next Steps

After processing your standards:

1. **Quality Check**: Review samples of extracted text
2. **Structure Analysis**: Identify patterns for parsing
3. **Database Design**: Plan schema for standards storage
4. **Search Implementation**: Set up Weaviate for standard searches
5. **API Development**: Create endpoints for standard queries

## Example: Complete NGSS Processing Workflow

```bash
# 1. Organize NGSS PDFs
python scripts/organize_standards_pdfs.py ~/Downloads/NGSS/

# 2. Analyze PDFs
python scripts/analyze_pdfs_for_ocr.py data/input/pdfs/standards/ngss/ --create-script

# 3. Process all NGSS documents
bash data/output/process_standards_pdfs.sh

# 4. Convert to structured JSON
python scripts/run_pipeline.py \
    --input_path data/output/text/standards/ngss/ \
    --pipeline_type json \
    --recursive

# 5. Ingest to Weaviate
python scripts/run_pipeline.py \
    --input_path data/output/json/standards/ngss/ \
    --pipeline_type weaviate \
    --collection NGSS_Standards \
    --recursive
```

This workflow gives you searchable, structured NGSS standards!