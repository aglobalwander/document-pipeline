"""Weaviate client for vector database integration."""
import os
import uuid
import time
from typing import Any, Dict, List, Optional, Union
import logging
import weaviate
from weaviate.util import generate_uuid5
# WeaviateBatch import removed, batching is handled via client context manager in v4

from doc_processing.config import get_settings
from doc_processing.embedding.base import BaseEmbedding

class WeaviateClient:
    """Client for interacting with Weaviate vector database."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Weaviate client.
        
        Args:
            config: Configuration options
        """
        self.settings = get_settings()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Set up Weaviate connection parameters
        self.url = self.config.get('url', self.settings.WEAVIATE_URL)
        self.api_key = self.config.get('api_key', self.settings.WEAVIATE_API_KEY)
        self.batch_size = self.config.get('batch_size', self.settings.WEAVIATE_BATCH_SIZE)
        
        # Initialize OpenAI client for embeddings if needed
        self.embedding_model = self.config.get('embedding_model', self.settings.DEFAULT_EMBEDDING_MODEL)
        
        # Initialize client
        self.client = self._init_client()
    
    def _init_client(self) -> weaviate.Client:
        """Initialize Weaviate client connection.
        
        Returns:
            Connected Weaviate client
            
        Raises:
            ConnectionError: If unable to connect to Weaviate
        """
        try:
            # Configure auth
            auth_config = None
            if self.api_key:
                auth_config = weaviate.auth.AuthApiKey(api_key=self.api_key)
            
            # Initialize client
            client = weaviate.Client(
                url=self.url,
                auth_client_secret=auth_config,
                additional_headers={
                    "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")  # For OpenAI modules
                }
            )
            
            # Check connection
            if not client.is_ready():
                raise ConnectionError(f"Unable to connect to Weaviate at {self.url}")
                
            self.logger.info(f"Connected to Weaviate at {self.url}")
            return client
            
        except Exception as e:
            self.logger.error(f"Error connecting to Weaviate: {str(e)}")
            raise ConnectionError(f"Failed to connect to Weaviate: {str(e)}")
    
    def create_schema(self, schema_definition: Dict[str, Any]) -> None:
        """Create schema in Weaviate.
        
        Args:
            schema_definition: Schema definition in Weaviate format
            
        Raises:
            Exception: If error creating schema
        """
        try:
            self.client.schema.create(schema_definition)
            self.logger.info(f"Created schema in Weaviate")
        except Exception as e:
            self.logger.error(f"Error creating schema: {str(e)}")
            raise
    
    def create_class(self, class_obj: Dict[str, Any]) -> None:
        """Create a single class in Weaviate schema.
        
        Args:
            class_obj: Class definition
            
        Raises:
            Exception: If error creating class
        """
        try:
            self.client.schema.create_class(class_obj)
            self.logger.info(f"Created class: {class_obj.get('class')}")
        except Exception as e:
            self.logger.error(f"Error creating class {class_obj.get('class')}: {str(e)}")
            raise
    
    def get_schema(self) -> Dict[str, Any]:
        """Get current schema from Weaviate.
        
        Returns:
            Schema definition
        """
        return self.client.schema.get()
    
    def class_exists(self, class_name: str) -> bool:
        """Check if class exists in schema.
        
        Args:
            class_name: Class name to check
            
        Returns:
            True if class exists, False otherwise
        """
        schema = self.get_schema()
        classes = schema.get('classes', [])
        return any(cls.get('class') == class_name for cls in classes)
    
    def delete_class(self, class_name: str) -> None:
        """Delete class from schema.
        
        Args:
            class_name: Class name to delete
            
        Raises:
            Exception: If error deleting class
        """
        try:
            self.client.schema.delete_class(class_name)
            self.logger.info(f"Deleted class: {class_name}")
        except Exception as e:
            self.logger.error(f"Error deleting class {class_name}: {str(e)}")
            raise
    
    def add_document(self, 
                    class_name: str, 
                    document: Dict[str, Any],
                    uuid_key: Optional[str] = None,
                    embedding: Optional[List[float]] = None) -> str:
        """Add a single document to Weaviate.
        
        Args:
            class_name: Class name to add document to
            document: Document data
            uuid_key: Key in document to use for generating UUID (optional)
            embedding: Pre-computed vector embedding (optional)
            
        Returns:
            UUID of created object
            
        Raises:
            Exception: If error adding document
        """
        try:
            # Generate UUID based on uuid_key if provided
            if uuid_key and uuid_key in document:
                obj_uuid = generate_uuid5(document[uuid_key])
            else:
                obj_uuid = None  # Let Weaviate generate it
            
            # Add document
            result = self.client.data_object.create(
                data_object=document,
                class_name=class_name,
                uuid=obj_uuid,
                vector=embedding
            )
            
            self.logger.debug(f"Added document to {class_name}: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding document to {class_name}: {str(e)}")
            raise
    
    def batch_add_documents(self, 
                          class_name: str, 
                          documents: List[Dict[str, Any]],
                          uuid_key: Optional[str] = None,
                          embedding_function: Optional[callable] = None) -> None:
        """Add multiple documents to Weaviate in batch.
        
        Args:
            class_name: Class name to add documents to
            documents: List of document data
            uuid_key: Key in document to use for generating UUID (optional)
            embedding_function: Function to generate embeddings (optional)
            
        Raises:
            Exception: If error adding documents
        """
        try:
            with self.client.batch as batch:
                batch.batch_size = self.batch_size
                
                for i, doc in enumerate(documents):
                    # Generate UUID based on uuid_key if provided
                    if uuid_key and uuid_key in doc:
                        obj_uuid = generate_uuid5(doc[uuid_key])
                    else:
                        obj_uuid = None  # Let Weaviate generate it
                    
                    # Generate embedding if function provided
                    vector = None
                    if embedding_function and callable(embedding_function):
                        vector = embedding_function(doc)
                    
                    # Add to batch
                    batch.add_data_object(
                        data_object=doc,
                        class_name=class_name,
                        uuid=obj_uuid,
                        vector=vector
                    )
                    
                    if i > 0 and i % 100 == 0:
                        self.logger.info(f"Processed {i}/{len(documents)} documents")
            
            self.logger.info(f"Added {len(documents)} documents to {class_name}")
            
        except Exception as e:
            self.logger.error(f"Error batch adding documents to {class_name}: {str(e)}")
            raise
    
    def query_documents(self, 
                      class_name: str, 
                      query_text: str, 
                      properties: List[str], 
                      limit: int = 10,
                      embedding_function: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Query documents based on vector similarity.
        
        Args:
            class_name: Class name to query
            query_text: Text to find similar documents for
            properties: Properties to include in results
            limit: Maximum number of results
            embedding_function: Function to generate query embedding
            
        Returns:
            List of matching documents
            
        Raises:
            Exception: If error querying
        """
        try:
            # Set up nearText query for text2vec-openai or similar modules
            if self.client.schema.get()['classes']:
                class_obj = next((c for c in self.client.schema.get()['classes'] if c['class'] == class_name), None)
                if not class_obj:
                    raise ValueError(f"Class {class_name} not found in schema")
                
                vectorizer = class_obj.get('vectorizer')
                
                # Query based on vectorizer type
                if 'text2vec' in vectorizer or 'openai' in vectorizer:
                    result = (
                        self.client.query
                        .get(class_name, properties)
                        .with_near_text({"concepts": [query_text]})
                        .with_limit(limit)
                        .do()
                    )
                elif 'custom' in vectorizer and embedding_function:
                    # Generate query vector
                    query_vector = embedding_function(query_text)
                    
                    result = (
                        self.client.query
                        .get(class_name, properties)
                        .with_near_vector({"vector": query_vector})
                        .with_limit(limit)
                        .do()
                    )
                else:
                    raise ValueError(f"Unsupported vectorizer {vectorizer} or missing embedding function")
                
                # Extract data objects from result
                if 'data' in result and 'Get' in result['data'] and class_name in result['data']['Get']:
                    return result['data']['Get'][class_name]
                return []
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error querying {class_name}: {str(e)}")
            raise
    
    def get_document_by_uuid(self, class_name: str, uuid: str, properties: List[str]) -> Optional[Dict[str, Any]]:
        """Get document by UUID.
        
        Args:
            class_name: Class name to query
            uuid: UUID of document
            properties: Properties to include in result
            
        Returns:
            Document if found, None otherwise
            
        Raises:
            Exception: If error retrieving document
        """
        try:
            result = (
                self.client.query
                .get(class_name, properties)
                .with_additional(['id'])
                .with_where({
                    "path": ["id"],
                    "operator": "Equal",
                    "valueString": uuid
                })
                .do()
            )
            
            # Extract data object from result
            if 'data' in result and 'Get' in result['data'] and class_name in result['data']['Get']:
                objects = result['data']['Get'][class_name]
                if objects:
                    return objects[0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting document {uuid} from {class_name}: {str(e)}")
            raise
    
    def delete_document(self, class_name: str, uuid: str) -> None:
        """Delete document by UUID.
        
        Args:
            class_name: Class name of document
            uuid: UUID of document
            
        Raises:
            Exception: If error deleting document
        """
        try:
            self.client.data_object.delete(uuid, class_name)
            self.logger.info(f"Deleted document {uuid} from {class_name}")
        except Exception as e:
            self.logger.error(f"Error deleting document {uuid} from {class_name}: {str(e)}")
            raise
    
    def count_documents(self, class_name: str) -> int:
        """Count documents in class.
        
        Args:
            class_name: Class name to count
            
        Returns:
            Number of documents
            
        Raises:
            Exception: If error counting documents
        """
        try:
            result = (
                self.client.query
                .aggregate(class_name)
                .with_meta_count()
                .do()
            )
            
            if 'data' in result and 'Aggregate' in result['data'] and class_name in result['data']['Aggregate']:
                return result['data']['Aggregate'][class_name][0]['meta']['count']
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error counting documents in {class_name}: {str(e)}")
            raise