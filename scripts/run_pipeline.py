#!/usr/bin/env python
"""
Flexible Script for Running Document and Media Processing Pipelines

Allows processing single files or directories with various configurations
and uploading results to Weaviate or saving to files.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import json
import time
import uuid
from typing import Optional, Dict, Any, List, Union

# Add project root to sys.path to allow importing doc_processing modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from doc_processing.document_pipeline import DocumentPipeline
from doc_processing.config import get_settings, ensure_directories_exist
from doc_processing.embedding.base import Pipeline, PipelineComponent

# Import Loaders
from doc_processing.loaders.text_loader import TextLoader
from doc_processing.loaders.markdown_loader import MarkdownLoader
from doc_processing.loaders.json_loader import JSONLoader
from doc_processing.loaders.docx_loader import DocxLoader
from doc_processing.loaders.pdf_loader import PDFLoader
from doc_processing.loaders.image_loader import ImageLoader # New
from doc_processing.loaders.video_loader import VideoLoader # New
from doc_processing.loaders.audio_loader import AudioLoader # Existing

# Import Processors
from doc_processing.processors.pdf_processor import HybridPDFProcessor
from doc_processing.processors.image_processor import ImageProcessor # New
from doc_processing.processors.deepgram_processor import DeepgramProcessor # New

# Import Transformers
from doc_processing.transformers.text_to_markdown import TextToMarkdown
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import DocumentChunker
from doc_processing.transformers.video_to_chunks import VideoToChunks # New

# Import Weaviate client getter
from weaviate_layer.client import get_weaviate_client

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Log to console
        # Add FileHandler if needed: logging.FileHandler("run_pipeline.log")
    ]
)
logger = logging.getLogger(__name__)

# --- Argument Parsing ---
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run document and media processing pipelines on files or directories.'
    )

    parser.add_argument('--input_path', type=str, required=True,
                        help='Path to the input file or directory.')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Base directory to save output files.')
    parser.add_argument('--pipeline_type', type=str, required=True,
                        choices=['text', 'markdown', 'json', 'hybrid', 'weaviate'],
                        help='Type of pipeline configuration to run.')
    parser.add_argument('--recursive', action='store_true',
                        help='Process directories recursively.')
    parser.add_argument('--output_format', type=str, choices=['txt', 'md', 'json'],
                        help='Explicit output format (default inferred from pipeline_type).')

    # LLM Configuration (used by various processors/transformers)
    parser.add_argument('--llm_provider', type=str, default='openai',
                        choices=['openai', 'gemini', 'anthropic', 'deepseek'],
                        help='LLM provider to use.')
    parser.add_argument('--llm_model', type=str,
                        help='Specific LLM model name to override the default.')
    parser.add_argument('--api_key', type=str,
                        help='API key for the selected LLM provider (uses environment variable if not set).')
    parser.add_argument('--prompt_name', type=str,
                        help='Base name of the prompt template file (e.g., "invoice_extraction" for invoice_extraction.j2).')

    # PDF Processing Configuration
    parser.add_argument('--ocr_mode', type=str, default='hybrid', choices=['hybrid', 'docling', 'gpt'],
                        help="OCR mode for PDF processing ('hybrid', 'docling', 'gpt'). Only relevant for PDF inputs.")
    parser.add_argument('--gpt_vision_prompt', type=str,
                        help='Path to a custom Jinja2 template file for GPT Vision OCR.')
    parser.add_argument('--no_page_images', action='store_true',
                        help='Disable PDF page image generation in the loader (saves time if only using Docling).')

    # Media Processing Configuration (New)
    parser.add_argument('--image_backend', type=str, default='openai', choices=['openai', 'gemini'],
                        help='Backend for image processing (captioning/vision).')
    parser.add_argument('--deepgram_params', type=json.loads, default={},
                        help='JSON string of parameters for the Deepgram API (e.g., \'{"diarize": true}\').')
    # Add arguments for VideoToChunks if needed (e.g., --video_split_strategy)

    # Weaviate Configuration (only relevant for 'weaviate' pipeline_type)
    parser.add_argument('--weaviate_class_prefix', type=str, default='Document',
                        help='Prefix for Weaviate class names (e.g., Document, DocumentChunk).')

    return parser.parse_args()

# --- Pipeline Building Functions (Refactored) ---

def _build_text_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing text-based documents."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(TextLoader())
    # Add other text-specific processors/transformers if needed
    return pipeline

def _build_markdown_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing Markdown documents."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(MarkdownLoader())
    # Add other markdown-specific processors/transformers if needed
    return pipeline

def _build_json_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing JSON documents."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(JSONLoader())
    # Add other JSON-specific processors/transformers if needed
    return pipeline

def _build_docx_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing DOCX documents."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(DocxLoader())
    # Add other docx-specific processors/transformers if needed
    return pipeline

def _build_pdf_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing PDF documents."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(PDFLoader(config.get('pdf_loader_config', {})))
    pipeline.pipeline.add_component(HybridPDFProcessor(config.get('pdf_processor_config', {})))
    # Add other PDF-specific transformers if needed
    return pipeline

def _build_image_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing image files."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(ImageLoader(config.get('image_loader_config', {})))
    pipeline.pipeline.add_component(ImageProcessor(config.get('image_processor_config', {})))
    # Add other image-specific transformers if needed
    return pipeline

def _build_audio_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing audio files."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(AudioLoader(config.get('audio_loader_config', {})))
    pipeline.pipeline.add_component(DeepgramProcessor(config.get('deepgram_processor_config', {})))
    # Add other audio-specific transformers if needed
    return pipeline

def _build_video_pipeline(config: Dict[str, Any]) -> DocumentPipeline:
    """Builds a pipeline for processing video files."""
    pipeline = DocumentPipeline(config=config)
    pipeline.pipeline.add_component(VideoLoader(config.get('video_loader_config', {})))
    pipeline.pipeline.add_component(DeepgramProcessor(config.get('deepgram_processor_config', {}))) # Transcribe audio track
    pipeline.pipeline.add_component(VideoToChunks(config.get('video_transformer_config', {}))) # Split transcript into chunks
    # Add other video-specific processors/transformers if needed
    return pipeline

def _build_weaviate_pipeline(file_path: Path, config: Dict[str, Any], weaviate_client: Any) -> DocumentPipeline:
    """Builds a pipeline for processing and uploading to Weaviate."""
    file_ext = file_path.suffix.lower()
    pipeline = DocumentPipeline(config=config, weaviate_client=weaviate_client)

    # Select base pipeline based on file type
    if file_ext in ['.txt', '.md', '.json', '.docx']:
        # For text-based documents, use the appropriate loader and then chunk
        if file_ext == '.txt':
            pipeline.pipeline.add_component(TextLoader())
        elif file_ext == '.md':
            pipeline.pipeline.add_component(MarkdownLoader())
        elif file_ext == '.json':
            pipeline.pipeline.add_component(JSONLoader())
        elif file_ext == '.docx':
            pipeline.pipeline.add_component(DocxLoader())
        pipeline.pipeline.add_component(DocumentChunker(config.get('chunker_config', {})))
    elif file_ext == '.pdf':
        # For PDFs, use the PDF pipeline and then chunk
        pipeline = _build_pdf_pipeline(config) # Start with PDF processing
        pipeline.pipeline.add_component(DocumentChunker(config.get('chunker_config', {})))
    elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']: # Add image extensions
        # For images, use the image pipeline
        pipeline = _build_image_pipeline(config)
        # No chunking needed for images typically, upload the item directly
    elif file_ext in ['.mp3', '.wav', '.aac', '.flac']: # Add audio extensions
         # For audio, use the audio pipeline
         pipeline = _build_audio_pipeline(config)
         # No chunking needed for audio items typically, upload the item directly
    elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']: # Add video extensions
         # For video, use the video pipeline
         pipeline = _build_video_pipeline(config)
         # Video pipeline includes chunking
    else:
        logger.warning(f"Unsupported file type '{file_ext}' for Weaviate pipeline. Skipping.")
        return None # Indicate unsupported file type

    return pipeline


# --- Weaviate Upload Functions (Refactored) ---

def _upload_document_to_weaviate(client: Any, document: Dict[str, Any], config: Dict[str, Any]) -> None:
    """Uploads a processed text-based document (and its chunks) to Weaviate."""
    doc_collection_name = "KnowledgeItem"
    chunk_collection_name = "KnowledgeMain"

    doc_uuid = document.get('id', str(uuid.uuid4()))
    doc_properties = {
        'body': document.get('content', ''),
        'title': document.get('metadata', {}).get('title', doc_uuid),
        'source': document.get('source_path', ''),
        'source_type': document.get('metadata', {}).get('file_type', 'unknown'),
        'created_at': document.get('metadata', {}).get('created_at', time.time()),
        'updated_at': time.time(),
        # Map other relevant metadata from the pipeline result to KnowledgeItem properties
        'chapter': document.get('metadata', {}).get('chapter'),
        'author': document.get('metadata', {}).get('author'),
        'year': document.get('metadata', {}).get('year'),
        'categories': document.get('metadata', {}).get('categories'),
        'type': document.get('metadata', {}).get('type'),
        'url': document.get('metadata', {}).get('url'),
        'format': document.get('metadata', {}).get('format'),
        'language': document.get('metadata', {}).get('language'),
        'summary': document.get('metadata', {}).get('summary'),
        'chunk_index': document.get('metadata', {}).get('chunk_index'), # Map chunk_index if present on main doc
    }
    doc_properties = {k: v for k, v in doc_properties.items() if v is not None}

    # Insert main document object
    client.collections.get(doc_collection_name).data_object.insert(
         properties=doc_properties,
         uuid=doc_uuid
    )

    # Upload chunks if available
    chunks = document.get('chunks', [])
    if chunks:
        chunk_collection = client.collections.get(chunk_collection_name)
        with chunk_collection.batch.dynamic() as batch:
            for chunk in chunks:
                chunk_uuid = str(uuid.uuid4())
                chunk_props = {
                    'text': chunk.get('text', chunk.get('content', '')), # Use 'text' from VideoToChunks or 'content'
                    'chunk_index': chunk.get('chunk_index', 0),
                    'filename': chunk.get('metadata', {}).get('filename'),
                    'tags': chunk.get('metadata', {}).get('tags'),
                    'document_id': doc_uuid, # Link to the parent KnowledgeItem
                }
                chunk_props = {k: v for k, v in chunk_props.items() if v is not None}
                batch.add_object(properties=chunk_props, uuid=chunk_uuid)

    logger.info(f"Uploaded document '{doc_uuid}' and {len(chunks)} chunks to Weaviate")


def _upload_image_to_weaviate(client: Any, result: Dict[str, Any], config: Dict[str, Any]) -> None:
    """Uploads a processed image result to the ImageItem collection and links to KnowledgeItem."""
    image_collection_name = "ImageItem"
    knowledge_item_collection_name = "KnowledgeItem"

    # Create a KnowledgeItem for the image
    knowledge_item_uuid = str(uuid.uuid4())
    knowledge_item_props = {
        'title': result.get('metadata', {}).get('filename', knowledge_item_uuid),
        'source': result.get('metadata', {}).get('filename', ''),
        'source_type': result.get('metadata', {}).get('file_type', 'unknown'),
        'created_at': int(time.time()), # Use current time for creation
        'updated_at': int(time.time()),
        'type': 'image', # Set type to image
        'url': result.get('metadata', {}).get('url'), # Include URL if available
        'format': result.get('metadata', {}).get('file_type'), # Use file type as format
        'language': result.get('metadata', {}).get('language'), # Include language if available
        'summary': result.get('content'), # Use caption as summary
        # Map other relevant metadata from the image result to KnowledgeItem properties
    }
    knowledge_item_props = {k: v for k, v in knowledge_item_props.items() if v is not None}

    client.collections.get(knowledge_item_collection_name).data_object.insert(
        properties=knowledge_item_props,
        uuid=knowledge_item_uuid
    )
    logger.info(f"Created KnowledgeItem '{knowledge_item_uuid}' for image.")


    # Upload image item data
    image_item_uuid = str(uuid.uuid4()) # Generate a unique ID for the image item
    image_item_props = {
        'caption': result.get('content', ''), # Map caption to 'caption'
        'ocr_text': result.get('metadata', {}).get('ocr', ''), # Map OCR text to 'ocr_text'
        'width': result.get('metadata', {}).get('width'),
        'height': result.get('metadata', {}).get('height'),
        'backend': config.get('image_processor_config', {}).get('backend'), # Include backend used
        'filename': result.get('metadata', {}).get('filename'),
        # Add a reference to the parent KnowledgeItem
        'ofKnowledgeItem': [{'uuid': knowledge_item_uuid}], # Link to the KnowledgeItem
    }
    image_item_props = {k: v for k, v in image_item_props.items() if v is not None}

    client.collections.get(image_collection_name).data_object.insert(
        properties=image_item_props,
        uuid=image_item_uuid
    )
    logger.info(f"Uploaded ImageItem '{image_item_uuid}' and linked to KnowledgeItem '{knowledge_item_uuid}'.")


def _upload_audio_to_weaviate(client: Any, result: Dict[str, Any], config: Dict[str, Any]) -> None:
    """Uploads a processed audio result to the AudioItem collection and links to KnowledgeItem."""
    audio_collection_name = "AudioItem"
    audio_chunk_collection_name = "AudioChunk" # Assuming chunks are handled separately if needed
    knowledge_item_collection_name = "KnowledgeItem"

    # Create a KnowledgeItem for the audio
    knowledge_item_uuid = str(uuid.uuid4())
    knowledge_item_props = {
        'title': result.get('metadata', {}).get('filename', knowledge_item_uuid),
        'source': result.get('metadata', {}).get('filename', ''),
        'source_type': result.get('metadata', {}).get('file_type', 'unknown'),
        'created_at': int(time.time()), # Use current time for creation
        'updated_at': int(time.time()),
        'type': 'audio', # Set type to audio
        'url': result.get('metadata', {}).get('url'), # Include URL if available
        'format': result.get('metadata', {}).get('file_type'), # Use file type as format
        'language': result.get('metadata', {}).get('language'), # Include language if available
        'summary': result.get('content'), # Use transcript as summary
        # Map other relevant metadata from the audio result to KnowledgeItem properties
    }
    knowledge_item_props = {k: v for k, v in knowledge_item_props.items() if v is not None}

    client.collections.get(knowledge_item_collection_name).data_object.insert(
        properties=knowledge_item_props,
        uuid=knowledge_item_uuid
    )
    logger.info(f"Created KnowledgeItem '{knowledge_item_uuid}' for audio.")

    # Upload audio item data
    audio_item_uuid = str(uuid.uuid4()) # Generate a unique ID for the audio item
    audio_item_props = {
        'transcript': result.get('content', ''), # Map transcript to 'transcript'
        'duration_sec': result.get('metadata', {}).get('duration_sec'),
        'language': result.get('metadata', {}).get('language'),
        'filename': result.get('metadata', {}).get('filename'),
        # Add a reference to the parent KnowledgeItem
        'ofKnowledgeItem': [{'uuid': knowledge_item_uuid}], # Link to the KnowledgeItem
    }
    audio_item_props = {k: v for k, v in audio_item_props.items() if v is not None}

    client.collections.get(audio_collection_name).data_object.insert(
        properties=audio_item_props,
        uuid=audio_item_uuid
    )
    logger.info(f"Uploaded AudioItem '{audio_item_uuid}' and linked to KnowledgeItem '{knowledge_item_uuid}'.")

    # If the result includes chunks (e.g., from VideoToChunks applied to audio), upload them
    chunks = result.get('chunks', [])
    if chunks:
        chunk_collection = client.collections.get(audio_chunk_collection_name)
        with chunk_collection.batch.dynamic() as batch:
            for chunk in chunks:
                chunk_uuid = str(uuid.uuid4())
                chunk_props = {
                    'text': chunk.get('text', chunk.get('content', '')),
                    'time_start': chunk.get('time_start'),
                    'time_end': chunk.get('time_end'),
                    'chunk_index': chunk.get('chunk_index', 0),
                    # Add a reference to the parent AudioItem
                    'ofAudioItem': [{'uuid': audio_item_uuid}], # Link to the AudioItem
                }
                chunk_props = {k: v for k, v in chunk_props.items() if v is not None}
                batch.add_object(properties=chunk_props, uuid=chunk_uuid)
        logger.info(f"Uploaded {len(chunks)} chunks to AudioChunk collection.")


def _upload_video_to_weaviate(client: Any, result: Dict[str, Any], config: Dict[str, Any]) -> None:
    """Uploads a processed video result to the VideoItem and VideoChunk collections and links to KnowledgeItem."""
    video_collection_name = "VideoItem"
    video_chunk_collection_name = "VideoChunk"
    knowledge_item_collection_name = "KnowledgeItem"

    # Create a KnowledgeItem for the video
    knowledge_item_uuid = str(uuid.uuid4())
    knowledge_item_props = {
        'title': result.get('metadata', {}).get('filename', knowledge_item_uuid),
        'source': result.get('metadata', {}).get('filename', ''),
        'source_type': result.get('metadata', {}).get('file_type', 'unknown'),
        'created_at': int(time.time()), # Use current time for creation
        'updated_at': int(time.time()),
        'type': 'video', # Set type to video
        'url': result.get('metadata', {}).get('url'), # Include URL if available
        'format': result.get('metadata', {}).get('file_type'), # Use file type as format
        'language': result.get('metadata', {}).get('language'), # Include language if available
        'summary': result.get('content'), # Use full transcript as summary
        # Map other relevant metadata from the video result to KnowledgeItem properties
    }
    knowledge_item_props = {k: v for k, v in knowledge_item_props.items() if v is not None}

    client.collections.get(knowledge_item_collection_name).data_object.insert(
        properties=knowledge_item_props,
        uuid=knowledge_item_uuid
    )
    logger.info(f"Created KnowledgeItem '{knowledge_item_uuid}' for video.")

    # Upload video item data
    video_item_uuid = str(uuid.uuid4()) # Generate a unique ID for the video item
    video_item_props = {
        'transcript': result.get('content', ''), # Map full transcript to 'transcript'
        'duration_sec': result.get('metadata', {}).get('duration_sec'),
        'language': result.get('metadata', {}).get('language'),
        'filename': result.get('metadata', {}).get('filename'),
        # Add a reference to the parent KnowledgeItem
        'ofKnowledgeItem': [{'uuid': knowledge_item_uuid}], # Link to the KnowledgeItem
    }
    video_item_props = {k: v for k, v in video_item_props.items() if v is not None}

    client.collections.get(video_collection_name).data_object.insert(
        properties=video_item_props,
        uuid=video_item_uuid
    )
    logger.info(f"Uploaded VideoItem '{video_item_uuid}' and linked to KnowledgeItem '{knowledge_item_uuid}'.")

    # Upload video chunks
    chunks = result.get('chunks', [])
    if chunks:
        chunk_collection = client.collections.get(video_chunk_collection_name)
        with chunk_collection.batch.dynamic() as batch:
            for chunk in chunks:
                chunk_uuid = str(uuid.uuid4())
                chunk_props = {
                    'text': chunk.get('text', chunk.get('content', '')),
                    'time_start': chunk.get('time_start'),
                    'time_end': chunk.get('time_end'),
                    'chunk_index': chunk.get('chunk_index', 0),
                    # Add a reference to the parent VideoItem
                    'ofVideoItem': [{'uuid': video_item_uuid}], # Link to the VideoItem
                }
                chunk_props = {k: v for k, v in chunk_props.items() if v is not None}
                batch.add_object(properties=chunk_props, uuid=chunk_uuid)
        logger.info(f"Uploaded {len(chunks)} chunks to VideoChunk collection.")


# --- Main Processing Logic ---
def main():
    """Main execution function."""
    args = parse_arguments()
    settings = get_settings()
    ensure_directories_exist() # Ensure base output dirs exist

    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True) # Ensure specific output dir exists

    # --- Identify Input Files ---
    if input_path.is_file():
        files_to_process = [input_path]
    elif input_path.is_dir():
        pattern = f"**/*" if args.recursive else "*"
        # Expanded supported extensions to include audio and video
        supported_extensions = [
            '.pdf', '.txt', '.md', '.json', '.docx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', # Image extensions
            '.mp3', '.wav', '.aac', '.flac', # Audio extensions
            '.mp4', '.mov', '.avi', '.mkv', # Video extensions
        ]
        files_to_process = [
            f for f in input_path.glob(pattern)
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
    else:
        logger.error(f"Input path is not a valid file or directory: {input_path}")
        sys.exit(1)

    if not files_to_process:
        logger.warning(f"No supported files found to process in {input_path}")
        sys.exit(0)

    logger.info(f"Found {len(files_to_process)} file(s) to process.")

    # --- Initialize Weaviate client if needed ---
    weaviate_client = None
    if args.pipeline_type == 'weaviate':
        try:
            weaviate_client = get_weaviate_client()
            logger.info("Successfully connected to Weaviate.")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            sys.exit(1)

    try: # Use a try...except...finally block to ensure client is closed and errors are caught
        for file_path in files_to_process:
            logger.info(f"--- Processing file: {file_path.name} ---")
            file_start_time = time.time()
            pipeline = None
            processed_result = None

            try:
                # --- Build Pipeline Configuration ---
                pipeline_config = {
                    'weaviate_enabled': args.pipeline_type == 'weaviate',
                    'llm_provider': args.llm_provider,
                    'api_key': args.api_key, # Will be None if not provided, client uses env var
                    'llm_model': args.llm_model, # General model override
                    # PDF Loader specific config
                    'pdf_loader_config': {
                        'generate_page_images': not args.no_page_images
                    },
                    # Hybrid Processor specific config (which contains GPTPVisionProcessor)
                    'pdf_processor_config': {
                         'ocr_mode': args.ocr_mode,
                         'llm_provider': args.llm_provider, # Pass provider choice down
                         'api_key': args.api_key,           # Pass api_key down
                         'vision_model': args.llm_model,    # Pass model override (GPTPVisionProcessor will use this if set)
                         'prompt_name': args.prompt_name,
                         'gpt_vision_prompt': args.gpt_vision_prompt,
                    },
                    # Media Processing Config (New)
                    'image_processor_config': {
                        'backend': args.image_backend,
                        'model': args.llm_model, # Use general LLM model override for image backend model
                        'api_key': args.api_key, # Pass api_key down
                    },
                    'deepgram_processor_config': {
                        'api_key': args.api_key, # Pass api_key down
                        'dg_params': args.deepgram_params,
                    },
                    'video_transformer_config': {}, # Add config for VideoToChunks if needed
                    # Add other component configs if needed (e.g., chunker for weaviate)
                    'chunker_config': {},
                    'json_transformer_config': {'prompt_name': args.prompt_name},
                    'markdown_transformer_config': {'prompt_name': args.prompt_name},
                }

                # Filter out None values from top-level config passed to pipeline
                pipeline_config = {k: v for k, v in pipeline_config.items() if v is not None}

                # --- Build and Instantiate Pipeline based on file type and pipeline type ---
                file_ext = file_path.suffix.lower()

                if args.pipeline_type == 'weaviate':
                    if not pipeline_config.get('weaviate_enabled'):
                         logger.error("Weaviate pipeline type selected, but Weaviate is not enabled in config.")
                         fail_count += 1
                         continue # Skip this file

                    pipeline = _build_weaviate_pipeline(file_path, pipeline_config, weaviate_client)
                    if pipeline is None: # Handle unsupported file types for weaviate pipeline
                         fail_count += 1
                         continue # Skip this file

                elif args.pipeline_type == 'text':
                     if file_ext in ['.txt', '.md', '.json', '.docx', '.pdf']:
                          pipeline = _build_text_pipeline(pipeline_config)
                          if file_ext == '.pdf': # Add PDF processor for text output from PDF
                               pipeline.pipeline.add_component(HybridPDFProcessor(pipeline_config.get('pdf_processor_config', {})))
                     else:
                          logger.warning(f"Unsupported file type '{file_ext}' for 'text' pipeline. Skipping.")
                          fail_count += 1
                          continue # Skip this file

                elif args.pipeline_type == 'markdown':
                     if file_ext in ['.txt', '.md', '.json', '.docx', '.pdf']:
                          pipeline = _build_markdown_pipeline(pipeline_config)
                          if file_ext == '.pdf': # Add PDF processor for markdown output from PDF
                               pipeline.pipeline.add_component(HybridPDFProcessor(pipeline_config.get('pdf_processor_config', {})))
                          pipeline.pipeline.add_component(TextToMarkdown(pipeline_config.get('markdown_transformer_config', {})))
                     else:
                          logger.warning(f"Unsupported file type '{file_ext}' for 'markdown' pipeline. Skipping.")
                          fail_count += 1
                          continue # Skip this file

                elif args.pipeline_type == 'json':
                     if file_ext in ['.txt', '.md', '.json', '.docx', '.pdf']:
                          pipeline = _build_json_pipeline(pipeline_config)
                          if file_ext == '.pdf': # Add PDF processor for json output from PDF
                               pipeline.pipeline.add_component(HybridPDFProcessor(pipeline_config.get('pdf_processor_config', {})))
                          pipeline.pipeline.add_component(TextToJSON(pipeline_config.get('json_transformer_config', {})))
                     else:
                          logger.warning(f"Unsupported file type '{file_ext}' for 'json' pipeline. Skipping.")
                          fail_count += 1
                          continue # Skip this file

                elif args.pipeline_type == 'hybrid':
                     if file_ext == '.pdf':
                          pipeline = _build_pdf_pipeline(pipeline_config)
                     else:
                          logger.warning(f"Unsupported file type '{file_ext}' for 'hybrid' pipeline. Skipping.")
                          fail_count += 1
                          continue # Skip this file

                else:
                    logger.error(f"Unsupported pipeline type: {args.pipeline_type}")
                    fail_count += 1
                    continue # Skip this file


                if pipeline is None: # Should not happen if file type is supported for the pipeline type
                     logger.error(f"Failed to build pipeline for {file_path.name}.")
                     fail_count += 1
                     continue # Skip this file


                logger.info(f"Configured pipeline: {[c.__class__.__name__ for c in pipeline.pipeline.components]}")

                # --- Process Document ---
                processed_result = pipeline.run(file_path)

                # --- Handle Output ---
                if 'error' in processed_result and processed_result['error']:
                     logger.error(f"Pipeline failed for {file_path.name}: {processed_result['error']}")
                     fail_count += 1
                else:
                    if args.pipeline_type == 'weaviate':
                        # Weaviate upload is handled within the pipeline.run for weaviate type
                        # based on the weaviate_enabled flag and presence of chunks/content
                        # We can add specific upload calls here if needed for different media types
                        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                             _upload_image_to_weaviate(weaviate_client, processed_result, pipeline_config)
                        elif file_ext in ['.mp3', '.wav', '.aac', '.flac']:
                             _upload_audio_to_weaviate(weaviate_client, processed_result, pipeline_config)
                        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
                             _upload_video_to_weaviate(weaviate_client, processed_result, pipeline_config)
                        elif file_ext in ['.pdf', '.txt', '.md', '.json', '.docx']:
                             _upload_document_to_weaviate(weaviate_client, processed_result, pipeline_config)
                        else:
                             logger.warning(f"Weaviate upload not explicitly handled for file type {file_ext}. Assuming handled by pipeline.")

                        success_count += 1 # Count as success if pipeline ran and upload attempted
                    else:
                        # Save output to file for non-weaviate pipeline types
                        output_filename = get_output_filename(file_path, args.pipeline_type, args.output_format)
                        output_path = output_dir / output_filename
                        save_output(processed_result, output_path, args.pipeline_type)
                        success_count += 1


            except Exception as e:
                logger.exception(f"Critical error processing file {file_path.name}: {e}") # Use logger.exception to include traceback
                fail_count += 1

            file_duration = time.time() - file_start_time
            logger.info(f"--- Finished processing {file_path.name} in {file_duration:.2f} seconds ---")

    except Exception as main_e: # Catch exceptions from the main try block (e.g., Weaviate connection failure)
        logger.exception(f"An error occurred during the main processing loop: {main_e}")
        sys.exit(1) # Exit with a non-zero code to indicate failure

    finally:
        # Ensure the Weaviate client is closed
        if weaviate_client:
            weaviate_client.close()
            logger.info("Weaviate client closed.")

    # --- Summary ---
    total_duration = time.time() - total_start_time
    logger.info("--- Processing Summary ---")
    logger.info(f"Total files processed: {len(files_to_process)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Total time: {total_duration:.2f} seconds")
    logger.info("--------------------------")


if __name__ == "__main__":
    main()