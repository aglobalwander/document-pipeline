"""PowerPoint (PPTX) processor using MarkItDown."""
import os
import uuid
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from doc_processing.embedding.base import PipelineComponent
from doc_processing.embedding.base import BaseProcessor, PipelineComponent

class MarkItDownPPTXProcessor(BaseProcessor, PipelineComponent):
    """Process PPTX files using MarkItDown and LibreOffice for hybrid mode."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the PPTX processor.
        
        Args:
            config: Configuration options
                pptx_strategy: Strategy for processing PPTX files ('hybrid', 'text', 'pdf')
        """
        super().__init__(config or {})
        self.logger = logging.getLogger(__name__)
        self.pptx_strategy = self.config.get('pptx_strategy', 'hybrid')
        self.logger.info(f"Initialized MarkItDownPPTXProcessor with strategy: {self.pptx_strategy}")
        
        # Path to LibreOffice executable for PDF conversion
        self.libreoffice_path = self.config.get(
            'libreoffice_path', 
            '/Applications/LibreOffice.app/Contents/MacOS/soffice'
        )
        
        # Verify LibreOffice is available if using hybrid or pdf strategy
        if self.pptx_strategy in ['hybrid', 'pdf'] and not os.path.exists(self.libreoffice_path):
            self.logger.warning(
                f"LibreOffice not found at {self.libreoffice_path}. "
                "PDF extraction may fail. Install with 'brew install --cask libreoffice'"
            )

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a PPTX document.
        
        Args:
            document: Document dictionary with content field containing PPTX file path
            
        Returns:
            Processed document with extracted content
        """
        if not document.get('content'):
            self.logger.error("No content field in document")
            return document
            
        pptx_path = document['content']
        if not os.path.exists(pptx_path):
            self.logger.error(f"PPTX file not found: {pptx_path}")
            return document
            
        self.logger.info(f"Processing PPTX file: {pptx_path} with strategy: {self.pptx_strategy}")
        
        try:
            if self.pptx_strategy == 'hybrid':
                return self._process_hybrid(document, pptx_path)
            elif self.pptx_strategy == 'pdf':
                return self._process_pdf_only(document, pptx_path)
            else:  # Default to text-only
                return self._process_text_only(document, pptx_path)
        except Exception as e:
            self.logger.error(f"Error processing PPTX file: {e}")
            # Fall back to text-only if other methods fail
            self.logger.info("Falling back to text-only extraction")
            return self._process_text_only(document, pptx_path)

    def _process_hybrid(self, document: Dict[str, Any], pptx_path: str) -> Dict[str, Any]:
        """Process PPTX using both PDF and speaker notes extraction."""
        # First get the text content from speaker notes
        text_result = self._process_text_only(document, pptx_path)
        
        # Then get the PDF content
        pdf_result = self._process_pdf_only(document, pptx_path)
        
        # Combine the results
        combined_content = []
        
        # Get the slides from both methods
        text_slides = text_result.get('slides', [])
        pdf_slides = pdf_result.get('slides', [])
        
        # Use the longer list as the base
        max_slides = max(len(text_slides), len(pdf_slides))
        
        for i in range(max_slides):
            slide_content = ""
            
            # Add PDF content if available
            if i < len(pdf_slides):
                slide_content += pdf_slides[i].get('content', '')
            
            # Add speaker notes if available
            if i < len(text_slides) and text_slides[i].get('notes'):
                if slide_content:
                    slide_content += "\n\n--- Notes ---\n"
                slide_content += text_slides[i].get('notes', '')
            
            combined_content.append({
                'slide_number': i + 1,
                'content': slide_content,
                'notes': text_slides[i].get('notes', '') if i < len(text_slides) else ''
            })
        
        # Update the document with combined content
        result = document.copy()
        result['content'] = "\n\n".join([slide['content'] for slide in combined_content])
        result['slides'] = combined_content
        result['metadata'] = document.get('metadata', {})
        result['metadata']['pptx_strategy'] = 'hybrid'
        result['metadata']['slide_count'] = len(combined_content)
        
        return result

    def _process_text_only(self, document: Dict[str, Any], pptx_path: str) -> Dict[str, Any]:
        """Extract text and speaker notes from PPTX using MarkItDown."""
        try:
            # Import here to avoid dependency issues if not installed
            from markitdown.pptx import extract_slides_from_pptx
            
            self.logger.info(f"Extracting text and notes from PPTX: {pptx_path}")
            slides = extract_slides_from_pptx(pptx_path)
            
            # Format the slides
            formatted_slides = []
            all_content = []
            
            for i, slide in enumerate(slides):
                slide_number = i + 1
                slide_title = slide.get('title', f"Slide {slide_number}")
                slide_content = slide.get('content', '')
                slide_notes = slide.get('notes', '')
                
                # Format the slide content
                formatted_content = f"# {slide_title}\n\n{slide_content}"
                all_content.append(formatted_content)
                
                formatted_slides.append({
                    'slide_number': slide_number,
                    'title': slide_title,
                    'content': formatted_content,
                    'notes': slide_notes
                })
            
            # Update the document
            result = document.copy()
            result['content'] = "\n\n".join(all_content)
            result['slides'] = formatted_slides
            result['metadata'] = document.get('metadata', {})
            result['metadata']['pptx_strategy'] = 'text'
            result['metadata']['slide_count'] = len(formatted_slides)
            
            return result
            
        except ImportError:
            self.logger.error("MarkItDown not installed. Install with 'pip install markitdown[pptx]'")
            # Return the original document
            return document
        except Exception as e:
            self.logger.error(f"Error extracting text from PPTX: {e}")
            return document

    def _process_pdf_only(self, document: Dict[str, Any], pptx_path: str) -> Dict[str, Any]:
        """Convert PPTX to PDF and extract text using LibreOffice."""
        try:
            import subprocess
            import tempfile
            from doc_processing.processors.pdf_processor import PDFProcessor
            
            # Create a temporary directory for the PDF
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = os.path.join(temp_dir, f"{uuid.uuid4()}.pdf")
                
                # Convert PPTX to PDF using LibreOffice
                self.logger.info(f"Converting PPTX to PDF: {pptx_path} -> {temp_pdf_path}")
                cmd = [
                    self.libreoffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', temp_dir,
                    pptx_path
                ]
                
                process = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                
                if process.returncode != 0:
                    self.logger.error(f"Error converting PPTX to PDF: {process.stderr}")
                    return document
                
                # Find the generated PDF file
                pdf_files = list(Path(temp_dir).glob("*.pdf"))
                if not pdf_files:
                    self.logger.error("No PDF file generated")
                    return document
                
                temp_pdf_path = str(pdf_files[0])
                
                # Process the PDF using PDFProcessor
                pdf_processor = PDFProcessor(self.config)
                pdf_document = document.copy()
                pdf_document['content'] = temp_pdf_path
                
                # Process the PDF
                processed_pdf = pdf_processor.process(pdf_document)
                
                # Extract slides from the PDF content
                pdf_content = processed_pdf.get('content', '')
                
                # Simple slide detection based on page breaks or slide markers
                slide_markers = [
                    "# Slide", "## Slide", "### Slide",
                    "Slide 1", "Slide 2", "Slide 3", "Slide 4", "Slide 5"
                ]
                
                slides = []
                current_slide = ""
                slide_number = 1
                
                # Split by common page/slide markers
                lines = pdf_content.split('\n')
                for line in lines:
                    is_new_slide = False
                    for marker in slide_markers:
                        if marker in line:
                            is_new_slide = True
                            break
                    
                    if is_new_slide and current_slide:
                        slides.append({
                            'slide_number': slide_number,
                            'content': current_slide.strip()
                        })
                        slide_number += 1
                        current_slide = line
                    else:
                        current_slide += line + '\n'
                
                # Add the last slide
                if current_slide:
                    slides.append({
                        'slide_number': slide_number,
                        'content': current_slide.strip()
                    })
                
                # If no slides were detected, create a single slide with all content
                if not slides:
                    slides.append({
                        'slide_number': 1,
                        'content': pdf_content
                    })
                
                # Update the document
                result = document.copy()
                result['content'] = pdf_content
                result['slides'] = slides
                result['metadata'] = document.get('metadata', {})
                result['metadata']['pptx_strategy'] = 'pdf'
                result['metadata']['slide_count'] = len(slides)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error processing PDF: {e}")
            return document

    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform method required by PipelineComponent interface."""
        return self.process(document)