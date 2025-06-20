import os
import sys

# Add the parent directory to the Python path to be able to import doc_processing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from doc_processing.document_pipeline import DocumentPipeline

# Define the YouTube URL for testing
youtube_url = "https://www.youtube.com/watch?v=BPj_yt_5d_w"

# Create a DocumentPipeline instance
# You might need to adjust the config based on your setup (e.g., Weaviate enabled/disabled)
# For a basic test, we can start with a minimal config.
pipeline_config = {
    'pipeline_type': 'text', # Or another type that includes VideoLoader and chunking
    'weaviate_enabled': False, # Set to True if you have Weaviate running and configured
    'video_loader_config': {}, # Add any specific video loader config here
    'chunker_config': {}, # Add any specific chunker config here
    # Add other necessary configurations for the pipeline components
}

try:
    pipeline = DocumentPipeline(config=pipeline_config)

    print(f"Processing YouTube video: {youtube_url}")

    # Process the YouTube URL
    # The result should be a dictionary containing the processed document data
    processed_document = pipeline.process_document(youtube_url)

    print("\n--- Processed Document Result ---")
    # Print relevant parts of the result
    print(f"Document ID: {processed_document.get('id')}")
    print(f"Source: {processed_document.get('source_path')}")
    print(f"Source Type: {processed_document.get('metadata', {}).get('source_type')}")
    print(f"Title: {processed_document.get('metadata', {}).get('title')}")
    print(f"Duration (sec): {processed_document.get('metadata', {}).get('duration_sec')}")
    print(f"Content (first 500 chars): {processed_document.get('content', '')[:500]}...")
    print(f"Number of Chunks: {len(processed_document.get('chunks', []))}")
    if processed_document.get('error'):
        print(f"Error: {processed_document.get('error')}")

except Exception as e:
    print(f"An error occurred during pipeline execution: {e}")