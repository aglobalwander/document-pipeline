"""Local-first image OCR with explicit opt-in remote captioning."""
import base64
from io import BytesIO
import logging
from typing import Any, Dict, Optional

import pytesseract
from PIL import Image

from doc_processing.config import get_settings
from doc_processing.embedding.base import BaseProcessor

logger = logging.getLogger(__name__)


class ImageProcessor(BaseProcessor):
    """Extract image text locally and optionally add a paid API caption."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()
        self.backend = self.config.get("backend", "local")
        if self.backend not in {"local", "openai", "gemini"}:
            raise ValueError(f"Unsupported image backend: {self.backend}")

        default_model = {
            "openai": self.settings.DEFAULT_OPENAI_VISION_MODEL,
            "gemini": self.settings.DEFAULT_GEMINI_MODEL,
        }.get(self.backend)
        self.model = self.config.get("model") or default_model
        self.skip_caption = self.config.get(
            "skip_caption",
            self.backend == "local",
        )
        logger.info(
            "ImageProcessor initialized with backend=%s model=%s skip_caption=%s",
            self.backend,
            self.model or "none",
            self.skip_caption,
        )

    def _generate_caption(self, image: Image.Image) -> str:
        buffered = BytesIO()
        image.convert("RGB").save(buffered, format="JPEG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image accurately and concisely."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }
        ]

        if self.backend == "openai":
            from doc_processing.llm.clients import OpenAIClient

            client = OpenAIClient(
                api_key=self.config.get(
                    "api_key",
                    self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY,
                ),
                model_name=self.model,
                config=self.config.get("llm_client_config"),
            )
        elif self.backend == "gemini":
            from doc_processing.llm.gemini_client import GeminiClient

            client = GeminiClient(
                api_key=self.config.get(
                    "api_key",
                    self.settings.GEMINI_API_KEY or self.settings.GOOGLE_API_KEY,
                ),
                model_name=self.model,
                config=self.config.get("llm_client_config"),
            )
        else:
            return ""

        return client.generate_multimodal_completion(messages, max_tokens=300)

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process the PIL image stored in ``document['content']``."""
        image = document.get("content")
        if not isinstance(image, Image.Image):
            document["error"] = "ImageProcessor expected a PIL Image in document['content']."
            return document

        caption = ""
        if not self.skip_caption:
            try:
                caption = self._generate_caption(image)
            except Exception as exc:
                logger.error("Error generating caption with %s: %s", self.backend, exc)
                caption = f"Error generating caption: {exc}"

        try:
            ocr_text = pytesseract.image_to_string(image)
            logger.info("Extracted OCR text using local Tesseract.")
        except Exception as exc:
            logger.error("Error performing local Tesseract OCR: %s", exc)
            ocr_text = f"Error performing OCR: {exc}"

        extracted_text = ocr_text.strip() if isinstance(ocr_text, str) else ""
        fallback_caption = caption.strip() if isinstance(caption, str) else ""
        document["content"] = extracted_text or fallback_caption
        metadata = document.setdefault("metadata", {})
        metadata.update(
            {
                "caption": caption,
                "ocr": ocr_text,
                "image_backend": self.backend,
                "image_model": self.model,
            }
        )
        return document
