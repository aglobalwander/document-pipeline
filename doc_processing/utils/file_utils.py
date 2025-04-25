"""Utility functions for file operations."""

import os
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

def calculate_file_hash(file_path: Path, algorithm: str = 'sha256', buffer_size: int = 65536) -> str:
    """Calculates the hash of a file.

    Args:
        file_path: Path to the file.
        algorithm: Hashing algorithm (e.g., 'sha256', 'md5').
        buffer_size: Size of chunks to read for hashing large files.

    Returns:
        Hexadecimal hash string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there's an error reading the file.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {file_path}")

    hasher = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        raise IOError(f"Error calculating hash for {file_path}: {e}") from e

def get_file_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts common metadata from a file.

    Args:
        file_path: Path to the file.

    Returns:
        Dictionary containing file metadata.
    """
    metadata = {}
    try:
        if not file_path.is_file():
            logger.warning(f"Metadata requested for non-existent file: {file_path}")
            return {"error": "File not found"}

        metadata['filename'] = file_path.name
        # metadata['file_path'] = str(file_path.resolve()) # Consider if full path is needed
        metadata['file_extension'] = file_path.suffix.lower()
        stat_info = os.stat(file_path)
        metadata['file_size'] = stat_info.st_size
        # Convert timestamps to ISO 8601 format in UTC
        metadata['created_at_utc'] = datetime.fromtimestamp(stat_info.st_ctime, tz=timezone.utc).isoformat()
        metadata['modified_at_utc'] = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat()
        metadata['accessed_at_utc'] = datetime.fromtimestamp(stat_info.st_atime, tz=timezone.utc).isoformat()

        # Calculate file hash (optional, can be time-consuming for large files)
        try:
            metadata['file_hash_sha256'] = calculate_file_hash(file_path)
        except Exception as hash_error:
            logger.warning(f"Could not calculate hash for {file_path}: {hash_error}")
            metadata['file_hash_sha256'] = None

    except Exception as e:
        logger.error(f"Error getting metadata for {file_path}: {e}")
        metadata['error'] = f"Error getting metadata: {e}"

    return metadata