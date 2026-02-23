"""Qwen (Alibaba) client for multimodal LLM interactions."""

import os
import json
import logging
import base64
from typing import Any, Dict, List, Optional
import requests

from .base import BaseLLMClient
from doc_processing.config import get_settings

logger = logging.getLogger(__name__)


class QwenClient(BaseLLMClient):
    """Client for interacting with Alibaba's Qwen-VL API (multimodal models)."""

    DEFAULT_MODEL = "qwen-vl-max"  # Qwen's best vision-capable model
    API_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Qwen client."""
        settings = get_settings()
        resolved_api_key = api_key or os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or settings.config.get("QWEN_API_KEY")
        resolved_model_name = model_name or os.getenv("QWEN_MODEL") or self.DEFAULT_MODEL

        super().__init__(
            api_key=resolved_api_key,
            model_name=resolved_model_name,
            config=config
        )

        if not self.api_key:
            logger.warning("Qwen API key not found. QwenClient will not function.")

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text completion using Qwen."""
        if not self.api_key:
            raise ValueError("Qwen API key not set. Check QWEN_API_KEY or DASHSCOPE_API_KEY environment variable.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.get_model_name(),
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 4000),
                "top_p": kwargs.get("top_p", 0.8)
            }
        }

        try:
            logger.debug(f"Sending completion request to Qwen model {self.get_model_name()}")
            response = requests.post(
                self.API_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            response.raise_for_status()

            data = response.json()

            # Qwen response format
            if data.get("output") and data["output"].get("choices"):
                completion = data["output"]["choices"][0].get("message", {}).get("content", "")
                return completion.strip()
            else:
                logger.warning("Qwen response structure unexpected or message content empty.")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"Qwen API request failed: {e}")
            raise

    def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output using Qwen."""
        if not self.api_key:
            raise ValueError("Qwen API key not set.")

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
            logger.error(f"Failed to parse JSON from Qwen completion. Error: {e}")
            raise ValueError(f"LLM output was not valid JSON. Completion: {raw_completion}")

    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Generate text completion using Qwen-VL with multimodal input (images + text).

        Args:
            messages: List of message dicts. Qwen expects a specific format for images.
                The client will convert OpenAI-style messages to Qwen format.
        """
        if not self.api_key:
            raise ValueError("Qwen API key not set.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Convert messages to Qwen format
        qwen_messages = self._convert_to_qwen_format(messages)

        payload = {
            "model": self.get_model_name(),
            "input": {
                "messages": qwen_messages
            },
            "parameters": {
                "temperature": kwargs.get("temperature", 0.2),
                "max_tokens": kwargs.get("max_tokens", 4000),
                "top_p": kwargs.get("top_p", 0.8)
            }
        }

        try:
            logger.debug(f"Sending multimodal completion request to Qwen model {self.get_model_name()}")
            response = requests.post(
                self.API_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 180)
            )
            response.raise_for_status()

            data = response.json()

            # Qwen response format
            if data.get("output") and data["output"].get("choices"):
                completion = data["output"]["choices"][0].get("message", {}).get("content", [])
                # Qwen may return content as list or string
                if isinstance(completion, list):
                    # Extract text from content array
                    text_parts = [item.get("text", "") for item in completion if item.get("text")]
                    return " ".join(text_parts).strip()
                else:
                    return completion.strip()
            else:
                logger.warning("Qwen multimodal response structure unexpected or message content empty.")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"Qwen multimodal API request failed: {e}")
            raise

    def _convert_to_qwen_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert OpenAI-style messages to Qwen format.

        Qwen expects:
        [
            {
                "role": "user",
                "content": [
                    {"text": "..."},
                    {"image": "data:image/jpeg;base64,..."}
                ]
            }
        ]
        """
        qwen_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # If content is already a list (multimodal)
            if isinstance(content, list):
                qwen_content = []
                for item in content:
                    if item.get("type") == "text":
                        qwen_content.append({"text": item.get("text", "")})
                    elif item.get("type") == "image_url":
                        image_url = item.get("image_url", {}).get("url", "")
                        qwen_content.append({"image": image_url})

                qwen_messages.append({
                    "role": role,
                    "content": qwen_content
                })
            # If content is a string
            else:
                qwen_messages.append({
                    "role": role,
                    "content": [{"text": content}]
                })

        return qwen_messages

    def supports_language(self, language: str) -> bool:
        """
        Check if Qwen has strong support for the given language.

        Qwen excels at Chinese, Japanese, Korean, and English.
        """
        return language.lower() in [
            'zh', 'zh-cn', 'zh-tw', 'chinese',
            'ja', 'japanese',
            'ko', 'korean',
            'en', 'english'
        ]
