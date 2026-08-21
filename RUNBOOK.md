# Runbook — pipeline-documents

## Setup and health

```bash
cd /Users/scottwilliams/Development/_02_platforms/pipeline-documents
poetry install
poetry run python -c "import doc_processing, pydantic; print('pipeline ready')"
poetry run python scripts/document_processing/run_pipeline.py --help
```

Use Poetry, not Conda. If the import check fails, the environment is not ready
even if a system-level `pytest` command happens to run.

## Routine processing

```bash
# Recommended PDF path: local and free
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown

# General file, folder, or URL
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/input \
  --pipeline_type markdown \
  --output_format md

# YouTube batch
poetry run python batch_youtube_download.py
```

## Kimi Code and Kimi K3

```bash
export PATH="/Users/scottwilliams/.kimi-code/bin:$PATH"
kimi update
kimi --version
kimi doctor
kimi -m kimi-code/k3 -p "Reply with exactly: K3_READY"
```

The Kimi Code OAuth subscription and `MOONSHOT_API_KEY` paid API are separate.
See `docs/KIMI_K3.md` before diagnosing auth or model routing.

For all model lanes, use the routing order in `docs/MODEL_ROUTING.md`: local
extraction, Codex subscription review, optional authenticated interactive
subscription review, then explicitly authorized paid API automation.

## Verification

```bash
poetry run pytest -q tests/test_kimi_client.py
poetry run pytest -q
git diff --check
```

## Recovery

- Interrupted Docling job: rerun the same command; cache resumes where
  supported.
- Bad checkpoint: add `--clear_cache`.
- Missing Poetry dependency: rerun `poetry install` and the import health check.
- Private YouTube failure: browser cookies may be required.
- Kimi `auth.login_required`: run `kimi login`; do not copy legacy OAuth files.
- Kimi model missing: complete login, start a new session, and select K3 through
  `/model` or `-m kimi-code/k3`.
