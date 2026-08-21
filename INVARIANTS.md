# Invariants — pipeline-documents

## Execution

- This is a local CLI tool, not a deployed service.
- Use the Poetry environment for repository Python commands.
- Enhanced Docling is the preferred PDF extraction path.
- Remote APIs are paid, opt-in fallbacks or transforms; never enable them by
  implication.
- Interactive subscription OAuth stays in its native Codex, Kimi Code, or
  Claude Code tool. It is never loaded into the Python API clients.
- The default PDF fallback chain and image OCR path are local-only.
- Remote response or interaction state is not stored unless the caller opts in
  explicitly.

## Data and credentials

- Generated outputs go under `data/output/` or an explicitly selected external
  collection root.
- Cache state belongs under `data/cache/`.
- Credentials belong in `~/.config/api-keys/.env.master`, never tracked files.
- Never print key values. Report presence by variable name only.
- Kimi Code OAuth does not satisfy `MOONSHOT_API_KEY`, and the API key does not
  authenticate the subscription CLI.

## Architecture

- Loaders read and normalize sources.
- Processors extract or clean content.
- Transformers change representation or structure.
- Remote structured extraction uses provider-native schema enforcement plus
  local Pydantic validation; it does not depend on one provider shim.
- Downstream ingestion/search is outside this repository's authority.

## Documentation

- Live code, tests, CLI `--help`, `README.md`, `RUNBOOK.md`, and this file outrank
  dated plans or archived notes.
- Historical documents stay historical; point them to current truth instead of
  silently rewriting past decisions.

## Git

- Preserve unrelated dirty-worktree changes.
- Do not edit active collection registries, generated outputs, or handoffs
  unless they are explicitly in scope.
- Remote: `https://github.com/aglobalwander/document-pipeline.git`
