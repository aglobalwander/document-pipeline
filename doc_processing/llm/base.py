"""Base class for Large Language Model (LLM) clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional # Added List

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM client.

        Args:
            api_key: The API key for the LLM provider.
            model_name: The default model name to use.
            config: Additional configuration options.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    def generate_completion(self, prompt: str, **kwargs) -> str:
        """
        Generate a text completion for a given prompt.

        Args:
            prompt: The input prompt string.
            **kwargs: Additional provider-specific arguments (e.g., temperature, max_tokens).

        Returns:
            The generated text completion.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
            Exception: For API errors or other issues.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_structured_output(self, prompt: str, output_schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Generate structured output (e.g., JSON) based on a prompt and schema.
        Not all providers might support this directly; implementations might use generate_completion
        with specific prompting techniques.

        Args:
            prompt: The input prompt string.
            output_schema: A dictionary representing the desired output structure (e.g., JSON schema).
            **kwargs: Additional provider-specific arguments.

        Returns:
            A dictionary containing the structured output.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
            Exception: For API errors or other issues.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_multimodal_completion(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Generate a text completion based on multimodal input (e.g., text and images).

        Args:
            messages: A list of message objects, potentially including image data
                      in a format specific to the provider's API.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The generated text completion.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
            Exception: For API errors or other issues.
        """
        raise NotImplementedError

    def get_model_name(self) -> Optional[str]:
        """Returns the configured model name."""
        return self.model_name