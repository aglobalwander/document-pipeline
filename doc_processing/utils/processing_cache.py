"""Processing cache utility for the document pipeline.

Holds two kinds of entries, both rooted in the pipeline data directory
(``<DATA_DIR>/cache``) rather than the current working directory:

- extraction results keyed by content hash + options (``*.result.json``)
- legacy per-document checkpoints (``*.json``)
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from doc_processing.config import get_settings


class ProcessingCache:
    """Filesystem-backed cache for extraction results and checkpoints."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the cache.

        Args:
            cache_dir: Override cache location. Defaults to
                ``<DATA_DIR>/cache`` so cache state never depends on the
                caller's working directory.
        """
        if cache_dir is None:
            cache_dir = Path(get_settings().DATA_DIR) / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Extraction results
    # ------------------------------------------------------------------

    def get_result_path(self, document_id: str) -> Path:
        """Path of the cached extraction result for a document id."""
        return self.cache_dir / f"{document_id}.result.json"

    def save_result(self, document_id: str, payload: Dict[str, Any]) -> None:
        """Persist a finished extraction result atomically.

        Args:
            document_id: Cache key (content hash based).
            payload: Extracted content/metadata to store.
        """
        cache_path = self.get_result_path(document_id)
        data = {
            "document_id": document_id,
            "payload": payload,
            "timestamp": time.time(),
        }
        tmp_path = cache_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, default=str)
        os.replace(tmp_path, cache_path)

    def load_result(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load a cached extraction result; returns None when unusable."""
        cache_path = self.get_result_path(document_id)
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Legacy checkpoints (kept for callers that manage their own resume state)
    # ------------------------------------------------------------------

    def get_cache_path(self, document_id: str) -> Path:
        """Generate a cache file path based on document ID."""
        return self.cache_dir / f"{document_id}.json"

    def save_checkpoint(
        self, document_id: str, processed_pages: Any, metadata: Dict[str, Any]
    ) -> None:
        """Save current processing state to cache."""
        cache_path = self.get_cache_path(document_id)
        checkpoint_data = {
            "document_id": document_id,
            "processed_pages": processed_pages,
            "metadata": metadata,
            "timestamp": time.time(),
        }
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(checkpoint_data, handle, ensure_ascii=False)

    def load_checkpoint(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load processing state from cache if it exists."""
        cache_path = self.get_cache_path(document_id)
        if cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        return None

    def clear_checkpoint(self, document_id: str) -> None:
        """Remove a single checkpoint."""
        cache_path = self.get_cache_path(document_id)
        if cache_path.exists():
            cache_path.unlink()

    def clear_all(self) -> int:
        """Clear every cached entry and return the number of removed files.

        Also removes ``*.tmp`` files left behind when a writer was interrupted
        mid-save.
        """
        cleared = 0
        if not self.cache_dir.exists():
            return cleared

        for pattern in ("*.json", "*.tmp"):
            for cache_file in sorted(self.cache_dir.glob(pattern)):
                cache_file.unlink()
                cleared += 1
        return cleared
