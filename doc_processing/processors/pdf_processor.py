"""PDF Processors for different strategies (Docling, Vision LLMs)."""
import os
import base64
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging
import fitz  # PyMuPDF
from PIL import Image

from doc_processing.embedding.base import BaseProcessor
from doc_processing.config import get_settings
from .gpt_vision_processor import GPTPVisionProcessor
from .enhanced_docling_processor import EnhancedDoclingPDFProcessor
from doc_processing.llm.gemini_client import GeminiClient
from doc_processing.templates.prompt_manager import PromptTemplateManager # Import PromptTemplateManager

logger = logging.getLogger(__name__)

# Define a base class for PDF processors
class BasePDFProcessor(BaseProcessor):
    """Base class for PDF processors."""
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a PDF document."""
        raise NotImplementedError("Subclasses must implement this method")

class DoclingPDFProcessor(BasePDFProcessor):
    """Processes PDF files using Docling."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()
        # Docling configuration
        self.docling_use_easyocr = self.config.get('docling_use_easyocr', True)
        self.docling_extract_tables = self.config.get('docling_extract_tables', True)
        self.docling_extract_figures = self.config.get('docling_extract_figures', True)

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document with Docling."""
        self.logger.info(f"Attempting Docling processing: {document.get('metadata', {}).get('filename', 'unknown')}")
        try:
            # Attempt Docling import here
            from docling.document_converter import DocumentConverter
            self.logger.info("Successfully imported Docling DocumentConverter.")

            source_path = document.get('source_path')
            if not source_path:
                raise ValueError("Document missing source_path")

            converter = DocumentConverter()

            result = converter.convert(
                source_path,
                # Pass options if needed, e.g.:
                # use_easyocr=self.docling_use_easyocr,
                # extract_tables=self.docling_extract_tables,
                # extract_figures=self.docling_extract_figures
            )

            if not result or not hasattr(result, 'document') or not result.document:
                 raise ValueError("Docling conversion failed or returned an empty result.")

            docling_doc = result.document

            content = self._extract_text_from_docling(docling_doc)
            document['content'] = content

            if self.docling_extract_tables and hasattr(docling_doc, 'tables') and docling_doc.tables:
                document['tables'] = self._extract_tables_from_docling(docling_doc)

            pages_count = len(docling_doc.pages) if hasattr(docling_doc, 'pages') else 0
            document['metadata']['num_pages'] = pages_count
            document['metadata']['num_processed_pages'] = pages_count

            document['pages'] = []
            if hasattr(docling_doc, 'pages') and docling_doc.pages:
                for i, page in enumerate(docling_doc.pages):
                    page_num = page.page_number if hasattr(page, 'page_number') else i + 1
                    page_content = self._extract_page_text_from_docling(page)
                    document['pages'].append({
                        'page_number': page_num,
                        'text': f"\n\nPage {page_num}\n{'-' * 40}\n{page_content}"
                    })
            else:
                 self.logger.warning("docling_doc does not have 'pages' attribute or it's empty.")

            self.logger.info(f"Successfully processed document with Docling")
            document['processing_method'] = 'docling'
            return document

        except ImportError:
            self.logger.error("Docling is not installed. Please install it to use DoclingPDFProcessor.")
            document['error'] = "Docling not installed."
            return document
        except Exception as e:
            self.logger.error(f"Error processing with Docling: {str(e)}")
            document['error'] = f"Docling processing error: {str(e)}"
            return document

    def _extract_text_from_docling(self, docling_doc: Any) -> str:
        """Extract text content from Docling document."""
        content = []
        if hasattr(docling_doc, 'pages'):
            for page in docling_doc.pages:
                page_content = self._extract_page_text_from_docling(page)
                if page_content:
                    page_num = page.page_number if hasattr(page, 'page_number') else 0
                    content.append(f"\n\nPage {page_num}\n{'-' * 40}\n")
                    content.append(page_content)
        return "\n".join(content)

    def _extract_page_text_from_docling(self, page: Any) -> str:
        """Extract text from a Docling page."""
        page_content = []
        if hasattr(page, 'blocks'):
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

class GPTPDFProcessor(BasePDFProcessor):
    """Processes PDF files using GPT Vision via GPTPVisionProcessor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()
        # Initialize GPTPVisionProcessor
        vision_config = {
            'llm_provider': self.config.get('llm_provider', 'openai'), # Default to 'openai'
            'vision_model': self.config.get('vision_model', self.settings.DEFAULT_OPENAI_VISION_MODEL),
            'llm_model': self.config.get('llm_model'),
            'api_key': self.config.get('api_key', self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY),
            'prompt_template': self.config.get('gpt_vision_prompt'),
            'template_dir': self.config.get('template_dir', self.settings.TEMPLATE_DIR),
            'llm_client_config': self.config.get('llm_client_config'),
        }
        vision_config = {k: v for k, v in vision_config.items() if v is not None}
        self.gpt_vision_processor = GPTPVisionProcessor(config=vision_config)

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document with GPT Vision."""
        self.logger.info(f"Attempting GPT Vision processing: {document.get('metadata', {}).get('filename', 'unknown')}")
        try:
            processed_document = self.gpt_vision_processor.process(document)
            processed_document['processing_method'] = 'gpt_vision' + processed_document.get('processing_method', '')
            return processed_document
        except Exception as e:
            self.logger.error(f"Error processing with GPT Vision: {str(e)}")
            document['error'] = f"GPT Vision processing error: {str(e)}"
            return document

class GeminiPDFProcessor(BasePDFProcessor):
    """Processes PDF files using Gemini native PDF processing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()
        self.gemini_client: Optional[GeminiClient] = None
        try:
            gemini_config = {
                'api_key': self.config.get('api_key', self.settings.GEMINI_API_KEY or self.settings.GOOGLE_API_KEY),
                'model_name': self.config.get('llm_model', GeminiClient.DEFAULT_MODEL),
                'llm_client_config': self.config.get('llm_client_config')
            }
            gemini_config = {k: v for k, v in gemini_config.items() if v is not None}
            self.gemini_client = GeminiClient(**gemini_config)
        except ImportError as e:
            self.logger.error(f"Cannot use Gemini for PDF processing: {e}. Ensure 'google-genai' is installed.")
        except Exception as e:
            self.logger.error(f"Failed to initialize GeminiClient for PDF processing: {e}")

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document with Gemini native PDF processing."""
        self.logger.info(f"Attempting Gemini native PDF processing: {document.get('metadata', {}).get('filename', 'unknown')}")
        if not self.gemini_client:
            document['error'] = "GeminiClient not initialized. Cannot perform Gemini native PDF processing."
            self.logger.error(document['error'])
            return document

        try:
            pdf_prompt_text = "Extract all text content from this PDF document."
            prompt_name = self.config.get('prompt_name')
            if prompt_name:
                template_name = f"{prompt_name}.j2"
                try:
                    template_dir = self.config.get('template_dir', self.settings.TEMPLATE_DIR)
                    template_manager = PromptTemplateManager(template_dir)
                    prompt_context = {'document': document, 'metadata': document.get('metadata', {})}
                    pdf_prompt_text = template_manager.render_prompt(template_name, prompt_context)
                    self.logger.info(f"Using Gemini PDF prompt from template: {template_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to load/render Gemini prompt template '{template_name}': {e}. Using default prompt.")

            extracted_text = self.gemini_client.process_pdf(
                pdf_path=document['source_path'],
                prompt=pdf_prompt_text
            )
            document['content'] = extracted_text
            document['processing_method'] = 'gemini_native_pdf'
            document['pages'] = [] # Clear pages generated by loader if using native PDF processing

            self.logger.info(f"Successfully processed document with Gemini native PDF processing")
            return document

        except Exception as e:
            self.logger.error(f"Error processing with Gemini native PDF: {str(e)}")
            document['error'] = f"Gemini native PDF processing error: {str(e)}"
            return document

class PDFProcessor(BasePDFProcessor):
    """
    Orchestrates PDF processing based on configured strategy and available processors.
    This class replaces the old HybridPDFProcessor logic for selecting processors.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()
        
        # First check if values are in config (from command line args)
        # If not, fall back to environment variables via settings
        # If neither is present, use hardcoded defaults
        self.processor_strategy = self.config.get(
            'pdf_processor_strategy',
            os.environ.get('PDF_PROCESSOR_STRATEGY', self.settings.PDF_PROCESSOR_STRATEGY)
        ).lower()
        
        self.active_processors = self.config.get(
            'active_pdf_processors',
            self.settings.ACTIVE_PDF_PROCESSORS
        )
        
        self.default_processor = self.config.get(
            'default_pdf_processor',
            os.environ.get('DEFAULT_PDF_PROCESSOR', self.settings.DEFAULT_PDF_PROCESSOR)
        ).lower()
        
        self.fallback_order = self.config.get(
            'pdf_fallback_order',
            self.settings.PDF_FALLBACK_ORDER
        ) # Docling is implicit first if active

        self.available_processors: Dict[str, BasePDFProcessor] = {}
        self._initialize_processors()

    def _initialize_processors(self):
        """Initializes the configured PDF processors."""
        processor_map = {
            'docling': DoclingPDFProcessor,
            'enhanced_docling': EnhancedDoclingPDFProcessor,
            'gpt': GPTPDFProcessor,
            'gemini': GeminiPDFProcessor,
        }

        for processor_name in self.active_processors:
            if processor_name in processor_map:
                try:
                    # Pass the relevant config to each processor
                    processor_config = self.config.copy() # Start with a copy of the main config
                    # Add processor-specific overrides if needed (e.g., docling_use_easyocr)
                    # For now, assuming the main config contains all necessary sub-configs
                    self.available_processors[processor_name] = processor_map[processor_name](config=processor_config)
                    self.logger.info(f"Initialized {processor_name} PDF processor.")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize {processor_name} PDF processor: {e}")
            else:
                self.logger.warning(f"Unknown PDF processor '{processor_name}' specified in config.")

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document based on the configured strategy."""
        self.logger.info(f"Processing PDF with strategy '{self.processor_strategy}': {document.get('metadata', {}).get('filename', 'unknown')}")

        if self.processor_strategy == 'exclusive':
            processor_name = self.default_processor
            processor = self.available_processors.get(processor_name)
            if processor:
                self.logger.info(f"Using exclusive processor: {processor_name}")
                return processor.process(document)
            else:
                error_msg = f"Exclusive processor '{processor_name}' is not active or failed to initialize."
                self.logger.error(error_msg)
                document['error'] = error_msg
                return document

        elif self.processor_strategy == 'fallback_chain':
            # The fallback chain includes Docling implicitly if it's active
            chain = [p for p in self.active_processors if p in self.available_processors]
            if not chain:
                 error_msg = "No active or available PDF processors for fallback chain."
                 self.logger.error(error_msg)
                 document['error'] = error_msg
                 return document

            self.logger.info(f"Using fallback chain: {chain}")
            last_error = None
            for processor_name in chain:
                processor = self.available_processors[processor_name] # We know it's available from chain construction
                self.logger.info(f"Attempting processor in fallback chain: {processor_name}")
                processed_document = processor.process(document.copy()) # Process a copy to avoid modifying original on failure
                if 'error' not in processed_document:
                    self.logger.info(f"Processor {processor_name} succeeded.")
                    return processed_document # Success, return the result
                else:
                    last_error = processed_document['error']
                    self.logger.warning(f"Processor {processor_name} failed: {last_error}. Trying next in chain.")

            # If we reach here, all processors in the chain failed
            error_msg = f"All processors in fallback chain failed. Last error: {last_error}"
            self.logger.error(error_msg)
            document['error'] = error_msg
            return document

        else:
            error_msg = f"Unknown PDF processor strategy: {self.processor_strategy}"
            self.logger.error(error_msg)
            document['error'] = error_msg
            return document
