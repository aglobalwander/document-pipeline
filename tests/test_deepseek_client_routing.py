"""DeepSeek direct and DashScope client routing tests."""

from doc_processing.llm import clients


def test_deepseek_client_uses_direct_base_url(monkeypatch):
    seen = {}

    class FakeOpenAI:
        def __init__(self, *, api_key, base_url=None):
            seen["api_key"] = api_key
            seen["base_url"] = base_url

    monkeypatch.setattr(clients, "OpenAI", FakeOpenAI)
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
    client = clients.DeepSeekClient(
        api_key="dashscope-test",
        model_name="deepseek-v4-pro",
        config={"route": "dashscope"},
    )

    assert client.route == "dashscope"
    assert client.get_model_name() == "deepseek-v4-pro"
    assert seen["api_key"] == "dashscope-test"
    assert seen["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
