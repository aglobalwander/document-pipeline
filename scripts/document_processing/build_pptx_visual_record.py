#!/usr/bin/env python3
"""Build a visual evidence record for a folder of PowerPoint decks.

The output is designed for downstream KM / Studio Lab use:
- deck-level metadata and source provenance
- slide text and speaker notes
- per-slide PNG screenshots rendered from a LibreOffice PDF export
- embedded media inventory
- keyword-ranked key-slide candidates
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from scripts.document_processing.export_pptx_slides import export_pptx_slide_payload


DEFAULT_INPUT_DIR = Path("data/input/powerpoint")
DEFAULT_OUTPUT_DIR = Path("data/output/powerpoint_visual_record")
DEFAULT_LIBREOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")

KEYWORD_PATTERNS: list[tuple[str, str, int]] = [
    ("ttg", r"\bTTGs?\b|Transdisciplinary Transfer Goals?", 10),
    ("dtg", r"\bDTGs?\b|Disciplinary Transfer Goals?", 10),
    ("transfer_goals", r"Transfer Goals?|Long[- ]Term Transfer Goals?", 8),
    ("macro_curriculum", r"Macro Curriculum|Curriculum Blueprint|Blueprint", 8),
    ("gvc", r"Guaranteed and Viable Curriculum|\bGVC\b", 8),
    ("eagles_eslr", r"\bEAGLES?\b|\bESLRs?\b|Expected Schoolwide", 7),
    ("core_commitments", r"Core Commitments?|Mission|Vision|Core Values|Cultures?", 6),
    ("learning_ecosystem", r"Learning Ecosystem|SAS Learning Ecosystem", 6),
    ("principles_of_practice", r"Principles of Practice|\bPoP\b|Learning Principles", 6),
    ("wasc", r"\bWASC\b|Areas? of Growth|Action Plan|self[- ]study", 5),
    ("priority_strategy", r"Priorit(?:y|ies)|Strategic|SAS Forward|Pillars?", 5),
    ("understandings_questions", r"Enduring Understandings?|\bEUs?\b|Essential Questions?|\bEQs?\b", 5),
    ("performance_evidence", r"Performance Tasks?|Cornerstone Tasks?|Evidence|Indicators?", 5),
    ("alphabet_glossary", r"Alphabet Soup|Glossary|Acronyms?|Terms", 5),
]


def slugify(value: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return (slug or "deck")[:max_len].strip("-") or "deck"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_to(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def file_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def convert_pptx_to_pdf(pptx_path: Path, output_dir: Path, libreoffice: Path) -> Path:
    if not libreoffice.exists():
        raise FileNotFoundError(f"LibreOffice not found at {libreoffice}")

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptx_pdf_") as tmp:
        tmp_dir = Path(tmp)
        command = [
            str(libreoffice),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_dir),
            str(pptx_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice PDF export failed for {pptx_path.name}: {result.stderr or result.stdout}"
            )

        pdf_candidates = sorted(tmp_dir.glob("*.pdf"))
        if not pdf_candidates:
            raise RuntimeError(f"LibreOffice did not create a PDF for {pptx_path.name}")

        pdf_path = output_dir / "deck.pdf"
        shutil.copy2(pdf_candidates[0], pdf_path)
        return pdf_path


def extract_slide_visibility(pptx_path: Path) -> list[dict[str, Any]]:
    """Return slide visibility metadata in presentation order.

    PowerPoint stores hidden-slide state on the slide XML. LibreOffice omits
    hidden slides during PDF export, so rendered pages must be mapped back to
    visible PPTX slide numbers rather than raw page indexes.
    """

    presentation_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
    relationships_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    package_rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"

    with zipfile.ZipFile(pptx_path) as archive:
        presentation = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
        rels = ElementTree.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}

        slides: list[dict[str, Any]] = []
        slide_id_list = presentation.find(f".//{presentation_ns}sldIdLst")
        if slide_id_list is None:
            return slides

        for slide_number, slide_id in enumerate(slide_id_list, start=1):
            relationship_id = slide_id.attrib[f"{relationships_ns}id"]
            target = relmap[relationship_id]
            target = target[3:] if target.startswith("../") else target
            slide_xml_path = f"ppt/{target}" if not target.startswith("ppt/") else target
            slide_xml = ElementTree.fromstring(archive.read(slide_xml_path))
            slides.append(
                {
                    "slide_number": slide_number,
                    "slide_xml_path": slide_xml_path,
                    "hidden": slide_xml.attrib.get("show") == "0",
                    "relationship_id": relationship_id,
                    "relationship_type": slide_id.attrib.get(f"{package_rel_ns}type"),
                }
            )
    return slides


def render_pdf_pages(
    pdf_path: Path,
    slides_dir: Path,
    visible_slide_numbers: list[int],
    scale: float = 2.0,
) -> list[dict[str, Any]]:
    import fitz  # PyMuPDF

    try:
        fitz.TOOLS.mupdf_display_errors(False)
    except Exception:
        pass

    slides_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            slide_number = (
                visible_slide_numbers[page_index - 1]
                if page_index <= len(visible_slide_numbers)
                else page_index
            )
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image_path = slides_dir / f"slide_{slide_number:03d}.png"
            pix.save(image_path)
            rendered.append(
                {
                    "slide_number": slide_number,
                    "pdf_page_number": page_index,
                    "image_path": str(image_path),
                    "width_px": pix.width,
                    "height_px": pix.height,
                }
            )
    return rendered


def extract_embedded_media(pptx_path: Path, media_dir: Path) -> list[dict[str, Any]]:
    media_dir.mkdir(parents=True, exist_ok=True)
    media: list[dict[str, Any]] = []
    with zipfile.ZipFile(pptx_path) as archive:
        for name in archive.namelist():
            if not name.startswith("ppt/media/") or name.endswith("/"):
                continue
            source_name = Path(name).name
            out_path = media_dir / source_name
            data = archive.read(name)
            out_path.write_bytes(data)
            media.append(
                {
                    "source_name": name,
                    "filename": source_name,
                    "path": str(out_path),
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    return media


def rank_key_slides(slides: list[dict[str, Any]], image_by_slide: dict[int, str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    compiled = [(label, re.compile(pattern, re.IGNORECASE), weight) for label, pattern, weight in KEYWORD_PATTERNS]
    for slide in slides:
        text = "\n".join(
            str(slide.get(field) or "")
            for field in ["title", "content", "notes", "normalized_text"]
        )
        matches: list[dict[str, Any]] = []
        score = 0
        for label, pattern, weight in compiled:
            count = len(pattern.findall(text))
            if count:
                score += weight * count
                matches.append({"label": label, "count": count, "weight": weight})
        if score:
            slide_number = int(slide["slide_number"])
            candidates.append(
                {
                    "slide_number": slide_number,
                    "score": score,
                    "title": slide.get("title"),
                    "hidden": bool(slide.get("hidden", False)),
                    "pdf_page_number": slide.get("pdf_page_number"),
                    "matches": matches,
                    "image_path": image_by_slide.get(slide_number),
                    "word_count": slide.get("word_count", 0),
                    "content_hash": slide.get("content_hash"),
                }
            )
    candidates.sort(key=lambda item: (-item["score"], item["slide_number"]))
    return candidates


def process_deck(pptx_path: Path, output_root: Path, libreoffice: Path, render_scale: float) -> dict[str, Any]:
    source_hash = sha256_file(pptx_path)
    deck_slug = f"{slugify(pptx_path.stem)}-{source_hash[:10]}"
    deck_dir = output_root / "decks" / deck_slug
    slides_dir = deck_dir / "slides"
    media_dir = deck_dir / "media"
    deck_dir.mkdir(parents=True, exist_ok=True)

    payload = export_pptx_slide_payload(pptx_path)
    visibility = extract_slide_visibility(pptx_path)
    visible_slide_numbers = [item["slide_number"] for item in visibility if not item["hidden"]]
    visibility_by_slide = {item["slide_number"]: item for item in visibility}
    pdf_path = convert_pptx_to_pdf(pptx_path, deck_dir, libreoffice)
    rendered = render_pdf_pages(pdf_path, slides_dir, visible_slide_numbers, scale=render_scale)
    image_by_slide = {item["slide_number"]: relative_to(Path(item["image_path"]), output_root) for item in rendered}
    render_by_slide = {item["slide_number"]: item for item in rendered}

    slides = []
    for slide in payload["slides"]:
        slide = dict(slide)
        slide_number = int(slide["slide_number"])
        slide_visibility = visibility_by_slide.get(slide_number, {})
        slide["hidden"] = bool(slide_visibility.get("hidden", False))
        slide["slide_xml_path"] = slide_visibility.get("slide_xml_path")
        slide["image_path"] = image_by_slide.get(slide_number)
        render_info = render_by_slide.get(slide_number, {})
        slide["pdf_page_number"] = render_info.get("pdf_page_number")
        slide["image_width_px"] = render_info.get("width_px")
        slide["image_height_px"] = render_info.get("height_px")
        slides.append(slide)

    media = extract_embedded_media(pptx_path, media_dir)
    for item in media:
        item["path"] = relative_to(Path(item["path"]), output_root)

    deck_payload = {
        "source_path": str(pptx_path),
        "filename": pptx_path.name,
        "source_sha256": source_hash,
        "source_size_bytes": pptx_path.stat().st_size,
        "source_modified_utc": file_timestamp(pptx_path),
        "deck_slug": deck_slug,
        "slide_count": payload["slide_count"],
        "visible_slide_count": len(visible_slide_numbers),
        "hidden_slide_count": len(visibility) - len(visible_slide_numbers),
        "rendered_slide_count": len(rendered),
        "render_warning": (
            None
            if len(rendered) == len(visible_slide_numbers)
            else f"PDF rendered {len(rendered)} pages for {len(visible_slide_numbers)} visible slides"
        ),
        "pdf_path": relative_to(pdf_path, output_root),
        "slides": slides,
        "embedded_media": media,
        "key_slide_candidates": rank_key_slides(slides, image_by_slide),
    }
    (deck_dir / "slides.json").write_text(json.dumps(deck_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return deck_payload


def write_summary(output_root: Path, decks: list[dict[str, Any]], failures: list[dict[str, str]], input_dir: Path) -> None:
    all_candidates: list[dict[str, Any]] = []
    for deck in decks:
        for candidate in deck["key_slide_candidates"]:
            item = dict(candidate)
            item["deck_slug"] = deck["deck_slug"]
            item["filename"] = deck["filename"]
            item["source_path"] = deck["source_path"]
            all_candidates.append(item)
    all_candidates.sort(key=lambda item: (-item["score"], item["filename"], item["slide_number"]))

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "output_root": str(output_root),
        "deck_count": len(decks),
        "failure_count": len(failures),
        "slide_count": sum(deck["slide_count"] for deck in decks),
        "visible_slide_count": sum(deck["visible_slide_count"] for deck in decks),
        "hidden_slide_count": sum(deck["hidden_slide_count"] for deck in decks),
        "rendered_slide_count": sum(deck["rendered_slide_count"] for deck in decks),
        "embedded_media_count": sum(len(deck["embedded_media"]) for deck in decks),
        "decks": [
            {
                "filename": deck["filename"],
                "deck_slug": deck["deck_slug"],
                "source_path": deck["source_path"],
                "source_sha256": deck["source_sha256"],
                "source_modified_utc": deck["source_modified_utc"],
                "slide_count": deck["slide_count"],
                "visible_slide_count": deck["visible_slide_count"],
                "hidden_slide_count": deck["hidden_slide_count"],
                "rendered_slide_count": deck["rendered_slide_count"],
                "render_warning": deck["render_warning"],
                "pdf_path": deck["pdf_path"],
                "slides_json": f"decks/{deck['deck_slug']}/slides.json",
                "key_slide_candidate_count": len(deck["key_slide_candidates"]),
                "embedded_media_count": len(deck["embedded_media"]),
            }
            for deck in decks
        ],
        "failures": failures,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_root / "key_slide_candidates.json").write_text(
        json.dumps(all_candidates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    readme = [
        "# PowerPoint Visual Record",
        "",
        f"Generated: {manifest['generated_at_utc']}",
        f"Input directory: `{input_dir}`",
        "",
        "This folder contains rendered slide screenshots, extracted text/notes, embedded media inventories, and key-slide candidates for KM / Studio Lab review.",
        "",
        f"Decks processed: {manifest['deck_count']}",
        f"PPTX slides: {manifest['slide_count']}",
        f"Visible/rendered slides: {manifest['visible_slide_count']}",
        f"Hidden slides: {manifest['hidden_slide_count']}",
        f"Embedded media files: {manifest['embedded_media_count']}",
        "",
        "Primary files:",
        "",
        "- `manifest.json`: deck-level provenance and output paths.",
        "- `key_slide_candidates.json`: keyword-ranked slide candidates for visual/story analysis.",
        "- `decks/<deck_slug>/slides.json`: full per-slide payload for each deck.",
        "- `decks/<deck_slug>/slides/slide_###.png`: rendered slide screenshots.",
    ]
    (output_root / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build visual evidence records from PPTX files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--libreoffice", type=Path, default=DEFAULT_LIBREOFFICE)
    parser.add_argument("--include", help="Regex filter applied to PPTX filenames")
    parser.add_argument("--limit", type=int, help="Process only the first N matching decks")
    parser.add_argument("--render-scale", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true", help="List matching files without writing outputs")
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    pattern = re.compile(args.include, re.IGNORECASE) if args.include else None
    pptx_files = sorted(path for path in input_dir.glob("*.pptx") if not pattern or pattern.search(path.name))
    if args.limit:
        pptx_files = pptx_files[: args.limit]

    if args.dry_run:
        for path in pptx_files:
            print(path)
        print(f"Matched {len(pptx_files)} PPTX file(s).")
        return

    decks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for index, pptx_path in enumerate(pptx_files, start=1):
        print(f"[{index}/{len(pptx_files)}] {pptx_path.name}")
        try:
            decks.append(process_deck(pptx_path.resolve(), output_dir, args.libreoffice, args.render_scale))
        except Exception as exc:
            failures.append({"source_path": str(pptx_path.resolve()), "error": str(exc)})
            print(f"  ERROR: {exc}")

    write_summary(output_dir, decks, failures, input_dir)
    print(f"Processed {len(decks)} deck(s), {sum(deck['slide_count'] for deck in decks)} slide(s).")
    if failures:
        print(f"Failures: {len(failures)}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
