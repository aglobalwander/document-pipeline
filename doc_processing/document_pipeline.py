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
from doc_processing.transformers.chunker import LangChainChunker # Import the new chunker
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


    def _initialize_pipeline_definitions(self):
        """Initialize the list of pipeline component definitions based on config."""
        self.logger.info("Initializing pipeline component definitions...")
        self._pipeline_component_definitions = [] # Ensure it's empty before populating
        pipeline_type = self.config.get('pipeline_type', 'text') # Default to 'text'
        self.logger.info(f"Configuring pipeline for type: {pipeline_type}")

        # Define component configurations from self.config if they exist
        chunker_config = self.config.get('chunker_config', {})
        hybrid_processor_config = self.config.get('hybrid_processor_config', {})
        markdown_config = self.config.get('markdown_config', {})
        json_config = self.config.get('json_config', {})
        instructor_config = self.config.get('instructor_config', {})
        # Add other configs as needed, e.g., text_cleaner_config

        # --- Define Pipeline Steps based on Type ---

        # Example: Add TextCleaner if configured globally or for specific types
        # if self.config.get('use_text_cleaner', False):
        #     self._pipeline_component_definitions.append({'class': TextCleaner, 'config': text_cleaner_config})

        if pipeline_type == 'text':
            # For the 'text' pipeline type, the goal is often to just output the raw loaded text.
            # No additional processing components (like chunking) are needed after the initial loader.
            # The initial loader (e.g., TextLoader) provides the 'content'.
            self.logger.info("Pipeline type 'text': No additional components added after initial loader.")
            pass # No components needed after the loader for simple text output
        elif pipeline_type == 'hybrid':
            # Hybrid PDF processing first, then chunking
            # Assumes initial loader (PDFLoader) provides necessary data for HybridPDFProcessor
            self._pipeline_component_definitions.append({'class': HybridPDFProcessor, 'config': hybrid_processor_config})
            self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})
        elif pipeline_type == 'markdown':
            # Convert to Markdown, then chunk
            # Assumes input is text content from a loader
            # Convert to Markdown. Chunking is usually not desired for the final Markdown output.
            self._pipeline_component_definitions.append({'class': TextToMarkdown, 'config': markdown_config})
            # self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config}) # Removed chunker
        elif pipeline_type == 'json':
            # Convert to JSON, then chunk
            # Assumes input is text content from a loader
            self._pipeline_component_definitions.append({'class': TextToJSON, 'config': json_config})
            # Note: Chunking JSON might not always make sense, depends on the structure.
            # Consider if chunking should happen *before* JSON conversion for some use cases.
            self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})
        elif pipeline_type == 'structured':
             # Use InstructorExtractor, then chunk
             # Assumes input is text content and config includes 'response_model'
             if 'response_model' not in instructor_config:
                 self.logger.error("InstructorExtractor requires 'response_model' in its config. Pipeline may fail.")
                 # Decide whether to raise error or proceed without extractor
             self._pipeline_component_definitions.append({'class': InstructorExtractor, 'config': instructor_config})
             self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})
        # Add elif blocks for other pipeline types (e.g., 'image', 'video', 'audio')
        # These might involve processors like ImageProcessor, VideoToChunks, AudioTranscription
        # elif pipeline_type == 'image':
        #     self._pipeline_component_definitions.append({'class': ImageProcessor, 'config': self.config.get('image_processor_config', {})})
        #     # Chunking might not apply directly to image metadata/description
        # elif pipeline_type == 'video':
        #      self._pipeline_component_definitions.append({'class': VideoToChunks, 'config': self.config.get('video_chunker_config', {})})
        # elif pipeline_type == 'audio':
        #      self._pipeline_component_definitions.append({'class': AudioTranscription, 'config': self.config.get('audio_transcription_config', {})}) # Example
        #      self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config}) # Chunk transcript
        else:
            self.logger.warning(f"Unknown or unsupported pipeline_type: {pipeline_type}. Defaulting to text pipeline (chunking only).")
            # Default to just chunking the content provided by the initial loader
            self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})

        self.logger.info(f"Pipeline definitions initialized with {len(self._pipeline_component_definitions)} components for type '{pipeline_type}'.")
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
        self.logger.info(f"Processing source path: {source_path_str}") # Added logging

        # Determine the appropriate initial loader based on the source_path
        initial_loader: BaseDocumentLoader
        if YouTubeLoader(self.config)._is_youtube_url(source_path_str):
             self.logger.info(f"Detected YouTube URL: {source_path_str}. Using YouTubeLoader.")
             initial_loader = YouTubeLoader(self.config)
             self.logger.info(f"Selected loader: YouTubeLoader") # Added logging
        elif source_path_str.lower().endswith('.pdf'):
             self.logger.info(f"Detected PDF file: {source_path_str}. Using PDFLoader.")
             initial_loader = PDFLoader(self.config.get('pdf_loader_config', {}))
             self.logger.info(f"Selected loader: PDFLoader") # Added logging
        elif source_path_str.lower().endswith(('.jpg', '.png', '.gif')):
             self.logger.info(f"Detected image file: {source_path_str}. Using ImageLoader.")
             initial_loader = ImageLoader(self.config.get('image_loader_config', {}))
             self.logger.info(f"Selected loader: ImageLoader") # Added logging
        elif source_path_str.lower().endswith(('.txt', '.md', '.json', '.docx')):
             self.logger.info(f"Detected text/document file: {source_path_str}. Using TextLoader.")
             # Note: This might need refinement to use specific loaders for MD, JSON, DOCX
             initial_loader = TextLoader(self.config.get('text_loader_config', {}))
             self.logger.info(f"Selected loader: TextLoader") # Added logging
        elif source_path_str.lower().endswith(('.3gp', '.flv', '.mkv', '.mp4')):
             self.logger.info(f"Detected video file: {source_path_str}. Using VideoLoader.")
             initial_loader = VideoLoader(self.config.get('video_loader_config', {}))
             self.logger.info(f"Selected loader: VideoLoader") # Added logging
        elif source_path_str.lower().endswith(('.wav', '.ogg', '.mp3', '.m4a')): # Added audio loader check
             self.logger.info(f"Detected audio file: {source_path_str}. Using AudioLoader.")
             from doc_processing.loaders.audio_loader import AudioLoader # Import AudioLoader
             initial_loader = AudioLoader(self.config.get('audio_loader_config', {}))
             self.logger.info(f"Selected loader: AudioLoader") # Added logging
        else:
             # Fallback for unknown file types or if no specific loader matched
             self.logger.warning(f"Could not determine loader for {source_path_str}. Defaulting to TextLoader.")
             initial_loader = TextLoader(self.config.get('text_loader_config', {})) # Default fallback loader
             self.logger.info(f"Selected loader: TextLoader (fallback)") # Added logging

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
            self.logger.info(f"Added pipeline component: {component_class.__name__}") # Added logging

        # Run the rest of the configured pipeline
        processed_document = processing_pipeline.run(pipeline_input)
        self.logger.info(f"Pipeline run completed. Result type: {type(processed_document)}") # Added logging

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
