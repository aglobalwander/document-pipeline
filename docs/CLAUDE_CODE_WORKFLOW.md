# Interactive Claude Code document workflow

Use local extraction first, then use the existing Claude Code subscription for
interactive review. This is separate from the paid Anthropic API.

## 1. Extract locally

```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path /absolute/path/document.pdf \
  --output_format markdown
```

Review the generated Markdown under `data/output/markdown/`.

## 2. Ask Claude Code for a bounded review

Give Claude Code the file path, the source or page range to compare, the desired
output, and whether edits are allowed. Examples:

- review OCR errors and report them with line references;
- restore reading order for one section;
- normalize a table without changing source wording;
- extract named fields into a supplied schema;
- compare the artifact with source pages for completeness.

Keep factual extraction separate from interpretation. For critical documents,
verify every correction against the source rather than inferring missing text.

## 3. Escalate deliberately

If local extraction fails, decide explicitly whether the next step is another
local processor, manual review, or a paid API. The general pipeline's remote
model flags apply to supported transform stages; they are not proof that every
provider is available as a PDF OCR processor.

Provider prices and model IDs change. Check official pricing immediately before
an approved paid run and record the model, input scope, and output path.

## Subscription versus API

| Surface | Authentication | Cost boundary |
|---|---|---|
| Claude Code interactive | existing Claude subscription | covered by subscription terms |
| Anthropic API | `ANTHROPIC_API_KEY` | metered API usage |

Do not claim that interactive subscription access makes automated API calls
free. Credentials load from `~/.config/api-keys/.env.master`; never put a real
key in this repository.
