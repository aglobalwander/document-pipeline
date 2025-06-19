"""Processor using GPT-4 Vision (or other multimodal LLMs) for OCR and analysis."""

import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests # Keep requests for potential direct image fetching if needed
from tqdm import tqdm  # Import tqdm for progress bar

from doc_processing.embedding.base import BaseProcessor # Corrected import path
from doc_processing.config import get_settings
from doc_processing.llm.base import BaseLLMClient
from doc_processing.llm.clients import OpenAIClient # Default client
# Removed GeminiClient import
from doc_processing.templates.prompt_manager import PromptTemplateManager

logger = logging.getLogger(__name__)

class GPTPVisionProcessor(BaseProcessor):
    """
    Processor that uses a multimodal LLM (like GPT-4 Vision) via the LLM Client
    abstraction to extract text content from images (e.g., pages of a PDF).
    """

    DEFAULT_PROMPT = "Describe the content of this image in detail. If it contains text, transcribe the text accurately."
    DEFAULT_TEMPLATE_DIR = get_settings().TEMPLATE_DIR

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the processor."""
        super().__init__(config)
        self.settings = get_settings()
        
        # Progress bar configuration
        self.show_progress_bar = self.config.get('show_progress_bar', True)

        # LLM Client Initialization
        self.llm_client: Optional[BaseLLMClient] = None
        llm_provider = self.config.get('llm_provider', 'openai') # Default to OpenAI
        # Use specific vision model from config or client's default
        llm_model = self.config.get('vision_model', self.config.get('llm_model'))

        # Instantiate the client (add more providers later)
        if llm_provider == 'openai':
            self.llm_client = OpenAIClient(
                api_key=self.config.get('api_key', self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY),
                model_name=llm_model, # Pass the specific vision model if provided
                config=self.config.get('llm_client_config')
            )
        # Removed GeminiClient initialization block
        # Add elif blocks here for other providers (Anthropic) when their clients are implemented
        else:
             # Handle non-OpenAI providers if this processor is mistakenly called for them
             if llm_provider != 'openai':
                  logger.warning(f"GPTPVisionProcessor received unsupported provider '{llm_provider}'. Only 'openai' is currently handled for page-image processing.")
             else: # Should not happen if logic is correct, but good to log
                  logger.error(f"Failed to initialize OpenAIClient for unknown reasons.")
             self.llm_client = None # Ensure client is None

        # Prompt configuration - prioritize prompt_name if provided
        self.prompt_name = self.config.get('prompt_name') # e.g., 'invoice_extraction'
        # Fallback to specific template path if prompt_name not given
        self.prompt_template_path = self.config.get('prompt_template') # e.g., 'pdf_extraction.j2'
        template_dir = self.config.get('template_dir', self.DEFAULT_TEMPLATE_DIR)
        self.template_manager = PromptTemplateManager(template_dir)


    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document pages (images) using the configured multimodal LLM.

        Expects document['pages'] to contain a list of dictionaries,
        each with an 'image_path' or 'image_base64' key.

        Args:
            document: The document dictionary.

        Returns:
            The document dictionary with extracted text added to page content.
        """
        if not self.llm_client:
            logger.error("LLM client not initialized. Cannot perform GPT Vision processing.")
            document['error'] = "GPTPVisionProcessor: LLM client not initialized."
            return document

        if 'pages' not in document or not isinstance(document['pages'], list):
            logger.warning("No 'pages' found in document or 'pages' is not a list. Skipping GPT Vision processing.")
            return document

        extracted_content = []
        total_pages = len(document['pages'])
        start_time = time.time()
        processing_times = []
        
        logger.info(f"Starting GPT Vision processing for {total_pages} pages...")
        
        # Create progress bar if enabled
        progress_bar = None
        if self.show_progress_bar:
            progress_bar = tqdm(total=total_pages, desc="Processing PDF pages", unit="page")
        
        for i, page_data in enumerate(document['pages']):
            page_num = i + 1
            page_start_time = time.time()
            
            # Calculate progress percentage
            progress_pct = (i / total_pages) * 100 if total_pages > 0 else 0
            
            # Calculate estimated time remaining if we have processed at least one page
            eta_str = ""
            if i > 0 and processing_times:
                avg_time_per_page = sum(processing_times) / len(processing_times)
                eta_seconds = avg_time_per_page * (total_pages - i)
                eta_min = int(eta_seconds // 60)
                eta_sec = int(eta_seconds % 60)
                eta_str = f", ETA: {eta_min}m {eta_sec}s"
            
            logger.info(f"Processing page {page_num}/{total_pages} ({progress_pct:.1f}%{eta_str}) with {self.llm_client.__class__.__name__}...")
            try:
                image_base64 = self._get_image_base64(page_data)
                if not image_base64:
                    logger.warning(f"Could not get base64 image for page {i+1}. Skipping.")
                    extracted_content.append(f"[Page {i+1} Image Error]")
                    
                    # Update progress bar for skipped pages if enabled
                    if progress_bar:
                        progress_bar.update(1)
                        progress_bar.set_postfix({"Status": "Image Error"})
                    continue

                # Prepare prompt context
                prompt_context = {
                    'page_number': i + 1,
                    'document_metadata': document.get('metadata', {}),
                    # Add other relevant context if needed
                }

                # Determine template name to use
                template_to_use = None
                if self.prompt_name:
                    template_to_use = f"{self.prompt_name}.j2" # Construct filename from name
                    logger.debug(f"Using prompt_name to look for template: {template_to_use}")
                elif self.prompt_template_path:
                    template_to_use = self.prompt_template_path # Use direct path if name not given
                    logger.debug(f"Using specific prompt_template path: {template_to_use}")

                # Render prompt using the determined template or default
                if template_to_use:
                    try:
                        prompt_text = self.template_manager.render_prompt(
                            template_to_use,
                            prompt_context
                        )
                        logger.info(f"Successfully rendered prompt from template: {template_to_use}")
                    except Exception as e:
                        logger.warning(f"Failed to render prompt template '{template_to_use}': {e}. Using default prompt.")
                        prompt_text = self.DEFAULT_PROMPT
                else:
                    logger.debug("No prompt_name or prompt_template provided. Using default prompt.")
                    prompt_text = self.DEFAULT_PROMPT

                # Construct payload for multimodal input (specific to client/API)
                # This part needs refinement based on how BaseLLMClient handles multimodal
                # For OpenAI, it expects a specific message format with image URLs/base64
                # We might need to adapt BaseLLMClient or handle it here for now.
                # Assuming OpenAIClient's generate_completion can be adapted or a new method is added.
                # Placeholder: Adapt this when client capabilities are clearer.

                # --- OpenAI Specific Example ---
                if isinstance(self.llm_client, OpenAIClient):
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                                }
                            ]
                        }
                    ]
                    # Call the client's multimodal method
                    page_text = self.llm_client.generate_multimodal_completion(
                        messages=messages,
                        max_tokens=self.config.get('max_tokens', 3000) # Pass relevant kwargs
                        # Add temperature etc. if needed from config
                    )
                    # Record processing time for this page
                    page_end_time = time.time()
                    page_duration = page_end_time - page_start_time
                    processing_times.append(page_duration)
                    
                    # Log completion with timing information
                    logger.info(f"Completed page {page_num}/{total_pages} in {page_duration:.2f}s")
                    
                    # Update progress bar if enabled
                    if progress_bar:
                        progress_bar.update(1)
                        progress_bar.set_postfix({"Time/page": f"{page_duration:.2f}s"})
                    
                    extracted_content.append(page_text)
                # --- End OpenAI Specific Handling ---
                # Removed Gemini specific handling block as it's handled natively in HybridPDFProcessor
                else:
                     # Fallback for potential future non-OpenAI clients needing image processing
                     if self.llm_client: # Check if client exists before accessing class name
                          logger.warning(f"Page-image based multimodal processing not implemented for {self.llm_client.__class__.__name__}. Skipping page {i+1}.")
                     else:
                          # This case should ideally not be reached if init logic is correct
                           logger.error(f"LLM client is None during page processing. Skipping page {i+1}.")
                     
                     # Update progress bar for unsupported client if enabled
                     if progress_bar:
                         progress_bar.update(1)
                         progress_bar.set_postfix({"Status": "Unsupported Client"})
                     
                     extracted_content.append(f"[Page {i+1} LLM Not Supported/Initialized]")


            except Exception as e:
                logger.error(f"Error processing page {i+1} with vision model: {e}")
                extracted_content.append(f"[Page {i+1} Processing Error: {e}]")
                
                # Update progress bar even on error if enabled
                if progress_bar:
                    progress_bar.update(1)
                    progress_bar.set_postfix({"Status": "Error"})

        # Close the progress bar if enabled
        if progress_bar:
            progress_bar.close()
        
        # Calculate and log total processing time
        total_time = time.time() - start_time
        avg_time_per_page = total_time / total_pages if total_pages > 0 else 0
        logger.info(f"Completed processing {total_pages} pages in {total_time:.2f}s (avg: {avg_time_per_page:.2f}s per page)")
        
        # Combine extracted text (consider adding page breaks)
        full_content = "\n\n--- Page Break ---\n\n".join(extracted_content)

        # Add or append to document content
        if 'content' in document and document['content']:
            document['content'] += "\n\n--- Vision Extracted Content ---\n\n" + full_content
        else:
            document['content'] = full_content

        # Update processing method info
        document['processing_method'] = document.get('processing_method', '') + '+GPTPVision'
        return document

    def _get_image_base64(self, page_data: Dict[str, Any]) -> Optional[str]:
        """Gets the base64 encoded image from page data."""
        if 'image_base64' in page_data:
            return page_data['image_base64']
        elif 'image_path' in page_data:
            try:
                img_path = Path(page_data['image_path'])
                if img_path.is_file():
                    with open(img_path, "rb") as image_file:
                        return base64.b64encode(image_file.read()).decode('utf-8')
                else:
                    logger.warning(f"Image path does not exist: {img_path}")
                    return None
            except Exception as e:
                logger.error(f"Error reading image file {page_data.get('image_path')}: {e}")
                return None
        else:
            logger.warning("Page data missing 'image_base64' or 'image_path'.")
            return None

    # Removed _call_openai_vision_directly placeholder method
