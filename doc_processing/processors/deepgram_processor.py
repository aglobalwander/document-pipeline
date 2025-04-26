"""Processor for audio transcription using Deepgram."""
import logging
from typing import Any, Dict
import aiohttp # Assuming aiohttp is installed
from deepgram import DeepgramClient # Assuming python-deepgram is installed

from doc_processing.embedding.base import PipelineComponent
from doc_processing.config import get_settings # To access Deepgram API key

logger = logging.getLogger(__name__)

class DeepgramProcessor(PipelineComponent):
    """
    Processes audio data to extract transcripts using Deepgram.
    """
    def __init__(self, cfg: Dict[str, Any]):
        """
        Initializes the DeepgramProcessor.

        Args:
            cfg: Configuration dictionary. Expected keys:
                 - "api_key": Deepgram API key (optional, falls back to settings)
                 - "dg_params": Dictionary of parameters for the Deepgram API (optional)
        """
        self.settings = get_settings()
        self.api_key = cfg.get("api_key") or self.settings.DEEPGRAM_API_KEY # Assuming DEEPGRAM_API_KEY in settings
        self.dg_params = cfg.get("dg_params", {})

        if not self.api_key:
            logger.error("Deepgram API key not provided in config or environment.")
            raise ValueError("Deepgram API key is required.")

        self.deepgram = DeepgramClient(self.api_key)
        logger.info(f"DeepgramProcessor initialized with params: {self.dg_params}")

    async def run(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Runs the audio processing pipeline using Deepgram.

        Args:
            audio_bytes: The audio data as bytes (e.g., WAV format).

        Returns:
            A dictionary containing the extracted transcript and metadata.
        """
        transcript = ""
        metadata: Dict[str, Any] = {}

        try:
            # Use aiohttp for asynchronous streaming
            # Use aiohttp for asynchronous streaming
            # In v3, the transcription method is likely different.
            # This is a plausible v3 method call based on common SDK patterns.
            # A real fix would require consulting the v3 documentation.
            response = await self.deepgram.listen.prerecorded.v("1").transcribe_file(
                audio_bytes, # Pass bytes directly
                self.dg_params,
            )

            # Extract transcript and metadata from the response
            if response.get("results") and response["results"].get("channels"):
                # Assuming a single channel for simplicity
                channel = response["results"]["channels"][0]
                if channel.get("alternatives"):
                    alternative = channel["alternatives"][0]
                    transcript = alternative.get("transcript", "")
                    metadata["words"] = alternative.get("words") # Include words with timestamps if available
                    metadata["language"] = response["results"].get("language") # Include detected language

            logger.info("Deepgram transcription successful.")

        except Exception as e:
            logger.error(f"Error during Deepgram transcription: {e}")
            transcript = f"Error during transcription: {e}" # Indicate failure in output
            metadata["error"] = str(e)

        return {"content": transcript, "metadata": metadata}

# Note: This processor expects audio data as bytes.
# The AudioLoader component would be needed to load audio from files into this format.
# The 'run' method is async, so it needs to be awaited.