"""Concrete implementations of OpenAI and OpenAI-compatible LLM clients."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Type, Union

from openai import OpenAI
from pydantic import BaseModel

from .base import BaseLLMClient
from doc_processing.config import get_settings

logger = logging.getLogger(__name__)

class OpenAIClient(BaseLLMClient):
    """OpenAI client using the provider-native Responses API."""

    DEFAULT_MODEL = "gpt-5.6-terra"
    API_ENDPOINT = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI client."""
        settings = get_settings()
        resolved_api_key = api_key or settings.OPENAI_API_KEY or settings.OPENAI_APIKEY
        resolved_model_name = model_name or settings.DEFAULT_OPENAI_CHAT_MODEL or self.DEFAULT_MODEL
        super().__init__(api_key=resolved_api_key, model_name=resolved_model_name, config=config)
        self.api_style = self.config.get("api_style", "responses")

        if not self.api_key:
            logger.warning("OpenAI API key not found. OpenAIClient will not function.")
            self.client = None
        else:
            base_url = self.config.get("base_url")
            self.client = OpenAI(api_key=self.api_key, base_url=base_url) if base_url else OpenAI(api_key=self.api_key)

    @staticmethod
    def _is_pydantic_schema(output_schema: Any) -> bool:
        return isinstance(output_schema, type) and issubclass(output_schema, BaseModel)

    @staticmethod
    def _parse_json_object(raw_completion: str) -> Dict[str, Any]:
        raw_completion = raw_completion.strip()
        try:
            return json.loads(raw_completion)
        except json.JSONDecodeError as error:
            json_start = raw_completion.find("{")
            json_end = raw_completion.rfind("}")
            if json_start != -1 and json_end > json_start:
                try:
                    return json.loads(raw_completion[json_start:json_end + 1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(
                f"LLM output was not valid JSON. Completion: {raw_completion[:500]}"
            ) from error

    def _responses_options(
        self,
        kwargs: Dict[str, Any],
        *,
        default_max_tokens: int,
    ) -> Dict[str, Any]:
        """Build Responses API options without silently enabling state storage."""
        options: Dict[str, Any] = {
            "model": self.get_model_name(),
            "max_output_tokens": kwargs.get("max_tokens", default_max_tokens),
            "store": kwargs.get("store", self.config.get("store", False)),
        }
        reasoning: Dict[str, Any] = {}
        reasoning_effort = kwargs.get(
            "reasoning_effort", self.config.get("reasoning_effort")
        )
        if reasoning_effort and reasoning_effort != "none":
            reasoning["effort"] = reasoning_effort
        for option, key in (
            ("reasoning_mode", "mode"),
            ("reasoning_context", "context"),
            ("reasoning_summary", "summary"),
        ):
            value = kwargs.get(option, self.config.get(option))
            if value is not None:
                reasoning[key] = value
        if reasoning:
            options["reasoning"] = reasoning

        text_config: Dict[str, Any] = {}
        verbosity = kwargs.get("verbosity", self.config.get("verbosity"))
        if verbosity:
            text_config["verbosity"] = verbosity
        if text_config:
            options["text"] = text_config

        for option in (
            "previous_response_id",
            "prompt_cache_key",
            "prompt_cache_retention",
            "safety_identifier",
            "service_tier",
        ):
            value = kwargs.get(option, self.config.get(option))
            if value is not None:
                options[option] = value
        if kwargs.get("temperature") is not None:
            options["temperature"] = kwargs["temperature"]
        return options

    def _chat_options(
        self,
        kwargs: Dict[str, Any],
        *,
        default_max_tokens: int,
    ) -> Dict[str, Any]:
        """Build options for OpenAI-compatible Chat Completions providers."""
        options: Dict[str, Any] = {
            "max_tokens": kwargs.get("max_tokens", default_max_tokens),
        }
        if kwargs.get("temperature") is not None:
            options["temperature"] = kwargs["temperature"]
        if kwargs.get("top_p") is not None:
            options["top_p"] = kwargs["top_p"]
        return options

    @staticmethod
    def _chat_text(response: Any) -> str:
        if response.choices and response.choices[0].message:
            return (response.choices[0].message.content or "").strip()
        return ""

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text using Responses, or Chat Completions for compatibility."""
        if not self.client:
            raise ValueError("OpenAI client not initialized (check API key).")

        try:
            if self.api_style == "responses":
                options = self._responses_options(kwargs, default_max_tokens=1500)
                response = self.client.responses.create(
                    input=prompt,
                    instructions=system_prompt,
                    **options,
                )
                return (response.output_text or "").strip()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = self.client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                **self._chat_options(kwargs, default_max_tokens=1500),
            )
            return self._chat_text(response)
        except Exception as error:
            logger.error("OpenAI-compatible completion request failed: %s", error)
            raise

    # Type hint for output_schema allows checking if it's a Pydantic model type
    def generate_structured_output(self, prompt: str, output_schema: Union[Dict[str, Any], Type[BaseModel]], system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate provider-enforced structured JSON output."""
        if not self.client:
            raise ValueError("OpenAI client not initialized (check API key).")

        default_system_prompt = "You are an expert data extraction assistant. Extract structured information from the user's text."
        instructions = system_prompt or default_system_prompt

        try:
            if self._is_pydantic_schema(output_schema):
                schema_dict = output_schema.model_json_schema()
            elif isinstance(output_schema, dict):
                schema_dict = output_schema
            else:
                schema_dict = {}

            if self.api_style == "responses":
                options = self._responses_options(kwargs, default_max_tokens=4000)
                if self._is_pydantic_schema(output_schema):
                    response = self.client.responses.parse(
                        input=prompt,
                        instructions=instructions,
                        text_format=output_schema,
                        **options,
                    )
                    parsed = response.output_parsed
                    if parsed is None:
                        raise ValueError("OpenAI structured response had no parsed output.")
                    return parsed.model_dump() if isinstance(parsed, BaseModel) else parsed

                text_config = dict(options.pop("text", {}))
                if schema_dict:
                    text_config["format"] = {
                        "type": "json_schema",
                        "name": kwargs.get("schema_name", "document_extraction"),
                        "strict": True,
                        "schema": schema_dict,
                    }
                else:
                    text_config["format"] = {"type": "json_object"}
                response = self.client.responses.create(
                    input=prompt,
                    instructions=instructions,
                    text=text_config,
                    **options,
                )
                return self._parse_json_object(response.output_text or "")

            json_instructions = instructions + "\n\nReturn one valid JSON object."
            if schema_dict:
                json_instructions += f"\nJSON Schema:\n{json.dumps(schema_dict)}"
            messages = [
                {"role": "system", "content": json_instructions},
                {"role": "user", "content": prompt},
            ]
            chat_options = self._chat_options(kwargs, default_max_tokens=4000)
            if self.config.get("use_json_mode", True):
                chat_options["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(
                model=self.get_model_name(), messages=messages, **chat_options
            )
            parsed = self._parse_json_object(self._chat_text(response))
            if self._is_pydantic_schema(output_schema):
                return output_schema.model_validate(parsed).model_dump()
            return parsed
        except Exception as error:
            logger.error("OpenAI-compatible structured output request failed: %s", error)
            raise

    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate text from OpenAI-style text/image messages."""
        if not self.client:
            raise ValueError("OpenAI client not initialized (check API key).")

        try:
            if self.api_style == "responses":
                instructions: List[str] = []
                response_input: List[Dict[str, Any]] = []
                for message in messages:
                    if message.get("role") == "system":
                        instructions.append(str(message.get("content", "")))
                        continue
                    content = message.get("content", "")
                    if isinstance(content, str):
                        response_input.append(
                            {"role": message.get("role", "user"), "content": content}
                        )
                        continue
                    converted_content = []
                    for part in content:
                        if part.get("type") == "text":
                            converted_content.append(
                                {"type": "input_text", "text": part.get("text", "")}
                            )
                        elif part.get("type") == "image_url":
                            image_url = part.get("image_url", {})
                            url = image_url.get("url") if isinstance(image_url, dict) else image_url
                            converted_content.append(
                                {"type": "input_image", "image_url": url}
                            )
                    response_input.append(
                        {"role": message.get("role", "user"), "content": converted_content}
                    )
                response = self.client.responses.create(
                    input=response_input,
                    instructions="\n\n".join(instructions) or None,
                    **self._responses_options(kwargs, default_max_tokens=3000),
                )
                return (response.output_text or "").strip()

            response = self.client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                **self._chat_options(kwargs, default_max_tokens=3000),
            )
            return self._chat_text(response)
        except Exception as error:
            logger.error("OpenAI-compatible multimodal request failed: %s", error)
            raise


class DeepSeekClient(OpenAIClient):
    """OpenAI-compatible client for DeepSeek direct or DashScope-hosted DeepSeek."""

    DEFAULT_MODEL = "deepseek-v4-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        route: str = "deepseek",
    ):
        settings = get_settings()
        client_config = dict(config or {})
        resolved_route = str(client_config.pop("route", route) or "deepseek").lower()
        client_config["api_style"] = "chat_completions"
        if resolved_route in {"dashscope", "bailian", "dashscope_deepseek"}:
            resolved_api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or settings.DASHSCOPE_API_KEY
            resolved_model_name = model_name or os.getenv("DASHSCOPE_DEEPSEEK_MODEL") or settings.DEFAULT_DASHSCOPE_DEEPSEEK_MODEL
            client_config["base_url"] = client_config.get("base_url") or settings.DASHSCOPE_COMPAT_BASE_URL
            self.route = "dashscope"
        else:
            resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or settings.DEEPSEEK_API_KEY
            resolved_model_name = model_name or os.getenv("DEEPSEEK_MODEL") or settings.DEFAULT_DEEPSEEK_MODEL
            client_config["base_url"] = client_config.get("base_url") or settings.DEEPSEEK_BASE_URL
            self.route = "deepseek"

        super().__init__(
            api_key=resolved_api_key,
            model_name=resolved_model_name,
            config=client_config,
        )

    def _chat_options(
        self,
        kwargs: Dict[str, Any],
        *,
        default_max_tokens: int,
    ) -> Dict[str, Any]:
        """Enable DeepSeek V4 thinking controls without legacy sampling noise."""
        options: Dict[str, Any] = {
            "max_tokens": kwargs.get("max_tokens", default_max_tokens),
        }
        reasoning_effort = kwargs.get(
            "reasoning_effort", self.config.get("reasoning_effort")
        )
        if reasoning_effort and reasoning_effort != "none":
            options["reasoning_effort"] = reasoning_effort

        thinking = kwargs.get("thinking", self.config.get("thinking"))
        if thinking in {"enabled", "disabled"}:
            options["extra_body"] = {"thinking": {"type": thinking}}

        if thinking != "enabled" and not reasoning_effort:
            if kwargs.get("temperature") is not None:
                options["temperature"] = kwargs["temperature"]
            if kwargs.get("top_p") is not None:
                options["top_p"] = kwargs["top_p"]
        return options


# Import and export Anthropic client
try:
    from .anthropic_client import AnthropicClient
    ANTHROPIC_CLIENT_AVAILABLE = True
except ImportError:
    ANTHROPIC_CLIENT_AVAILABLE = False
    logger.warning("AnthropicClient not available. Install 'anthropic' package to use Claude.")

# Import and export Gemini client
try:
    from .gemini_client import GeminiClient
    GEMINI_CLIENT_AVAILABLE = True
except ImportError:
    GEMINI_CLIENT_AVAILABLE = False
    logger.warning("GeminiClient not available.")

# Import and export Kimi client
try:
    from .kimi_client import KimiClient
    KIMI_CLIENT_AVAILABLE = True
except ImportError:
    KIMI_CLIENT_AVAILABLE = False
    logger.warning("KimiClient not available.")

# Import and export Qwen client
try:
    from .qwen_client import QwenClient
    QWEN_CLIENT_AVAILABLE = True
except ImportError:
    QWEN_CLIENT_AVAILABLE = False
    logger.warning("QwenClient not available.")

__all__ = ['OpenAIClient', 'DeepSeekClient', 'BaseLLMClient']

if ANTHROPIC_CLIENT_AVAILABLE:
    __all__.append('AnthropicClient')

if GEMINI_CLIENT_AVAILABLE:
    __all__.append('GeminiClient')

if KIMI_CLIENT_AVAILABLE:
    __all__.append('KimiClient')

if QWEN_CLIENT_AVAILABLE:
    __all__.append('QwenClient')
