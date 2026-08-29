# Standards framework PDF processing

Standards PDFs often combine columns, tables, codes, footnotes, and hierarchy.
Preserve the source wording and structure before downstream modeling.

## 1. Keep source authority visible

Record the framework, publisher, edition/date, source URL or file path, and page
range. Extraction output is evidence derived from the official document; it is
not a replacement authority.

## 2. Inventory in place

The pipeline accepts absolute paths, so copying into the repository is optional:

```bash
poetry run python scripts/collections/inventory_collection.py \
  --source_dir /absolute/path/standards
```

For PDF-specific analysis, use the current utility path:

```bash
poetry run python scripts/pdf_processing/analyze_pdfs_for_ocr.py \
  /absolute/path/standards
```

Read the script's help/header before relying on source-specific options.

### AP raw-source archive

The flat `data/input/pdfs/standards/ap_guides/` directory is a legacy working
corpus and must not be overwritten when College Board republishes a guide at the
same URL. Current AP bytes belong in the ignored, content-addressed local
archive:

```text
data/input/pdfs/standards/ap_guide_archive/
  <package-id>/<sha256>/<official-filename>.pdf
```

Tracked edition selection and review-baseline state live in
`scripts/standards/ap_editions.json`. Build the archive only from a complete,
already downloaded 40-package directory and the pinned KM source manifest:

```bash
poetry run python scripts/standards/ap_pdf_archive.py archive \
  --source-manifest /absolute/path/ap_current_source_package_manifest.json \
  --source-manifest-ref knowledge-management:research/standards_frameworks/deconstructing_standards/audits/2026-08-16-ap-ib-full-wave/ap_current_source_package_manifest.json \
  --expected-source-manifest-sha256 f2ce852f0e56bf7b14ce1fece92a68885a6cd848023029a02af1a6faa40b97dd \
  --matrix /absolute/path/ap-current-readiness-matrix-v2.json \
  --matrix-ref knowledge-management:research/standards_frameworks/deconstructing_standards/audits/2026-08-29-ap-current-guide-review/readiness-matrix-v2/ap-current-readiness-matrix-v2.json \
  --expected-matrix-sha256 2e3626ac97c6afd1aa87e0db4cffc23edb2e1567e73ed5856583c9453a99e846 \
  --download-dir /absolute/path/to/complete-download \
  --archive-root data/input/pdfs/standards/ap_guide_archive \
  --index scripts/standards/ap_editions.json \
  --observed-on YYYY-MM-DD

poetry run python scripts/standards/ap_pdf_archive.py verify \
  --source-manifest /absolute/path/ap_current_source_package_manifest.json \
  --source-manifest-ref knowledge-management:research/standards_frameworks/deconstructing_standards/audits/2026-08-16-ap-ib-full-wave/ap_current_source_package_manifest.json \
  --expected-source-manifest-sha256 f2ce852f0e56bf7b14ce1fece92a68885a6cd848023029a02af1a6faa40b97dd \
  --matrix /absolute/path/ap-current-readiness-matrix-v2.json \
  --matrix-ref knowledge-management:research/standards_frameworks/deconstructing_standards/audits/2026-08-29-ap-current-guide-review/readiness-matrix-v2/ap-current-readiness-matrix-v2.json \
  --expected-matrix-sha256 2e3626ac97c6afd1aa87e0db4cffc23edb2e1567e73ed5856583c9453a99e846 \
  --index scripts/standards/ap_editions.json
```

The helper requires `file`, `pdfinfo`, and `pdftotext`. It fails closed unless
the authority hashes, all 40 package identities, and all 43 named offerings
match. The index keeps every observed source artifact by SHA-256. If a PDF has
no detected edition label or more than one, it records a review hold and does
not choose one merely to match the baseline metadata.

An official URL returning different bytes is a distinct source artifact, even
when the edition label or page count is unchanged. Preserve both identities and
never rewrite the reviewed baseline or infer that matching extracted text
proves matching PDF bytes. The pipeline index records byte lineage only;
content-review and release readiness remain with the owning source-model
workflow. Raw PDFs stay private and gitignored; the tracked index contains
hashes and local relative paths, not the publisher's copyrighted bytes.

## 3. Extract locally

For a framework with layout, tables, or scanned pages:

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/framework.pdf \
  --output_dir /absolute/path/processed \
  --output_format markdown
```

For a simple born-digital PDF:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/framework.pdf \
  --output_dir /absolute/path/processed \
  --pipeline_type text \
  --pdf_processor pymupdf
```

For a directory:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/standards \
  --output_dir /absolute/path/processed \
  --pipeline_type text \
  --recursive \
  --pdf_processor enhanced_docling
```

## 4. Verify before structuring

Check:

- statement wording against source pages;
- identifiers and hierarchical parent/child order;
- table row/column alignment;
- cross-references, annotations, and footnotes;
- edition metadata and page coverage.

Do not normalize wording, invent missing parents, or collapse fragmented source
chains during extraction.

## 5. Transform and hand off

After the Markdown/text artifact passes review, use framework-specific scripts
under `scripts/standards/` or `scripts/standards_org/`. These scripts have
source-specific assumptions; inspect their headers and tests first.

Generic JSON conversion is available:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/framework.md \
  --pipeline_type json \
  --output_format json
```

Downstream standards modeling and search/index ingestion belong to their owning
repositories. Keep the official source metadata with every handoff.
