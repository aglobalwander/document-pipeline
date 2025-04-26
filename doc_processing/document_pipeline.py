"""Main document processing pipeline."""
import os
import uuid
import time
import logging
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path
from pydantic import BaseModel

from doc_processing.config import get_settings, ensure_directories_exist
from doc_processing.embedding.base import Pipeline, PipelineComponent  # Corrected import path
from doc_processing.loaders.pdf_loader import PDFLoader
from doc_processing.processors.pdf_processor import HybridPDFProcessor  # Renamed from GPTVisionPDFProcessor
from doc_processing.transformers.text_to_markdown import TextToMarkdown
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import DocumentChunker
from doc_processing.transformers.instructor_extractor import InstructorExtractor


class DocumentPipeline:
    """Document processing pipeline."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, weaviate_client: Optional[Any] = None):
        """Initialize document pipeline.

        Args:
            config: Configuration options
            weaviate_client: Optional pre-initialized Weaviate client instance from weaviate_layer.client
        """
        self.settings = get_settings()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        self.weaviate_client = weaviate_client
        # weaviate_enabled is true if a client is provided OR if the config explicitly enables it (and we expect a client to be provided externally in that case)
        self.weaviate_enabled = self.weaviate_client is not None or self.config.get('weaviate_enabled', False)

        if self.weaviate_enabled and self.weaviate_client is None:
            # If enabled via config but no client provided, raise an error
            raise ValueError("Weaviate is enabled in configuration but no client instance was provided to the pipeline.")

        # Create directories if they don't exist
        ensure_directories_exist()

        # Initialize pipeline components based on configuration
        self._initialize_pipeline()

    def _initialize_pipeline(self) -> None:
        """Initialize pipeline components based on configuration."""
        # Core pipeline
        self.pipeline = Pipeline()

        # No internal client or schema manager initialization needed here anymore when using external client.

    # -------------------------------------------------------------------------
    # Pipeline configuration helpers
    # -------------------------------------------------------------------------

    def configure_pdf_to_text_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to text conversion."""
        pdf_loader = PDFLoader(self.config.get('pdf_loader_config', {}))
        pdf_processor = HybridPDFProcessor(self.config.get('pdf_processor_config', {}))
        self.pipeline.add_component(pdf_loader)
        self.pipeline.add_component(pdf_processor)
        return self

    def configure_hybrid_pdf_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for hybrid PDF processing with Docling and GPT Vision."""
        pdf_loader = PDFLoader(self.config.get('pdf_loader_config', {}))
        processor_config = {
            'use_docling': self.config.get('use_docling', True),
            'docling_use_easyocr': self.config.get('docling_use_easyocr', True),
            'docling_extract_tables': self.config.get('docling_extract_tables', True),
            'model': self.config.get('model', 'gpt-4o'),
            'max_tokens': self.config.get('max_tokens', 1500),
            'resolution_scale': self.config.get('resolution_scale', 2),
        }
        hybrid_processor = HybridPDFProcessor(processor_config)
        self.pipeline.add_component(pdf_loader)
        self.pipeline.add_component(hybrid_processor)
        self.logger.info("Configured hybrid PDF processing pipeline")
        return self

    def configure_structured_extraction_pipeline(self, response_model: Type[BaseModel]) -> 'DocumentPipeline':
        """Configure pipeline for structured data extraction using Instructor."""
        self.configure_hybrid_pdf_pipeline()
        extractor_config = {
            'model': self.config.get('extraction_model', 'gpt-4o'),
            'temperature': self.config.get('temperature', 0.2),
            'max_tokens': self.config.get('max_tokens', 4000),
            'system_prompt': self.config.get('system_prompt', "You are an expert document analyzer. Extract structured information from the document."),
        }
        instructor_extractor = InstructorExtractor(response_model=response_model, config=extractor_config)
        self.pipeline.add_component(instructor_extractor)
        self.logger.info(f"Added structured extraction with {response_model.__name__} model")
        return self

    def configure_pdf_to_markdown_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to markdown conversion."""
        self.configure_pdf_to_text_pipeline()
        markdown_transformer = TextToMarkdown(self.config.get('markdown_transformer_config', {}))
        self.pipeline.add_component(markdown_transformer)
        return self

    def configure_pdf_to_json_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to JSON conversion."""
        self.configure_pdf_to_text_pipeline()
        json_transformer = TextToJSON(self.config.get('json_transformer_config', {}))
        self.pipeline.add_component(json_transformer)
        return self

    def configure_pdf_to_weaviate_pipeline(self) -> 'DocumentPipeline':
        """Configure pipeline for PDF to Weaviate ingestion."""
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
        self.configure_pdf_to_text_pipeline()
        chunker = DocumentChunker(self.config.get('chunker_config', {}))
        self.pipeline.add_component(chunker)
        return self

    # -------------------------------------------------------------------------
    # Processing helpers
    # -------------------------------------------------------------------------

    def process_document(self, source_path: Union[str, Path]) -> Dict[str, Any]:
        """Process a single document."""
        doc_id = str(uuid.uuid4())
        result = self.pipeline.run(str(source_path))
        if 'id' not in result:
            result['id'] = doc_id
        if self.weaviate_enabled and 'chunks' in result:
            self._upload_to_weaviate(result)
        return result

    def process_directory(self, directory_path: Union[str, Path], file_extension: str = '.pdf') -> List[Dict[str, Any]]:
        """Process all documents in a directory."""
        path = Path(directory_path)
        if not path.is_dir():
            raise ValueError(f"Directory does not exist: {path}")
        files = list(path.glob(f'*{file_extension}'))
        self.logger.info(f"Found {len(files)} {file_extension} files in {path}")
        results = []
        for fp in files:
            try:
                self.logger.info(f"Processing {fp}")
                results.append(self.process_document(fp))
            except Exception as exc:  # noqa: BLE001
                self.logger.error(f"Error processing {fp}: {exc}")
        return results

    # -------------------------------------------------------------------------
    # Weaviate helpers
    # -------------------------------------------------------------------------

    def _upload_to_weaviate(self, document: Dict[str, Any]) -> None:
        """Upload a processed document (and its chunks) to Weaviate."""
        if not self.weaviate_enabled:
            return
        doc_collection = self.weaviate_client.collections.get("KnowledgeItem")
        chunk_collection = self.weaviate_client.collections.get("KnowledgeMain")

        doc_uuid = document.get('id', str(uuid.uuid4()))
        doc_properties = {
            'body': document.get('content', ''),
            'title': document.get('metadata', {}).get('title', doc_uuid),
            'source': document.get('source_path', ''),
            'source_type': document.get('metadata', {}).get('file_type', 'unknown'),
            'created_at': document.get('metadata', {}).get('created_at', time.time()),
            'updated_at': time.time(),
            # ... map more metadata as needed
        }
        doc_properties = {k: v for k, v in doc_properties.items() if v is not None}
        doc_collection.data_object.insert(properties=doc_properties, uuid=doc_uuid)

        chunks = document.get('chunks', [])
        if chunks:
            with chunk_collection.batch.dynamic() as batch:
                for ch in chunks:
                    ch_uuid = str(uuid.uuid4())
                    ch_props = {
                        'text': ch.get('content', ''),
                        'chunk_index': ch.get('chunk_index', 0),
                        'document_id': doc_uuid,
                    }
                    batch.add_object(properties=ch_props, uuid=ch_uuid)
        self.logger.info(f"Uploaded document '{doc_uuid}' with {len(chunks)} chunks to Weaviate")

    # -------------------------------------------------------------------------
    # Query helpers
    # -------------------------------------------------------------------------

    def query_similar_documents(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Return documents similar to the query text."""
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
        collection = self.weaviate_client.collections.get("KnowledgeItem")
        response = collection.query.near_text(
            query=query_text,
            limit=limit,
            return_properties=['title', 'body', 'source', 'url', 'summary', 'created_at', 'chunk_index'], # Removed 'source_type'
            return_metadata=["distance"] # Request distance metadata
            # Removed the invalid 'vector' parameter
        )
        return [
            {'uuid': obj.uuid, 'distance': obj.metadata.distance, 'properties': obj.properties} # Access distance via metadata
            for obj in response.objects
        ]

    def query_similar_chunks(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return text chunks similar to the query text."""
        if not self.weaviate_enabled:
            raise ValueError("Weaviate is not enabled in this pipeline")
        collection = self.weaviate_client.collections.get("KnowledgeMain")
        response = collection.query.near_text(
            query=query_text,
            limit=limit,
            return_properties=['text', 'chunk_index', 'filename', 'tags', 'document_id'],
            return_metadata=["distance"], # Use return_metadata for distance
            # Removed the invalid 'vector' parameter
        )
        return [
            {
                'uuid': obj.uuid,
                'distance': obj.metadata.distance, # Access distance via metadata
                'properties': obj.properties,
            }
            for obj in response.objects
        ]

    def get_document_context(self, query_text: str, context_chunks: int = 3) -> str:
        """Concatenate top-N matching chunks into a context string."""
        chunks = self.query_similar_chunks(query_text, limit=context_chunks)
        return "\n\n".join(ch['properties'].get('text', '') for ch in chunks)
