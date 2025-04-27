"""Word (DOCX) processor using Mammoth."""
import os
import logging
from typing import Dict, Any, Optional

from doc_processing.embedding.base import PipelineComponent
from doc_processing.embedding.base import BaseProcessor, PipelineComponent

class MammothDOCXProcessor(BaseProcessor, PipelineComponent):
    """Process DOCX files using Mammoth for Markdown conversion."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the DOCX processor.
        
        Args:
            config: Configuration options
        """
        super().__init__(config or {})
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized MammothDOCXProcessor")

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a DOCX document.
        
        Args:
            document: Document dictionary with content field containing DOCX file path
            
        Returns:
            Processed document with extracted content
        """
        if not document.get('content'):
            self.logger.error("No content field in document")
            return document
            
        # Check if content is a file path or already extracted text
        docx_path = document.get('source_path', document.get('content', ''))
        
        # If it's a file path, check if it exists
        if os.path.exists(docx_path):
            self.logger.info(f"Processing DOCX file from path: {docx_path}")
        else:
            # If it's not a file path, it might be the extracted text content from DocxLoader
            self.logger.info(f"Processing DOCX content that was already loaded by DocxLoader")
            
            # If the content is already extracted text, convert it to markdown and return
            if 'content' in document and isinstance(document['content'], str) and not os.path.exists(document['content']):
                # Content is already text, not a file path
                markdown = document['content']
                
                # Update the document
                processed_doc = document.copy()
                processed_doc['content'] = markdown
                processed_doc['metadata'] = document.get('metadata', {})
                processed_doc['metadata']['docx_processor'] = 'text_content'
                
                return processed_doc
            else:
                self.logger.error(f"DOCX file not found: {docx_path}")
                return document
            
        self.logger.info(f"Processing DOCX file: {docx_path}")
        
        try:
            # Import here to avoid dependency issues if not installed
            import mammoth
            from markdownify import markdownify
            
            # Extract HTML from DOCX
            with open(docx_path, 'rb') as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value
                
                # Convert HTML to Markdown with GitHub-flavored tables
                markdown = markdownify(html, convert='github')
                
                # Update the document
                processed_doc = document.copy()
                processed_doc['content'] = markdown
                processed_doc['metadata'] = document.get('metadata', {})
                processed_doc['metadata']['docx_processor'] = 'mammoth'
                
                # Add warnings to metadata
                if result.messages:
                    processed_doc['metadata']['warnings'] = [str(msg) for msg in result.messages]
                
                return processed_doc
                
        except ImportError:
            self.logger.error("Mammoth or markdownify not installed. Install with 'pip install mammoth markdownify'")
            return document
        except Exception as e:
            self.logger.error(f"Error processing DOCX file: {e}")
            return document

    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform method required by PipelineComponent interface."""
        return self.process(document)