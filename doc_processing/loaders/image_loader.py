"""Loader for image files."""
import logging
from typing import Any, Dict, Union
from pathlib import Path
from PIL import Image # Assuming Pillow is installed

from doc_processing.embedding.base import PipelineComponent

logger = logging.getLogger(__name__)

class ImageLoader(PipelineComponent):
    """
    Loads image files (e.g., JPEG, PNG) and returns them as PIL Image objects.
    """
    def __init__(self, cfg: Dict[str, Any] = None):
        """
        Initializes the ImageLoader.

        Args:
            cfg: Configuration dictionary (optional).
        """
        self.cfg = cfg or {}
        logger.info("ImageLoader initialized.")

    def run(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Loads an image file.

        Args:
            file_path: The path to the image file.

        Returns:
            A dictionary containing the loaded PIL Image object and metadata.
        """
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"File not found: {file_path}")
            return {"content": None, "metadata": {"error": f"File not found: {file_path}"}}

        try:
            img = Image.open(path)
            logger.info(f"Successfully loaded image: {file_path}")
            metadata = {
                "filename": path.name,
                "file_type": path.suffix.lower(),
                "width": img.width,
                "height": img.height,
            }
            return {"content": img, "metadata": metadata}

        except Exception as e:
            logger.error(f"Error loading image file {file_path}: {e}")
            return {"content": None, "metadata": {"error": f"Error loading image: {e}"}}

# Note: This loader returns a PIL Image object in the 'content' key.
# The subsequent processor (ImageProcessor) should be designed to accept this format.