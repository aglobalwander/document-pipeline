"""Concrete implementation for Google Gemini LLM client using the new google-genai SDK."""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

# Import the new Google library and types
try:
    from google import genai
    from google.genai import types
    # Import specific exceptions if needed for finer error handling
    # from google.api_core import exceptions as google_exceptions
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    # Raise error later if user tries to use it without installation

from .base import BaseLLMClient
from doc_processing.config import get_settings

logger = logging.getLogger(__name__)

class GeminiClient(BaseLLMClient):
    """Client for interacting with Google's Gemini API using google-genai SDK."""

    DEFAULT_MODEL = "gemini-1.5-pro-latest" # Or fetch from settings
    # Note: Specific vision models might not be needed if using generate_content with mixed types

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize Gemini client using google-genai."""
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError("The 'google-genai' library is required to use the GeminiClient. Please install it using 'pip install google-genai'.")

        settings = get_settings()
        resolved_api_key = api_key or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY # Check both potential env vars
        resolved_model_name = model_name or self.DEFAULT_MODEL
        super().__init__(api_key=resolved_api_key, model_name=resolved_model_name, config=config)

        if not self.api_key:
            logger.warning("Google API key (GEMINI_API_KEY or GOOGLE_API_KEY) not found. GeminiClient will not function.")
            self.client = None
        else:
            try:
                # Use the new client initialization
                self.client = genai.Client(api_key=self.api_key)
                # Test connection or list models? Optional.
                # models_list = self.client.models.list() # Example check
                logger.debug(f"Gemini client initialized successfully using google-genai SDK.")
            except Exception as e:
                logger.error(f"Failed to configure or initialize Gemini client (google-genai): {e}")
                self.client = None

    def _prepare_generation_config(self, system_instruction: Optional[str] = None, **kwargs) -> types.GenerateContentConfig: # Correct class name
         """Helper to create GenerateContentConfig from kwargs, including system instruction."""
         config_args = {
                "max_output_tokens": kwargs.get("max_tokens", 8192),
                "temperature": kwargs.get("temperature", 0.7),
                # Add other standard config args here if needed (top_p, top_k etc.)
                "response_mime_type": kwargs.get("response_mime_type"), # Pass through if provided
                "response_schema": kwargs.get("response_schema") # Pass through if provided
         }
         # Add system instruction only if provided
         if system_instruction:
              config_args["system_instruction"] = types.Content(parts=[types.Part(text=system_instruction)]) # Wrap in Content/Part structure

         # Filter out None values before creating config
         filtered_config_args = {k: v for k, v in config_args.items() if v is not None}

         # Use the correct class name here as well
         return types.GenerateContentConfig(**filtered_config_args)

    def _extract_text_from_response(self, response) -> str:
        """Helper to reliably extract text from Gemini response."""
        try:
            if response and hasattr(response, 'text'):
                 return response.text.strip()
            elif response and response.parts:
                 return "".join(part.text for part in response.parts).strip()
            elif response and response.candidates:
                 # More robust candidate checking
                 if response.candidates[0].content and response.candidates[0].content.parts:
                      return "".join(part.text for part in response.candidates[0].content.parts).strip()
            logger.warning(f"Could not extract text from Gemini response structure. Response: {response}")
            return ""
        except (AttributeError, IndexError, Exception) as e:
            logger.error(f"Error extracting text from Gemini response: {e}")
            return ""


    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text completion using Gemini."""
        if not self.client:
            raise ValueError("Gemini client not initialized (check API key).")

        contents = [prompt] # Simple text prompt

        try:
            logger.debug(f"Sending completion request to Gemini model {self.get_model_name()}")
            # Prepare config, passing system prompt to the helper
            generation_config = self._prepare_generation_config(system_instruction=system_prompt, **kwargs)

            response = self.client.models.generate_content(
                model=self.get_model_name(),
                contents=contents,
                config=generation_config # Pass the combined config object
                # system_instruction is now inside generation_config
                # Add safety_settings if needed
            )
            logger.debug(f"Received response from Gemini.")
            return self._extract_text_from_response(response)

        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            raise

    def generate_structured_output(self, prompt: str, output_schema: Dict[str, Any], system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate structured JSON output using Gemini (requires specific prompting or JSON mode)."""
        if not self.client:
            raise ValueError("Gemini client not initialized (check API key).")

        # Use JSON mode if available and requested
        use_json_mode = self.config.get('use_json_mode', True) # Default to trying JSON mode
        response_mime_type = "application/json" if use_json_mode else None

        # Prepare prompt (system instructions handled separately now)
        contents = [prompt]

        try:
            logger.debug(f"Sending structured output request to Gemini model {self.get_model_name()} (JSON mode: {use_json_mode})")
            system_instruction = system_prompt or "You are an expert data extraction assistant. Respond ONLY with the valid JSON object requested."
            # Prepare config, passing system prompt and JSON mode args to the helper
            generation_config = self._prepare_generation_config(
                 system_instruction=system_instruction,
                 temperature=kwargs.get("temperature", 0.1), # Lower temp for structured
                 max_tokens=kwargs.get("max_tokens", 4096),
                 response_mime_type=response_mime_type,
                 response_schema=output_schema if use_json_mode else None
            )

            response = self.client.models.generate_content(
                model=self.get_model_name(),
                contents=contents,
                config=generation_config # Pass the combined config object
            )
            logger.debug(f"Received response from Gemini.")

            raw_completion = self._extract_text_from_response(response)

            if not raw_completion:
                 raise ValueError("Gemini structured output request returned empty text.")

            # Attempt to parse the completion as JSON
            try:
                # JSON mode should return clean JSON, but add fallback cleaning just in case
                json_start = raw_completion.find('{')
                json_end = raw_completion.rfind('}')
                if json_start != -1 and json_end != -1:
                    json_str = raw_completion[json_start:json_end+1]
                    parsed_json = json.loads(json_str)
                    return parsed_json
                else:
                     return json.loads(raw_completion.strip()) # Try parsing directly
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini completion. Error: {e}. Completion: '{raw_completion[:500]}...'")
                raise ValueError(f"LLM output was not valid JSON. Completion: {raw_completion}")

        except Exception as e:
            logger.error(f"Gemini structured output request failed: {e}")
            raise

    def process_pdf(self, pdf_path: str, prompt: str, **kwargs) -> str:
        """Processes a PDF file directly using Gemini's native PDF support."""
        if not self.client:
            raise ValueError("Gemini client not initialized (check API key).")

        file_path = Path(pdf_path)
        if not file_path.is_file():
             raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Processing PDF natively with Gemini: {file_path.name}")

        try:
            # Read PDF bytes
            pdf_bytes = file_path.read_bytes()

            # Prepare content parts using types.Part.from_bytes as per latest docs
            contents = [
                 # Prompt order might matter, example shows Part first
                 types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'), # Use types.Part
                 prompt
            ]

            # Configure generation, passing system prompt to helper
            system_instruction = kwargs.get("system_prompt")
            generation_config = self._prepare_generation_config(system_instruction=system_instruction, **kwargs)


            # Send request
            response = self.client.models.generate_content(
                model=self.get_model_name(), # Ensure model supports PDF input
                contents=contents,
                config=generation_config # Pass the combined config object
                # Add safety_settings if needed
            )
            logger.debug("Received response from Gemini PDF processing.")

            return self._extract_text_from_response(response)

        except Exception as e:
            logger.error(f"Gemini PDF processing request failed: {e}")
            raise

    # Re-implement generate_multimodal_completion to satisfy the abstract base class
    # This will adapt the input format for generate_content
    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate text completion using Gemini with multimodal input (adapts to generate_content)."""
        if not self.client:
            raise ValueError("Gemini client not initialized (check API key).")

        # Convert the OpenAI-style message format to Gemini's content list format
        gemini_contents = []
        try:
            for msg in messages:
                 # Process only user messages for content parts
                 if msg.get('role') == 'user' and isinstance(msg.get('content'), list):
                      for part_data in msg['content']:
                           if isinstance(part_data, dict):
                                part_type = part_data.get('type')
                                if part_type == 'text':
                                     gemini_contents.append(part_data.get('text', ''))
                                elif part_type == 'image_url':
                                     # Handle base64 encoded images
                                     image_url = part_data.get('image_url', {}).get('url', '')
                                     if image_url.startswith('data:image'):
                                          from PIL import Image
                                          import io
                                          import base64
                                          try:
                                               # Extract base64 data (remove prefix like 'data:image/jpeg;base64,')
                                               base64_str = image_url.split(',', 1)[1]
                                               img_bytes = base64.b64decode(base64_str)
                                               img = Image.open(io.BytesIO(img_bytes))
                                               # Append as Blob for generate_content
                                               # Determine mime type (simple check for now)
                                               mime_type = image_url.split(';')[0].split(':')[1] if '/' in image_url.split(';')[0] else 'image/png' # Default guess
                                               gemini_contents.append(types.Blob(mime_type=mime_type, data=img_bytes))
                                          except Exception as img_err:
                                               logger.error(f"Failed to process base64 image for Gemini: {img_err}")
                                               # Decide how to handle error: skip image, add placeholder text?
                                               gemini_contents.append("[Image processing error]")
                                     else:
                                          logger.warning(f"Unsupported image_url format for Gemini multimodal: {image_url[:60]}...")
                                          gemini_contents.append("[Unsupported image URL]")
                                else:
                                     logger.warning(f"Unsupported part type in message content: {part_type}")
                           elif isinstance(part_data, str): # Handle plain string parts
                                gemini_contents.append(part_data)
                 # Ignore non-user messages or messages with unexpected content format for this conversion
            if not gemini_contents:
                 raise ValueError("Could not convert input messages to valid Gemini content format.")

        except Exception as e:
             logger.error(f"Error converting message format for Gemini multimodal input: {e}")
             raise ValueError("Invalid message format for Gemini multimodal input.") from e

        # Now call generate_content with the constructed contents list
        try:
            logger.debug(f"Sending adapted multimodal request to Gemini model {self.get_model_name()}")
            # Prepare config, passing system prompt to helper
            system_instruction = kwargs.get("system_prompt")
            generation_config = self._prepare_generation_config(system_instruction=system_instruction, **kwargs)


            response = self.client.models.generate_content(
                model=self.get_model_name(), # Ensure model supports multimodal input
                contents=gemini_contents,
                config=generation_config # Pass the combined config object
            )
            logger.debug(f"Received adapted multimodal response from Gemini.")
            return self._extract_text_from_response(response)

        except Exception as e:
            logger.error(f"Gemini adapted multimodal request failed: {e}")
            raise