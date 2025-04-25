"""Concrete implementations of LLM clients for different providers."""

import os
import json
import logging
import requests
from typing import Any, Dict, List, Optional, Type, TypeVar, Union # Added List
# Need pydantic and instructor for internal handling
from pydantic import BaseModel
import instructor
from instructor import Mode
from openai import OpenAI

from .base import BaseLLMClient
from doc_processing.config import get_settings

logger = logging.getLogger(__name__)

class OpenAIClient(BaseLLMClient):
    """Client for interacting with OpenAI's API (GPT models)."""

    DEFAULT_MODEL = "gpt-4.1" # Or fetch from settings if preferred
    API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI client."""
        settings = get_settings()
        resolved_api_key = api_key or settings.OPENAI_API_KEY or settings.OPENAI_APIKEY
        resolved_model_name = model_name or self.DEFAULT_MODEL
        super().__init__(api_key=resolved_api_key, model_name=resolved_model_name, config=config)

        if not self.api_key:
            logger.warning("OpenAI API key not found. OpenAIClient will not function.")
            self.client = None
            self.instructor_client = None
        else:
            # Initialize the standard OpenAI client
            self.client = OpenAI(api_key=self.api_key)
            # Initialize the instructor-patched client
            try:
                self.instructor_client = instructor.from_openai(
                    self.client,
                    mode=Mode.TOOLS_STRICT, # Or configure mode via self.config
                )
                logger.debug("Instructor client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize instructor client: {e}")
                self.instructor_client = None # Ensure it's None if init fails

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text completion using OpenAI Chat Completions."""
        if not self.client:
            raise ValueError("OpenAI client not initialized (check API key).")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            logger.debug(f"Sending completion request to OpenAI model {self.get_model_name()}")
            response = self.client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1500),
                # Add other kwargs if needed
            )
            logger.debug(f"Received response from OpenAI.")

            if response.choices and response.choices[0].message:
                completion = response.choices[0].message.content or ""
                return completion.strip()
            else:
                logger.warning("OpenAI response structure unexpected or message content empty.")
                return ""
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise # Re-raise the exception

    # Type hint for output_schema allows checking if it's a Pydantic model type
    def generate_structured_output(self, prompt: str, output_schema: Union[Dict[str, Any], Type[BaseModel]], system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate structured JSON output using OpenAI, leveraging Instructor if a Pydantic model is provided."""
        if not self.client:
            raise ValueError("OpenAI client not initialized (check API key).")

        messages = []
        # Use provided system prompt or default if none given
        default_system_prompt = "You are an expert data extraction assistant. Extract structured information from the user's text."
        messages.append({"role": "system", "content": system_prompt or default_system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            # Check if output_schema is a Pydantic model type and instructor client is available
            if isinstance(output_schema, type) and issubclass(output_schema, BaseModel) and self.instructor_client:
                logger.debug(f"Using Instructor to generate structured output with model {output_schema.__name__}")
                # Use instructor client with response_model
                response = self.instructor_client.chat.completions.create(
                    model=self.get_model_name(),
                    messages=messages,
                    response_model=output_schema, # Pass the Pydantic model type
                    temperature=kwargs.get("temperature", 0.2), # Lower temp for structured output
                    max_tokens=kwargs.get("max_tokens", 4000),
                )
                # Instructor returns the validated Pydantic model instance
                return response.model_dump() # Return as dictionary

            # --- Fallback: Use standard client with JSON prompting ---
            else:
                if isinstance(output_schema, type) and issubclass(output_schema, BaseModel):
                     logger.warning("Instructor client not available or output_schema not Pydantic model. Falling back to JSON prompting.")
                     # Convert Pydantic model to JSON schema for the prompt if needed
                     schema_dict = output_schema.model_json_schema()
                elif isinstance(output_schema, dict):
                     schema_dict = output_schema # Assume it's already a JSON schema dict
                else:
                     logger.warning("Invalid output_schema type. Attempting generic extraction.")
                     schema_dict = {} # Empty schema, rely on prompt

                # Add JSON instructions to system prompt if not using instructor
                json_system_prompt = (system_prompt or default_system_prompt) + \
                    "\n\nYour response MUST be a single, valid JSON object conforming to the following schema (if provided), with no extra text or explanation before or after it."
                if schema_dict:
                    schema_string = json.dumps(schema_dict, indent=2)
                    json_system_prompt += f"\n\nDesired JSON Schema:\n```json\n{schema_string}\n```"
                messages[0]['content'] = json_system_prompt # Update system prompt

                logger.debug(f"Using standard OpenAI client with JSON prompting. Schema: {schema_dict.keys() if schema_dict else 'None'}")
                response = self.client.chat.completions.create(
                    model=self.get_model_name(),
                    messages=messages,
                    temperature=kwargs.get("temperature", 0.2),
                    max_tokens=kwargs.get("max_tokens", 4000),
                    # Consider adding response_format={"type": "json_object"} for newer models
                )

                if response.choices and response.choices[0].message:
                    raw_completion = response.choices[0].message.content or ""
                    # Attempt to parse the completion as JSON
                    try:
                        json_start = raw_completion.find('{')
                        json_end = raw_completion.rfind('}')
                        if json_start != -1 and json_end != -1:
                            json_str = raw_completion[json_start:json_end+1]
                            parsed_json = json.loads(json_str)
                            return parsed_json
                        else:
                            return json.loads(raw_completion) # Try parsing whole string
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from standard completion. Error: {e}. Completion: '{raw_completion[:500]}...'")
                        raise ValueError(f"LLM output was not valid JSON. Completion: {raw_completion}")
                else:
                     raise ValueError("Standard OpenAI completion failed or returned empty message.")

        except Exception as e:
            logger.error(f"OpenAI structured output request failed: {e}")
            raise # Re-raise the exception

    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate text completion using OpenAI Chat Completions with multimodal input."""
        if not self.client:
            raise ValueError("OpenAI client not initialized (check API key).")

        # Ensure messages format is suitable for multimodal input if needed
        # (The structure passed from GPTPVisionProcessor should be correct for OpenAI)

        try:
            logger.debug(f"Sending multimodal completion request to OpenAI model {self.get_model_name()}")
            response = self.client.chat.completions.create(
                model=self.get_model_name(), # Should be a vision-capable model like gpt-4o
                messages=messages,
                temperature=kwargs.get("temperature", 0.2), # Often lower temp for OCR
                max_tokens=kwargs.get("max_tokens", 3000), # May need more tokens for vision
                # Add other kwargs if needed
            )
            logger.debug(f"Received multimodal response from OpenAI.")

            if response.choices and response.choices[0].message:
                completion = response.choices[0].message.content or ""
                return completion.strip()
            else:
                logger.warning("OpenAI multimodal response structure unexpected or message content empty.")
                return ""
        except Exception as e:
            logger.error(f"OpenAI multimodal API request failed: {e}")
            raise # Re-raise the exception


# Add other client implementations here later (AnthropicClient, GeminiClient, etc.)