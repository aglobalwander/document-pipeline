"""Schema management for Weaviate document classes."""
import json
from typing import Any, Dict, List, Optional, Union
import logging
from pathlib import Path

from doc_processing.config import get_settings
from doc_processing.embedding.weaviate_client import WeaviateClient

class SchemaManager:
    """Manage Weaviate schema definitions."""
    
    def __init__(self, weaviate_client: Optional[WeaviateClient] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize schema manager.
        
        Args:
            weaviate_client: Weaviate client instance (optional)
            config: Configuration options (optional)
        """
        self.settings = get_settings()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize Weaviate client if not provided
        if weaviate_client:
            self.client = weaviate_client
        else:
            self.client = WeaviateClient(self.config)
    
    def create_document_schema(self, 
                             class_name: str,
                             description: str,
                             properties: List[Dict[str, Any]],
                             vectorizer: str = "text2vec-openai") -> Dict[str, Any]:
        """Create document schema definition.
        
        Args:
            class_name: Class name for the schema
            description: Description of the class
            properties: List of property definitions
            vectorizer: Vectorizer module to use
            
        Returns:
            Schema definition
        """
        schema = {
            "class": class_name,
            "description": description,
            "vectorizer": vectorizer,
            "properties": properties,
            "moduleConfig": {
                "text2vec-openai": {
                    "model": "text-embedding-ada-002",
                    "modelVersion": "002",
                    "type": "text"
                }
            }
        }
        
        self.logger.info(f"Created schema definition for class {class_name}")
        return schema
    
    def create_property(self, 
                       name: str, 
                       data_type: List[str], 
                       description: str,
                       tokenization: str = "word",
                       index: bool = True,
                       vectorize: bool = True) -> Dict[str, Any]:
        """Create property definition for schema.
        
        Args:
            name: Property name
            data_type: List of data types
            description: Description of property
            tokenization: Tokenization method
            index: Whether to index the property
            vectorize: Whether to include in vectorization
            
        Returns:
            Property definition
        """
        property_def = {
            "name": name,
            "dataType": data_type,
            "description": description,
            "tokenization": tokenization,
            "indexSearchable": index,
            "indexFilterable": index,
            "moduleConfig": {
                "text2vec-openai": {
                    "skip": not vectorize,
                    "vectorizePropertyName": False
                }
            }
        }
        
        return property_def
    
    def create_reference_property(self, 
                                name: str, 
                                target_class: str, 
                                description: str) -> Dict[str, Any]:
        """Create reference property definition for schema.
        
        Args:
            name: Property name
            target_class: Target class name
            description: Description of property
            
        Returns:
            Reference property definition
        """
        property_def = {
            "name": name,
            "dataType": ["cref"],
            "description": description,
            "moduleConfig": {
                "text2vec-openai": {
                    "skip": True
                }
            },
            "reference": {
                "type": "cref",
                "target": [target_class]
            }
        }
        
        return property_def
    
    def register_schema(self, schema: Dict[str, Any]) -> None:
        """Register schema with Weaviate.
        
        Args:
            schema: Schema definition
            
        Raises:
            Exception: If error registering schema
        """
        try:
            # Check if class already exists
            class_name = schema.get('class')
            if self.client.class_exists(class_name):
                self.logger.warning(f"Class {class_name} already exists. Skipping...")
                return
            
            # Create class
            self.client.create_class(schema)
            self.logger.info(f"Registered schema for class {class_name}")
            
        except Exception as e:
            self.logger.error(f"Error registering schema: {str(e)}")
            raise
    
    def save_schema_to_file(self, schema: Dict[str, Any], file_path: Union[str, Path]) -> None:
        """Save schema definition to file.
        
        Args:
            schema: Schema definition
            file_path: Path to save file
            
        Raises:
            Exception: If error saving file
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2)
                
            self.logger.info(f"Saved schema to {path}")
            
        except Exception as e:
            self.logger.error(f"Error saving schema to file: {str(e)}")
            raise
    
    def load_schema_from_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load schema definition from file.
        
        Args:
            file_path: Path to schema file
            
        Returns:
            Schema definition
            
        Raises:
            Exception: If error loading file
        """
        try:
            path = Path(file_path)
            
            with open(path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
                
            self.logger.info(f"Loaded schema from {path}")
            return schema
            
        except Exception as e:
            self.logger.error(f"Error loading schema from file: {str(e)}")
            raise
    
    def create_document_schema_for_text(self, class_name: str, description: str) -> Dict[str, Any]:
        """Create standard schema for text documents.
        
        Args:
            class_name: Class name for the schema
            description: Description of the class
            
        Returns:
            Schema definition
        """
        properties = [
            self.create_property(
                name="content",
                data_type=["text"],
                description="Full document content",
                vectorize=True
            ),
            self.create_property(
                name="title",
                data_type=["text"],
                description="Document title",
                vectorize=True
            ),
            self.create_property(
                name="source",
                data_type=["text"],
                description="Source of the document",
                vectorize=False
            ),
            self.create_property(
                name="source_type",
                data_type=["text"],
                description="Type of source (pdf, text, markdown, etc.)",
                vectorize=False
            ),
            self.create_property(
                name="created_at",
                data_type=["date"],
                description="Creation date",
                vectorize=False
            ),
            self.create_property(
                name="updated_at",
                data_type=["date"],
                description="Last update date",
                vectorize=False
            ),
            self.create_property(
                name="metadata",
                data_type=["object"],
                description="Additional metadata",
                vectorize=False
            )
        ]
        
        return self.create_document_schema(
            class_name=class_name,
            description=description,
            properties=properties
        )
    
    def create_document_schema_for_chunks(self, 
                                        class_name: str, 
                                        description: str,
                                        parent_class: Optional[str] = None) -> Dict[str, Any]:
        """Create standard schema for document chunks.
        
        Args:
            class_name: Class name for the schema
            description: Description of the class
            parent_class: Parent document class name (optional)
            
        Returns:
            Schema definition
        """
        properties = [
            self.create_property(
                name="content",
                data_type=["text"],
                description="Chunk content",
                vectorize=True
            ),
            self.create_property(
                name="chunk_index",
                data_type=["int"],
                description="Index of chunk in document",
                vectorize=False
            ),
            self.create_property(
                name="document_id",
                data_type=["text"],
                description="ID of parent document",
                vectorize=False
            ),
            self.create_property(
                name="metadata",
                data_type=["object"],
                description="Additional metadata",
                vectorize=False
            )
        ]
        
        # Add reference to parent document if specified
        if parent_class:
            properties.append(
                self.create_reference_property(
                    name="document",
                    target_class=parent_class,
                    description="Reference to parent document"
                )
            )
        
        return self.create_document_schema(
            class_name=class_name,
            description=description,
            properties=properties
        )