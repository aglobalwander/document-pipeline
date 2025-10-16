"""Concrete implementation for Anthropic Claude LLM client."""

import os
import json
import logging
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel

# Import Anthropic SDK
try:
    import anthropic
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import BaseLLMClient
from doc_processing.config import get_settings

logger = logging.getLogger(__name__)

class AnthropicClient(BaseLLMClient):
    """Client for interacting with Anthropic's Claude API."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"  # Latest Sonnet with vision
    # Alternative models: "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"

    # Claude 3.5 Sonnet pricing (per million tokens): $3 input / $15 output
    # Claude 3 Opus pricing: $15 input / $75 output
    # For PDF/vision: Sonnet is the sweet spot for quality/cost

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("The 'anthropic' library is required to use AnthropicClient. Install it with: pip install anthropic")

        settings = get_settings()
        resolved_api_key = api_key or settings.ANTHROPIC_API_KEY
        resolved_model_name = model_name or self.DEFAULT_MODEL
        super().__init__(api_key=resolved_api_key, model_name=resolved_model_name, config=config)

        if not self.api_key:
            logger.warning("Anthropic API key (ANTHROPIC_API_KEY) not found. AnthropicClient will not function.")
            self.client = None
        else:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.debug("Anthropic client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text completion using Claude."""
        if not self.client:
            raise ValueError("Anthropic client not initialized (check API key).")

        try:
            logger.debug(f"Sending completion request to Claude model {self.get_model_name()}")

            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Claude uses system parameter separately
            create_params = {
                "model": self.get_model_name(),
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            }

            if system_prompt:
                create_params["system"] = system_prompt

            response = self.client.messages.create(**create_params)

            logger.debug("Received response from Claude.")

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            else:
                logger.warning("Claude response was empty.")
                return ""

        except Exception as e:
            logger.error(f"Anthropic API request failed: {e}")
            raise

    def generate_structured_output(self, prompt: str, output_schema: Union[Dict[str, Any], Type[BaseModel]], system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate structured JSON output using Claude."""
        if not self.client:
            raise ValueError("Anthropic client not initialized (check API key).")

        # Prepare schema for prompt
        if isinstance(output_schema, type) and issubclass(output_schema, BaseModel):
            schema_dict = output_schema.model_json_schema()
        elif isinstance(output_schema, dict):
            schema_dict = output_schema
        else:
            logger.warning("Invalid output_schema type. Attempting generic extraction.")
            schema_dict = {}

        # Build system prompt with JSON instructions
        default_system_prompt = "You are an expert data extraction assistant. Extract structured information accurately."
        json_instructions = (system_prompt or default_system_prompt) + \
            "\n\nYou MUST respond with a single, valid JSON object with no additional text before or after. Do not use markdown code blocks."

        if schema_dict:
            schema_string = json.dumps(schema_dict, indent=2)
            json_instructions += f"\n\nRequired JSON Schema:\n{schema_string}"

        try:
            logger.debug(f"Sending structured output request to Claude model {self.get_model_name()}")

            response = self.client.messages.create(
                model=self.get_model_name(),
                system=json_instructions,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.1),  # Lower temp for structured output
            )

            logger.debug("Received response from Claude.")

            if response.content and len(response.content) > 0:
                raw_completion = response.content[0].text.strip()

                # Parse JSON
                try:
                    # Remove markdown code blocks if present
                    if raw_completion.startswith("```"):
                        lines = raw_completion.split('\n')
                        raw_completion = '\n'.join(lines[1:-1]) if len(lines) > 2 else raw_completion

                    json_start = raw_completion.find('{')
                    json_end = raw_completion.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_str = raw_completion[json_start:json_end+1]
                        parsed_json = json.loads(json_str)
                        return parsed_json
                    else:
                        return json.loads(raw_completion.strip())
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from Claude. Error: {e}. Response: '{raw_completion[:500]}...'")
                    raise ValueError(f"LLM output was not valid JSON. Response: {raw_completion}")
            else:
                raise ValueError("Claude returned empty response.")

        except Exception as e:
            logger.error(f"Anthropic structured output request failed: {e}")
            raise

    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate text completion with multimodal input (text + images)."""
        if not self.client:
            raise ValueError("Anthropic client not initialized (check API key).")

        try:
            logger.debug(f"Sending multimodal request to Claude model {self.get_model_name()}")

            # Convert OpenAI-style messages to Claude format
            claude_messages = []
            system_content = None

            for msg in messages:
                if msg.get('role') == 'system':
                    system_content = msg.get('content', '')
                elif msg.get('role') == 'user':
                    content = msg.get('content')

                    # Handle string content
                    if isinstance(content, str):
                        claude_messages.append({
                            "role": "user",
                            "content": content
                        })
                    # Handle list content (multimodal)
                    elif isinstance(content, list):
                        claude_content = []
                        for part in content:
                            if isinstance(part, dict):
                                part_type = part.get('type')
                                if part_type == 'text':
                                    claude_content.append({
                                        "type": "text",
                                        "text": part.get('text', '')
                                    })
                                elif part_type == 'image_url':
                                    # Extract base64 image data
                                    image_url = part.get('image_url', {}).get('url', '')
                                    if image_url.startswith('data:image'):
                                        # Parse data URL: data:image/jpeg;base64,<data>
                                        media_type = image_url.split(';')[0].split(':')[1]
                                        base64_data = image_url.split(',', 1)[1]

                                        claude_content.append({
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": media_type,
                                                "data": base64_data
                                            }
                                        })

                        if claude_content:
                            claude_messages.append({
                                "role": "user",
                                "content": claude_content
                            })

            if not claude_messages:
                raise ValueError("No valid messages to send to Claude.")

            # Build request parameters
            create_params = {
                "model": self.get_model_name(),
                "messages": claude_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.2),
            }

            if system_content:
                create_params["system"] = system_content

            response = self.client.messages.create(**create_params)

            logger.debug("Received multimodal response from Claude.")

            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            else:
                logger.warning("Claude multimodal response was empty.")
                return ""

        except Exception as e:
            logger.error(f"Anthropic multimodal request failed: {e}")
            raise

    def process_pdf(self, pdf_path: str, prompt: str, **kwargs) -> str:
        """Process a PDF file directly using Claude's native PDF support."""
        if not self.client:
            raise ValueError("Anthropic client not initialized (check API key).")

        file_path = Path(pdf_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Processing PDF natively with Claude: {file_path.name}")

        try:
            # Read PDF and encode as base64
            pdf_data = file_path.read_bytes()
            pdf_base64 = base64.standard_b64encode(pdf_data).decode('utf-8')

            # Build message with PDF document
            message_content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_base64
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]

            # Get system prompt from kwargs
            system_prompt = kwargs.get("system_prompt")

            create_params = {
                "model": self.get_model_name(),
                "messages": [{"role": "user", "content": message_content}],
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.2),
            }

            if system_prompt:
                create_params["system"] = system_prompt

            response = self.client.messages.create(**create_params)

            logger.debug("Received response from Claude PDF processing.")

            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            else:
                logger.warning("Claude PDF processing returned empty response.")
                return ""

        except Exception as e:
            logger.error(f"Claude PDF processing request failed: {e}")
            raise
