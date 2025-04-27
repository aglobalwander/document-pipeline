# Pipeline Documents Command Cheat Sheet

This is a comprehensive reference for all commands available in the pipeline-documents repository. Use this guide to quickly find the right command for your document processing needs, from simple one-off operations to complex Weaviate integrations.

⸻

## 0. Conventions

```bash
python -m cli.weav_cli ...          # Typer CLI for schema/data operations
python run_pipeline.py ...          # Flexible ETL runner (files/dirs/URLs)
just ...                            # Optional shortcuts (add to Justfile)
```

**Prerequisites**: 
- Execute from repo root with active virtualenv
- Required API keys set in environment variables (OpenAI, Gemini, Deepgram, Weaviate)

⸻

## 1. Quick Ingest Commands

| Action | Command |
|--------|---------|
| Process single PDF → Markdown | `python run_pipeline.py --input_path docs/intro.pdf --pipeline_type markdown` |
| Chunk + ingest PDF to KB | `python run_pipeline.py --input_path docs/intro.pdf --pipeline_type weaviate` |
| Process folder (non-recursive) | `python run_pipeline.py --input_path data/pdfs --pipeline_type text` |
| Process folder recursively | `python run_pipeline.py --input_path data/pdfs -r --pipeline_type text` |
| Image processing with Gemini | `python run_pipeline.py --input_path data/images -r --pipeline_type weaviate --image_backend gemini` |
| Deepgram diarization | `python run_pipeline.py --input_path data/audio -r --pipeline_type weaviate --deepgram_params '{"diarize": true}'` |
| YouTube ingestion | `python run_pipeline.py --input_path https://youtu.be/abcd1234 --pipeline_type weaviate` |

⸻

## 2. Targeted Collections

**Specific collection:**
```bash
# Send PDF to a specific collection (creates if YAML exists / uses fallback schema)
python run_pipeline.py --input_path docs/study.pdf \
                     --pipeline_type weaviate \
                     --collection ResearchDocs
```

**Temporary collection:**
```bash
# Create a timestamped temporary collection (auto TMP schema)
python run_pipeline.py --input_path tests/fixtures/sample.pdf \
                     --pipeline_type weaviate \
                     --collection tmp_playground_$(date +%s)
```

> Note: Collections are auto-created by `ensure_collection_exists()`. Chunks land in `ResearchDocsChunks` (or `tmp_playground_*Chunks`).

⸻

## 3. Collection Management

| Action | Command |
|--------|---------|
| Create from schemas | `python -m cli.weav_cli weav create --media` |
| Create from YAML | `python -m cli.weav_cli weav create CustomColl --schema-file schemas/custom.yaml` |
| List collections | `python -m cli.weav_cli weav list` |
| Inspect collection | `python -m cli.weav_cli weav show KnowledgeItem` |
| Drop collection | `python -m cli.weav_cli weav drop tmp_playground_123 -y` |

⸻

## 4. Format Transforms

| Conversion | Command |
|------------|---------|
| Markdown → JSON | `python run_pipeline.py --input_path notes/readme.md --pipeline_type json --output_format json` |
| TXT → Markdown | `python run_pipeline.py --input_path data/txt -r --pipeline_type markdown` |
| DOCX → Text | `python run_pipeline.py --input_path docs/report.docx --pipeline_type text` |
| DOCX → Markdown | `python run_pipeline.py --input_path docs/report.docx --pipeline_type markdown` |
| PPTX → Weaviate | `python run_pipeline.py --input_path slides/deck.pptx --pipeline_type weaviate --pptx_strategy hybrid` |
| JSON → CSV | `python run_pipeline.py --input_path data/json/invoice.json --pipeline_type json --output_format csv` |
| JSON → Excel | `python run_pipeline.py --input_path data/json/invoice.json --pipeline_type json --output_format xlsx` |

⸻

## 5. Maintenance & Diagnostics

```bash
# Find large files (10MB or larger)
python tools/find_large_files.py 10M

# List the 15 largest directories in the repo
python tools/du_top.py --top 15

# Verify Weaviate connection is working
python weaviate_layer/check_weaviate_api.py

# Run test suite (excludes slow tests)
just test  # Alias for: pytest -m "not slow"
```

⸻

## 6. Justfile Shortcuts

```bash
# View all shortcuts
just -l

# Process PDF to Markdown
just pdf-md path=docs/intro.pdf

# Ingest to Weaviate
just ingest-weav path=docs/

# Temporary collection
just tmp-coll name=tmp_$(date +%s)
```

⸻

## 7. Advanced Options

### PPTX Processing

```bash
# Process PowerPoint with hybrid strategy (PDF + speaker notes)
python run_pipeline.py --input_path slides/team_deck.pptx \
                      --pipeline_type weaviate \
                      --pptx_strategy hybrid
```

### Excel Output Options

```bash
# Use a custom Excel template
python run_pipeline.py --input_path data/json/invoice.json \
                      --pipeline_type json \
                      --output_format xlsx \
                      --excel_template finance

# Specify a custom template directory
python run_pipeline.py --input_path data/json/invoice.json \
                      --pipeline_type json \
                      --output_format xlsx \
                      --excel_template_dir /path/to/templates
```

### CSV Output Options

```bash
# Merge multiple JSON files into a single CSV
python run_pipeline.py --input_path data/json \
                      --pipeline_type json \
                      --output_format csv \
                      --merge_csv
```

## 8. Future Enhancements

- [ ] Add `pipeline weav promote` – copies objects & drops tmp collection
- [ ] Implement `cleanup_tmp` – nightly job to delete tmp_* older than 14 days
- [ ] Auto-infer pipeline type from MIME / extension (pipeline_type auto)
- [ ] Add `just ingest-youtube <url>` – wrapper for video transcription path

*Last updated: 2025-04-27*