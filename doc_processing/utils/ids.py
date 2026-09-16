"""Stable identifier helpers shared by extraction scripts.

Several standards extractors derived row IDs by hashing text with MD5 and
truncating to 8 hex characters. Keeping one implementation means every
framework produces the same style of ID and the IDs stay reproducible.
"""
import hashlib
from typing import Any


def short_hash(value: Any, length: int = 8) -> str:
    """Return a truncated MD5 hex digest of ``value`` as a string.

    Args:
        value: Value to hash; converted with ``str()`` when not already text.
        length: Number of hex characters to keep.

    Returns:
        Lowercase hex digest of ``length`` characters.
    """
    text = value if isinstance(value, str) else str(value)
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:length]


def generate_unique_id(text: str, prefix: str = "") -> str:
    """Generate a deterministic, content-derived ID.

    Args:
        text: Source text the ID is derived from.
        prefix: Optional prefix such as ``"ISTE_"``.

    Returns:
        ``f"{prefix}{hash}"`` using an 8-character MD5 prefix.
    """
    return f"{prefix}{short_hash(text)}"