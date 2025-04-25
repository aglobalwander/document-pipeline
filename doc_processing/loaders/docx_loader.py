"""Loader for DOCX files."""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Import the necessary library
try:
    import docx
except ImportError:
    raise ImportError("The 'python-docx' library is required to load DOCX files. Please install it using 'pip install python-docx'.")

from doc_processing.embedding.base import BaseDocumentLoader # Corrected class name
from doc_processing.utils.file_utils import get_file_metadata

logger = logging.getLogger(__name__)

class DocxLoader(BaseDocumentLoader): # Corrected inheritance
    """Loads DOCX (.docx) files."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the DOCX loader."""
        super().__init__(config)
        # Add any docx specific config here if needed later

    def load(self, source_path: str) -> Dict[str, Any]:
        """Loads a DOCX file.

        Args:
            source_path: Path to the DOCX file.

        Returns:
            Dictionary containing file content (extracted text) and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If there's an error reading or processing the file.
        """
        file_path = Path(source_path)
        logger.info(f"Loading DOCX file from: {file_path}")

        if not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Open and read the DOCX file
            document = docx.Document(file_path)
            full_text = []
            for para in document.paragraphs:
                full_text.append(para.text)
            content = '\n'.join(full_text)

            # Get metadata
            metadata = get_file_metadata(file_path)
            metadata['file_type'] = 'docx'

            # Add specific DOCX metadata if desired (e.g., core properties)
            try:
                core_props = document.core_properties
                metadata['docx_author'] = core_props.author
                metadata['docx_last_modified_by'] = core_props.last_modified_by
                # Add others as needed: title, subject, keywords, comments etc.
            except Exception as prop_error:
                logger.warning(f"Could not extract core properties from DOCX {file_path.name}: {prop_error}")


            logger.info(f"Successfully loaded DOCX file: {file_path.name}")
            return {
                "source_path": str(file_path),
                "content": content,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error loading DOCX file {file_path}: {e}")
            # Catch specific docx errors if needed, e.g., docx.opc.exceptions.PackageNotFoundError
            raise IOError(f"Error loading DOCX file {file_path}: {e}") from e