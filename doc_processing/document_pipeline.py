"""Main document processing pipeline."""
import os
import uuid
import time
import logging
import tempfile # Import tempfile for temporary PDF handling
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path
from pydantic import BaseModel

from doc_processing.config import get_settings, ensure_directories_exist
from doc_processing.embedding.base import Pipeline, PipelineComponent, BaseDocumentLoader
from doc_processing.loaders.pdf_loader import PDFLoader
from doc_processing.loaders.youtube_loader import YouTubeLoader
from doc_processing.loaders.docx_loader import DocxLoader # Import DocxLoader
from doc_processing.processors.pdf_processor import PDFProcessor # Updated import
from doc_processing.processors.docx_processor import MammothDOCXProcessor # Import DOCX processor
from doc_processing.processors.pptx_processor import MarkItDownPPTXProcessor # Import MarkItDown PPTX processor
# Removed import of HybridPPTXProcessor
from doc_processing.transformers.text_to_markdown import TextToMarkdown
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import LangChainChunker # Import the new chunker
from doc_processing.transformers.instructor_extractor import InstructorExtractor
from doc_processing.transformers.json_to_csv import JsonToCSV # Import JSON to CSV transformer
from doc_processing.transformers.json_to_excel import JsonToExcel # Import JSON to Excel transformer
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
        # Removed hybrid_processor_config
        markdown_config = self.config.get('markdown_config', {})
        json_config = self.config.get('json_config', {})
        instructor_config = self.config.get('instructor_config', {})
        
        # Add configs for new processors and transformers
        docx_config = self.config.get('docx_config', {})
        pptx_config = self.config.get('pptx_config', {})
        json_to_csv_config = self.config.get('json_to_csv_config', {})
        json_to_excel_config = self.config.get('json_to_excel_config', {})
        
        # Add excel_template to json_to_excel_config if provided
        if self.config.get('excel_template'):
            json_to_excel_config['excel_template'] = self.config.get('excel_template')
        
        # Add excel_template_dir to json_to_excel_config if provided
        if self.config.get('excel_template_dir'):
            json_to_excel_config['excel_template_dir'] = self.config.get('excel_template_dir')
        
        # Add merge_csv flag to json_to_csv_config if provided
        if self.config.get('merge_csv'):
            json_to_csv_config['merge_csv'] = self.config.get('merge_csv')

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
        # Removed elif pipeline_type == 'hybrid': block

        elif pipeline_type == 'markdown':
            # Convert to Markdown. The MammothDOCXProcessor handles DOCX to Markdown.
            # TextToMarkdown is only needed if the initial loader provides raw text.
            # For now, we assume Mammoth handles the full conversion for DOCX.
            self.logger.info("Pipeline type 'markdown': MammothDOCXProcessor handles conversion for DOCX.")
            # If other loaders provide raw text for markdown pipeline, TextToMarkdown might be needed conditionally.
            # For now, remove it as Mammoth handles DOCX->MD.
            # self._pipeline_component_definitions.append({'class': TextToMarkdown, 'config': markdown_config}) # Removed TextToMarkdown
            pass # Keep pass for correct indentation
        elif pipeline_type == 'json':
            # Convert to JSON, then chunk
            # Assumes input is text content from a loader
            self._pipeline_component_definitions.append({'class': TextToJSON, 'config': json_config})
            
            # Add JSON to CSV or Excel transformer based on output_format
            output_format = self.config.get('output_format')
            if output_format == 'csv':
                self._pipeline_component_definitions.append({'class': JsonToCSV, 'config': json_to_csv_config})
            elif output_format == 'xlsx':
                self._pipeline_component_definitions.append({'class': JsonToExcel, 'config': json_to_excel_config})
            else:
                # Default behavior: chunk the JSON
                self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})
        elif pipeline_type == 'structured':
             # Use InstructorExtractor, then chunk
             # Assumes input is text content and config includes 'response_model'
             if 'response_model' not in instructor_config:
                 self.logger.error("InstructorExtractor requires 'response_model' in its config. Pipeline may fail.")
                 # Decide whether to raise error or proceed without extractor
             self._pipeline_component_definitions.append({'class': InstructorExtractor, 'config': instructor_config})
             self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})
        elif pipeline_type == 'weaviate':
            # For Weaviate ingestion, the processing steps depend on the input file type.
            # The specific processor (PDF, DOCX, PPTX, etc.) will be added in process_document.
            # Chunking is always needed before Weaviate ingestion.
            self.logger.info("Configuring 'weaviate' pipeline: Processor (determined by input type) -> LangChainChunker")
            self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})
            pass # Keep pass for correct indentation

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
            # Keep the warning for truly unknown types not explicitly handled above
            self.logger.warning(f"Unknown or unsupported pipeline_type: {pipeline_type}. Defaulting to text pipeline (chunking only).")
            # Default to just chunking the content provided by the initial loader
            self._pipeline_component_definitions.append({'class': LangChainChunker, 'config': chunker_config})

        self.logger.info(f"Pipeline definitions initialized with {len(self._pipeline_component_definitions)} components for type '{pipeline_type}'.")


    # -------------------------------------------------------------------------
    # Processing helpers
    # -------------------------------------------------------------------------

    def process_document(self, source_path: Union[str, Path]) -> Dict[str, Any]:
        """Process a single document or YouTube URL."""
        source_path_str = str(source_path)
        self.logger.info(f"Processing source path: {source_path_str}") # Added logging

        # Determine the appropriate initial loader based on the source_path
        initial_load_result: Optional[Dict[str, Any]] = None
        initial_loader: Optional[BaseDocumentLoader] = None

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
        elif source_path_str.lower().endswith('.docx'):
             self.logger.info(f"Detected DOCX file: {source_path_str}. Using DocxLoader for initial loading.")
             initial_loader = DocxLoader(self.config.get('docx_loader_config', {}))
             self.logger.info(f"Selected loader: DocxLoader for DOCX") # Added logging
        elif source_path_str.lower().endswith('.pptx'):
             self.logger.info(f"Detected PPTX file: {source_path_str}. Skipping initial text loading.")
             # Create a document dictionary with just the input path and metadata
             initial_load_result = {
                 "input_path": source_path_str,
                 "content": source_path_str, # Pass the file path in the content field
                 "metadata": {
                     "filename": Path(source_path_str).name,
                     "filetype": "pptx"
                 }
             }
             self.logger.info(f"Created initial document structure for PPTX.")
             # No initial_loader needed for PPTX as we handle it with a specific processor
        elif source_path_str.lower().endswith(('.txt', '.md', '.json')):
             self.logger.info(f"Detected text/document file: {source_path_str}. Using TextLoader.")
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

        # Run the initial loader if it was determined (i.e., not a PPTX file handled above)
        if initial_loader:
            initial_load_result = initial_loader.load(source_path_str)

        # Initialize a new pipeline for subsequent processing
        processing_pipeline = Pipeline()

        # Add specific processors based on file type and pipeline type/strategy
        if source_path_str.lower().endswith('.docx'):
            self.logger.info(f"Adding MammothDOCXProcessor for DOCX processing")
            processing_pipeline.add_component(MammothDOCXProcessor(self.config.get('docx_config', {})))
        elif source_path_str.lower().endswith('.pptx'):
            # Use MarkItDownPPTXProcessor for PPTX files as per updated plan
            self.logger.info(f"Adding MarkItDownPPTXProcessor for PPTX processing")
            # Explicitly set pptx_strategy to 'text' as per the updated plan
            pptx_processor_config = self.config.get('pptx_config', {})
            pptx_processor_config['pptx_strategy'] = 'text'
            processing_pipeline.add_component(MarkItDownPPTXProcessor(pptx_processor_config))
        elif source_path_str.lower().endswith('.pdf'):
             # Add PDFProcessor here if the pipeline type is not 'weaviate' or 'hybrid'
             # For 'weaviate' and 'hybrid', PDFProcessor is added in _initialize_pipeline_definitions
             # based on the overall pipeline structure.
             # This logic might need refinement based on how PDFProcessor is intended to be used
             # in different pipeline types. For now, keep it simple and assume PDFProcessor
             # is added in _initialize_pipeline_definitions for relevant pipeline types.
             pass # PDFProcessor is added in _initialize_pipeline_definitions for 'hybrid' and 'weaviate'

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
        # Note: For PPTX, initial_load_result is already the document dict, so no merge needed here.
        if initial_loader and initial_load_result and 'metadata' in initial_load_result:
             # Merge metadata, prioritizing metadata from later stages if keys overlap
             merged_metadata = initial_load_result['metadata'].copy()
             merged_metadata.update(processed_document.get('metadata', {}))
             processed_document['metadata'] = merged_metadata

        # Handle Weaviate ingestion if enabled and chunks are present
        if self.weaviate_enabled and 'chunks' in processed_document:
             self._upload_to_weaviate(processed_document)

        # Clean up temporary PDF file if it was created during PPTX processing (only for hybrid strategy, which is now removed)
        # This cleanup logic is no longer needed with MarkItDownPPTXProcessor
        # if processed_document.get('metadata', {}).get('filetype') == 'pptx' and \
        #    processed_document.get('metadata', {}).get('pdf_path'):
        #     temp_pdf_path = Path(processed_document['metadata']['pdf_path'])
        #     try:
        #         if temp_pdf_path.exists():
        #             temp_pdf_path.unlink()
        #             self.logger.info(f"Cleaned up temporary PDF file: {temp_pdf_path}")
        #     except Exception as e:
        #         self.logger.error(f"Error cleaning up temporary PDF file {temp_pdf_path}: {e}")


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
                results.append(self.process_document(fp)) # Append the single dict result
            except Exception as exc:  # noqa: BLE001
                self.logger.error(f"Error processing {fp}: {exc}")
        return results

    # -------------------------------------------------------------------------
    # Weaviate helpers
    # -------------------------------------------------------------------------

    def _upload_to_weaviate(self, document: Dict[str, Any]) -> None:
        """Upload a processed document (and its chunks) to Weaviate."""
        if not self.weaviate_enabled:
            self.logger.debug("Weaviate not enabled, skipping upload.")
            return

        # Get the target collection name from the pipeline configuration
        collection_name = self.config.get('collection_name')
        if not collection_name:
            self.logger.error("Weaviate upload failed: 'collection_name' not found in pipeline configuration.")
            # Optionally add the error to the document dict
            document['error'] = document.get('error', '') + " Weaviate upload failed: Missing collection name in config."
            return

        try:
            # Get the specified collection for ingesting chunks
            chunk_collection = self.weaviate_client.collections.get(collection_name)
            self.logger.info(f"Targeting Weaviate collection: {collection_name}")
        except Exception as e:
            self.logger.error(f"Failed to get Weaviate collection '{collection_name}': {e}")
            document['error'] = document.get('error', '') + f" Weaviate upload failed: Cannot access collection '{collection_name}'."
            return

        # We will ingest chunks into the specified collection.
        # The document-level metadata might be implicitly linked via document_id in chunks,
        # or the user schema might handle it differently. Removing direct doc insertion.
        doc_uuid = document.get('id', str(uuid.uuid4())) # Still need a document ID for linking chunks

        chunks = document.get('chunks', [])
        if not chunks:
            self.logger.warning(f"No chunks found in document {doc_uuid} to upload to Weaviate collection '{collection_name}'.")
            return

        uploaded_count = 0
        try:
            with chunk_collection.batch.dynamic() as batch:
                for idx, ch in enumerate(chunks):
                    # Use chunk_index from data if available, otherwise use loop index
                    chunk_index = ch.get('chunk_index', idx)
                    chunk_text = ch.get('content', ch.get('text')) # Try 'content' then 'text'

                    if not chunk_text:
                         self.logger.warning(f"Skipping chunk {chunk_index} for document {doc_uuid} due to missing text content.")
                         continue

                    ch_uuid = str(uuid.uuid4()) # Generate UUID for each chunk object
                    # Ensure properties match common chunk schemas or user needs to adapt their schema
                    ch_props = {
                        'text': chunk_text,
                        'chunk_index': chunk_index,
                        'document_id': doc_uuid, # Link back to the conceptual document
                        # Add other relevant metadata from chunk if needed, e.g., ch.get('metadata')
                    }
                    batch.add_object(properties=ch_props, uuid=ch_uuid)
                    uploaded_count += 1
            # Check batch results if needed (omitted for brevity)
            self.logger.info(f"Successfully uploaded {uploaded_count} chunks for document '{doc_uuid}' to Weaviate collection '{collection_name}'.")
        except Exception as e:
             self.logger.error(f"Error during Weaviate batch upload to collection '{collection_name}' for document {doc_uuid}: {e}")
             document['error'] = document.get('error', '') + f" Weaviate batch upload failed for collection '{collection_name}'."

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
