"""CLI for media processing commands."""
import typer
import logging

# Import necessary components (will be implemented later)
# from doc_processing.loaders.audio_loader import AudioLoader
# from doc_processing.processors.deepgram_processor import DeepgramProcessor
# from doc_processing.processors.image_processor import ImageProcessor
# from doc_processing.transformers.video_to_chunks import VideoToChunks
# from weaviate_layer.manage_collections import ingest_rows

logging.basicConfig(level=logging.INFO)

app = typer.Typer()

@app.command("ingest-audio")
def ingest_audio(
    folder_path: str = typer.Argument(..., help="Path to the folder containing audio files."),
    # Add options for Deepgram config if needed
):
    """
    Ingests audio files from a folder into Weaviate.
    """
    logging.info(f"Ingesting audio files from {folder_path}...")
    # Implementation will involve AudioLoader, DeepgramProcessor, and ingest_rows
    pass

@app.command("ingest-images")
def ingest_images(
    folder_path: str = typer.Argument(..., help="Path to the folder containing image files."),
    backend: str = typer.Option("openai", "--backend", help="Image processing backend (openai or gemini)."),
    # Add other options for ImageProcessor config if needed
):
    """
    Ingests image files from a folder into Weaviate.
    """
    logging.info(f"Ingesting image files from {folder_path} with {backend} backend...")
    # Implementation will involve an Image Loader, ImageProcessor, and ingest_rows
    pass

@app.command("ingest-video")
def ingest_video(
    folder_path: str = typer.Argument(..., help="Path to the folder containing video files."),
    # Add options for Deepgram and VideoToChunks config if needed
):
    """
    Ingests video files from a folder into Weaviate (transcript only).
    """
    logging.info(f"Ingesting video files from {folder_path} (transcript only)...")
    # Implementation will involve VideoLoader, DeepgramProcessor, VideoToChunks, and ingest_rows
    pass

if __name__ == "__main__":
    app()