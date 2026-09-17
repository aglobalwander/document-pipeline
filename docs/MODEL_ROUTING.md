# Model routing and subscription-first policy

Last reviewed: 2026-08-12

## Routing order

Use these lanes in order:

1. Run deterministic extraction locally: Enhanced Docling for PDFs,
   MarkItDown or Mammoth for Office files, and Tesseract for image OCR.
2. Use the current Codex task for one-off review, cleanup, restructuring, and
   judgment. This uses Scott's interactive subscription rather than a pipeline
   API key.
3. If another perspective is specifically useful, use an authenticated
   subscription CLI interactively and verify its account/model status first.
4. Use `--llm_provider` only for repeatable automation that explicitly
   authorizes a metered API call.

The Python pipeline must never read a subscription CLI's OAuth files or
pretend that those credentials are API keys. Subscription products and API
platforms have different authentication, usage rules, and billing.

## Interactive subscription lanes

| Tool | Current local state | Repository use |
|---|---|---|
| Codex | `gpt-5.6-sol` in the active Codex configuration | Preferred interactive review and restructuring lane |
| Kimi Code | OAuth-managed `kimi-code/k3` | Optional interactive second opinion; never reuse its OAuth token as `MOONSHOT_API_KEY` |
| Claude Code | Installed; no repository-pinned model, so verify each session with `/model` and `/status` | Optional interactive second opinion; keep `ANTHROPIC_API_KEY` unset so it does not override subscription authentication |
| Gemini CLI | Installed, but subscription eligibility must be verified in the current account | Do not assume an individual Google AI subscription is a working CLI lane; use it only when organizational subscription status is confirmed |

Do not automate an interactive subscription by scraping or repurposing OAuth
credentials. If an officially supported non-interactive path is billed
separately, classify it as an API/automation lane rather than subscription
interactive use.

## Explicit API defaults

These defaults matter only after the caller opts in with `--llm_provider` or an
explicit remote PDF/image processor.

| Provider | Default model | Review outcome |
|---|---|---|
| OpenAI | `gpt-5.6-terra` | Balanced GPT-5.6 default using the Responses API; vision uses the same multimodal model |
| Anthropic | `claude-sonnet-4-6` | Updated from an obsolete Claude 3/early Claude 4 identifier |
| Gemini | `gemini-3.6-flash` | Updated from the retired `gemini-1.5-pro-latest` alias; stable multimodal/document model |
| DeepSeek direct | `deepseek-v4-flash` | Current direct API model |
| DashScope DeepSeek | `deepseek-v4-flash` | Current Alibaba Model Studio model |
| Kimi Platform | `kimi-k3` | Current paid Platform API model; distinct from `kimi-code/k3` |
| Qwen internal client | `qwen3.6-flash` | Updated from `qwen-vl-max`; balanced current multimodal model, not exposed by the general CLI |
| OpenAI embeddings | `text-embedding-3-small` | Updated from legacy `text-embedding-ada-002` |

Environment variables can override these defaults. An override does not turn a
paid API into a subscription call.

## Provider-native API methods

The clients no longer force every provider through one legacy completion
shape:

| Provider | Native method | Capabilities used |
|---|---|---|
| OpenAI | Responses API | reasoning effort, text verbosity, multimodal input, native Pydantic/JSON-schema output |
| Anthropic | Messages API | effort control, adaptive/extended thinking, native structured output, PDF/image input |
| Gemini | Interactions API | thinking level, multimodal/document input, structured output, optional interaction continuity |
| DeepSeek V4 | Chat Completions compatibility API | native thinking toggle, reasoning effort, JSON object mode |
| Kimi K3 | Kimi Platform Chat Completions | K3 reasoning effort, strict JSON schema, multimodal input |
| Qwen | DashScope multimodal generation | hybrid thinking control, native JSON object mode, image/video-capable model |

OpenAI-compatible Chat Completions remains an intentional compatibility path
for DeepSeek and DashScope; it is not the OpenAI default. Gemini's older
`generate_content` path remains available by setting client `api_style` to
`generate_content` in code. Remote response/interaction storage is disabled by
default for document privacy; `--store_remote_state` is an explicit opt-in.

The model SDK update removed the `instructor` dependency. Structured output is
now validated through each provider's native schema API and Pydantic locally.
The reviewed direct versions are OpenAI Python `3.0.0`, Anthropic `0.121.0`,
Google Gen AI `2.17.0`, and tiktoken `0.13.0`.

## Dependency review outcome

The lock refresh also updated Docling and the repository's YouTube tooling,
replaced the full LangChain dependency with the smaller
`langchain-text-splitters` package actually imported by the code, and removed
the redundant direct `markdownify` declaration. Typer is updated to the newest
line compatible with Docling.

These major-version holds are intentional rather than missed upgrades:

| Package | Constraint kept | Reason |
|---|---|---|
| Python | `>=3.13,<3.14` | Applied 2026-09-17. Floor raised from `^3.10` because 3.10 reaches end-of-life in Oct 2026. The `<3.14` ceiling is verified, not assumed: `onnxruntime <=1.23.2` publishes cp310–cp313 wheels only, so the OCR stack cannot install on 3.14 (onnxruntime publishes cp314 wheels from 1.24.1, so opening 3.14 means moving that ceiling — the OCR migration this repo avoided). `youtube-transcript-api`'s own `python = ">=3.10,<3.14"` override is a second, independent guard; on 3.13 it installs normally, and the live YouTube path is yt-dlp, not that package |
| pandas | `^2.2.0` | pandas 3 is a separate compatibility migration, not a lock refresh |
| pytest | `^8.3` | pytest 9 is a separate test-infrastructure migration |
| onnxruntime | `<=1.23.2` | Preserve the existing runtime compatibility ceiling |
| Typer | `<0.27` | Required by the resolved Docling dependency graph |

Poetry's warnings about legacy `[tool.poetry]` metadata are also deferred to a
separate packaging-metadata migration; they do not make the current lock
invalid.

## CLI behavior

Local extraction requires no model flag:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.pdf \
  --pipeline_type markdown
```

Local JSON uses rule-based extraction when no provider is selected:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/notes.md \
  --pipeline_type json
```

A paid structured transform must name the provider:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/notes.md \
  --pipeline_type json \
  --llm_provider kimi \
  --llm_model kimi-k3
```

Provider-native reasoning can be selected without changing the subscription
boundary:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/notes.md \
  --pipeline_type json \
  --llm_provider openai \
  --reasoning_effort medium \
  --reasoning_mode standard \
  --text_verbosity low
```

Omit reasoning flags to use the model's provider default. OpenAI GPT-5.6
additionally supports `--reasoning_mode standard` (default) or `pro`. Claude
`--thinking enabled` additionally requires `--thinking_budget`; Claude
adaptive thinking uses `--thinking adaptive`. Gemini accepts
`--thinking_summaries auto`. DeepSeek accepts `--thinking enabled` or
`--thinking disabled`.

Remote PDF and image modes require matching explicit provider flags. Local PDF
fallback chains contain only Enhanced Docling, Docling, and PyMuPDF.

## Review cadence

Model aliases and subscription rules change. Before changing an API default:

1. Check the provider's official model and deprecation documentation.
2. Confirm the existing client protocol supports the proposed model.
3. Run contract tests without a live paid request.
4. Make live billing tests a separate, explicit opt-in.

Official references used for this review:

- <https://developers.openai.com/api/docs/models>
- <https://developers.openai.com/api/docs/guides/migrate-to-responses>
- <https://developers.openai.com/api/docs/guides/structured-outputs>
- <https://platform.claude.com/docs/en/about-claude/models/overview>
- <https://platform.claude.com/docs/en/build-with-claude/structured-outputs>
- <https://platform.claude.com/docs/en/build-with-claude/effort>
- <https://ai.google.dev/gemini-api/docs/models>
- <https://ai.google.dev/gemini-api/docs/interactions-overview>
- <https://github.com/google-gemini/gemini-cli/discussions/28017>
- <https://api-docs.deepseek.com/updates/>
- <https://api-docs.deepseek.com/guides/thinking_mode>
- <https://api-docs.deepseek.com/guides/json_mode>
- <https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/env-vars>
- <https://www.alibabacloud.com/help/en/model-studio/deepseek-api>
- <https://www.alibabacloud.com/help/en/model-studio/vision-model>
- <https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output>
