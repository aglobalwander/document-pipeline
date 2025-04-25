"""Hybrid PDF Processor choosing between Docling and Vision-based OCR."""
import os
import base64
import io
# Removed requests import as direct API calls are removed
from concurrent.futures import ThreadPoolExecutor, as_completed # Keep for potential future use? Or remove if vision processor handles concurrency. Let's keep for now.
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging
import fitz  # PyMuPDF
from PIL import Image
# Removed jinja2 import as prompt handling moved to GPTPVisionProcessor

# Removed the top-level import of docling.Document as it seems to cause issues
# from docling import Document as DoclingDocument # Keep for potential type hints

from doc_processing.embedding.base import BaseProcessor
from doc_processing.config import get_settings
# Import the dedicated Vision processor and Gemini client
from .gpt_vision_processor import GPTPVisionProcessor
from doc_processing.llm.gemini_client import GeminiClient # Import GeminiClient

logger = logging.getLogger(__name__)

class HybridPDFProcessor(BaseProcessor):
    """
    Processes PDF files using either Docling (for text-based PDFs) or
    a Vision LLM (like GPT-4 Vision via GPTPVisionProcessor) for image-based PDFs,
    or allows forcing a specific method.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()

        # OCR Mode Selection
        # 'hybrid': Choose automatically based on PDF properties (default)
        # 'docling': Force use of Docling (if available)
        # 'gpt': Force use of GPTPVisionProcessor
        self.ocr_mode = self.config.get('ocr_mode', 'hybrid').lower()
        # Removed DOCLING_AVAILABLE check here, it will be handled during processing attempt
        if self.ocr_mode not in ['hybrid', 'docling', 'gpt']:
            logger.warning(f"Invalid ocr_mode '{self.ocr_mode}'. Defaulting to 'hybrid'.")
            self.ocr_mode = 'hybrid'

        # Docling configuration (only relevant if docling or hybrid mode is possible)
        self.docling_use_easyocr = self.config.get('docling_use_easyocr', True)
        self.docling_extract_tables = self.config.get('docling_extract_tables', True)
        self.docling_extract_figures = self.config.get('docling_extract_figures', True)

        # Initialize GPTPVisionProcessor (only relevant if gpt or hybrid mode is possible)
        # Pass relevant parts of the config down
        # Build config for GPTPVisionProcessor, using defaults from settings if not in self.config
        vision_config = {
            # Default to 'openai' if not specified
            'llm_provider': self.config.get('llm_provider', 'openai'),
            # Use specific vision model from config, or default vision model from settings
            'vision_model': self.config.get('vision_model', self.settings.DEFAULT_OPENAI_VISION_MODEL),
             # Pass general llm_model from config as potential fallback if vision_model isn't set in GPTPVisionProcessor
            'llm_model': self.config.get('llm_model'),
            # Get API key from config, or fallback to settings (checking both potential env var names)
            'api_key': self.config.get('api_key', self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY),
            # Pass through other relevant configs
            'prompt_template': self.config.get('gpt_vision_prompt'),
            'template_dir': self.config.get('template_dir', self.settings.TEMPLATE_DIR), # Default to main template dir
            'llm_client_config': self.config.get('llm_client_config'),
        }
        # Filter out None values to avoid overriding defaults within GPTPVisionProcessor unnecessarily
        vision_config = {k: v for k, v in vision_config.items() if v is not None}
        # Initialize GPTPVisionProcessor only if needed (e.g., for OpenAI or fallback)
        if self.ocr_mode == 'gpt' or self.ocr_mode == 'hybrid': # Or if provider is OpenAI
             self.gpt_vision_processor = GPTPVisionProcessor(config=vision_config)
        else:
             self.gpt_vision_processor = None # Not needed if forcing Docling and not using Gemini fallback

        # Initialize GeminiClient separately if needed for direct PDF processing
        self.gemini_client: Optional[GeminiClient] = None
        if self.config.get('llm_provider') == 'gemini':
             try:
                 # Pass relevant config down to the new GeminiClient
                 gemini_config = {
                     'api_key': self.config.get('api_key', self.settings.GEMINI_API_KEY or self.settings.GOOGLE_API_KEY),
                     'model_name': self.config.get('llm_model', GeminiClient.DEFAULT_MODEL), # Use general model or Gemini default
                     # Pass other relevant sub-configs if GeminiClient uses them
                     'llm_client_config': self.config.get('llm_client_config')
                 }
                 gemini_config = {k: v for k, v in gemini_config.items() if v is not None} # Filter None
                 self.gemini_client = GeminiClient(**gemini_config)
             except ImportError as e:
                  # Use the correct package name in the error message
                  logger.error(f"Cannot use Gemini for PDF processing: {e}. Ensure 'google-genai' is installed.")
             except Exception as e:
                  logger.error(f"Failed to initialize GeminiClient for PDF processing: {e}")


        # Configuration for the old internal GPT Vision logic (now removed)
        # self.max_tokens = self.config.get('max_tokens', 1000)
        # self.max_retries = self.config.get('max_retries', 3)
        # self.concurrent_pages = self.config.get('concurrent_pages', 4)
        # self.resolution_scale = self.config.get('resolution_scale', 2)
        # self.prompt_template = self.config.get('prompt_template', 'pdf_extraction.j2') # Moved to GPTPVisionProcessor config
        
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document with appropriate method.
        
        Args:
            document: Dictionary containing PDF document content and metadata
            
        Returns:
            Processed document with extracted text content
        """
        self.logger.info(f"Processing PDF: {document.get('metadata', {}).get('filename', 'unknown')}")
        
        try:
            # --- Determine Processing Path ---
            provider = self.config.get('llm_provider', 'openai') # Get provider from config

            # 1. Handle Gemini Native PDF Processing
            if provider == 'gemini' and self.gemini_client:
                 self.logger.info("Using Gemini native PDF processing.")
                 # We need a prompt for Gemini PDF processing. Use a default or get from config.
                 pdf_prompt = self.config.get('gemini_pdf_prompt', "Extract all text content from this PDF document.")
                 try:
                      extracted_text = self.gemini_client.process_pdf(
                          pdf_path=document['source_path'],
                          prompt=pdf_prompt
                          # Pass other kwargs like max_tokens if needed from config
                      )
                      document['content'] = extracted_text
                      document['processing_method'] = 'gemini_native_pdf'
                      # Note: Gemini processes the whole PDF, so 'pages' might not be relevant here unless Gemini provides page info.
                      # Clear or adapt the 'pages' structure if necessary.
                      document['pages'] = [] # Clear pages generated by loader if using native PDF processing
                 except Exception as gemini_err:
                      self.logger.error(f"Gemini native PDF processing failed: {gemini_err}. Falling back if possible.")
                      # Decide on fallback: maybe try GPT Vision? Or just fail? Let's fail for now.
                      document['error'] = f"Gemini native PDF processing failed: {gemini_err}"
                      return document # Return with error

            # 2. Handle Docling (if forced or chosen by hybrid heuristic)
            elif self.ocr_mode == 'docling' or (self.ocr_mode == 'hybrid' and self._should_use_docling(document)):
                mode_used = 'docling_forced' if self.ocr_mode == 'docling' else 'docling_hybrid'
                self.logger.info(f"Attempting Docling processing (mode: {self.ocr_mode})")
                try:
                    document = self._process_with_docling(document) # This method now handles its own import and fallback
                    document['processing_method'] = mode_used
                    # Check if _process_with_docling fell back
                    if 'error' in document and "Docling processing error" in document['error'] and self.gpt_vision_processor:
                         self.logger.info("Docling failed, falling back to GPT Vision (within _process_with_docling).")
                         # The fallback already happened inside _process_with_docling if it called self.gpt_vision_processor.process
                         # We might need to adjust the processing_method set by the fallback
                         if 'processing_method' in document and '+GPTPVision' in document['processing_method']:
                              document['processing_method'] = f"{mode_used}_fallback_gpt"
                         else: # If fallback failed or didn't run gpt_vision_processor
                              pass # Keep the error state from docling failure
                    elif 'error' in document and "Docling processing error" in document['error']:
                         self.logger.warning("Docling failed, and no GPT Vision fallback was available or configured.")

                except Exception as docling_err: # Catch potential errors in the call itself
                     self.logger.error(f"Unexpected error during Docling processing attempt: {docling_err}")
                     document['error'] = f"Unexpected Docling error: {docling_err}"
                     # Optionally attempt GPT Vision fallback here too if desired and available
                     if self.gpt_vision_processor:
                          self.logger.info("Falling back to GPT Vision due to unexpected Docling error.")
                          document = self.gpt_vision_processor.process(document)
                          document['processing_method'] = f"{mode_used}_fallback_gpt_unexpected"


            # 3. Handle Forced GPT Vision or Hybrid Fallback (if not Gemini)
            elif self.ocr_mode == 'gpt' or (self.ocr_mode == 'hybrid' and provider != 'gemini'):
                 if not self.gpt_vision_processor:
                      self.logger.error("GPT Vision processing requested but GPTPVisionProcessor not initialized.")
                      document['error'] = "GPTPVisionProcessor not available."
                 else:
                      mode_used = 'gpt_forced' if self.ocr_mode == 'gpt' else 'hybrid_fallback_gpt'
                      self.logger.info(f"Using GPT Vision processing (mode: {self.ocr_mode})")
                      document = self.gpt_vision_processor.process(document)
                      # GPTPVisionProcessor sets its own processing_method, maybe prepend our mode?
                      document['processing_method'] = f"{mode_used}" + document.get('processing_method', '')


            # 4. Handle unsupported configurations
            else:
                 self.logger.error(f"Unsupported configuration: provider='{provider}', ocr_mode='{self.ocr_mode}'. Cannot process PDF.")
                 document['error'] = "Unsupported PDF processing configuration."


            return document

        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}")
            document['error'] = str(e)
            return document
    
    def _should_use_docling(self, document: Dict[str, Any]) -> bool:
        """Determine if Docling should be used for processing based on heuristics.
        Note: This no longer checks for Docling availability, only heuristics.
        Availability is checked when _process_with_docling is called.

        Args:
            document: Document dictionary

        Returns:
            True if heuristics suggest Docling should be tried, False otherwise
        """
        # Removed DOCLING_AVAILABLE check
        # Check if Docling usage is generally enabled in config (if such a flag exists)
        # if not self.config.get('use_docling_processing', True): # Example config flag
        #     return False

        # Get metadata
        metadata = document.get('metadata', {})
        
        # Check if document appears to be a scan
        is_scan = metadata.get('is_scan', False)
        
        # Check PDF version - newer PDFs are more likely to have extractable text
        # PDF 1.5+ often have better text extraction capabilities
        recent_pdf = metadata.get('pdf_version', 0) >= 1.5 if 'pdf_version' in metadata else False
        
        # Use native PDF text extraction for newer PDFs that aren't scans
        if recent_pdf and not is_scan:
            return True
            
        # If this file was already analyzed, follow previous decision
        if 'requires_ocr' in metadata:
            return not metadata['requires_ocr']
            
        # Default to using GPT Vision for better accuracy 
        # if we're not sure about document characteristics
        return False
    
    def _process_with_docling(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document with Docling. Attempts import internally.

        Args:
            document: Dictionary containing PDF document content and metadata

        Returns:
            Processed document with extracted text content, or falls back to GPT Vision on error.
        """
        try:
            # Attempt Docling import here
            from docling.document_converter import DocumentConverter
            self.logger.info("Successfully imported Docling DocumentConverter.")

            # Get document source path
            source_path = document.get('source_path')
            if not source_path:
                raise ValueError("Document missing source_path")
            
            # Instantiate the converter
            # Pass relevant config options if DoclingConverter accepts them
            # For now, using defaults. Check Docling docs for config options.
            converter = DocumentConverter()

            # Process with Docling using the converter instance
            result = converter.convert(
                source_path,
                # Pass options if needed, e.g.:
                # use_easyocr=self.docling_use_easyocr,
                # extract_tables=self.docling_extract_tables,
                # extract_figures=self.docling_extract_figures
            )

            # Check if conversion was successful and document exists
            if not result or not hasattr(result, 'document') or not result.document:
                 raise ValueError("Docling conversion failed or returned an empty result.")

            docling_doc = result.document # Get the actual document object

            # Extract text content
            content = self._extract_text_from_docling(docling_doc)

            # Update document with extracted text content
            document['content'] = content

            # Extract tables if available (check docling_doc structure)
            # Assuming tables are still accessible via docling_doc.tables
            if self.docling_extract_tables and hasattr(docling_doc, 'tables') and docling_doc.tables:
                document['tables'] = self._extract_tables_from_docling(docling_doc)

            # Update metadata (check docling_doc structure)
            pages_count = len(docling_doc.pages) if hasattr(docling_doc, 'pages') else 0
            document['metadata']['num_pages'] = pages_count
            document['metadata']['num_processed_pages'] = pages_count

            # Create pages array (check docling_doc structure)
            document['pages'] = []
            if hasattr(docling_doc, 'pages') and docling_doc.pages:
                for i, page in enumerate(docling_doc.pages):
                    # Check if 'page' is an object with 'page_number' attribute
                    page_num = 0 # Default page number
                    if hasattr(page, 'page_number'):
                        page_num = page.page_number
                    else:
                        self.logger.warning(f"Item at index {i} in docling_doc.pages does not have 'page_number'. Using default 0. Item type: {type(page)}")
                        # Attempt to get page number based on index if it's missing
                        page_num = i + 1 # Fallback to 1-based index

                    page_content = self._extract_page_text_from_docling(page)
                    document['pages'].append({
                        'page_number': page_num,
                        'text': f"\n\nPage {page_num}\n{'-' * 40}\n{page_content}"
                    })
            else:
                 self.logger.warning("docling_doc does not have 'pages' attribute or it's empty.")


            self.logger.info(f"Successfully processed document with Docling")
            return document
                
        except Exception as e:
            self.logger.error(f"Error processing with Docling: {str(e)}")
            document['error'] = f"Docling processing error: {str(e)}"
            # Fallback to GPT Vision
            self.logger.info("Falling back to GPT Vision")
            # Fallback to GPT Vision using the dedicated processor
            self.logger.info("Falling back to GPT Vision")
            return self.gpt_vision_processor.process(document)
    
    def _extract_text_from_docling(self, docling_doc: Any) -> str:
        """Extract text content from Docling document.
        
        Args:
            docling_doc: Docling document object
            
        Returns:
            Extracted text content
        """
        # Combine all text blocks in reading order
        content = []
        
        if hasattr(docling_doc, 'pages'):
            for page in docling_doc.pages:
                page_content = self._extract_page_text_from_docling(page)
                
                # Add page separator
                if page_content:
                    page_num = page.page_number if hasattr(page, 'page_number') else 0
                    content.append(f"\n\nPage {page_num}\n{'-' * 40}\n")
                    content.append(page_content)
        
        return "\n".join(content)
    
    def _extract_page_text_from_docling(self, page: Any) -> str:
        """Extract text from a Docling page.
        
        Args:
            page: Docling page object
            
        Returns:
            Extracted text content
        """
        page_content = []
        
        if hasattr(page, 'blocks'):
            for block in page.blocks:
                if hasattr(block, 'text') and block.text:
                    page_content.append(block.text)
        
        return "\n".join(page_content)
    
    def _extract_tables_from_docling(self, docling_doc: Any) -> List[Dict[str, Any]]:
        """Extract tables from Docling document.
        
        Args:
            docling_doc: Docling document object
            
        Returns:
            List of extracted tables
        """
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
    
    # Removed internal GPT Vision processing methods (_process_with_gpt_vision, _process_page,
    # _encode_image, _render_prompt_template, _perform_ocr_with_gpt4).
    # This functionality is now handled by the dedicated GPTPVisionProcessor.