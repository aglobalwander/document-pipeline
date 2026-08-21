"""Provider-native LLM protocol contracts with no live API calls."""

from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from doc_processing.llm.anthropic_client import AnthropicClient
from doc_processing.llm.clients import DeepSeekClient, OpenAIClient
from doc_processing.llm.gemini_client import GeminiClient
from doc_processing.llm.qwen_client import QwenClient


class DocumentTitle(BaseModel):
    title: str


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return SimpleNamespace(output_text='{"title":"Example"}')

    def parse(self, **kwargs):
        self.calls.append(("parse", kwargs))
        return SimpleNamespace(output_parsed=DocumentTitle(title="Example"))


def test_openai_defaults_to_responses_with_private_stateless_requests():
    client = OpenAIClient(api_key="test-key")
    responses = FakeResponses()
    client.client = SimpleNamespace(responses=responses)

    result = client.generate_completion(
        "Summarize this.",
        reasoning_effort="medium",
        reasoning_mode="pro",
        verbosity="low",
    )

    assert result == '{"title":"Example"}'
    _, payload = responses.calls[0]
    assert payload["model"] == "gpt-5.6-terra"
    assert payload["store"] is False
    assert payload["reasoning"] == {"effort": "medium", "mode": "pro"}
    assert payload["text"] == {"verbosity": "low"}


def test_openai_uses_responses_parse_for_pydantic_output():
    client = OpenAIClient(api_key="test-key")
    responses = FakeResponses()
    client.client = SimpleNamespace(responses=responses)

    result = client.generate_structured_output(
        "Extract the title.", DocumentTitle
    )

    assert result == {"title": "Example"}
    method, payload = responses.calls[0]
    assert method == "parse"
    assert payload["text_format"] is DocumentTitle
    assert payload["store"] is False


def test_openai_converts_chat_style_images_for_responses():
    client = OpenAIClient(api_key="test-key")
    responses = FakeResponses()
    client.client = SimpleNamespace(responses=responses)

    client.generate_multimodal_completion(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Read this."},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,AAAA"},
                    },
                ],
            }
        ]
    )

    _, payload = responses.calls[0]
    assert payload["input"][0]["content"] == [
        {"type": "input_text", "text": "Read this."},
        {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
    ]


def test_deepseek_uses_chat_completions_thinking_controls():
    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="complete"))]
        )

    client = DeepSeekClient(
        api_key="test-key",
        config={"reasoning_effort": "high", "thinking": "enabled"},
    )
    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    assert client.generate_completion("Analyze this.", temperature=0.2) == "complete"
    assert seen["reasoning_effort"] == "high"
    assert seen["extra_body"] == {"thinking": {"type": "enabled"}}
    assert "temperature" not in seen


class FakeAnthropicMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="work"),
                SimpleNamespace(type="text", text='{"title":"Example"}'),
            ]
        )

    def parse(self, **kwargs):
        self.calls.append(("parse", kwargs))
        return SimpleNamespace(
            parsed_output=DocumentTitle(title="Example"), content=[]
        )


def test_anthropic_uses_effort_and_native_structured_output():
    client = AnthropicClient(api_key="test-key")
    messages = FakeAnthropicMessages()
    client.client = SimpleNamespace(messages=messages)

    result = client.generate_structured_output(
        "Extract the title.", DocumentTitle, reasoning_effort="medium"
    )

    assert result == {"title": "Example"}
    method, payload = messages.calls[0]
    assert method == "parse"
    assert payload["output_format"] is DocumentTitle
    assert payload["output_config"] == {"effort": "medium"}


class FakeInteractions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text='{"title":"Example"}')


def test_gemini_defaults_to_interactions_and_maps_reasoning_effort():
    client = GeminiClient(api_key="test-key")
    interactions = FakeInteractions()
    client.client = SimpleNamespace(interactions=interactions)

    result = client.generate_completion("Summarize.", reasoning_effort="high")

    assert result == '{"title":"Example"}'
    payload = interactions.calls[0]
    assert payload["model"] == "gemini-3.6-flash"
    assert payload["store"] is False
    assert payload["generation_config"]["thinking_level"] == "high"


def test_gemini_interactions_enforces_json_schema():
    client = GeminiClient(api_key="test-key")
    interactions = FakeInteractions()
    client.client = SimpleNamespace(interactions=interactions)

    result = client.generate_structured_output(
        "Extract the title.", DocumentTitle
    )

    assert result == {"title": "Example"}
    payload = interactions.calls[0]
    assert payload["response_mime_type"] == "application/json"
    assert payload["response_format"]["schema"]["required"] == ["title"]


def test_gemini_pdf_uses_interactions_document_input(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    client = GeminiClient(api_key="test-key")
    interactions = FakeInteractions()
    client.client = SimpleNamespace(interactions=interactions)

    client.process_pdf(str(pdf_path), "Extract text.")

    document = interactions.calls[0]["input"][0]
    assert document["type"] == "document"
    assert document["mime_type"] == "application/pdf"
    assert document["data"]


class FakeHTTPResponse:
    def __init__(self, content: str):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "output": {
                "choices": [{"message": {"content": self.content}}]
            }
        }


def test_qwen_uses_current_balanced_multimodal_model(monkeypatch):
    seen = {}

    def post(url, *, headers, json, timeout):
        seen.update(url=url, payload=json)
        return FakeHTTPResponse("complete")

    monkeypatch.setattr("doc_processing.llm.qwen_client.requests.post", post)
    client = QwenClient(api_key="test-key")

    assert client.generate_completion("Summarize.", enable_thinking=True) == "complete"
    assert client.get_model_name() == "qwen3.6-flash"
    assert seen["payload"]["parameters"]["result_format"] == "message"
    assert seen["payload"]["parameters"]["enable_thinking"] is True
    assert "temperature" not in seen["payload"]["parameters"]


def test_qwen_structured_output_uses_json_mode_without_thinking(monkeypatch):
    seen = {}

    def post(url, *, headers, json, timeout):
        seen["payload"] = json
        return FakeHTTPResponse('{"title":"Example"}')

    monkeypatch.setattr("doc_processing.llm.qwen_client.requests.post", post)

    result = QwenClient(api_key="test-key").generate_structured_output(
        "Extract the title.",
        {"type": "object", "properties": {"title": {"type": "string"}}},
    )

    assert result == {"title": "Example"}
    parameters = seen["payload"]["parameters"]
    assert parameters["enable_thinking"] is False
    assert parameters["response_format"] == {"type": "json_object"}
