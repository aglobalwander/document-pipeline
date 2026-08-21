"""Document structure extractor using provider-native structured output."""
from typing import Any, Dict, List, Optional, Type, TypeVar
import logging
from pydantic import BaseModel

from doc_processing.embedding.base import BaseTransformer
from doc_processing.config import get_settings
# Import the new LLM client base and implementation
from doc_processing.llm.base import BaseLLMClient
from doc_processing.llm.clients import DeepSeekClient, KimiClient, OpenAIClient

# Define the type variable for the response model
T = TypeVar('T', bound=BaseModel)

class InstructorExtractor(BaseTransformer):
    """Extract structured data; the legacy class name is kept for compatibility."""
    
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
        # Remote structured extraction is always an explicit paid API choice.
        llm_provider = self.config.get('llm_provider')
        llm_model = self.config.get('llm_model') # Let client use its default if not specified

        if not llm_provider:
            self.logger.error(
                "Structured extraction requires an explicit llm_provider; "
                "subscription CLIs are interactive tools, not pipeline credentials."
            )
        elif llm_provider == 'openai':
            self.llm_client = OpenAIClient(
                api_key=self.config.get('api_key', self.settings.OPENAI_API_KEY or self.settings.OPENAI_APIKEY),
                model_name=llm_model,
                config=self.config.get('llm_client_config')
            )
        elif llm_provider in {'deepseek', 'dashscope', 'dashscope_deepseek'}:
            route = 'dashscope' if llm_provider in {'dashscope', 'dashscope_deepseek'} else self.config.get('deepseek_route', 'deepseek')
            client_config = dict(self.config.get('llm_client_config') or {})
            client_config.setdefault('route', route)
            api_key = self.config.get('api_key')
            if not api_key:
                api_key = self.settings.DASHSCOPE_API_KEY if route == 'dashscope' else self.settings.DEEPSEEK_API_KEY
            self.llm_client = DeepSeekClient(
                api_key=api_key,
                model_name=llm_model,
                config=client_config,
            )
        elif llm_provider in {'kimi', 'moonshot'}:
            self.llm_client = KimiClient(
                api_key=self.config.get('api_key'),
                model_name=llm_model,
                config=self.config.get('llm_client_config'),
            )
        elif llm_provider == 'anthropic':
            from doc_processing.llm.anthropic_client import AnthropicClient
            self.llm_client = AnthropicClient(
                api_key=self.config.get('api_key', self.settings.ANTHROPIC_API_KEY),
                model_name=llm_model,
                config=self.config.get('llm_client_config'),
            )
        elif llm_provider == 'gemini':
            from doc_processing.llm.gemini_client import GeminiClient
            self.llm_client = GeminiClient(
                api_key=self.config.get(
                    'api_key',
                    self.settings.GEMINI_API_KEY or self.settings.GOOGLE_API_KEY,
                ),
                model_name=llm_model,
                config=self.config.get('llm_client_config'),
            )
        else:
            self.logger.error(
                "InstructorExtractor supports openai, anthropic, gemini, deepseek, dashscope, and kimi; "
                "received %r.",
                llm_provider,
            )
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
             document['error'] = "Structured extractor: LLM client not initialized."
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
