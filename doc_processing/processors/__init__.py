"""PDF processors for document processing pipeline.

Importing this package must stay cheap: the concrete processors pull in heavy
optional dependencies (docling, PyMuPDF, provider SDKs) that are only needed
when a specific processor is actually used. Names are therefore resolved
lazily through PEP 562 module ``__getattr__``, so both of these keep working
without importing docling:

    from doc_processing.processors import EnhancedDoclingPDFProcessor
    from doc_processing.processors.pymupdf_processor import PyMuPDFProcessor
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .enhanced_docling_processor import EnhancedDoclingPDFProcessor
    from .gpt_vision_processor import GPTPVisionProcessor
    from .pdf_processor import (
        DoclingPDFProcessor,
        GeminiPDFProcessor,
        GPTPDFProcessor,
        PDFProcessor,
    )
    from .pymupdf_processor import PyMuPDFProcessor

_EXPORTS: Dict[str, str] = {
    "PDFProcessor": ".pdf_processor",
    "DoclingPDFProcessor": ".pdf_processor",
    "GPTPDFProcessor": ".pdf_processor",
    "GeminiPDFProcessor": ".pdf_processor",
    "EnhancedDoclingPDFProcessor": ".enhanced_docling_processor",
    "PyMuPDFProcessor": ".pymupdf_processor",
    "GPTPVisionProcessor": ".gpt_vision_processor",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve processor classes on first access instead of at import time."""
    try:
        module_name = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value  # cache for subsequent lookups
    return value


def __dir__() -> list:
    return sorted(set(globals()) | set(_EXPORTS))