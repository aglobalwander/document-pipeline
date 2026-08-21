"""Subscription-first routing contracts with no live model calls."""

from PIL import Image
import pytest

from doc_processing.config import Settings
from doc_processing.processors.claude_pdf_processor import ClaudePDFProcessor
from doc_processing.processors.image_processor import ImageProcessor
from doc_processing.processors.pdf_processor import GeminiPDFProcessor, GPTPDFProcessor
from doc_processing.transformers.text_to_json import TextToJSON
from scripts.document_processing.run_pipeline import parse_arguments


BASE_ARGS = ["--input_path", "example.txt", "--pipeline_type", "text"]


@pytest.fixture(autouse=True)
def clear_model_default_overrides(monkeypatch):
    for name in (
        "DEFAULT_EMBEDDING_MODEL",
        "DEFAULT_VISION_MODEL",
        "DEFAULT_CHAT_MODEL",
        "DEFAULT_ANTHROPIC_MODEL",
        "DEFAULT_GEMINI_MODEL",
        "DEFAULT_DEEPSEEK_MODEL",
        "DEFAULT_QWEN_MODEL",
        "KIMI_MODEL",
        "ACTIVE_PDF_PROCESSORS",
        "PDF_FALLBACK_ORDER",
    ):
        monkeypatch.delenv(name, raising=False)


def test_general_cli_defaults_are_local_only():
    args = parse_arguments(BASE_ARGS)

    assert args.llm_provider is None
    assert args.ocr_mode == "enhanced_docling"
    assert args.image_backend == "local"


@pytest.mark.parametrize(
    "extra_args",
    [
        ["--llm_model", "some-model"],
        ["--image_backend", "openai"],
        ["--pdf_processor", "gpt"],
        ["--reasoning_effort", "medium"],
        ["--store_remote_state"],
    ],
)
def test_remote_model_options_require_explicit_matching_provider(extra_args):
    with pytest.raises(SystemExit) as exc_info:
        parse_arguments([*BASE_ARGS, *extra_args])

    assert exc_info.value.code == 2


def test_remote_pdf_processor_accepts_matching_explicit_provider():
    args = parse_arguments(
        [*BASE_ARGS, "--pdf_processor", "gemini", "--llm_provider", "gemini"]
    )

    assert args.pdf_processor == "gemini"
    assert args.llm_provider == "gemini"


def test_settings_default_pdf_processors_never_include_remote_apis():
    settings = Settings()

    assert settings.ACTIVE_PDF_PROCESSORS == [
        "enhanced_docling",
        "docling",
        "pymupdf",
    ]
    assert settings.PDF_FALLBACK_ORDER == [
        "enhanced_docling",
        "docling",
        "pymupdf",
    ]


def test_current_api_model_defaults_are_centralized():
    settings = Settings()

    assert settings.DEFAULT_OPENAI_CHAT_MODEL == "gpt-5.6-terra"
    assert settings.DEFAULT_OPENAI_VISION_MODEL == "gpt-5.6-terra"
    assert settings.DEFAULT_OPENAI_EMBEDDING_MODEL == "text-embedding-3-small"
    assert settings.DEFAULT_ANTHROPIC_MODEL == "claude-sonnet-4-6"
    assert settings.DEFAULT_GEMINI_MODEL == "gemini-3.6-flash"
    assert settings.DEFAULT_DEEPSEEK_MODEL == "deepseek-v4-flash"
    assert settings.DEFAULT_QWEN_MODEL == "qwen3.6-flash"
    assert settings.KIMI_MODEL == "kimi-k3"


def test_json_without_provider_uses_local_rules():
    transformer = TextToJSON()

    assert transformer.use_llm is False
    assert transformer.llm_client is None


def test_explicit_use_llm_still_requires_provider():
    with pytest.raises(ValueError, match="explicit llm_provider"):
        TextToJSON({"use_llm": True})


@pytest.mark.parametrize(
    "processor_class",
    [GPTPDFProcessor, GeminiPDFProcessor, ClaudePDFProcessor],
)
def test_remote_pdf_processors_reject_implicit_api_use(processor_class):
    with pytest.raises(ValueError, match="explicit llm_provider"):
        processor_class({})


def test_image_processor_defaults_to_local_tesseract(monkeypatch):
    monkeypatch.setattr(
        "doc_processing.processors.image_processor.pytesseract.image_to_string",
        lambda image: "local text",
    )
    document = {
        "content": Image.new("RGB", (8, 8), "white"),
        "metadata": {"filename": "test.png"},
    }

    result = ImageProcessor().process(document)

    assert result["content"] == "local text"
    assert result["metadata"]["image_backend"] == "local"
    assert result["metadata"]["image_model"] is None


def test_native_reasoning_options_are_available_but_remote_state_is_off():
    args = parse_arguments(
        [
            *BASE_ARGS,
            "--llm_provider",
            "openai",
            "--reasoning_effort",
            "medium",
            "--reasoning_mode",
            "pro",
            "--text_verbosity",
            "low",
        ]
    )

    assert args.reasoning_effort == "medium"
    assert args.reasoning_mode == "pro"
    assert args.text_verbosity == "low"
    assert args.store_remote_state is False


def test_claude_extended_thinking_requires_a_budget():
    with pytest.raises(SystemExit) as exc_info:
        parse_arguments(
            [
                *BASE_ARGS,
                "--llm_provider",
                "anthropic",
                "--thinking",
                "enabled",
            ]
        )

    assert exc_info.value.code == 2


def test_provider_specific_effort_levels_are_validated():
    with pytest.raises(SystemExit) as exc_info:
        parse_arguments(
            [
                *BASE_ARGS,
                "--llm_provider",
                "gemini",
                "--reasoning_effort",
                "max",
            ]
        )

    assert exc_info.value.code == 2
