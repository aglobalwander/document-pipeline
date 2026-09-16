"""Loader for video files, extracting the audio track.

The audio track is decoded locally with FFmpeg into 16 kHz mono PCM WAV bytes.
No remote service is contacted; transcription requires a processor that the
caller selects explicitly.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from doc_processing.embedding.base import BaseDocumentLoader
from doc_processing.loaders.audio_loader import decode_to_wav_bytes, ensure_ffmpeg

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_SUFFIXES = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".3gp", ".m4v", ".wmv",
}


class VideoLoader(BaseDocumentLoader):
    """Loads a video file and returns its extracted audio track plus metadata."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initializes the VideoLoader.

        Args:
            config: Optional configuration; supports ``sample_rate``.
        """
        super().__init__(config)
        self.sample_rate = self.config.get("sample_rate", 16000)

    def _build_metadata(
        self, path: Path, initial_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Merge caller metadata with best-effort FFmpeg probe results."""
        metadata: Dict[str, Any] = dict(initial_metadata or {})
        metadata.update({
            "filename": path.name,
            "file_type": "video",
            "extension": path.suffix.lower(),
        })

        try:
            ffmpeg = ensure_ffmpeg()
            probe = ffmpeg.probe(str(path))
            streams = probe.get("streams", [])
            video_stream = next(
                (s for s in streams if s.get("codec_type") == "video"), None
            )
            audio_stream = next(
                (s for s in streams if s.get("codec_type") == "audio"), None
            )
            metadata["has_audio_stream"] = audio_stream is not None

            duration = None
            if video_stream and "duration" in video_stream:
                duration = float(video_stream["duration"])
            elif "duration" in probe.get("format", {}):
                duration = float(probe["format"]["duration"])
            metadata["duration_sec"] = duration
        except Exception as exc:  # noqa: BLE001 - metadata is best effort
            logger.warning(f"Could not probe video metadata for {path}: {exc}")
            metadata.setdefault("duration_sec", None)

        return metadata

    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load a video file and extract its audio track.

        Args:
            source: Path to the video file.

        Returns:
            Document dictionary whose ``content`` holds WAV bytes on success.
            Failures set an ``error`` key instead of raising.
        """
        path = self.validate_source(source)
        document: Dict[str, Any] = {
            "source_path": str(path),
            "content": None,
            "pages": [],
            "metadata": self._build_metadata(path),
        }

        try:
            document["content"] = decode_to_wav_bytes(path, self.sample_rate)
            document["metadata"]["audio_format"] = "wav/pcm_s16le"
            document["metadata"]["sample_rate"] = self.sample_rate
            document["metadata"]["content_bytes"] = len(document["content"])
            logger.info(
                f"Successfully extracted audio from video: {path} "
                f"({len(document['content'])} bytes)"
            )
        except ImportError as exc:
            logger.error(str(exc))
            document["error"] = str(exc)
        except Exception as exc:  # noqa: BLE001 - surfaced in the document payload
            error_msg = f"Error processing video file {path}: {exc}"
            logger.error(error_msg)
            document["metadata"]["error"] = error_msg
            document["error"] = error_msg

        return document

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Dict-in/dict-out contract kept for pipeline compatibility.

        Args:
            document: Dictionary containing the video path in ``content``.

        Returns:
            ``{"content": <wav bytes>, "metadata": {...}}``.
        """
        file_path = (document or {}).get("content")
        initial_metadata = (document or {}).get("metadata", {})

        if not file_path:
            error_msg = "No file path provided in input data."
            logger.error(error_msg)
            return {"content": None, "metadata": {**initial_metadata, "error": error_msg}}

        loaded = self.load(file_path)
        metadata = {**initial_metadata, **loaded.get("metadata", {})}
        if loaded.get("error"):
            metadata["error"] = loaded["error"]
        return {"content": loaded.get("content"), "metadata": metadata}


# Note: This loader requires FFmpeg to be installed and accessible on PATH.
# It returns audio bytes in the 'content' key and video metadata in 'metadata'.
# A transcription processor must be selected explicitly if transcripts are needed.
