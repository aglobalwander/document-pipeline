"""Loader for video files, extracting audio."""
import logging
from typing import Any, Dict, Union
from pathlib import Path
import ffmpeg # Assuming ffmpeg-python is installed

from doc_processing.embedding.base import PipelineComponent

logger = logging.getLogger(__name__)

class VideoLoader(PipelineComponent):
    """
    Loads video files and extracts the audio track as WAV bytes.
    Requires FFmpeg to be installed and in the system's PATH.
    """
    def __init__(self, cfg: Dict[str, Any] = None):
        """
        Initializes the VideoLoader.

        Args:
            cfg: Configuration dictionary (optional).
        """
        self.cfg = cfg or {}
        logger.info("VideoLoader initialized.")

    def run(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Loads a video file and extracts its audio track.

        Args:
            file_path: The path to the video file.

        Returns:
            A dictionary containing the audio data as WAV bytes and metadata.
            Returns {"content": None, "metadata": {"error": ...}} on failure.
        """
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"File not found: {file_path}")
            return {"content": None, "metadata": {"error": f"File not found: {file_path}"}}

        audio_bytes = None
        metadata: Dict[str, Any] = {
            "filename": path.name,
            "file_type": path.suffix.lower(),
        }

        try:
            # Probe the video file to get metadata like duration
            probe = ffmpeg.probe(str(path))
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)

            if video_stream and 'duration' in video_stream:
                 metadata['duration_sec'] = float(video_stream['duration'])
            elif 'duration' in probe['format']:
                 metadata['duration_sec'] = float(probe['format']['duration'])
            else:
                 metadata['duration_sec'] = None
                 logger.warning(f"Could not determine duration for video: {file_path}")


            if audio_stream:
                # Extract audio as WAV bytes
                out, err = (
                    ffmpeg
                    .input(str(path))
                    .output('pipe:', format='wav', acodec='pcm_s16le', ar='16000') # Output WAV, 16kHz mono PCM
                    .run(capture_stdout=True, capture_stderr=True)
                )
                audio_bytes = out
                logger.info(f"Successfully extracted audio from video: {file_path}")
            else:
                logger.warning(f"No audio stream found in video file: {file_path}")
                metadata["error"] = "No audio stream found in video."


        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error processing video file {file_path}: {e.stderr.decode()}")
            metadata["error"] = f"FFmpeg error: {e.stderr.decode()}"
        except Exception as e:
            logger.error(f"Error processing video file {file_path}: {e}")
            metadata["error"] = f"Error processing video: {e}"

        return {"content": audio_bytes, "metadata": metadata}

# Note: This loader requires FFmpeg to be installed and accessible in the system's PATH.
# It returns audio data as bytes in the 'content' key and video metadata in 'metadata'.
# The subsequent processor (DeepgramProcessor) should be designed to accept audio bytes.