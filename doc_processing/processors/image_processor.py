"""Processor for analyzing images using vision models."""
import logging
from typing import Any, Dict

# Assuming these imports are available in the environment
import openai
import google.generativeai as genai
import pytesseract
from PIL import Image # Assuming Pillow is installed

from doc_processing.embedding.base import PipelineComponent

logger = logging.getLogger(__name__)

class ImageProcessor(PipelineComponent):
    """
    Processes images to extract captions and OCR text using vision models.
    """
    def __init__(self, cfg: Dict[str, Any]):
        """
        Initializes the ImageProcessor.

        Args:
            cfg: Configuration dictionary. Expected keys:
                 - "backend": "openai" or "gemini" (default: "openai")
                 - "model": Specific model name (optional, overrides default)
        """
        self.backend = cfg.get("backend", "openai")
        self.model = cfg.get("model") or (
            "gpt-4o-mini" if self.backend == "openai" else "gemini-pro-vision"
        )
        logger.info(f"ImageProcessor initialized with backend: {self.backend}, model: {self.model}")

    def run(self, img_arr: Image.Image) -> Dict[str, Any]:
        """
        Runs the image processing pipeline.

        Args:
            img_arr: The image as a PIL Image object.

        Returns:
            A dictionary containing the extracted caption and OCR text.
        """
        caption = ""
        ocr_text = ""

        try:
            # Get caption from vision model
            if self.backend == "openai":
                # Convert PIL Image to bytes for OpenAI Vision
                # Note: This assumes the image is in a format supported by OpenAI Vision (e.g., JPEG, PNG)
                # You might need to handle different formats or add conversion logic.
                # For simplicity, assuming JPEG for now.
                from io import BytesIO
                buffered = BytesIO()
                img_arr.save(buffered, format="JPEG")
                img_bytes = buffered.getvalue()

                # Encode image bytes to base64
                import base64
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this image."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}},
                            ],
                        }
                    ],
                    max_tokens=100, # Increased max_tokens for potentially better captions
                )
                caption = response.choices[0].message.content.strip()
                logger.info(f"Generated caption using OpenAI: {caption}")

            elif self.backend == "gemini":
                 # Gemini Vision can directly take PIL Image
                 response = genai.generate_content(
                     model=self.model,
                     contents=[{"mime_type": "image/jpeg", "data": img_arr.tobytes()}], # Assuming JPEG format
                 )
                 caption = response.text.strip()
                 logger.info(f"Generated caption using Gemini: {caption}")

            else:
                logger.warning(f"Unsupported image processing backend: {self.backend}")

        except Exception as e:
            logger.error(f"Error generating caption with {self.backend} backend: {e}")
            caption = f"Error generating caption: {e}" # Indicate failure in output

        try:
            # Perform OCR using pytesseract
            ocr_text = pytesseract.image_to_string(img_arr)
            logger.info("Extracted OCR text using pytesseract.")
        except Exception as e:
            logger.error(f"Error performing OCR with pytesseract: {e}")
            ocr_text = f"Error performing OCR: {e}" # Indicate failure in output


        return {"content": caption, "metadata": {"ocr": ocr_text}}

# Note: This processor expects a PIL Image object as input.
# A loader component would be needed to load images from files into this format.