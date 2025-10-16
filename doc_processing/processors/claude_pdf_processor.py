"""Processor using Claude (Anthropic) for direct PDF processing with native PDF support."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from doc_processing.embedding.base import BaseProcessor
from doc_processing.config import get_settings
from doc_processing.templates.prompt_manager import PromptTemplateManager

logger = logging.getLogger(__name__)

class ClaudePDFProcessor(BaseProcessor):
    """
    Processor that uses Claude's native PDF processing capabilities.

    Advantages over image-based processing:
    - Direct PDF input (no image conversion needed)
    - Better text extraction (can access PDF text layer)
    - Cheaper (processes whole document in one API call)
    - Faster (no per-page processing)
    - Better context understanding (sees full document structure)

    Claude Pricing (as of 2024):
    - Claude 3.5 Sonnet: $3 input / $15 output per million tokens
    - Claude 3 Opus: $15 input / $75 output per million tokens
    - Recommended: Sonnet for best quality/cost ratio
    """

    DEFAULT_PROMPT = """Extract all text content from this PDF document. Maintain the document structure, including:
- Headings and sections
- Paragraphs and lists
- Tables (format as markdown tables)
- Figure captions and references
- Page breaks (indicate with ---PAGE BREAK---)

Provide clean, accurate transcription of all text."""

    DEFAULT_TEMPLATE_DIR = get_settings().TEMPLATE_DIR

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Claude PDF processor."""
        super().__init__(config)
        self.settings = get_settings()

        # Initialize Claude client
        self.claude_client = None
        try:
            from doc_processing.llm.anthropic_client import AnthropicClient

            self.claude_client = AnthropicClient(
                api_key=self.config.get('api_key', self.settings.ANTHROPIC_API_KEY),
                model_name=self.config.get('model_name', 'claude-sonnet-4-20250514'),
                config=self.config.get('llm_client_config')
            )
            logger.info(f"Initialized Claude PDF processor with model: {self.claude_client.get_model_name()}")
        except ImportError:
            logger.error("AnthropicClient not available. Install 'anthropic' package.")
            self.claude_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
            self.claude_client = None

        # Prompt configuration
        self.prompt_name = self.config.get('prompt_name')
        self.prompt_template_path = self.config.get('prompt_template')
        template_dir = self.config.get('template_dir', self.DEFAULT_TEMPLATE_DIR)
        self.template_manager = PromptTemplateManager(template_dir)

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a PDF document using Claude's native PDF support.

        Args:
            document: Document dictionary with 'source_path' key pointing to PDF file

        Returns:
            Document dictionary with extracted content
        """
        if not self.claude_client:
            logger.error("Claude client not initialized. Cannot process PDF.")
            document['error'] = "ClaudePDFProcessor: Claude client not initialized."
            return document

        source_path = document.get('source_path')
        if not source_path:
            logger.error("No source_path found in document.")
            document['error'] = "ClaudePDFProcessor: No source_path provided."
            return document

        pdf_path = Path(source_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            document['error'] = f"ClaudePDFProcessor: PDF file not found: {pdf_path}"
            return document

        logger.info(f"Processing PDF with Claude: {pdf_path.name}")
        start_time = time.time()

        try:
            # Prepare prompt
            prompt_context = {
                'document_metadata': document.get('metadata', {}),
                'filename': pdf_path.name
            }

            # Determine template to use
            template_to_use = None
            if self.prompt_name:
                template_to_use = f"{self.prompt_name}.j2"
            elif self.prompt_template_path:
                template_to_use = self.prompt_template_path

            # Render prompt from template or use default
            if template_to_use:
                try:
                    prompt = self.template_manager.render_template(
                        template_to_use,
                        **prompt_context
                    )
                    logger.debug(f"Using template prompt: {template_to_use}")
                except Exception as e:
                    logger.warning(f"Failed to load template {template_to_use}: {e}. Using default prompt.")
                    prompt = self.DEFAULT_PROMPT
            else:
                prompt = self.DEFAULT_PROMPT
                logger.debug("Using default PDF extraction prompt")

            # Get system prompt from config
            system_prompt = self.config.get('system_prompt',
                "You are an expert document extraction assistant. Extract text accurately while preserving structure and formatting.")

            # Process PDF with Claude
            logger.info("Sending PDF to Claude for processing...")
            extracted_text = self.claude_client.process_pdf(
                pdf_path=str(pdf_path),
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=self.config.get('max_tokens', 4096),
                temperature=self.config.get('temperature', 0.1)
            )

            processing_time = time.time() - start_time
            logger.info(f"Claude PDF processing completed in {processing_time:.2f}s")

            # Update document with extracted content
            document['content'] = extracted_text
            document['metadata']['processing_method'] = 'claude_pdf'
            document['metadata']['processing_time_seconds'] = processing_time
            document['metadata']['model_used'] = self.claude_client.get_model_name()
            document['metadata']['num_characters'] = len(extracted_text)

            # Extract basic page info if possible
            # Claude's response might include page markers if prompted
            if '---PAGE BREAK---' in extracted_text or 'Page ' in extracted_text:
                pages = []
                # Simple page splitting (can be enhanced)
                page_sections = extracted_text.split('---PAGE BREAK---')
                for i, section in enumerate(page_sections):
                    if section.strip():
                        pages.append({
                            'page_number': i + 1,
                            'text': section.strip()
                        })
                document['pages'] = pages
                document['metadata']['num_pages'] = len(pages)
            else:
                # Single page or no clear page markers
                document['pages'] = [{
                    'page_number': 1,
                    'text': extracted_text
                }]

            logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
            return document

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Claude PDF processing failed after {processing_time:.2f}s: {e}")
            document['error'] = f"ClaudePDFProcessor error: {str(e)}"
            document['metadata']['processing_method'] = 'claude_pdf_failed'
            document['metadata']['processing_time_seconds'] = processing_time
            return document
