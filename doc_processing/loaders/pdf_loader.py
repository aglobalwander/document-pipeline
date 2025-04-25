"""PDF Document Loader."""
import os
from typing import Any, Dict, Optional, Union
from pathlib import Path
import fitz  # PyMuPDF
import hashlib
# Imports needed for image generation
import base64
import io
from PIL import Image
import logging # Added logging import

from doc_processing.embedding.base import BaseDocumentLoader

logger = logging.getLogger(__name__) # Added logger instance

class PDFLoader(BaseDocumentLoader):
    """Loader for PDF documents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.extract_metadata = self.config.get('extract_metadata', True)
        self.check_password = self.config.get('check_password', True)
        self.password = self.config.get('password', None)
        # Config for image generation
        self.generate_page_images = self.config.get('generate_page_images', True) # Default to True if vision is primary path
        self.resolution_scale = self.config.get('resolution_scale', 2) # Default resolution scale

    def _encode_image(self, pil_image: Image.Image) -> str:
        """Encode PIL Image to base64 string."""
        with io.BytesIO() as buffer:
            pil_image.save(buffer, format="PNG") # Use PNG for potentially better quality
            return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load PDF document from source path, optionally generating page images.

        Args:
            source: Path to PDF document

        Returns:
            Dictionary containing document content and metadata
        """
        source_path = self.validate_source(source)
        # Use self.logger inherited from BaseDocumentLoader
        self.logger.info(f"Loading PDF from {source_path}")

        # Initialize document dict
        document = {
            'source_path': str(source_path),
            'metadata': {
                'filename': source_path.name,
                'file_type': 'pdf',
                'file_size': source_path.stat().st_size,
                'created_at': source_path.stat().st_ctime,
                'modified_at': source_path.stat().st_mtime,
                'file_hash': self._calculate_hash(source_path),
            },
            'content': None,
            'pages': [] # Initialize pages list
        }

        try:
            # Open PDF document
            doc = fitz.open(source_path)

            # Check if PDF is password protected
            if doc.needs_pass:
                if self.password:
                    if not doc.authenticate(self.password):
                        raise ValueError("Incorrect password for encrypted PDF")
                else:
                    raise ValueError("PDF is password protected but no password provided")

            # Extract PDF metadata
            if self.extract_metadata:
                pdf_metadata = doc.metadata
                if pdf_metadata:
                    document['metadata'].update({
                        'title': pdf_metadata.get('title'),
                        'author': pdf_metadata.get('author'),
                        'subject': pdf_metadata.get('subject'),
                        'keywords': pdf_metadata.get('keywords'),
                        'creator': pdf_metadata.get('creator'),
                        'producer': pdf_metadata.get('producer'),
                        'creation_date': pdf_metadata.get('creationDate'),
                        'modification_date': pdf_metadata.get('modDate'),
                    })

                document['metadata']['num_pages'] = len(doc)
                # Safely get pdf_version and attempt to convert to float
                pdf_version_str = getattr(doc, 'pdf_version', '0') # Default to '0' string
                try:
                    document['metadata']['pdf_version'] = float(pdf_version_str)
                except (ValueError, TypeError):
                    self.logger.warning(f"Could not convert pdf_version '{pdf_version_str}' to float. Storing as string.")
                    document['metadata']['pdf_version'] = pdf_version_str # Store original string on error

                # Get basic TOC if available
                toc = doc.get_toc()
                if toc:
                    document['metadata']['toc'] = toc

            # Generate page images if configured
            if self.generate_page_images:
                self.logger.info(f"Generating base64 images for {len(doc)} pages...")
                pages_data = []
                for i, page in enumerate(doc):
                    try:
                        pix = page.get_pixmap(matrix=fitz.Matrix(self.resolution_scale, self.resolution_scale))
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        base64_image = self._encode_image(img)
                        pages_data.append({
                            'page_number': i + 1,
                            'image_base64': base64_image
                            # Optionally add page dimensions?
                            # 'width': pix.width,
                            # 'height': pix.height
                        })
                    except Exception as page_err:
                        self.logger.error(f"Error processing page {i+1} into image: {page_err}")
                        # Add placeholder or skip? Add placeholder for now.
                        pages_data.append({
                            'page_number': i + 1,
                            'error': f"Failed to generate image: {page_err}"
                        })
                document['pages'] = pages_data
                self.logger.info(f"Finished generating page images.")
            else:
                 # Ensure pages list exists even if not generating images
                 document['pages'] = []


            # Initialize empty content - downstream processors will populate this
            document['content'] = ""

            # Close the document
            doc.close()

            return document

        except Exception as e:
            self.logger.error(f"Error loading PDF {source_path}: {str(e)}")
            document['error'] = str(e)
            # Ensure pages list exists even on error if not generated before
            if 'pages' not in document:
                 document['pages'] = []
            return document

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA-256 hash
        """
        hash_sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()