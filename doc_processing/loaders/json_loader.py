"""Loader for JSON files."""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from doc_processing.embedding.base import BaseDocumentLoader # Corrected class name
from doc_processing.utils.file_utils import get_file_metadata

logger = logging.getLogger(__name__)

class JSONLoader(BaseDocumentLoader): # Corrected inheritance
    """Loads JSON (.json) files."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the JSON loader."""
        super().__init__(config)
        self.encoding = self.config.get('encoding', 'utf-8')

    def load(self, source_path: str) -> Dict[str, Any]:
        """Loads a JSON file.

        Args:
            source_path: Path to the JSON file.

        Returns:
            Dictionary containing parsed JSON data and metadata.
            The original file content is stored in metadata['raw_content'].

        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If there's an error reading the file.
            json.JSONDecodeError: If the file content is not valid JSON.
        """
        file_path = Path(source_path)
        logger.info(f"Loading JSON file from: {file_path}")

        if not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        raw_content = ""
        try:
            # Read file content
            with open(file_path, 'r', encoding=self.encoding) as f:
                raw_content = f.read()

            # Parse JSON data
            json_data = json.loads(raw_content)

            # Get metadata
            metadata = get_file_metadata(file_path)
            metadata['file_type'] = 'json'
            metadata['raw_content'] = raw_content # Store original text

            logger.info(f"Successfully loaded and parsed JSON file: {file_path.name}")
            return {
                "source_path": str(file_path),
                "content": json_data, # Parsed JSON data is the main content
                "metadata": metadata
            }

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {file_path} with {self.encoding}: {e}. Try specifying a different encoding.")
            raise IOError(f"Encoding error reading {file_path}: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in file {file_path}: {e}")
            raise # Re-raise the specific JSON error
        except Exception as e:
            logger.error(f"Error loading JSON file {file_path}: {e}")
            raise IOError(f"Error loading JSON file {file_path}: {e}") from e