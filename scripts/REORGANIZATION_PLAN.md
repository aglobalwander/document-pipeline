# Scripts Reorganization Plan

## Current Scripts Analysis

### Categories Identified:

1. **PDF Processing**
   - analyze_pdfs_for_ocr.py
   - batch_process_pymupdf.py
   - benchmark_pymupdf.py
   - complete_pymupdf_processing.py
   - post_process_pymupdf_output.py
   - process_all_with_pymupdf.py
   - quick_pymupdf_test.py
   - test_pymupdf.py
   - test_pymupdf_simple.py

2. **Standards Processing** (already moved)
   - In `/scripts/standards/`

3. **Document Processing**
   - batch_process.py
   - direct_docx_markitdown.py
   - direct_markitdown.py
   - master_docling.py
   - run_pipeline.py
   - test_enhanced_docling.py

4. **Weaviate/Database Operations**
   - check_weaviate_api.py
   - delete_adaptive_schools_collection.py
   - direct_ingest_adaptive_school.py
   - ingest_adaptive_school.py
   - query_adaptive_schools.py
   - setup_weaviate_mcp.py
   - verify_adaptive_schools_collection.py
   - verify_weaviate_connection.py
   - weaviate_operations.py

5. **Content Splitting/Organization**
   - split_by_headings.py
   - split_chapters.py
   - split_cognitive_coaching.py
   - summarize_adaptive_schools.py

6. **Standards Organization** (separate from extraction)
   - analyze_standards_pdfs.py
   - organize_standards_pdfs.py
   - process_and_organize_all_standards.py
   - process_standards_frameworks.py
   - process_subject_briefs.py
   - reorganize_standards_by_source.py
   - test_new_ngss_pdfs.py
   - test_subject_briefs_pymupdf.py

7. **Utilities/Setup**
   - create_default_template.py
   - create_dummy_pptx.py
   - download_nltk_resources.py
   - download_punkt_tab.py
   - filesize.py
   - git_lfs_migrate.py

8. **YouTube/Media**
   - test_youtube_loader.py
   - test_yt_dlp_standalone.py

## New Directory Structure:
```
scripts/
├── pdf_processing/
├── document_processing/
├── weaviate/
├── content_processing/
├── standards/           (already exists)
├── standards_org/       (organization scripts)
├── utilities/
├── media/
└── archive/            (deprecated/old scripts)
```