"""PyMuPDF processor for fast text extraction from PDFs with embedded text."""
import fitz  # PyMuPDF
from typing import Dict, Optional, List
from pathlib import Path
import logging

from doc_processing.embedding.base import BaseProcessor


class PyMuPDFProcessor(BaseProcessor):
    """
    Fast text extraction using PyMuPDF for PDFs with embedded text.
    
    This processor is extremely fast but only works on PDFs that already
    contain extractable text (not scanned images).
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize PyMuPDF processor."""
        super().__init__()
        self.config = config or {}
        self.name = "pymupdf"
        self.extract_tables = self.config.get('extract_tables', True)
        self.extract_images = self.config.get('extract_images', False)
        self.min_text_length = self.config.get('min_text_length', 50)
        
    def process(self, document: Dict) -> Dict:
        """
        Extract text from PDF using PyMuPDF.
        
        Args:
            document: Dictionary containing 'source_path' key
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            pdf_path = document.get('source_path')
            if not pdf_path:
                raise ValueError("No source path provided")
            
            # Open PDF
            doc = fitz.open(pdf_path)
            
            # Initialize results
            extracted_text = []
            extracted_tables = []
            metadata = {
                'page_count': len(doc),
                'pdf_metadata': doc.metadata,
                'is_encrypted': doc.is_encrypted,
                'has_text': False,
                'has_tables': False,
                'extraction_method': 'pymupdf',
                'pages_with_text': [],
                'pages_without_text': []
            }
            
            # Process each page
            total_text_length = 0
            page_count = len(doc)
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text("text")
                
                # Check if page has meaningful text
                if len(text.strip()) >= self.min_text_length:
                    metadata['has_text'] = True
                    metadata['pages_with_text'].append(page_num + 1)
                    extracted_text.append(f"=== Page {page_num + 1} ===\n{text}")
                    total_text_length += len(text)
                else:
                    metadata['pages_without_text'].append(page_num + 1)
                
                # Extract tables if enabled
                if self.extract_tables:
                    tables = page.find_tables()
                    if tables:
                        metadata['has_tables'] = True
                        for table_idx, table in enumerate(tables):
                            table_text = self._format_table(table, page_num + 1, table_idx + 1)
                            extracted_tables.append(table_text)
            
            # Close document
            doc.close()
            
            # Check if we extracted enough text
            if not metadata['has_text'] or total_text_length < (self.min_text_length * page_count * 0.5):
                # This PDF doesn't have enough embedded text - need OCR
                logging.info(f"PyMuPDF: Insufficient text extracted from {Path(pdf_path).name}")
                logging.info(f"Pages with text: {len(metadata['pages_with_text'])}/{metadata['page_count']}")
                document['requires_ocr'] = True
                document['pymupdf_attempted'] = True
                document['metadata'] = metadata
                # Return document as-is to trigger fallback
                return document
            
            # Combine text and tables
            full_content = []
            
            # Add main text
            if extracted_text:
                full_content.append("=== DOCUMENT TEXT ===\n")
                full_content.extend(extracted_text)
            
            # Add tables
            if extracted_tables:
                full_content.append("\n\n=== EXTRACTED TABLES ===\n")
                full_content.extend(extracted_tables)
            
            # Update document
            document['content'] = '\n\n'.join(full_content)
            document['metadata'] = metadata
            document['processor_used'] = self.name
            document['extraction_successful'] = True
            
            # Add summary statistics
            metadata['total_text_length'] = total_text_length
            metadata['avg_text_per_page'] = total_text_length / page_count if page_count > 0 else 0
            
            logging.info(f"PyMuPDF: Successfully extracted {total_text_length} characters from {Path(pdf_path).name}")
            
            return document
            
        except Exception as e:
            logging.error(f"PyMuPDF extraction failed: {str(e)}")
            document['error'] = str(e)
            document['requires_ocr'] = True
            document['pymupdf_attempted'] = True
            return document
    
    def _format_table(self, table, page_num: int, table_num: int) -> str:
        """
        Format table data as readable text.
        
        Args:
            table: PyMuPDF table object
            page_num: Page number (1-indexed)
            table_num: Table number on page (1-indexed)
            
        Returns:
            Formatted table as string
        """
        try:
            rows = []
            rows.append(f"\n--- Table {table_num} on Page {page_num} ---")
            
            # Extract table data
            table_data = table.extract()
            
            if not table_data:
                return ""
            
            # Format each row
            for row_idx, row in enumerate(table_data):
                # Clean cells - replace None with empty string
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                
                # Skip completely empty rows
                if all(cell == "" for cell in cleaned_row):
                    continue
                
                # Join cells with separator
                row_text = " | ".join(cleaned_row)
                rows.append(row_text)
                
                # Add separator after header row (first row)
                if row_idx == 0 and len(table_data) > 1:
                    separator = "-" * len(row_text)
                    rows.append(separator)
            
            return '\n'.join(rows)
            
        except Exception as e:
            logging.warning(f"Table extraction failed: {str(e)}")
            return f"\n--- Table {table_num} on Page {page_num} (extraction failed) ---"
    
    def can_process(self, document: Dict) -> bool:
        """
        Check if this processor can handle the document.
        
        PyMuPDF can process any PDF, but may not extract text from scanned pages.
        """
        source_path = document.get('source_path', '')
        if not source_path:
            return False
        
        # Check if it's a PDF
        file_extension = Path(source_path).suffix.lower()
        return file_extension == '.pdf'
    
    def estimate_cost(self, document: Dict) -> float:
        """
        Estimate the cost of processing this document.
        
        PyMuPDF is free to use.
        """
        return 0.0