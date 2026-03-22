---
paths:
  - "scripts/**"
  - "src/**"
  - "*.py"
---

## Processing Strategy

### Cost Hierarchy (use cheapest that works)
1. **Enhanced Docling** (FREE) — default for PDFs, local OCR, excellent quality
2. **Claude Code** (FREE with subscription) — default for LLM tasks, interactive
3. **Gemini API** ($0.08-0.30/1M tokens) — batch automation, only when explicitly asked
4. **Claude/GPT API** ($2.50-15/1M tokens) — only when explicitly asked

### Environment
**Use Poetry** — NOT conda, NOT venv. All packages installed via Poetry.
```bash
poetry run python <script.py>
```

### Pipeline Pattern
Extract (Docling/MarkItDown) → Transform/Structure (Claude Code) → Output

### Output Convention
Default output: `data/output/`. Never overwrite — use timestamped subdirectories for batch runs.

### Feeds Into
- **knowledge-management** — highest-volume data flow in ecosystem
- Outputs become Milvus collection entries (literature_v1, practitioner_resources_v1, etc.)
