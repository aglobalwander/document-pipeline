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
            import re # Import re for regex

            # Define custom style map for better Markdown conversion
            style_map = """
            p[style-name='Heading 1'] => # $1
            p[style-name='Heading 2'] => ## $1
            p[style-name='Heading 3'] => ### $1
            p[style-name='Heading 4'] => #### $1
            p[style-name='Heading 5'] => ##### $1
            p[style-name='Heading 6'] => ###### $1
            p[style-name='Title'] => # $1
            p[style-name='Subtitle'] => ## $1
            r[style-name='Strong'] => **$1**
            r[style-name='Emphasis'] => *$1*
            """
            
            with open(docx_path, 'rb') as docx_file:
                # Use the markdown_options parameter to convert directly to markdown
                result = mammoth.convert_to_markdown(docx_file, style_map=style_map)
                markdown = result.value

                # --- Debugging: Save HTML content to a temporary file ---
                # temp_html_path = "temp_output.html"
                # try:
                #     with open(temp_html_path, 'w', encoding='utf-8') as f:
                #         f.write(html_content)
                #     self.logger.info(f"Saved temporary HTML output to {temp_html_path}")
                # except IOError as e:
                #     self.logger.error(f"Error saving temporary HTML file: {e}")
                # --- End Debugging ---
                
                # Remove Markdown image syntax (e.g., ![alt text](image_url))
                # This regex looks for ! followed by anything in brackets [] and anything in parentheses ()
                # Using re.DOTALL to match newlines within the brackets
                markdown = re.sub(r'!?\[.*?\]\(.*?\)', '', markdown, flags=re.DOTALL)

                # Log any warnings from Mammoth
                if result.messages:
                    for message in result.messages:
                        self.logger.warning(f"Mammoth conversion warning: {message}")
                
                # Log the markdown content
                self.logger.info(f"Generated markdown content length: {len(markdown)}")
                self.logger.info(f"Markdown content starts with: {markdown[:100]}...")
                
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
            self.logger.error("Mammoth not installed. Install with 'pip install mammoth'")
            return document
        except Exception as e:
            self.logger.error(f"Error processing DOCX file: {e}")
            return document

    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform method required by PipelineComponent interface."""
        return self.process(document)