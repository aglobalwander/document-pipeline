# AGENTS.md

Operational guidance for Codex and other coding agents in this repository.

## Purpose and boundaries

This project extracts and transforms PDF, DOCX, PPTX, text, images, audio,
video, and supported URLs into text, Markdown, JSON, CSV, or XLSX. It does not
own Milvus, Postgres, or other downstream ingestion.

Processing defaults:

- Use the active Codex subscription interactively for one-off LLM review and
  restructuring. This is the default LLM lane for repository work.
- Use Enhanced Docling locally for PDFs.
- Use MarkItDown or Mammoth for Office formats.
- Use Kimi Code or Claude Code only as authenticated interactive subscription
  tools when an additional review is useful. Verify the active account/model;
  never repurpose their OAuth credentials for the Python pipeline.
- Use Gemini, Kimi K3, OpenAI, Anthropic, DeepSeek, or DashScope APIs only when
  explicitly requested. They are paid automation paths.
- Keep `--llm_provider` unset for local processing. A selected provider is an
  explicit paid API opt-in, never an automatic fallback.
- Never imply that local extraction proves downstream ingestion succeeded.

See `docs/MODEL_ROUTING.md` for the current subscription/API boundary and model
audit. Recheck official provider documentation before changing model aliases.

## Required environment

Use Poetry for every repository Python command. Do not use the available Conda
environments.

```bash
poetry install
poetry run python -c "import doc_processing; print('ready')"
```

Credentials live at `~/.config/api-keys/.env.master` and are loaded by
`doc_processing/config.py`. Never print, copy, or commit key values. Prefer
`MOONSHOT_API_KEY` for Kimi Platform; `KIMI_API_KEY` is a compatibility alias.

## Main entry points

```bash
# Recommended local PDF path
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown

# General file, directory, or URL path
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/input \
  --pipeline_type text \
  --recursive

# Direct Office conversion
poetry run python scripts/document_processing/direct_markitdown.py \
  /absolute/path/input.docx \
  /absolute/path/output.md

# YouTube batch
poetry run python batch_youtube_download.py
```

Always read live help before documenting new flags:

```bash
poetry run python scripts/document_processing/run_pipeline.py --help
poetry run python scripts/document_processing/master_docling.py --help
```

## Kimi K3

The pipeline API client defaults to `kimi-k3` at
`https://api.moonshot.ai/v1`. K3 is wired to JSON/structured transforms through
`--llm_provider kimi`; it is not a PDF processor choice.

The subscription Kimi Code CLI is a separate OAuth product. Current standalone
state lives under `~/.kimi-code/`; its model alias is `kimi-code/k3`. Do not
label the OAuth lane as an Open Platform API request or reuse its credentials.
See `docs/KIMI_K3.md`.

## Repository map

- `doc_processing/loaders/`: source loading
- `doc_processing/processors/`: extraction, OCR, transcription, cleanup
- `doc_processing/transformers/`: output and schema transforms
- `doc_processing/llm/`: optional remote-model clients
- `scripts/document_processing/`: main CLI entry points
- `scripts/collections/`: large collection workflows
- `tests/`: unit and integration tests
- `data/output/`, `data/cache/`: generated, ignored runtime state

## Verification

Use tests proportionate to the change:

```bash
poetry run pytest -q tests/test_kimi_client.py
poetry run pytest -q
git diff --check
```

Some integration tests require sample files under `data/input/`. Report a
missing fixture separately from a code failure.

## Documentation authority

Current practice lives in `README.md`, `docs/README.md`, `RUNBOOK.md`,
`INVARIANTS.md`, and live code/help. `docs/plans/`, `docs/archive/`,
`CLEANUP_SUMMARY.md`, and `documentation_plan.md` are historical evidence, not
current command authority.

Preserve unrelated dirty-worktree changes. Do not edit generated artifacts,
collection registries, or active handoffs unless they are in the user's scope.
