"""Loader for audio files.

Normalizes an audio file into 16 kHz mono PCM WAV bytes so a downstream
processor (for example the explicitly opted-in DeepgramProcessor) can consume
it. Decoding happens locally through FFmpeg; no remote API is called here.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from doc_processing.embedding.base import BaseDocumentLoader
from doc_processing.utils.file_utils import get_file_metadata

logger = logging.getLogger(__name__)

# Audio containers this loader accepts.
SUPPORTED_AUDIO_SUFFIXES = {
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wma",
}


def ensure_ffmpeg():
    """Import ffmpeg-python lazily so importing loaders never requires it."""
    try:
        import ffmpeg as _ffmpeg
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "ffmpeg-python is required to load audio/video files. "
            "Run 'poetry install' and make sure the ffmpeg binary is on PATH."
        ) from exc
    return _ffmpeg


def decode_to_wav_bytes(source_path: Path, sample_rate: int = 16000) -> bytes:
    """Decode a supported audio container to mono PCM WAV bytes."""
    ffmpeg = ensure_ffmpeg()
    out, _ = (
        ffmpeg
        .input(str(source_path))
        .output("pipe:", format="wav", acodec="pcm_s16le", ar=str(sample_rate), ac=1)
        .run(capture_stdout=True, capture_stderr=True)
    )
    return out


class AudioLoader(BaseDocumentLoader):
    """Loads an audio file and returns its decoded WAV bytes plus metadata."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initializes the AudioLoader.

        Args:
            config: Optional configuration; supports ``sample_rate``.
        """
        super().__init__(config)
        self.sample_rate = self.config.get("sample_rate", 16000)

    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load an audio file.

        Args:
            source: Path to the audio file.

        Returns:
            Document dictionary whose ``content`` holds WAV bytes on success.
            Failures set an ``error`` key instead of raising, matching
            PDFLoader and VideoLoader behaviour.
        """
        path = self.validate_source(source)
        document: Dict[str, Any] = {
            "source_path": str(path),
            "content": None,
            "pages": [],
            "metadata": {
                "filename": path.name,
                "file_type": "audio",
                "extension": path.suffix.lower(),
            },
        }

        try:
            document["metadata"].update(get_file_metadata(path))
            document["content"] = decode_to_wav_bytes(path, self.sample_rate)
            document["metadata"]["audio_format"] = "wav/pcm_s16le"
            document["metadata"]["sample_rate"] = self.sample_rate
            document["metadata"]["content_bytes"] = len(document["content"])
            self.logger.info(
                f"Decoded audio from {path} ({len(document['content'])} bytes)"
            )
        except ImportError as exc:
            self.logger.error(str(exc))
            document["error"] = str(exc)
        except Exception as exc:  # noqa: BLE001 - surfaced in the document payload
            self.logger.error(f"Error decoding audio file {path}: {exc}")
            document["metadata"]["error"] = f"Error decoding audio file: {exc}"
            document["error"] = str(exc)

        return document