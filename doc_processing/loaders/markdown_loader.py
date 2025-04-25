"""Loader for Markdown files."""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from doc_processing.embedding.base import BaseDocumentLoader # Corrected class name
from doc_processing.utils.file_utils import get_file_metadata

logger = logging.getLogger(__name__)

class MarkdownLoader(BaseDocumentLoader): # Corrected inheritance
    """Loads Markdown (.md) files."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Markdown loader."""
        super().__init__(config)
        self.encoding = self.config.get('encoding', 'utf-8')

    def load(self, source_path: str) -> Dict[str, Any]:
        """Loads a Markdown file.

        Args:
            source_path: Path to the Markdown file.

        Returns:
            Dictionary containing file content and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If there's an error reading the file.
        """
        file_path = Path(source_path)
        logger.info(f"Loading Markdown file from: {file_path}")

        if not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read file content
            with open(file_path, 'r', encoding=self.encoding) as f:
                content = f.read()

            # Get metadata
            metadata = get_file_metadata(file_path)
            metadata['file_type'] = 'md' # Add specific file type

            logger.info(f"Successfully loaded Markdown file: {file_path.name}")
            return {
                "source_path": str(file_path),
                "content": content,
                "metadata": metadata
            }

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {file_path} with {self.encoding}: {e}. Try specifying a different encoding.")
            raise IOError(f"Encoding error reading {file_path}: {e}") from e
        except Exception as e:
            logger.error(f"Error loading Markdown file {file_path}: {e}")
            raise IOError(f"Error loading Markdown file {file_path}: {e}") from e