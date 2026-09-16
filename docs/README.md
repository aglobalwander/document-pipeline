# Pipeline Documents documentation

The repository is a local-first extraction/transform system. These documents
are organized by reader and authority so historical plans do not override
current behavior.

## Guides

- [User guide](USER_GUIDE.md): setup, everyday workflows, outputs, and recovery
- [Kimi K3](KIMI_K3.md): current CLI/API boundary and capability usage
- [Model routing](MODEL_ROUTING.md): subscription-first policy and current API model audit
- [OCR guide](guides/OCR_GUIDE.md): choosing a PDF extraction strategy
- [PyMuPDF usage](guides/PYMUPDF_USAGE.md): fast embedded-text extraction
- [Standards PDF processing](guides/STANDARDS_PDF_PROCESSING.md): standards-specific workflows

## Reference

- [Command reference](COMMANDS.md): exact supported entry points and flags
- [System map](../SYSTEM_MAP.md): components and integrations
- [Runbook](../RUNBOOK.md): setup, health checks, and recovery
- [Invariants](../INVARIANTS.md): non-negotiable boundaries
- [Overview](OVERVIEW.md): non-technical explanation

## Agent instructions

- [AGENTS.md](../AGENTS.md): Codex and general coding-agent instructions
- [CLAUDE.md](../CLAUDE.md): Claude Code instructions

## Handoffs

- [Incoming notes](handoff/INCOMING.md): requests from other repos that this repo must act on
- [Outgoing notes](handoff/OUTGOING.md): notes this repo sends to other repos
- [KM request: IB guide re-extraction](handoff/2026-09-16-km-request-ib-guide-re-extraction.md):
  received request for three IB guide runs plus two sweep-label corrections

## History

- `plans/`: dated designs that describe intended behavior at that point in time
- `archive/`: retired implementation and migration notes
- `../CLEANUP_SUMMARY.md`, `../documentation_plan.md`, and
  `../scripts/REORGANIZATION_PLAN.md`: point-in-time records, not current
  operating instructions

When a historical document conflicts with code, tests, `README.md`, this index,
the runbook, or the invariants, use the live source and update the live docs.

## First commands

```bash
poetry install
poetry run python scripts/document_processing/master_docling.py --help
poetry run python scripts/document_processing/run_pipeline.py --help
poetry run pytest -q
```

Remote APIs are paid and opt-in. Local Docling extraction remains the default.
