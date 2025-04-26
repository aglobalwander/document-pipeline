"""Main document processing pipeline."""
import os
import uuid
import time
import logging
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path
from pydantic import BaseModel

from doc_processing.config import get_settings, ensure_directories_exist
from doc_processing.embedding.base import Pipeline, PipelineComponent, BaseDocumentLoader
from doc_processing.loaders.pdf_loader import PDFLoader
from doc_processing.loaders.youtube_loader import YouTubeLoader
from doc_processing.processors.pdf_processor import HybridPDFProcessor
from doc_processing.transformers.text_to_markdown import TextToMarkdown
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import DocumentChunker
from doc_processing.transformers.instructor_extractor import InstructorExtractor
from doc_processing.loaders.image_loader import ImageLoader
from doc_processing.loaders.text_loader import TextLoader
from doc_processing.loaders.video_loader import VideoLoader


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

        # Store pipeline component definitions based on configuration, but don't add to self.pipeline yet
        self._pipeline_component_definitions: List[Dict[str, Any]] = []
        self._initialize_pipeline_definitions()

        # self.pipeline will be initialized in process_document

    def _initialize_pipeline_definitions(self) -> None:
        """Define pipeline components based on configuration."""
        pipeline_type = self.config.get('pipeline_type', 'text') # Default to 'text' pipeline

        # Define component classes and their configs for each pipeline type (excluding the initial loader)
        if pipeline_type == 'text':
            self._pipeline_component_definitions = [
                {'class': HybridPDFProcessor, 'config': self.config.get('pdf_processor_config', {})},
                # Add other text processing components here if needed
            ]
        elif pipeline_type == 'markdown':
            self._pipeline_component_definitions = [
                {'class': HybridPDFProcessor, 'config': self.config.get('pdf_processor_config', {})},
                {'class': TextToMarkdown, 'config': self.config.get('markdown_transformer_config', {})},
            ]
        elif pipeline_type == 'json':
             self._pipeline_component_definitions = [
                {'class': HybridPDFProcessor, 'config': self.config.get('pdf_processor_config', {})},
                {'class': TextToJSON, 'config': self.config.get('json_transformer_config', {})},
            ]
        elif pipeline_type == 'hybrid':
             self._pipeline_component_definitions = [
                {'class': HybridPDFProcessor, 'config': self.config.get('pdf_processor_config', {})},
                # Hybrid pipeline might have other specific components
            ]
        elif pipeline_type == 'weaviate':
             if not self.weaviate_enabled:
                 raise ValueError("Weaviate is not enabled for the 'weaviate' pipeline type.")
             self._pipeline_component_definitions = [
                {'class': HybridPDFProcessor, 'config': self.config.get('pdf_processor_config', {})},
                {'class': DocumentChunker, 'config': self.config.get('chunker_config', {})},
                # Weaviate ingestion is handled in process_document after chunking
            ]
        # Add other pipeline types here (e.g., 'youtube_text', 'youtube_weaviate')
        # For now, YouTube processing will use the components defined for the selected pipeline_type
        # after the YouTubeLoader.

        self.logger.info(f"Initialized pipeline definitions for type: {pipeline_type}")

    # -------------------------------------------------------------------------
    # Pipeline configuration helpers (These methods are now outdated and removed)
    # -------------------------------------------------------------------------
    # The configure_* methods were removed as pipeline configuration is now handled
    # in _initialize_pipeline_definitions based on the 'pipeline_type' config.


    # -------------------------------------------------------------------------
    # Processing helpers
    # -------------------------------------------------------------------------

    def process_document(self, source_path: Union[str, Path]) -> Dict[str, Any]:
        """Process a single document or YouTube URL."""
        source_path_str = str(source_path)

        # Determine the appropriate initial loader based on the source_path
        initial_loader: BaseDocumentLoader
        if YouTubeLoader(self.config)._is_youtube_url(source_path_str):
             self.logger.info(f"Detected YouTube URL: {source_path_str}. Using YouTubeLoader.")
             initial_loader = YouTubeLoader(self.config)
        elif source_path_str.lower().endswith('.pdf'):
             self.logger.info(f"Detected PDF file: {source_path_str}. Using PDFLoader.")
             initial_loader = PDFLoader(self.config.get('pdf_loader_config', {}))
        elif source_path_str.lower().endswith(('.jpg', '.png', '.gif')):
             self.logger.info(f"Detected image file: {source_path_str}. Using ImageLoader.")
             initial_loader = ImageLoader(self.config.get('image_loader_config', {}))
        elif source_path_str.lower().endswith(('.txt', '.md', '.json', '.docx')):
             self.logger.info(f"Detected text/document file: {source_path_str}. Using TextLoader.")
             # Note: This might need refinement to use specific loaders for MD, JSON, DOCX
             initial_loader = TextLoader(self.config.get('text_loader_config', {}))
        elif source_path_str.lower().endswith(('.3gp', '.flv', '.mkv', '.mp4')):
             self.logger.info(f"Detected video file: {source_path_str}. Using VideoLoader.")
             initial_loader = VideoLoader(self.config.get('video_loader_config', {}))
        else:
             # Fallback for unknown file types or if no specific loader matched
             self.logger.warning(f"Could not determine loader for {source_path_str}. Defaulting to TextLoader.")
             initial_loader = TextLoader(self.config.get('text_loader_config', {})) # Default fallback loader

        # Run the initial loader
        initial_load_result = initial_loader.load(source_path_str)

        # Initialize a new pipeline for subsequent processing
        processing_pipeline = Pipeline()

        # The output of the initial loader becomes the input for the rest of the pipeline
        pipeline_input = initial_load_result

        # If the initial loader was YouTubeLoader, the content is a file path.
        # The next component should be the VideoLoader to process this file.
        # Add the subsequent pipeline components based on the stored definitions
        for component_def in self._pipeline_component_definitions:
            component_class = component_def['class']
            component_config = component_def.get('config', {})
            processing_pipeline.add_component(component_class(component_config))

        # Run the rest of the configured pipeline
        processed_document = processing_pipeline.run(pipeline_input)

        # Ensure the result is a dictionary
        if not isinstance(processed_document, dict):
             self.logger.error(f"Pipeline did not return a dictionary: {type(processed_document)}")
             # Attempt to convert if it's a list with a single item, otherwise raise error
             if isinstance(processed_document, list) and len(processed_document) == 1 and isinstance(processed_document[0], dict):
                  processed_document = processed_document[0]
             else:
                  raise TypeError(f"Pipeline result is not a dictionary: {processed_document}")


        # Assign a unique ID if not already present
        if 'id' not in processed_document:
            processed_document['id'] = str(uuid.uuid4())

        # Merge initial metadata from YouTubeLoader if it exists
        if isinstance(initial_loader, YouTubeLoader) and initial_load_result and 'metadata' in initial_load_result:
             # Merge metadata, prioritizing metadata from later stages if keys overlap
             merged_metadata = initial_load_result['metadata'].copy()
             merged_metadata.update(processed_document.get('metadata', {}))
             processed_document['metadata'] = merged_metadata

        # Handle Weaviate ingestion if enabled and chunks are present
        if self.weaviate_enabled and 'chunks' in processed_document:
             self._upload_to_weaviate(processed_document)

        # The return type should be Dict[str, Any] for a single processed document
        return processed_document

    def process_directory(self, directory_path: Union[str, Path], file_extension: str = '.pdf') -> List[Dict[str, Any]]:
        """Process all documents in a directory."""
        path = Path(directory_path)
        if not path.is_dir():
            raise ValueError(f"Directory does not exist: {path}")
        # Note: This method currently assumes processing local files with a specific extension.
        # It might need refactoring to handle directories containing mixed file types or URLs
        # if that becomes a requirement. For now, it remains focused on local files.
        files = list(path.glob(f'*{file_extension}'))
        self.logger.info(f"Found {len(files)} {file_extension} files in {path}")
        results = []
        for fp in files:
            try:
                self.logger.info(f"Processing {fp}")
                # Call process_document for each file
                results.extend(self.process_document(fp)) # Use extend as process_document now returns List
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
            'source': document.get('source_path', ''), # Use source_path from the document
            'source_type': document.get('metadata', {}).get('source_type', 'unknown'), # Use source_type from metadata
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
