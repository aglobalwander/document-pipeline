#!/usr/bin/env python3
"""
Lightweight batch PDF-to-markdown converter using PyMuPDF.
No GPU models required - pure text extraction with basic structure preservation.

Usage:
    poetry run python scripts/document_processing/batch_pdf_to_markdown.py \
        --input_dir /path/to/pdfs \
        --output_dir /path/to/output \
        [--suffix _docling]  # match Docling naming convention
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pymupdf  # PyMuPDF

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_pdf_to_markdown(pdf_path: Path) -> str:
    """Extract text from PDF and convert to basic markdown."""
    doc = pymupdf.open(str(pdf_path))
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Get text blocks with position info for structure detection
        blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)["blocks"]

        page_lines = []
        for block in blocks:
            if block["type"] != 0:  # Skip image blocks
                continue

            for line in block["lines"]:
                text = ""
                max_size = 0
                is_bold = False

                for span in line["spans"]:
                    text += span["text"]
                    max_size = max(max_size, span["size"])
                    if "bold" in span["font"].lower() or "Bold" in span["font"]:
                        is_bold = True

                text = text.strip()
                if not text:
                    continue

                # Detect headings by font size
                if max_size >= 18:
                    text = f"# {text}"
                elif max_size >= 14 and is_bold:
                    text = f"## {text}"
                elif max_size >= 12 and is_bold:
                    text = f"### {text}"
                elif is_bold and len(text) < 120:
                    text = f"**{text}**"

                page_lines.append(text)

        if page_lines:
            pages.append("\n".join(page_lines))

    doc.close()

    # Join pages with separator
    full_text = "\n\n---\n\n".join(pages)

    # Clean up excessive whitespace
    full_text = re.sub(r'\n{4,}', '\n\n\n', full_text)

    return full_text


def normalize_filename(name: str) -> str:
    """Normalize PDF filename to clean markdown name."""
    stem = Path(name).stem
    # Replace spaces and special chars
    stem = stem.replace(' ', '_')
    # Remove parentheses but keep content
    stem = re.sub(r'[()]', '', stem)
    # Lowercase
    stem = stem.lower()
    return stem


def process_directory(input_dir: Path, output_dir: Path, suffix: str = "") -> dict:
    """Process all PDFs in directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(input_dir.glob("*.pdf")) + sorted(input_dir.glob("*.PDF"))
    results = {"success": [], "failed": []}

    logger.info(f"Found {len(pdfs)} PDFs in {input_dir}")

    for pdf_path in pdfs:
        try:
            logger.info(f"Processing: {pdf_path.name}")
            markdown = extract_pdf_to_markdown(pdf_path)

            out_name = f"{normalize_filename(pdf_path.name)}{suffix}.md"
            out_path = output_dir / out_name
            out_path.write_text(markdown, encoding="utf-8")

            char_count = len(markdown)
            logger.info(f"  -> {out_name} ({char_count:,} chars)")
            results["success"].append({"file": pdf_path.name, "output": out_name, "chars": char_count})

        except Exception as e:
            logger.error(f"  FAILED: {pdf_path.name} - {e}")
            results["failed"].append({"file": pdf_path.name, "error": str(e)})

    return results


def main():
    parser = argparse.ArgumentParser(description="Batch PDF to Markdown converter (PyMuPDF)")
    parser.add_argument("--input_dir", required=True, help="Directory containing PDFs")
    parser.add_argument("--output_dir", required=True, help="Output directory for markdown files")
    parser.add_argument("--suffix", default="", help="Suffix to add to output filenames (e.g. _docling)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    results = process_directory(input_dir, output_dir, args.suffix)

    logger.info(f"\nResults: {len(results['success'])} succeeded, {len(results['failed'])} failed")
    if results["failed"]:
        for f in results["failed"]:
            logger.error(f"  Failed: {f['file']} - {f['error']}")


if __name__ == "__main__":
    main()
