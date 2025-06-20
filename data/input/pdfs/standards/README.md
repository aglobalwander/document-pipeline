# Standards Framework PDFs

This directory contains organized standards framework PDFs.

## Structure

- `actful/` - 13 documents
- `ap_guides/` - 40 documents
- `ap_guides_dl/` - 1 documents
- `briefs/` - 6 documents
- `c3_framework/` - 2 documents
- `common_core/` - 4 documents
- `common_core_ela/` - 6 documents
- `common_core_math/` - 2 documents
- `course_guides/` - 24 documents
- `isca/` - 1 documents
- `iste/` - 1 documents
- `ncas/` - 12 documents
- `ngss/` - 14 documents
- `p.e_/` - 3 documents
- `student_guides/` - 3 documents

## Processing

To analyze these PDFs and determine best OCR method:
```bash
python scripts/analyze_pdfs_for_ocr.py data/input/pdfs/standards --create-script
```

To process all PDFs:
```bash
bash data/output/process_standards_pdfs.sh
```
