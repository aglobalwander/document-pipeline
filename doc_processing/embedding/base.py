"""Base classes for document processing pipeline."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseDocumentLoader(ABC):
    """Base class for all document loaders."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load document from source.
        
        Args:
            source: Path to document or document content
            
        Returns:
            Dictionary containing document content and metadata
        """
        pass
    
    def validate_source(self, source: Union[str, Path]) -> Path:
        """Validate source path exists.
        
        Args:
            source: Path to document
            
        Returns:
            Validated Path object
            
        Raises:
            FileNotFoundError: If source path does not exist
        """
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Source path does not exist: {path}")
        return path


class BaseProcessor(ABC):
    """Base class for all document processors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process document content.
        
        Args:
            document: Dictionary containing document content and metadata
            
        Returns:
            Processed document with updated content and metadata
        """
        pass


class BaseTransformer(ABC):
    """Base class for all document transformers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform document content.
        
        Args:
            document: Dictionary containing document content and metadata
            
        Returns:
            Transformed document with updated content and metadata
        """
        pass


class PipelineComponent:
    """Wrapper for pipeline components with pre and post processing hooks."""
    
    def __init__(self, component: Union[BaseDocumentLoader, BaseProcessor, BaseTransformer]):
        self.component = component
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def pre_process(self, data: Any) -> Any:
        """Hook for pre-processing data before passing to component."""
        return data
    
    def post_process(self, data: Any) -> Any:
        """Hook for post-processing data after component processing."""
        return data
    
    def execute(self, data: Any) -> Any:
        """Execute component with pre and post processing."""
        self.logger.debug(f"Executing {self.component.__class__.__name__}")
        pre_processed = self.pre_process(data)
        
        if isinstance(self.component, BaseDocumentLoader):
            result = self.component.load(pre_processed)
        elif isinstance(self.component, BaseProcessor):
            result = self.component.process(pre_processed)
        elif isinstance(self.component, BaseTransformer):
            result = self.component.transform(pre_processed)
        else:
            raise TypeError(f"Unsupported component type: {type(self.component)}")
        
        return self.post_process(result)


class Pipeline:
    """Pipeline for processing documents through a series of components."""
    
    def __init__(self, components: List[PipelineComponent] = None):
        self.components = components or []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def add_component(self, component: Union[BaseDocumentLoader, BaseProcessor, BaseTransformer]) -> 'Pipeline':
        """Add component to pipeline.
        
        Args:
            component: Pipeline component
            
        Returns:
            Self for method chaining
        """
        self.components.append(PipelineComponent(component))
        return self
        
    def run(self, source: Any) -> Dict[str, Any]:
        """Run pipeline on source.
        
        Args:
            source: Input source for first component
            
        Returns:
            Processed document
        """
        self.logger.info(f"Running pipeline with {len(self.components)} components")
        result = source
        
        for component in self.components:
            result = component.execute(result)
            
        return result
class BaseEmbedding(ABC):
    """Base class for embedding models."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        pass