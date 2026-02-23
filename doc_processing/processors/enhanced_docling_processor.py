"""Enhanced PDF Processor using Docling with multi-format output capabilities and caching."""
import os
import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging

# Import necessary Docling classes for proper configuration
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from doc_processing.embedding.base import BaseProcessor
from doc_processing.config import get_settings
from doc_processing.utils.processing_cache import ProcessingCache

logger = logging.getLogger(__name__)

class EnhancedDoclingPDFProcessor(BaseProcessor):
    """
    Enhanced processor for PDF files using Docling with multi-format output capabilities.
    Leverages Docling's native processing for optimal text extraction and formatting.
    Includes caching support for resumable processing.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()
        
        # Docling configuration
        self.docling_extract_tables = self.config.get('docling_extract_tables', True)
        
        # Output format options
        self.output_format = self.config.get('output_format', 'text')  # Primary output format: 'text', 'markdown', 'json'
        self.output_all_formats = self.config.get('output_all_formats', True)  # Whether to output all formats
        
        # Caching options
        self.use_cache = self.config.get('use_cache', True)
        self.cache = ProcessingCache() if self.use_cache else None
        
    def _generate_document_id(self, source_path: str) -> str:
        """Generate a unique document ID based on file path and modification time."""
        path_obj = Path(source_path)
        if not path_obj.exists():
            return hashlib.md5(source_path.encode()).hexdigest()
        
        # Use filename and modification time for a unique ID
        mod_time = path_obj.stat().st_mtime
        return f"{path_obj.stem}_{int(mod_time)}"

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document with Docling and output in multiple formats with caching support."""
        self.logger.info(f"Processing document with Docling: {document.get('metadata', {}).get('filename', 'unknown')}")
        
        source_path = document.get('source_path')
        if not source_path:
            raise ValueError("Document missing source_path")
        
        # Generate document ID for caching
        doc_id = self._generate_document_id(source_path)
        
        # Check for existing checkpoint if caching is enabled
        processed_pages = []
        if self.use_cache:
            checkpoint = self.cache.load_checkpoint(doc_id)
            if checkpoint:
                self.logger.info(f"Found processing checkpoint for {doc_id} with {len(checkpoint['processed_pages'])} pages")
                processed_pages = checkpoint["processed_pages"]
                
                # If we have all pages processed, return the cached result
                if len(processed_pages) == document.get('metadata', {}).get('num_pages', 0):
                    self.logger.info(f"Using complete cached result for {doc_id}")
                    # Reconstruct document from cache
                    document['pages'] = processed_pages
                    document['processing_method'] = 'docling_cached'
                    return document
                
                self.logger.info(f"Resuming processing from page {len(processed_pages) + 1}")
        
        try:
            # Attempt Docling import here
            from docling.document_converter import DocumentConverter
            self.logger.info("Successfully imported Docling DocumentConverter.")

            # Create pipeline options with our desired settings
            pipeline_options = PdfPipelineOptions(
                do_table_structure=self.docling_extract_tables,
            )
            
            # Create the DocumentConverter with format options
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            
            self.logger.info(f"Creating DocumentConverter with pipeline options: do_table_structure={self.docling_extract_tables}")
            self.logger.debug(f"Converting document: {source_path}")
            
            # Convert the document
            result = converter.convert(source_path)

            if not result or not hasattr(result, 'document') or not result.document:
                raise ValueError("Docling conversion failed or returned an empty result.")

            docling_doc = result.document
            
            # Extract content in available formats
            try:
                text_content = docling_doc.export_to_text()
                self.logger.info(f"  - Text: {len(text_content)} characters")
            except (AttributeError, Exception) as e:
                self.logger.warning(f"Failed to export to text: {str(e)}")
                text_content = ""
                
            try:
                markdown_content = docling_doc.export_to_markdown()
                self.logger.info(f"  - Markdown: {len(markdown_content)} characters")
            except (AttributeError, Exception) as e:
                self.logger.warning(f"Failed to export to markdown: {str(e)}")
                markdown_content = ""
                
            # JSON export is not available in the current Docling API
            # Instead, we'll create a simple JSON representation of the document
            try:
                # Extract per-page content by splitting markdown on page boundaries
                # Docling markdown often has page breaks or section headers we can use
                page_texts = self._split_content_by_pages(markdown_content, text_content, docling_doc)

                # Create a simple JSON representation
                json_data = {
                    "metadata": {
                        "filename": document.get('metadata', {}).get('filename', ''),
                        "num_pages": len(docling_doc.pages) if hasattr(docling_doc, 'pages') else 0,
                    },
                    "content": text_content,
                    "pages": page_texts
                }

                json_content = json.dumps(json_data, indent=2)
                self.logger.info(f"  - JSON: {len(json_content)} characters")
            except Exception as e:
                self.logger.warning(f"Failed to create JSON representation: {str(e)}")
                json_content = "{}"
            
            self.logger.info(f"Exported document in multiple formats")
            
            # Set the primary content based on the requested output format
            if self.output_format == 'markdown' and markdown_content:
                document['content'] = markdown_content
            elif self.output_format == 'json' and json_content:
                document['content'] = json_content
            else:  # Default to text
                document['content'] = text_content
            
            # Store all formats if requested
            if self.output_all_formats:
                if text_content:
                    document['text_content'] = text_content
                if markdown_content:
                    document['markdown_content'] = markdown_content
                if json_content:
                    document['json_content'] = json_content
            
            # Extract tables if available
            if self.docling_extract_tables and hasattr(docling_doc, 'tables') and docling_doc.tables:
                document['tables'] = self._extract_tables_from_docling(docling_doc)
                self.logger.info(f"Extracted {len(document['tables'])} tables from document")

            # Update metadata
            pages_count = len(docling_doc.pages) if hasattr(docling_doc, 'pages') else 0
            document['metadata']['num_pages'] = pages_count
            document['metadata']['num_processed_pages'] = pages_count
            
            # Process individual pages
            document['pages'] = []
            if hasattr(docling_doc, 'pages') and docling_doc.pages:
                # Determine which pages we need to process
                start_page = len(processed_pages)
                
                for i, page in enumerate(docling_doc.pages):
                    page_num = page.page_number if hasattr(page, 'page_number') else i + 1
                    
                    # Skip pages we've already processed
                    if i < start_page:
                        document['pages'].append(processed_pages[i])
                        continue
                    
                    # Get page content
                    if hasattr(page, 'export_to_text'):
                        page_content = page.export_to_text()
                    else:
                        page_content = self._extract_page_text_from_docling(page)
                    
                    page_data = {
                        'page_number': page_num,
                        'text': f"\n\nPage {page_num}\n{'-' * 40}\n{page_content}"
                    }
                    
                    document['pages'].append(page_data)
                    
                    # Save checkpoint after each page if caching is enabled
                    if self.use_cache:
                        processed_pages = document['pages']
                        self.cache.save_checkpoint(doc_id, processed_pages, document['metadata'])
                        self.logger.debug(f"Saved checkpoint after processing page {page_num}")
                
                self.logger.info(f"Processed {len(document['pages'])} individual pages")
            else:
                self.logger.warning("Document does not have 'pages' attribute or it's empty.")

            # Clear checkpoint after successful processing if caching is enabled
            if self.use_cache:
                self.cache.clear_checkpoint(doc_id)
                self.logger.info(f"Cleared checkpoint for {doc_id} after successful processing")

            self.logger.info(f"Successfully processed document with Docling")
            document['processing_method'] = 'docling'
            return document

        except ImportError:
            self.logger.error("Docling is not installed. Please install it to use EnhancedDoclingPDFProcessor.")
            document['error'] = "Docling not installed."
            return document
        except Exception as e:
            self.logger.error(f"Error processing with Docling: {str(e)}")
            document['error'] = f"Docling processing error: {str(e)}"
            return document

    # Helper methods for extracting content from Docling document

    def _split_content_by_pages(self, markdown_content: str, text_content: str, docling_doc: Any) -> List[Dict[str, Any]]:
        """
        Split document content into per-page chunks.
        Uses Docling's internal page structure to extract content per page.
        """
        pages = []
        num_pages = len(docling_doc.pages) if hasattr(docling_doc, 'pages') else 0

        if num_pages == 0:
            return pages

        # Try to extract per-page content from docling_doc's internal structure
        if hasattr(docling_doc, 'pages'):
            for i, page in enumerate(docling_doc.pages):
                page_num = i + 1
                page_text = self._extract_page_text_from_docling(page)

                pages.append({
                    "page_number": page_num,
                    "text": page_text
                })

        # If we couldn't extract per-page content, split the full content evenly
        if not any(p.get("text") for p in pages) and text_content:
            # Simple heuristic: split content roughly by page count
            lines = text_content.split('\n')
            lines_per_page = max(1, len(lines) // num_pages)

            pages = []
            for i in range(num_pages):
                start_idx = i * lines_per_page
                end_idx = start_idx + lines_per_page if i < num_pages - 1 else len(lines)
                page_text = '\n'.join(lines[start_idx:end_idx])
                pages.append({
                    "page_number": i + 1,
                    "text": page_text
                })

        return pages

    def _extract_page_text_from_docling(self, page: Any) -> str:
        """Extract text from a Docling page by iterating over its items/elements."""
        page_content = []

        # Try different approaches to extract page content from Docling
        # Approach 1: Check for items attribute (common in newer Docling)
        if hasattr(page, 'items'):
            for item in page.items:
                if hasattr(item, 'text') and item.text:
                    page_content.append(item.text)
                elif hasattr(item, 'content') and item.content:
                    page_content.append(str(item.content))

        # Approach 2: Check for children attribute
        if not page_content and hasattr(page, 'children'):
            for child in page.children:
                if hasattr(child, 'text') and child.text:
                    page_content.append(child.text)

        # Approach 3: Check for body/main_text
        if not page_content and hasattr(page, 'body'):
            if hasattr(page.body, 'text'):
                page_content.append(page.body.text)
            elif isinstance(page.body, str):
                page_content.append(page.body)

        # Approach 4: Original blocks approach
        if not page_content and hasattr(page, 'blocks'):
            for block in page.blocks:
                if hasattr(block, 'text') and block.text:
                    page_content.append(block.text)

        return "\n".join(page_content)

    def _extract_tables_from_docling(self, docling_doc: Any) -> List[Dict[str, Any]]:
        """Extract tables from Docling document."""
        tables = []
        if hasattr(docling_doc, 'tables'):
            for table_idx, table in enumerate(docling_doc.tables):
                table_data = {
                    'table_index': table_idx,
                    'page_number': table.page.page_number if hasattr(table, 'page') and hasattr(table.page, 'page_number') else None,
                    'rows': []
                }
                if hasattr(table, 'data') and table.data:
                    table_data['rows'] = table.data
                tables.append(table_data)
        return tables
