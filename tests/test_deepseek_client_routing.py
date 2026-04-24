"""DeepSeek direct and DashScope client routing tests."""

import sys
from types import ModuleType, SimpleNamespace

sys.modules.setdefault(
    "instructor",
    SimpleNamespace(
        Mode=SimpleNamespace(TOOLS_STRICT="tools_strict"),
        from_openai=lambda *args, **kwargs: object(),
    ),
)

for module_name, class_name in (
    ("doc_processing.llm.anthropic_client", "AnthropicClient"),
    ("doc_processing.llm.gemini_client", "GeminiClient"),
    ("doc_processing.llm.kimi_client", "KimiClient"),
    ("doc_processing.llm.qwen_client", "QwenClient"),
):
    module = ModuleType(module_name)
    setattr(module, class_name, object)
    sys.modules.setdefault(module_name, module)

from doc_processing.llm import clients


def test_deepseek_client_uses_direct_base_url(monkeypatch):
    seen = {}

    class FakeOpenAI:
        def __init__(self, *, api_key, base_url=None):
            seen["api_key"] = api_key
            seen["base_url"] = base_url

    monkeypatch.setattr(clients, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(clients.instructor, "from_openai", lambda *args, **kwargs: object())

    client = clients.DeepSeekClient(
        api_key="deepseek-test",
        model_name="deepseek-v4-pro",
        config={"route": "deepseek"},
    )

    assert client.route == "deepseek"
    assert client.get_model_name() == "deepseek-v4-pro"
    assert seen["api_key"] == "deepseek-test"
    assert seen["base_url"] == "https://api.deepseek.com/v1"


def test_deepseek_client_uses_dashscope_base_url(monkeypatch):
    seen = {}

    class FakeOpenAI:
        def __init__(self, *, api_key, base_url=None):
            seen["api_key"] = api_key
            seen["base_url"] = base_url

    monkeypatch.setattr(clients, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(clients.instructor, "from_openai", lambda *args, **kwargs: object())

    client = clients.DeepSeekClient(
        api_key="dashscope-test",
        model_name="deepseek-v4-pro",
        config={"route": "dashscope"},
    )

    assert client.route == "dashscope"
    assert client.get_model_name() == "deepseek-v4-pro"
    assert seen["api_key"] == "dashscope-test"
    assert seen["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
