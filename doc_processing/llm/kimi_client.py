"""Kimi (Moonshot AI) client for multimodal LLM interactions."""

import os
import json
import logging
import base64
from typing import Any, Dict, List, Optional
import requests

from .base import BaseLLMClient
from doc_processing.config import get_settings

logger = logging.getLogger(__name__)


class KimiClient(BaseLLMClient):
    """Client for interacting with Moonshot AI's Kimi API (multimodal models)."""

    DEFAULT_MODEL = "moonshot-v1-128k"  # Kimi's vision-capable model
    API_ENDPOINT = "https://api.moonshot.cn/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Kimi client."""
        settings = get_settings()
        resolved_api_key = api_key or os.getenv("KIMI_API_KEY") or settings.config.get("KIMI_API_KEY")
        resolved_model_name = model_name or os.getenv("KIMI_MODEL") or self.DEFAULT_MODEL

        super().__init__(
            api_key=resolved_api_key,
            model_name=resolved_model_name,
            config=config
        )

        if not self.api_key:
            logger.warning("Kimi API key not found. KimiClient will not function.")

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text completion using Kimi Chat Completions."""
        if not self.api_key:
            raise ValueError("Kimi API key not set. Check KIMI_API_KEY environment variable.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.get_model_name(),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 4000),
        }

        try:
            logger.debug(f"Sending completion request to Kimi model {self.get_model_name()}")
            response = requests.post(
                self.API_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            response.raise_for_status()

            data = response.json()
            if data.get("choices") and data["choices"][0].get("message"):
                completion = data["choices"][0]["message"].get("content", "")
                return completion.strip()
            else:
                logger.warning("Kimi response structure unexpected or message content empty.")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"Kimi API request failed: {e}")
            raise

    def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output using Kimi."""
        if not self.api_key:
            raise ValueError("Kimi API key not set.")

        # Add JSON instructions to system prompt
        default_system_prompt = "You are an expert data extraction assistant. Extract structured information from the user's text."
        json_system_prompt = (system_prompt or default_system_prompt) + \
            "\n\nYour response MUST be a single, valid JSON object conforming to the following schema, with no extra text or explanation before or after it."

        if output_schema:
            schema_string = json.dumps(output_schema, indent=2)
            json_system_prompt += f"\n\nDesired JSON Schema:\n```json\n{schema_string}\n```"

        # Generate completion
        raw_completion = self.generate_completion(
            prompt,
            system_prompt=json_system_prompt,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 4000)
        )

        # Parse JSON
        try:
            json_start = raw_completion.find('{')
            json_end = raw_completion.rfind('}')
            if json_start != -1 and json_end != -1:
                json_str = raw_completion[json_start:json_end+1]
                parsed_json = json.loads(json_str)
                return parsed_json
            else:
                return json.loads(raw_completion)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Kimi completion. Error: {e}")
            raise ValueError(f"LLM output was not valid JSON. Completion: {raw_completion}")

    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Generate text completion using Kimi with multimodal input (images + text).

        Args:
            messages: List of message dicts with format:
                [
                    {"role": "system", "content": "..."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "..."},
                            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
                        ]
                    }
                ]
        """
        if not self.api_key:
            raise ValueError("Kimi API key not set.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.get_model_name(),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 4000),
        }

        try:
            logger.debug(f"Sending multimodal completion request to Kimi model {self.get_model_name()}")
            response = requests.post(
                self.API_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 180)
            )
            response.raise_for_status()

            data = response.json()
            if data.get("choices") and data["choices"][0].get("message"):
                completion = data["choices"][0]["message"].get("content", "")
                return completion.strip()
            else:
                logger.warning("Kimi multimodal response structure unexpected or message content empty.")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"Kimi multimodal API request failed: {e}")
            raise

    def supports_language(self, language: str) -> bool:
        """
        Check if Kimi has strong support for the given language.

        Kimi excels at Chinese and has good English support.
        """
        return language.lower() in ['zh', 'zh-cn', 'zh-tw', 'en', 'english', 'chinese']
