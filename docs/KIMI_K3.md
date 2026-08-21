# Kimi K3 integration

Last verified: 2026-07-20

Kimi K3 is Moonshot AI's current flagship model. It has native text, image, and
video understanding, a 1,048,576-token context window, always-on preserved
thinking, and `low`, `high`, or `max` reasoning effort. The API model ID is
`kimi-k3`.

Official references:

- [Kimi K3 technical blog](https://www.kimi.com/blog/kimi-k3)
- [Kimi K3 API quickstart](https://platform.kimi.ai/docs/guide/kimi-k3-quickstart)
- [Kimi model list](https://platform.kimi.ai/docs/models)
- [Kimi Code documentation](https://moonshotai.github.io/kimi-code/)

## Two separate lanes

| Lane | Authentication | Model selection | Use here |
|---|---|---|---|
| Kimi Code CLI | Kimi subscription OAuth | `/model` or `-m kimi-code/k3` | interactive review and agentic coding |
| Kimi Open Platform API | `MOONSHOT_API_KEY` | API model `kimi-k3` | explicit paid pipeline automation |

OAuth in Kimi Code does not provide an Open Platform API key to Python. Do not
copy tokens or keys between the two homes.

## Kimi Code CLI

Install or update the standalone CLI:

```bash
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
kimi update
kimi --version
kimi doctor
```

The standalone CLI stores data under `~/.kimi-code/`. A migrated legacy Python
installation may remain available as `kimi-legacy` under `~/.local/bin/`.

Select K3 in a new session. Do not switch an established conversation from
another model to K3 because K3 expects its preserved thinking history.

```bash
kimi -m kimi-code/k3 -p \
  "Do not modify files. Review README.md and report broken commands with file:line references."
```

K3 is trained for long-horizon work and can be over-proactive on small or
ambiguous tasks. State file boundaries, forbidden actions, output format, and
success criteria explicitly.

## Pipeline API configuration

The pipeline loads credentials from `~/.config/api-keys/.env.master` through
`doc_processing.config`. Use the canonical Kimi Platform names:

```dotenv
MOONSHOT_API_KEY=replace_in_master_store_only
KIMI_MODEL=kimi-k3
MOONSHOT_BASE_URL=https://api.moonshot.ai/v1
```

`KIMI_API_KEY` and `KIMI_BASE_URL` remain compatibility aliases. Never put a
real key into a tracked `.env`, `.env.backup`, fixture, command, or log.

Programmatic usage:

```python
from doc_processing.llm.kimi_client import KimiClient

client = KimiClient()  # no request is made during construction
result = client.generate_completion(
    "Summarize the extraction risks in this text.",
    reasoning_effort="low",
)
```

When a schema is supplied, structured output uses K3's strict JSON Schema mode
rather than prompt-only JSON extraction:

```python
schema = {
    "type": "object",
    "properties": {"title": {"type": "string"}},
    "required": ["title"],
    "additionalProperties": False,
}
data = client.generate_structured_output("Title: Example", schema)
```

Passing an empty schema requests K3's generic JSON-object mode. This keeps the
general `--pipeline_type json` path usable when the caller does not have a
schema, while schema-bound workflows retain strict validation.

The general pipeline exposes Kimi for JSON and structured transforms:

```bash
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path /absolute/path/document.md \
  --pipeline_type json \
  --output_format json \
  --llm_provider kimi \
  --llm_model kimi-k3
```

This is paid API automation. Use it only when explicitly requested; local
extraction followed by interactive review remains the preferred default.

## Capability contract

- Text and long context: supported. The Open Platform K3 API advertises
  1,048,576 tokens; the managed CLI catalog on this account currently advertises
  262,144 tokens, so plan CLI work against the lower observed limit.
- Image and video message parts: supported by the API client pass-through.
- JSON output: strict JSON Schema when supplied; generic JSON-object mode when
  no schema is supplied.
- Thinking: always on for K3; `reasoning_effort` accepts `low`, `high`, `max`.
- Multi-turn/tool calls: preserve the complete assistant message, including
  `reasoning_content` and `tool_calls`.
- Reasoning defaults differ by lane: the K3 API defaults to `max`; the current
  managed CLI catalog defaults to `high`.
- K2.x `thinking` request configuration: do not use for K3.

## Verification

Mocked tests make no paid requests:

```bash
poetry run pytest -q tests/test_kimi_client.py
```

Verify the CLI separately after OAuth login:

```bash
kimi doctor
kimi -m kimi-code/k3 -p "Reply with exactly: K3_READY"
```

A successful text prompt proves model routing and basic generation only. Vision,
long-context retrieval, structured API output, and agentic file work are
separate capability checks and should be reported independently.

### Local verification snapshot — 2026-07-20

- Text/model routing: passed with the managed `kimi-code/k3` provider.
- Read-only repository tool use: passed; K3 identified a missing client test
  branch, which was independently verified and added.
- Image understanding: passed on a generated green-triangle/`37` fixture.
- Video understanding: passed on a generated red-then-blue MP4 fixture.
- Exact-output compliance: imperfect; text, image, and video answers could add
  a short preamble even when an exact final format was requested.
- Strict API schema behavior: covered by mocked request-contract tests only. No
  paid Kimi Platform request was made.
- One-million-token retrieval was not exercised; the managed CLI advertises a
  smaller context than the Open Platform API.
