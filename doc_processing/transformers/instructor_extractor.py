"""Document structure extractor using Instructor."""
from typing import Any, Dict, List, Optional, Type, TypeVar
import logging
from pydantic import BaseModel

from doc_processing.embedding.base import BaseTransformer
from doc_processing.config import get_settings
# Import the new LLM client base and implementation
from doc_processing.llm.base import BaseLLMClient
from doc_processing.llm.clients import OpenAIClient # Default client

# Define the type variable for the response model
T = TypeVar('T', bound=BaseModel)

class InstructorExtractor(BaseTransformer):
    """Extract structured data from documents using Instructor."""
    
    def __init__(self, response_model: Type[BaseModel], config: Optional[Dict[str, Any]] = None):
        """Initialize with Pydantic response model.
        
        Args:
            response_model: Pydantic model for validation
            config: Configuration options
        """
        super().__init__(config)
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Response model
        self.response_model = response_model
        
        # LLM Client Initialization
        self.llm_client: Optional[BaseLLMClient] = None
        # Determine provider (default to openai as Instructor primarily works with it)
        llm_provider = self.config.get('llm_provider', 'openai')
        llm_model = self.config.get('llm_model') # Let client use its default if not specified

        if llm_provider == 'openai':
            self.llm_client = OpenAIClient(
                api_key=self.config.get('api_key', self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY),
                model_name=llm_model,
                config=self.config.get('llm_client_config')
            )
        else:
            self.logger.error(f"InstructorExtractor currently only supports 'openai' provider, but '{llm_provider}' was configured.")
            # Optionally raise an error or disable functionality

        # Store parameters for the call
        self.temperature = self.config.get('temperature', 0.2)
        self.max_tokens = self.config.get('max_tokens', 4000)
        self.system_prompt = self.config.get('system_prompt',
            "You are an expert document analyzer. Extract structured information from the document content provided by the user. "
            "Pay attention to details and organize the information accurately according to the requested format."
        )
    
    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform document content to structured data.
        
        Args:
            document: Document to extract from
            
        Returns:
            Document with added structured data
        """
        if not document.get('content'):
            self.logger.warning(f"Document has no content to extract from")
            return document
        
        if not self.llm_client:
             self.logger.error("LLM client not initialized. Cannot perform structured extraction.")
             document['error'] = "InstructorExtractor: LLM client not initialized."
             return document

        try:
            content = document.get('content', '')
            # Limit content length passed to the prompt
            max_content_length = self.config.get('max_prompt_content_length', 100000)
            prompt_content = content[:max_content_length]

            self.logger.info(f"Extracting structured data using {self.response_model.__name__} via {self.llm_client.__class__.__name__}")

            # Call the LLM client's structured output method, passing the Pydantic model type
            structured_data_dict = self.llm_client.generate_structured_output(
                prompt=prompt_content,
                output_schema=self.response_model, # Pass the Pydantic model type directly
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                # Pass other relevant kwargs if needed
            )

            # Add structured data to document
            document['structured_data'] = structured_data_dict
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error extracting structured data: {str(e)}")
            document['error'] = f"Structured extraction error: {str(e)}"
            return document