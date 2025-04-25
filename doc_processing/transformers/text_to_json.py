"""Transform text documents to structured JSON format."""
import json
import re
from typing import Any, Dict, List, Optional, Union
import logging
from pathlib import Path
import jinja2
import requests
import os

from doc_processing.embedding.base import BaseTransformer
from doc_processing.templates.prompt_manager import PromptTemplateManager
from doc_processing.config import get_settings
# Import the new LLM client base and implementation
from doc_processing.llm.base import BaseLLMClient
from doc_processing.llm.clients import OpenAIClient

class TextToJSON(BaseTransformer):
    """Transform text documents to structured JSON format."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize transformer.
        
        Args:
            config: Configuration options
        """
        super().__init__(config)
        self.settings = get_settings()
        
        # Get template manager
        # Use the correct template directory for prompts
        template_dir = self.config.get('template_dir', self.settings.TEMPLATE_DIR)
        self.template_manager = PromptTemplateManager(template_dir)
        
        # JSON configuration
        self.json_schema = self.config.get('json_schema', None)
        self.use_llm = self.config.get('use_llm', True) # Keep flag to enable/disable LLM use
        self.schema_prompt_template = self.config.get('schema_prompt_template', 'json_extraction.j2')

        # LLM Client Initialization
        self.llm_client: Optional[BaseLLMClient] = None
        if self.use_llm:
            # Determine provider (default to openai for now)
            llm_provider = self.config.get('llm_provider', 'openai')
            llm_model = self.config.get('llm_model') # Let client use its default if not specified

            # Instantiate the client (add more providers later)
            if llm_provider == 'openai':
                self.llm_client = OpenAIClient(
                    api_key=self.config.get('api_key', self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY),
                    model_name=llm_model,
                    config=self.config.get('llm_client_config') # Pass specific client config if needed
                )
            else:
                self.logger.warning(f"Unsupported LLM provider specified: {llm_provider}. LLM extraction disabled.")
                self.use_llm = False # Disable LLM if provider is wrong
    
    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform text document to JSON.
        
        Args:
            document: Document to transform
            
        Returns:
            Document with added JSON content
        """
        if not document.get('content'):
            self.logger.warning(f"Document has no content to transform")
            document['json'] = {}
            return document
        
        try:
            content = document.get('content', '')
            
            # Transform to JSON
            if self.use_llm and self.llm_client: # Check if client was successfully initialized
                # Use LLM to extract structured data
                json_data = self._extract_with_llm(document)
            else:
                if self.use_llm and not self.llm_client:
                    self.logger.warning("LLM extraction requested but client failed to initialize (check API key/provider). Falling back to rules.")
                # Use rule-based extraction
                json_data = self._extract_with_rules(document)
            
            # Add JSON to document
            document['json'] = json_data
            
            # Save to file if output_path is provided
            output_path = self.config.get('output_path')
            if output_path:
                self._save_json(json_data, output_path, document)
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error transforming document to JSON: {str(e)}")
            document['error'] = f"JSON transformation error: {str(e)}"
            document['json'] = {}
            return document
    
    def _extract_with_llm(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data using LLM.
        
        Args:
            document: Document to extract from
            
        Returns:
            Structured JSON data
            
        Raises:
            Exception: If error extracting data
        """
        try:
            content = document.get('content', '')
            
            # Prepare prompt with schema
            schema_str = json.dumps(self.json_schema) if self.json_schema else "Extract the main information from the text into a structured JSON format."
            
            # Render prompt template
            try:
                prompt = self.template_manager.render_prompt(
                    self.schema_prompt_template, 
                    {
                        'content': content,
                        'schema': schema_str,
                        'document': document
                    }
                )
            except jinja2.exceptions.TemplateNotFound:
                # Fallback if template not found
                self.logger.warning(f"JSON schema prompt template not found: {self.schema_prompt_template}")
                prompt = f"""Extract the structured information from the following text into JSON format. 
                
{schema_str}

TEXT:
{content[:5000]}  # Limit content length
"""
            
            # Call the LLM client's structured output method
            # Pass the schema dictionary directly
            json_output = self.llm_client.generate_structured_output(
                prompt=prompt,
                output_schema=self.json_schema or {}, # Pass schema or empty dict
                # Pass other relevant kwargs from config if needed
                temperature=self.config.get('temperature', 0.2),
                max_tokens=self.config.get('max_tokens', 4000)
            )
            return json_output

        except Exception as e:
            self.logger.error(f"Error extracting JSON with LLM client: {str(e)}")
            raise

    # Removed _call_openai_api and _parse_json_from_result methods as they are now handled by the LLM client
    
    def _extract_with_rules(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data using rule-based approach.
        
        Args:
            document: Document to extract from
            
        Returns:
            Structured JSON data
        """
        content = document.get('content', '')
        metadata = document.get('metadata', {})
        
        # Basic metadata extraction
        result = {
            "document_id": document.get('id', None),
            "title": metadata.get('title') or self._extract_title(content),
            "source": metadata.get('source', None),
            "metadata": metadata
        }
        
        # Extract sections if document has been processed with section extraction
        if 'sections' in document:
            result['sections'] = [
                {
                    "heading": section.get('heading', {}).get('text', 'Untitled Section'),
                    "level": section.get('heading', {}).get('level', 0),
                    "content_summary": section.get('content', '')[:200] + '...' if len(section.get('content', '')) > 200 else section.get('content', '')
                }
                for section in document['sections']
            ]
        
        return result
    
    def _extract_title(self, content: str) -> str:
        """Extract title from content text.
        
        Args:
            content: Document content
            
        Returns:
            Extracted title or default
        """
        lines = content.strip().split('\n')
        
        # Use first non-empty line as title
        for line in lines[:10]:  # Check first 10 lines
            if line.strip():
                # Limit length for title
                title = line.strip()
                if len(title) > 80:
                    title = title[:77] + '...'
                return title
        
        return "Untitled Document"
    
    def _save_json(self, json_data: Dict[str, Any], output_path: Union[str, Path], document: Dict[str, Any]) -> None:
        """Save JSON to file.
        
        Args:
            json_data: JSON data to save
            output_path: Path to save file
            document: Original document
            
        Raises:
            Exception: If error saving file
        """
        try:
            # If output_path is a directory, create a filename
            path = Path(output_path)
            
            if path.is_dir():
                # Generate filename from document metadata
                if 'metadata' in document and 'filename' in document['metadata']:
                    filename = Path(document['metadata']['filename']).stem + '.json'
                else:
                    filename = f"document_{document.get('id', 'untitled')}.json"
                path = path / filename
            
            # Make sure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Saved JSON to {path}")
            
        except Exception as e:
            self.logger.error(f"Error saving JSON file: {str(e)}")
            raise