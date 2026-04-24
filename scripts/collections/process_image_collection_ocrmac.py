#!/usr/bin/env python3
"""Deduplicate and OCR an image collection using macOS Vision via ocrmac."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ocrmac.ocrmac import text_from_image


DEFAULT_INPUT_DIR = Path(
    "/Users/scottwilliams/Development/_02_platforms/pipeline-documents/data/input/images"
)
DEFAULT_OUTPUT_DIR = Path(
    "/Users/scottwilliams/Development/_02_platforms/pipeline-documents/"
    "data/output/collections/islc-module-2-images"
)


@dataclass
class ImageRecord:
    source_file: str
    sha256: str
    duplicate_of: str | None
    included: bool
    output_text_file: str | None
    extracted_characters: int


def iter_image_files(input_dir: Path) -> Iterable[Path]:
    supported = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in supported:
            yield path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(lines: list[tuple[str, float, list[float]]]) -> str:
    ordered = sorted(lines, key=lambda item: (-item[2][1], item[2][0]))
    texts = [line[0].strip() for line in ordered if line and line[0].strip()]
    return "\n".join(texts).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--language",
        action="append",
        dest="languages",
        default=["en-US"],
        help="Preferred OCR language code. Can be passed multiple times.",
    )
    args = parser.parse_args()

    text_dir = args.output_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    seen_hashes: dict[str, str] = {}
    records: list[ImageRecord] = []

    for image_path in iter_image_files(args.input_dir):
        if image_path.name.startswith("Sample"):
            continue

        sha = file_hash(image_path)
        duplicate_of = seen_hashes.get(sha)
        if duplicate_of:
            records.append(
                ImageRecord(
                    source_file=image_path.name,
                    sha256=sha,
                    duplicate_of=duplicate_of,
                    included=False,
                    output_text_file=None,
                    extracted_characters=0,
                )
            )
            continue

        seen_hashes[sha] = image_path.name
        lines = text_from_image(
            str(image_path),
            recognition_level="accurate",
            language_preference=args.languages,
            confidence_threshold=0.0,
            detail=True,
        )
        text = clean_text(lines)
        output_name = f"{image_path.stem}_ocr.txt"
        output_path = text_dir / output_name
        output_path.write_text(text, encoding="utf-8")
        records.append(
            ImageRecord(
                source_file=image_path.name,
                sha256=sha,
                duplicate_of=None,
                included=True,
                output_text_file=str(output_path),
                extracted_characters=len(text),
            )
        )

    manifest = {
        "collection_name": "islc-module-2-images",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(args.input_dir),
        "output_dir": str(args.output_dir),
        "image_count_total": len(list(iter_image_files(args.input_dir))),
        "image_count_processed": sum(1 for record in records if record.included),
        "duplicate_count_skipped": sum(1 for record in records if not record.included),
        "records": [asdict(record) for record in records],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    inventory_lines = [
        "# ISLC Module 2 image OCR inventory",
        "",
        f"- Input directory: `{args.input_dir}`",
        f"- Unique images processed: `{manifest['image_count_processed']}`",
        f"- Exact duplicates skipped: `{manifest['duplicate_count_skipped']}`",
        "",
        "## Files",
    ]
    for record in records:
        if record.included:
            inventory_lines.append(
                f"- `{record.source_file}` -> `{Path(record.output_text_file).name}` "
                f"({record.extracted_characters} chars)"
            )
        else:
            inventory_lines.append(
                f"- `{record.source_file}` skipped as duplicate of `{record.duplicate_of}`"
            )
    (args.output_dir / "inventory.md").write_text(
        "\n".join(inventory_lines) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
