"""Kimi API client for text, structured, image, and video-aware requests."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import urljoin

import requests
from pydantic import BaseModel

from doc_processing.config import get_settings

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class KimiClient(BaseLLMClient):
    """Client for Moonshot AI's OpenAI-compatible Kimi API.

    Kimi K3 is the default paid API model. Local extraction remains the
    pipeline default; constructing this client never makes an API request.
    """

    DEFAULT_MODEL = "kimi-k3"
    DEFAULT_BASE_URL = "https://api.moonshot.ai/v1"
    DEFAULT_MAX_COMPLETION_TOKENS = 16_000

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Kimi without contacting the API."""
        settings = get_settings()
        client_config = dict(config or {})
        resolved_api_key = (
            api_key
            or os.getenv("MOONSHOT_API_KEY")
            or os.getenv("KIMI_API_KEY")
            or settings.MOONSHOT_API_KEY
            or settings.KIMI_API_KEY
        )
        resolved_model_name = (
            model_name
            or os.getenv("KIMI_MODEL")
            or client_config.get("model")
            or settings.KIMI_MODEL
            or self.DEFAULT_MODEL
        )
        base_url = (
            client_config.get("base_url")
            or os.getenv("MOONSHOT_BASE_URL")
            or os.getenv("KIMI_BASE_URL")
            or settings.MOONSHOT_BASE_URL
            or self.DEFAULT_BASE_URL
        )

        super().__init__(
            api_key=resolved_api_key,
            model_name=resolved_model_name,
            config=client_config,
        )
        self.base_url = base_url.rstrip("/")
        self.api_endpoint = urljoin(f"{self.base_url}/", "chat/completions")

        if not self.api_key:
            logger.warning(
                "Kimi API key not found. Set MOONSHOT_API_KEY (preferred) or "
                "KIMI_API_KEY before making a paid API request."
            )

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "Kimi API key not set. Check MOONSHOT_API_KEY or KIMI_API_KEY."
            )

    def _request_payload(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.get_model_name(),
            "messages": messages,
            "max_completion_tokens": kwargs.get(
                "max_completion_tokens",
                kwargs.get("max_tokens", self.DEFAULT_MAX_COMPLETION_TOKENS),
            ),
        }

        # K3 always reasons. Omitting reasoning_effort preserves the provider's
        # current default (max); callers can explicitly request low/high/max.
        for parameter in ("reasoning_effort", "temperature", "top_p", "response_format"):
            value = kwargs.get(parameter)
            if value is not None:
                payload[parameter] = value

        return payload

    def _post_completion(self, payload: Dict[str, Any], timeout: int) -> str:
        self._require_api_key()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Kimi API request failed: %s", exc)
            raise

        choices = data.get("choices") or []
        message = choices[0].get("message") if choices else None
        content = message.get("content") if message else None
        if not isinstance(content, str):
            logger.warning("Kimi response did not contain text message content.")
            return ""
        return content.strip()

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a text completion using Kimi Chat Completions."""
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = self._request_payload(messages, **kwargs)
        logger.debug("Sending completion request to Kimi model %s", self.get_model_name())
        return self._post_completion(payload, timeout=kwargs.get("timeout", 300))

    def generate_structured_output(
        self,
        prompt: str,
        output_schema: Union[Dict[str, Any], Type[BaseModel]],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate JSON constrained by Kimi K3's native structured output."""
        self._require_api_key()
        if isinstance(output_schema, type) and issubclass(output_schema, BaseModel):
            schema = output_schema.model_json_schema()
        elif isinstance(output_schema, dict):
            schema = output_schema
        else:
            raise TypeError("output_schema must be a JSON Schema dictionary or Pydantic model.")

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if schema:
            messages.append({"role": "user", "content": prompt})
        else:
            # TextToJSON intentionally allows callers to request arbitrary JSON
            # without supplying a schema. K3's JSON object mode covers that path.
            messages.append(
                {
                    "role": "user",
                    "content": f"Return a valid JSON object.\n\n{prompt}",
                }
            )

        structured_kwargs = dict(kwargs)
        if schema:
            structured_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": structured_kwargs.pop("schema_name", "document_extraction"),
                    "strict": True,
                    "schema": schema,
                },
            }
        else:
            structured_kwargs["response_format"] = {"type": "json_object"}
        payload = self._request_payload(messages, **structured_kwargs)
        raw_completion = self._post_completion(
            payload,
            timeout=structured_kwargs.get("timeout", 300),
        )

        try:
            return json.loads(raw_completion)
        except json.JSONDecodeError as exc:
            logger.error("Kimi structured output was not valid JSON: %s", exc)
            raise ValueError("Kimi structured output was not valid JSON.") from exc

    def generate_multimodal_completion(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """Generate a completion from OpenAI-style text/image/video messages."""
        payload = self._request_payload(messages, **kwargs)
        logger.debug("Sending multimodal request to Kimi model %s", self.get_model_name())
        return self._post_completion(payload, timeout=kwargs.get("timeout", 300))

    def supports_language(self, language: str) -> bool:
        """Return whether the client has first-class Chinese or English support."""
        return language.lower() in {
            "zh",
            "zh-cn",
            "zh-tw",
            "en",
            "english",
            "chinese",
        }
