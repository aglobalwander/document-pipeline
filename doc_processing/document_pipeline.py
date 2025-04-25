"""Main document processing pipeline."""
import os
import uuid
import time
import logging
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path
from pydantic import BaseModel

from doc_processing.config import get_settings, ensure_directories_exist
from doc_processing.embedding.base import Pipeline, PipelineComponent # Corrected import path
from doc_processing.loaders.pdf_loader import PDFLoader
from doc_processing.processors.pdf_processor import HybridPDFProcessor # Renamed from GPTVisionPDFProcessor
from doc_processing.transformers.text_to_markdown import TextToMarkdown
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import DocumentChunker
from doc_processing.transformers.instructor_extractor import InstructorExtractor
from doc_processing.embedding.weaviate_client import WeaviateClient
from doc_processing.embedding.schema_manager import SchemaManager

class DocumentPipeline:
    """Document processing pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize document pipeline.
        
        Args:
            config: Configuration options
        """
        self.settings = get_settings()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Create directories if they don't exist
        ensure_directories_exist()
        
        # Initialize pipeline components based on configuration
        self._initialize_pipeline()
    
    def _initialize_pipeline(self) -> None:
        """Initialize pipeline components based on configuration."""
        # Core pipeline
        self.pipeline = Pipeline()
        
        # Weaviate components (optional)
        self.weaviate_enabled = self.config.get('weaviate_enabled', False)
        if self.weaviate_enabled:
            self.weaviate_client = WeaviateClient(self.config.get('weaviate_config', {}))
            self.schema_manager = SchemaManager(self.weaviate_client)
            
            # Create default schema if needed
            self._initialize_weaviate_schema()
    
    def _initialize_weaviate_schema(self) -> None:
        """Initialize Weaviate schema if needed."""
        if not self.weaviate_enabled:
            return
            
        try:
            # Check if document class exists
            doc_class_name = self.config.get('document_class_name', 'Document')
            chunk_class_name = self.config.get('chunk_class_name', 'DocumentChunk')
            
            if not self.weaviate_client.class_exists(doc_class_name):
                # Create document schema
                doc_schema = self.schema_manager.create_document_schema_for_text(
                    class_name=doc_class_name,
                    description="Document with full text content"
                )
                self.schema_manager.register_schema(doc_schema)
            
            if not self.weaviate_client.class_exists(chunk_class_name):
                # Create chunk schema
                chunk_schema = self.schema_manager.create_document_schema_for_chunks(
                    class_name=chunk_class_name,
                    description="Document chunk for semantic search",
                    parent_class=doc_class_name
                )
                self.schema_manager.register_schema(chunk_schema)
                
            self.logger.info(f"Weaviate schema initialized with classes: {doc_class_name}, {chunk_class_name}")
            
        except Exception as e:
            self.logger.error(f"Error initializing Weaviate schema: {str(e)}")
            raise
    
    def configure_pdf_to_text_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to text conversion.
        
        Returns:
            Self for method chaining
        """
        # PDF loader
        pdf_loader = PDFLoader(self.config.get('pdf_loader_config', {}))
        
        # PDF processor using GPT-4 Vision
        # Use the renamed Hybrid processor
        pdf_processor = HybridPDFProcessor(self.config.get('pdf_processor_config', {}))
        
        # Add components to pipeline
        self.pipeline.add_component(pdf_loader)
        self.pipeline.add_component(pdf_processor)
        
        return self
    
    def configure_hybrid_pdf_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for hybrid PDF processing with Docling and GPT Vision.
        
        Returns:
            Self for method chaining
        """
        # PDF loader
        pdf_loader = PDFLoader(self.config.get('pdf_loader_config', {}))
        
        # Create hybrid processor with configuration
        processor_config = {
            'use_docling': self.config.get('use_docling', True),
            'docling_use_easyocr': self.config.get('docling_use_easyocr', True),
            'docling_extract_tables': self.config.get('docling_extract_tables', True),
            'model': self.config.get('model', 'gpt-4o'),
            'max_tokens': self.config.get('max_tokens', 1500),
            'resolution_scale': self.config.get('resolution_scale', 2),
        }
        
        # Use integrated processor with hybrid approach
        # Use the renamed Hybrid processor
        hybrid_processor = HybridPDFProcessor(processor_config)
        
        # Add components to pipeline
        self.pipeline.add_component(pdf_loader)
        self.pipeline.add_component(hybrid_processor)
        
        self.logger.info("Configured hybrid PDF processing pipeline")
        return self
    
    def configure_structured_extraction_pipeline(self, response_model: Type[BaseModel]) -> 'DocumentPipeline':
        """Configure pipeline for structured data extraction using Instructor.
        
        Args:
            response_model: Pydantic model for structured output
        
        Returns:
            Self for method chaining
        """
        # First configure hybrid PDF processing
        self.configure_hybrid_pdf_pipeline()
        
        # Add instructor extractor with response model
        extractor_config = {
            'model': self.config.get('extraction_model', 'gpt-4o'),
            'temperature': self.config.get('temperature', 0.2),
            'max_tokens': self.config.get('max_tokens', 4000),
            'system_prompt': self.config.get('system_prompt',
                "You are an expert document analyzer. Extract structured information from the document."
            )
        }
        
        # Create and add instructor extractor
        instructor_extractor = InstructorExtractor(
            response_model=response_model,
            config=extractor_config
        )
        self.pipeline.add_component(instructor_extractor)
        
        self.logger.info(f"Added structured extraction with {response_model.__name__} model")
        return self
    
    def configure_pdf_to_markdown_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to markdown conversion.
        
        Returns:
            Self for method chaining
        """
        # First set up PDF to text pipeline
        self.configure_pdf_to_text_pipeline()
        
        # Add markdown transformer
        markdown_transformer = TextToMarkdown(self.config.get('markdown_transformer_config', {}))
        self.pipeline.add_component(markdown_transformer)
        
        return self
    
    def configure_pdf_to_json_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to JSON conversion.
        
        Returns:
            Self for method chaining
        """
        # First set up PDF to text pipeline
        self.configure_pdf_to_text_pipeline()
        
        # Add JSON transformer
        json_transformer = TextToJSON(self.config.get('json_transformer_config', {}))
        self.pipeline.add_component(json_transformer)
        
        return self
    
    def configure_pdf_to_weaviate_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to Weaviate ingestion.
        
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If Weaviate is not enabled
        """
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
        
        # First set up PDF to text pipeline
        self.configure_pdf_to_text_pipeline()
        
        # Add chunker
        chunker = DocumentChunker(self.config.get('chunker_config', {}))
        self.pipeline.add_component(chunker)
        
        return self
    
    def process_document(self, source_path: Union[str, Path]) -> Dict[str, Any]:
        """Process document with configured pipeline.
        
        Args:
            source_path: Path to source document
            
        Returns:
            Processed document
            
        Raises:
            Exception: If processing fails
        """
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Process document with pipeline
            result = self.pipeline.run(str(source_path))
            
            # Add document ID if not present
            if 'id' not in result:
                result['id'] = doc_id
            
            # Upload to Weaviate if enabled
            if self.weaviate_enabled and 'chunks' in result:
                self._upload_to_weaviate(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing document {source_path}: {str(e)}")
            raise
    
    def process_directory(self, directory_path: Union[str, Path], file_extension: str = '.pdf') -> List[Dict[str, Any]]:
        """Process all documents in directory with specified extension.
        
        Args:
            directory_path: Path to directory
            file_extension: File extension to filter (default: .pdf)
            
        Returns:
            List of processed documents
            
        Raises:
            Exception: If processing fails
        """
        try:
            # Convert to Path object
            path = Path(directory_path)
            
            # Check if directory exists
            if not path.is_dir():
                raise ValueError(f"Directory does not exist: {path}")
            
            # Get all files with specified extension
            files = list(path.glob(f'*{file_extension}'))
            self.logger.info(f"Found {len(files)} {file_extension} files in {path}")
            
            # Process each file
            results = []
            for file_path in files:
                try:
                    self.logger.info(f"Processing {file_path}")
                    result = self.process_document(file_path)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    # Continue with next file
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing directory {directory_path}: {str(e)}")
            raise
    
    def _upload_to_weaviate(self, document: Dict[str, Any]) -> None:
        """Upload document and chunks to Weaviate.
        
        Args:
            document: Processed document with chunks
            
        Raises:
            Exception: If upload fails
        """
        try:
            if not self.weaviate_enabled:
                return
                
            doc_class_name = self.config.get('document_class_name', 'Document')
            chunk_class_name = self.config.get('chunk_class_name', 'DocumentChunk')
            
            # Prepare document data
            doc_data = {
                'content': document.get('content', ''),
                'title': document.get('metadata', {}).get('title', document.get('id', 'Untitled')),
                'source': document.get('source_path', ''),
                'source_type': document.get('metadata', {}).get('file_type', 'unknown'),
                'created_at': document.get('metadata', {}).get('created_at', time.time()),
                'updated_at': time.time(),
                'metadata': {
                    key: value for key, value in document.get('metadata', {}).items()
                    if key not in ['content', 'chunks', 'pages', 'error']
                }
            }
            
            # Add document to Weaviate
            doc_uuid = self.weaviate_client.add_document(
                class_name=doc_class_name,
                document=doc_data,
                uuid_key='id'
            )
            
            # Add chunks to Weaviate
            chunks = document.get('chunks', [])
            for chunk in chunks:
                chunk_data = {
                    'content': chunk.get('content', ''),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'document_id': document.get('id', None),
                    'metadata': chunk.get('metadata', {})
                }
                
                # Add chunk reference to parent document
                if doc_uuid:
                    self.weaviate_client.add_document(
                        class_name=chunk_class_name,
                        document=chunk_data,
                        uuid_key='document_id'
                    )
            
            self.logger.info(f"Uploaded document and {len(chunks)} chunks to Weaviate")
            
        except Exception as e:
            self.logger.error(f"Error uploading to Weaviate: {str(e)}")
            raise
    
    def query_similar_documents(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query Weaviate for similar documents.
        
        Args:
            query_text: Query text
            limit: Maximum number of results
            
        Returns:
            List of similar documents
            
        Raises:
            ValueError: If Weaviate is not enabled
        """
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
            
        doc_class_name = self.config.get('document_class_name', 'Document')
        
        # Query Weaviate
        results = self.weaviate_client.query_documents(
            class_name=doc_class_name,
            query_text=query_text,
            properties=['title', 'content', 'source', 'source_type', 'metadata'],
            limit=limit
        )
        
        return results
    
    def query_similar_chunks(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Query Weaviate for similar chunks.
        
        Args:
            query_text: Query text
            limit: Maximum number of results
            
        Returns:
            List of similar chunks
            
        Raises:
            ValueError: If Weaviate is not enabled
        """
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
            
        chunk_class_name = self.config.get('chunk_class_name', 'DocumentChunk')
        
        # Query Weaviate
        results = self.weaviate_client.query_documents(
            class_name=chunk_class_name,
            query_text=query_text,
            properties=['content', 'chunk_index', 'document_id', 'metadata'],
            limit=limit
        )
        
        return results
    
    def get_document_context(self, query_text: str, context_chunks: int = 3) -> str:
        """Get document context for query.
        
        Args:
            query_text: Query text
            context_chunks: Number of chunks to include in context
            
        Returns:
            Document context as string
            
        Raises:
            ValueError: If Weaviate is not enabled
        """
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
            
        # Query similar chunks
        chunks = self.query_similar_chunks(query_text, limit=context_chunks)
        
        # Combine chunks into context
        context = "\n\n".join([chunk.get('content', '') for chunk in chunks])
        
        return context