"""Enhanced PDF Processor using Docling with multi-format output and caching.

Design notes:
- One ``DocumentConverter`` is built per processor instance and reused for every
  document, so Docling's model/pipeline initialisation is paid once per run
  instead of once per file.
- ``use_cache`` stores one finished extraction result per (file content hash,
  option) pair. Docling conversion is atomic, so the previous per-page
  checkpoints could never avoid re-conversion while writing a growing JSON file
  after every page.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from doc_processing.config import get_settings
from doc_processing.embedding.base import BaseProcessor
from doc_processing.utils.file_utils import calculate_file_hash
from doc_processing.utils.processing_cache import ProcessingCache

logger = logging.getLogger(__name__)

# Document keys persisted in the result cache payload.
_CACHE_PAYLOAD_KEYS = (
    "content",
    "text_content",
    "markdown_content",
    "json_content",
    "pages",
    "tables",
    "metadata",
)


class EnhancedDoclingPDFProcessor(BaseProcessor):
    """Enhanced processor for PDF files using Docling with multi-format output."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.settings = get_settings()

        # Docling pipeline options. ``None`` means "leave Docling's own default
        # in place", so behaviour changes only when a caller asks for it.
        self.docling_extract_tables = self.config.get("docling_extract_tables", True)
        self.do_ocr = self.config.get("docling_do_ocr")
        self.generate_page_images = self.config.get("docling_generate_page_images")
        self.images_scale = self.config.get("docling_images_scale")
        self.do_picture_classification = self.config.get("docling_do_picture_classification")
        self.do_code_enrichment = self.config.get("docling_do_code_enrichment")
        self.do_formula_enrichment = self.config.get("docling_do_formula_enrichment")

        # Output format options
        self.output_format = self.config.get("output_format", "text")
        self.output_all_formats = self.config.get("output_all_formats", True)

        # Caching options
        self.use_cache = self.config.get("use_cache", True)
        self.cache = ProcessingCache() if self.use_cache else None

        # Reused across documents (see module docstring)
        self._converter = None
        self._converter_options: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _requested_pipeline_options(self) -> Dict[str, Any]:
        """Docling options requested by config; ``None`` values are unset."""
        return {
            "do_table_structure": self.docling_extract_tables,
            "do_ocr": self.do_ocr,
            "generate_page_images": self.generate_page_images,
            "images_scale": self.images_scale,
            "do_picture_classification": self.do_picture_classification,
            "do_code_enrichment": self.do_code_enrichment,
            "do_formula_enrichment": self.do_formula_enrichment,
        }

    def _get_converter(self):
        """Build the Docling converter once, then reuse it for every document."""
        if self._converter is not None:
            return self._converter

        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        requested = {
            key: value
            for key, value in self._requested_pipeline_options().items()
            if value is not None
        }
        # Only pass options this Docling build understands.
        supported = set(getattr(PdfPipelineOptions, "model_fields", {}) or {})
        accepted = {key: value for key, value in requested.items() if key in supported}
        unsupported = sorted(set(requested) - set(accepted))
        if unsupported:
            self.logger.warning(f"Docling build does not support options: {unsupported}")

        pipeline_options = PdfPipelineOptions(**accepted)
        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        self._converter_options = accepted
        self.logger.info(f"Initialized Docling converter with options: {accepted}")
        return self._converter

    def _cache_key(self, source_path: str) -> str:
        """Cache key from file content hash plus the effective extraction options."""
        path = Path(source_path)
        try:
            file_hash = calculate_file_hash(path)
        except Exception as exc:  # noqa: BLE001 - fall back to a path-based key
            self.logger.warning(f"Could not hash {path} for caching ({exc}); using path key")
            file_hash = hashlib.md5(source_path.encode()).hexdigest()

        options = json.dumps(
            {
                "pipeline": self._requested_pipeline_options(),
                "output_format": self.output_format,
                "output_all_formats": self.output_all_formats,
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(f"{file_hash}|{options}".encode()).hexdigest()[:16]
        return f"{path.stem}_{digest}"

# ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text/markdown/JSON from a PDF, reusing a cached result if valid.

        Args:
            document: Loaded document dictionary with a ``source_path``.

        Returns:
            Document dictionary with extracted content, or an ``error`` key.
        """
        self.logger.info(
            "Processing document with Docling: "
            f"{document.get('metadata', {}).get('filename', 'unknown')}"
        )

        source_path = document.get("source_path")
        if not source_path:
            raise ValueError("Document missing source_path")

        cache_key = self._cache_key(source_path) if self.use_cache else None
        if cache_key:
            cached = self.cache.load_result(cache_key)
            payload = (cached or {}).get("payload") or {}
            if payload:
                self.logger.info(f"Reusing cached Docling result for cache key {cache_key}")
                document.update(payload)
                document["processing_method"] = "docling_cached"
                return document

        try:
            converter = self._get_converter()
            self.logger.debug(f"Converting document: {source_path}")
            result = converter.convert(source_path)

            if not result or not hasattr(result, "document") or not result.document:
                raise ValueError("Docling conversion failed or returned an empty result.")

            docling_doc = result.document

            text_content = ""
            try:
                text_content = docling_doc.export_to_text()
                self.logger.info(f"  - Text: {len(text_content)} characters")
            except Exception as exc:  # noqa: BLE001 - export is best effort
                self.logger.warning(f"Failed to export to text: {exc}")

            markdown_content = ""
            try:
                markdown_content = docling_doc.export_to_markdown()
                self.logger.info(f"  - Markdown: {len(markdown_content)} characters")
            except Exception as exc:  # noqa: BLE001 - export is best effort
                self.logger.warning(f"Failed to export to markdown: {exc}")

            # Docling has no JSON export; build a small representation instead.
            json_content = "{}"
            try:
                page_texts = self._split_content_by_pages(
                    markdown_content, text_content, docling_doc
                )
                json_data = {
                    "metadata": {
                        "filename": document.get("metadata", {}).get("filename", ""),
                        "num_pages": len(docling_doc.pages) if hasattr(docling_doc, "pages") else 0,
                    },
                    "content": text_content,
                    "pages": page_texts,
                }
                json_content = json.dumps(json_data, indent=2)
                self.logger.info(f"  - JSON: {len(json_content)} characters")
            except Exception as exc:  # noqa: BLE001 - export is best effort
                self.logger.warning(f"Failed to create JSON representation: {exc}")

            if self.output_format == "markdown" and markdown_content:
                document["content"] = markdown_content
            elif self.output_format == "json" and json_content:
                document["content"] = json_content
            else:
                document["content"] = text_content

            if self.output_all_formats:
                if text_content:
                    document["text_content"] = text_content
                if markdown_content:
                    document["markdown_content"] = markdown_content
                if json_content:
                    document["json_content"] = json_content

            if (
                self.docling_extract_tables
                and hasattr(docling_doc, "tables")
                and docling_doc.tables
            ):
                document["tables"] = self._extract_tables_from_docling(docling_doc)
                self.logger.info(f"Extracted {len(document['tables'])} tables from document")

            pages_count = len(docling_doc.pages) if hasattr(docling_doc, "pages") else 0
            document.setdefault("metadata", {})
            document["metadata"]["num_pages"] = pages_count
            document["metadata"]["num_processed_pages"] = pages_count

            document["pages"] = []
            if hasattr(docling_doc, "pages") and docling_doc.pages:
                for index, page in enumerate(docling_doc.pages):
                    page_num = page.page_number if hasattr(page, "page_number") else index + 1
                    if hasattr(page, "export_to_text"):
                        page_content = page.export_to_text()
                    else:
                        page_content = self._extract_page_text_from_docling(page)
                    document["pages"].append(
                        {
                            "page_number": page_num,
                            "text": f"\n\nPage {page_num}\n{'-' * 40}\n{page_content}",
                        }
                    )
                self.logger.info(f"Processed {len(document['pages'])} individual pages")
            else:
                self.logger.warning("Document does not have 'pages' attribute or it's empty.")

            document["processing_method"] = "docling"

            if cache_key:
                payload = {
                    key: document[key] for key in _CACHE_PAYLOAD_KEYS if key in document
                }
                try:
                    self.cache.save_result(cache_key, payload)
                except Exception as exc:  # noqa: BLE001 - caching must never fail a run
                    self.logger.warning(f"Could not cache result for {cache_key}: {exc}")

            self.logger.info("Successfully processed document with Docling")
            return document

        except ImportError:
            self.logger.error(
                "Docling is not installed. Please install it to use EnhancedDoclingPDFProcessor."
            )
            document["error"] = "Docling not installed."
            return document
        except Exception as exc:  # noqa: BLE001 - reported through the document
            self.logger.error(f"Error processing with Docling: {exc}")
            document["error"] = f"Docling processing error: {exc}"
            return document

# ------------------------------------------------------------------
    # Docling content helpers
    # ------------------------------------------------------------------

    def _split_content_by_pages(
        self, markdown_content: str, text_content: str, docling_doc: Any
    ) -> List[Dict[str, Any]]:
        """Split document content into per-page chunks.

        Uses Docling's internal page structure to extract content per page and
        falls back to splitting the exported text evenly.
        """
        pages = []
        num_pages = len(docling_doc.pages) if hasattr(docling_doc, "pages") else 0

        if num_pages == 0:
            return pages

        if hasattr(docling_doc, "pages"):
            for i, page in enumerate(docling_doc.pages):
                page_num = i + 1
                page_text = self._extract_page_text_from_docling(page)
                pages.append({
                    "page_number": page_num,
                    "text": page_text,
                })

        # If per-page extraction produced nothing, split the text evenly.
        if not any(p.get("text") for p in pages) and text_content:
            lines = text_content.split("\n")
            lines_per_page = max(1, len(lines) // num_pages)

            pages = []
            for i in range(num_pages):
                start_idx = i * lines_per_page
                end_idx = start_idx + lines_per_page if i < num_pages - 1 else len(lines)
                pages.append({
                    "page_number": i + 1,
                    "text": "\n".join(lines[start_idx:end_idx]),
                })

        return pages

    def _extract_page_text_from_docling(self, page: Any) -> str:
        """Extract text from a Docling page by iterating over its items/elements."""
        page_content = []

        # Approach 1: Check for items attribute (common in newer Docling)
        if hasattr(page, "items"):
            for item in page.items:
                if hasattr(item, "text") and item.text:
                    page_content.append(item.text)
                elif hasattr(item, "content") and item.content:
                    page_content.append(str(item.content))

        # Approach 2: Check for children attribute
        if not page_content and hasattr(page, "children"):
            for child in page.children:
                if hasattr(child, "text") and child.text:
                    page_content.append(child.text)

        # Approach 3: Check for body/main_text
        if not page_content and hasattr(page, "body"):
            if hasattr(page.body, "text"):
                page_content.append(page.body.text)
            elif isinstance(page.body, str):
                page_content.append(page.body)

        # Approach 4: Original blocks approach
        if not page_content and hasattr(page, "blocks"):
            for block in page.blocks:
                if hasattr(block, "text") and block.text:
                    page_content.append(block.text)

        return "\n".join(page_content)

    def _extract_tables_from_docling(self, docling_doc: Any) -> List[Dict[str, Any]]:
        """Extract tables from a Docling document as JSON-safe data."""
        tables = []
        if hasattr(docling_doc, "tables"):
            for table_idx, table in enumerate(docling_doc.tables):
                table_data = {
                    "table_index": table_idx,
                    "page_number": (
                        table.page.page_number
                        if hasattr(table, "page") and hasattr(table.page, "page_number")
                        else None
                    ),
                    "rows": [],
                }
                if hasattr(table, "data") and table.data:
                    table_data["rows"] = self._json_safe_rows(table.data)
                tables.append(table_data)
        return tables

    @staticmethod
    def _json_safe_rows(table_data: Any) -> Any:
        """Convert Docling ``TableData`` into plain JSON-serializable rows.

        ``TableData`` is a pydantic model, so a document carrying tables cannot
        be JSON-encoded (cache writes, ``--output_format json``) until it is
        reduced to plain data.
        """
        for dumper_name in ("model_dump", "dict"):
            dumper = getattr(table_data, dumper_name, None)
            if callable(dumper):
                try:
                    return json.loads(json.dumps(dumper(), default=str))
                except Exception:  # noqa: BLE001 - fall through to a string form
                    continue
        if table_data is None or isinstance(table_data, (str, int, float, list, dict)):
            return table_data
        return str(table_data)
