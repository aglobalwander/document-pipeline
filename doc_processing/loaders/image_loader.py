"""Loader for image files."""
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from PIL import Image # Assuming Pillow is installed

from doc_processing.embedding.base import BaseDocumentLoader
from doc_processing.utils.file_utils import get_file_metadata

logger = logging.getLogger(__name__)

class ImageLoader(BaseDocumentLoader):
    """
    Loads image files (e.g., JPEG, PNG) and returns them as PIL Image objects.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the ImageLoader.

        Args:
            config: Configuration dictionary (optional).
        """
        super().__init__(config)
        logger.info("ImageLoader initialized.")

    def load(self, source_path: str) -> Dict[str, Any]:
        """
        Loads an image file.

        Args:
            source_path: The path to the image file.

        Returns:
            A dictionary containing the loaded PIL Image object and metadata.
        """
        path = Path(source_path)
        if not path.is_file():
            logger.error(f"File not found: {path}")
            raise FileNotFoundError(f"File not found: {path}")

        try:
            img = Image.open(path)
            logger.info(f"Successfully loaded image: {path}")
            metadata = get_file_metadata(path)
            metadata.update({
                "file_type": path.suffix.lower(),
                "width": img.width,
                "height": img.height,
            })
            return {
                "source_path": str(path),
                "content": img,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error loading image file {path}: {e}")
            raise IOError(f"Error loading image file {path}: {e}") from e

# Note: This loader returns a PIL Image object in the 'content' key.
# The subsequent processor (ImageProcessor) should be designed to accept this format.
