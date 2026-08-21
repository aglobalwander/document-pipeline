"""Kimi K3 client contract tests with no live API calls."""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.llm.kimi_client import KimiClient


class FakeResponse:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


@pytest.fixture
def no_settings_keys(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_MODEL", raising=False)
    monkeypatch.delenv("MOONSHOT_BASE_URL", raising=False)
    monkeypatch.delenv("KIMI_BASE_URL", raising=False)
    monkeypatch.setattr(
        "doc_processing.llm.kimi_client.get_settings",
        lambda: SimpleNamespace(
            MOONSHOT_API_KEY="",
            KIMI_API_KEY="",
            KIMI_MODEL="kimi-k3",
            MOONSHOT_BASE_URL="https://api.moonshot.ai/v1",
        ),
    )


def test_defaults_to_k3_and_current_global_endpoint(no_settings_keys):
    client = KimiClient(api_key="test-key")

    assert client.get_model_name() == "kimi-k3"
    assert client.api_endpoint == "https://api.moonshot.ai/v1/chat/completions"


def test_prefers_canonical_moonshot_environment_key(monkeypatch, no_settings_keys):
    monkeypatch.setenv("MOONSHOT_API_KEY", "canonical-key")
    monkeypatch.setenv("KIMI_API_KEY", "legacy-key")

    assert KimiClient().api_key == "canonical-key"


def test_completion_uses_k3_payload_and_current_token_field(
    monkeypatch,
    no_settings_keys,
):
    seen = {}

    def fake_post(url, *, headers, json, timeout):
        seen.update(url=url, headers=headers, payload=json, timeout=timeout)
        return FakeResponse("  complete  ")

    monkeypatch.setattr("doc_processing.llm.kimi_client.requests.post", fake_post)
    client = KimiClient(api_key="test-key")

    result = client.generate_completion(
        "Summarize this.",
        system_prompt="Be concise.",
        reasoning_effort="low",
        max_tokens=2_000,
    )

    assert result == "complete"
    assert seen["url"] == "https://api.moonshot.ai/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer test-key"
    assert seen["payload"] == {
        "model": "kimi-k3",
        "messages": [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Summarize this."},
        ],
        "max_completion_tokens": 2_000,
        "reasoning_effort": "low",
    }


def test_payload_defaults_and_sampling_parameters(monkeypatch, no_settings_keys):
    seen = {}

    def fake_post(url, *, headers, json, timeout):
        seen["payload"] = json
        return FakeResponse("complete")

    monkeypatch.setattr("doc_processing.llm.kimi_client.requests.post", fake_post)

    KimiClient(api_key="test-key").generate_completion(
        "hi",
        temperature=0.3,
        top_p=0.9,
    )

    assert seen["payload"] == {
        "model": "kimi-k3",
        "messages": [{"role": "user", "content": "hi"}],
        "max_completion_tokens": 16_000,
        "temperature": 0.3,
        "top_p": 0.9,
    }


def test_structured_output_uses_strict_json_schema(monkeypatch, no_settings_keys):
    seen = {}

    def fake_post(url, *, headers, json, timeout):
        seen["payload"] = json
        return FakeResponse('{"title":"Example"}')

    monkeypatch.setattr("doc_processing.llm.kimi_client.requests.post", fake_post)
    schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
        "additionalProperties": False,
    }

    result = KimiClient(api_key="test-key").generate_structured_output(
        "Extract the title.",
        schema,
    )

    assert result == {"title": "Example"}
    assert seen["payload"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "document_extraction",
            "strict": True,
            "schema": schema,
        },
    }


def test_structured_output_accepts_pydantic_model(monkeypatch, no_settings_keys):
    class DocumentTitle(BaseModel):
        title: str

    seen = {}

    def fake_post(url, *, headers, json, timeout):
        seen["payload"] = json
        return FakeResponse('{"title":"Example"}')

    monkeypatch.setattr("doc_processing.llm.kimi_client.requests.post", fake_post)

    result = KimiClient(api_key="test-key").generate_structured_output(
        "Extract the title.",
        DocumentTitle,
    )

    assert result == {"title": "Example"}
    schema = seen["payload"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["title"]["type"] == "string"
    assert schema["required"] == ["title"]


def test_structured_output_without_schema_uses_json_object_mode(
    monkeypatch,
    no_settings_keys,
):
    seen = {}

    def fake_post(url, *, headers, json, timeout):
        seen["payload"] = json
        return FakeResponse('{"title":"Example"}')

    monkeypatch.setattr("doc_processing.llm.kimi_client.requests.post", fake_post)

    result = KimiClient(api_key="test-key").generate_structured_output(
        "Extract useful fields.",
        {},
    )

    assert result == {"title": "Example"}
    assert seen["payload"]["response_format"] == {"type": "json_object"}
    assert seen["payload"]["messages"][-1]["content"].startswith(
        "Return a valid JSON object."
    )


def test_multimodal_messages_pass_through_unchanged(monkeypatch, no_settings_keys):
    seen = {}
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image."},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AAAA"},
                },
            ],
        }
    ]

    def fake_post(url, *, headers, json, timeout):
        seen["payload"] = json
        return FakeResponse("diagram")

    monkeypatch.setattr("doc_processing.llm.kimi_client.requests.post", fake_post)

    result = KimiClient(api_key="test-key").generate_multimodal_completion(messages)

    assert result == "diagram"
    assert seen["payload"]["messages"] == messages


def test_missing_key_fails_before_network(monkeypatch, no_settings_keys):
    monkeypatch.setattr(
        "doc_processing.llm.kimi_client.requests.post",
        lambda *args, **kwargs: pytest.fail("network should not be called"),
    )

    with pytest.raises(ValueError, match="MOONSHOT_API_KEY"):
        KimiClient().generate_completion("hello")


def test_document_pipeline_propagates_kimi_cli_options_to_json_transformer():
    pipeline = DocumentPipeline(
        config={
            "pipeline_type": "json",
            "llm_provider": "kimi",
            "llm_model": "kimi-k3",
            "api_key": "test-key",
        }
    )

    transformer_config = pipeline._pipeline_component_definitions[0]["config"]
    assert transformer_config["llm_provider"] == "kimi"
    assert transformer_config["llm_model"] == "kimi-k3"
    assert transformer_config["api_key"] == "test-key"
