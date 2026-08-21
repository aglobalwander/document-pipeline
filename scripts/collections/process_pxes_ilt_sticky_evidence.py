#!/usr/bin/env python3
"""Prepare and locally OCR the 2026-08-17 PXES ILT evidence photographs.

This collection workflow is intentionally bounded: it preserves source hashes,
creates privacy-safer auto-oriented derivatives, runs local Tesseract OCR, and
builds a row-per-evidence-unit review surface. OCR and Codex-assisted visual
transcriptions remain proposals until a human clears ``manual_review``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = (
    REPO_ROOT
    / "data"
    / "collection_specs"
    / "pxes_ilt_2026_08_17_sticky_evidence.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_box_to_pixels(
    normalized_box: list[float], width: int, height: int
) -> tuple[int, int, int, int]:
    if len(normalized_box) != 4:
        raise ValueError(f"Expected four box values, got {normalized_box!r}")
    left, top, right, bottom = normalized_box
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError(f"Invalid normalized box: {normalized_box!r}")
    return (
        round(left * width),
        round(top * height),
        round(right * width),
        round(bottom * height),
    )


def prepare_image(source: Path, content_rotation_degrees: int) -> tuple[Image.Image, dict[str, Any]]:
    with Image.open(source) as opened:
        exif = opened.getexif()
        metadata = {
            "source_width": opened.width,
            "source_height": opened.height,
            "source_exif_orientation": exif.get(274),
            "source_datetime_original": exif.get(36867),
        }
        prepared = ImageOps.exif_transpose(opened).convert("RGB")
    if content_rotation_degrees:
        prepared = prepared.rotate(content_rotation_degrees, expand=True)
    metadata.update(
        {
            "prepared_width": prepared.width,
            "prepared_height": prepared.height,
            "content_rotation_degrees": content_rotation_degrees,
        }
    )
    return prepared, metadata


def enhance_for_ocr(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    # Full-resolution iPhone frames make local Tesseract unnecessarily slow;
    # 2400 px retains the handwriting scale needed for this review-first lane.
    gray.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.35)
    return gray.filter(ImageFilter.UnsharpMask(radius=1.2, percent=165, threshold=3))


def ocr_image(image: Image.Image, *, page_segmentation_mode: int) -> dict[str, Any]:
    config = f"--oem 3 --psm {page_segmentation_mode}"
    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config=config,
        output_type=pytesseract.Output.DICT,
    )
    line_tokens: dict[tuple[int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    all_confidences: list[float] = []
    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0
        if not text or confidence < 0:
            continue
        token = {
            "text": text,
            "confidence": round(confidence / 100.0, 4),
            "bbox_pixels": {
                "x": int(data["left"][index]),
                "y": int(data["top"][index]),
                "width": int(data["width"][index]),
                "height": int(data["height"][index]),
            },
        }
        key = (
            int(data["page_num"][index]),
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        line_tokens[key].append(token)
        all_confidences.append(confidence / 100.0)

    lines: list[dict[str, Any]] = []
    for line_index, (key, tokens) in enumerate(line_tokens.items(), start=1):
        xs = [token["bbox_pixels"]["x"] for token in tokens]
        ys = [token["bbox_pixels"]["y"] for token in tokens]
        rights = [
            token["bbox_pixels"]["x"] + token["bbox_pixels"]["width"]
            for token in tokens
        ]
        bottoms = [
            token["bbox_pixels"]["y"] + token["bbox_pixels"]["height"]
            for token in tokens
        ]
        lines.append(
            {
                "line_id": f"line-{line_index:03d}",
                "tesseract_group": {
                    "page": key[0],
                    "block": key[1],
                    "paragraph": key[2],
                    "line": key[3],
                },
                "text": " ".join(token["text"] for token in tokens),
                "mean_confidence": round(
                    sum(token["confidence"] for token in tokens) / len(tokens), 4
                ),
                "bbox_pixels": {
                    "x": min(xs),
                    "y": min(ys),
                    "width": max(rights) - min(xs),
                    "height": max(bottoms) - min(ys),
                },
                "tokens": tokens,
                "manual_review": True,
            }
        )

    return {
        "engine": "tesseract",
        "engine_version": str(pytesseract.get_tesseract_version()).splitlines()[0],
        "language": "eng",
        "page_segmentation_mode": page_segmentation_mode,
        "text": "\n".join(line["text"] for line in lines),
        "token_count": len(all_confidences),
        "mean_token_confidence": (
            round(sum(all_confidences) / len(all_confidences), 4)
            if all_confidences
            else None
        ),
        "lines": lines,
        "manual_review": True,
        "limitation": "Local OCR of handwriting is machine-proposed and not a verified transcription.",
    }


def save_ocr_result(result: dict[str, Any], json_path: Path, text_path: Path) -> None:
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(result["text"] + ("\n" if result["text"] else ""), encoding="utf-8")


def create_contact_sheets(
    records: list[dict[str, Any]], output_dir: Path, *, columns: int = 4
) -> list[str]:
    sheet_dir = output_dir / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    cell_width, image_height, label_height = 520, 360, 76
    rows_per_sheet = 4
    page_capacity = columns * rows_per_sheet
    paths: list[str] = []
    for page_index in range(0, len(records), page_capacity):
        page_records = records[page_index : page_index + page_capacity]
        rows = (len(page_records) + columns - 1) // columns
        sheet = Image.new("RGB", (cell_width * columns, (image_height + label_height) * rows), "#f2f1eb")
        for local_index, record in enumerate(page_records):
            crop_path = Path(record["crop_path"])
            with Image.open(crop_path) as crop:
                thumb = crop.convert("RGB")
                thumb.thumbnail((cell_width - 24, image_height - 24))
                x = (local_index % columns) * cell_width + (cell_width - thumb.width) // 2
                y = (local_index // columns) * (image_height + label_height) + 12
                sheet.paste(thumb, (x, y))
            # Draw labels through ImageMagick's companion contact-sheet metadata:
            # a compact index file avoids font/environment variance in Pillow.
        sheet_path = sheet_dir / f"evidence_units_{page_index // page_capacity + 1:02d}.jpg"
        sheet.save(sheet_path, quality=90, optimize=True)
        label_path = sheet_path.with_suffix(".labels.txt")
        label_path.write_text(
            "\n".join(
                f"{record['record_id']}\t{record['layer']}\t{record['source_marker_normalized'] or 'unresolved'}"
                for record in page_records
            )
            + "\n",
            encoding="utf-8",
        )
        paths.append(str(sheet_path))
    return paths


def write_review_guide(output_dir: Path, record_count: int) -> None:
    guide = f"""# PXES ILT sticky-evidence transcription review

This package contains {record_count} cropped evidence units from the August 17,
2026 PXES ILT session. It is transcription staging, not thematic analysis or an
institutional finding.

## Review order

1. Open `contact_sheets/` and the matching crop under `crops/`.
2. Compare `ocr_text_raw` and `proposed_transcription` in
   `review/transcription_review.csv` against the crop.
3. Enter a human-confirmed reading in `human_verified_transcription`.
4. Confirm the source marker separately from the text. Participant initials,
   `PE` (pair echoes), and `ST` (shared threads) are distinct provenance layers.
   Participants authored both the PE and ST notes.
5. Set `manual_review` to `false` only when text, marker, and crop lineage have
   all been visually confirmed. Do not fill gaps by inference.

The red-marker sidebar is the visible substantive capture of the 09:00-09:10
open conversation. Treat its legible content as captured evidence; reserve
`unavailable` only for illegible, occluded, or out-of-frame content.

## Confidence semantics

- `ocr_mean_confidence` is Tesseract's token score; it is not handwriting
  transcription accuracy.
- `transcription_confidence` is a bounded visual proposal (`high`, `medium`, or
  `low`) and still requires human review.
- Blank or crossed-out writing stays bracketed or unresolved until confirmed.

The source photographs remain in Session Planner. Prepared images here are
metadata-stripped working derivatives; successful OCR does not prove downstream
Campaign or Data Analysis interpretation.
"""
    (output_dir / "review" / "REVIEW_GUIDE.md").write_text(guide, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    source_dir = Path(spec["source_dir"])
    output_dir = Path(spec["output_dir"])
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    prepared_dir = output_dir / "prepared"
    enhanced_dir = output_dir / "prepared_ocr"
    full_ocr_dir = output_dir / "ocr" / "raw" / "full"
    crop_dir = output_dir / "crops"
    crop_ocr_dir = output_dir / "ocr" / "raw" / "crops"
    review_dir = output_dir / "review"
    for directory in (
        prepared_dir,
        enhanced_dir,
        full_ocr_dir,
        crop_dir,
        crop_ocr_dir,
        review_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    photos_by_name = {photo["file"]: photo for photo in spec["photos"]}
    source_files = sorted(source_dir.glob("*.JPG"))
    expected_files = sorted(photos_by_name)
    observed_files = [path.name for path in source_files]
    if observed_files != expected_files:
        raise ValueError(
            "Source set differs from spec. "
            f"Expected {expected_files!r}; observed {observed_files!r}"
        )

    source_records: list[dict[str, Any]] = []
    prepared_paths: dict[str, Path] = {}
    seen_hashes: dict[str, str] = {}
    for source in source_files:
        photo_spec = photos_by_name[source.name]
        digest = sha256_file(source)
        duplicate_of = seen_hashes.get(digest)
        if duplicate_of is None:
            seen_hashes[digest] = source.name
        prepared, image_metadata = prepare_image(
            source, int(photo_spec.get("content_rotation_degrees", 0))
        )
        prepared_path = prepared_dir / f"{source.stem}.jpg"
        prepared.save(prepared_path, quality=95, optimize=True)
        prepared_paths[source.name] = prepared_path
        enhanced = enhance_for_ocr(prepared)
        enhanced_path = enhanced_dir / f"{source.stem}_ocr.png"
        enhanced.save(enhanced_path, optimize=True)
        full_ocr = ocr_image(enhanced, page_segmentation_mode=11)
        save_ocr_result(
            full_ocr,
            full_ocr_dir / f"{source.stem}.json",
            full_ocr_dir / f"{source.stem}.txt",
        )
        source_records.append(
            {
                "source_file": source.name,
                "source_path": str(source),
                "sha256": digest,
                "bytes": source.stat().st_size,
                "duplicate_of": duplicate_of,
                "photo_role": photo_spec["role"],
                "prepared_path": str(prepared_path),
                "prepared_ocr_path": str(enhanced_path),
                "ocr_json_path": str(full_ocr_dir / f"{source.stem}.json"),
                "ocr_text_path": str(full_ocr_dir / f"{source.stem}.txt"),
                "ocr_token_count": full_ocr["token_count"],
                "ocr_mean_token_confidence": full_ocr["mean_token_confidence"],
                **image_metadata,
            }
        )
        enhanced.close()
        prepared.close()

    review_records: list[dict[str, Any]] = []
    for unit in spec["evidence_units"]:
        source_name = unit["primary_photo"]
        with Image.open(prepared_paths[source_name]) as prepared:
            pixel_box = normalized_box_to_pixels(
                unit["normalized_box"], prepared.width, prepared.height
            )
            crop = prepared.crop(pixel_box)
        crop_path = crop_dir / f"{unit['record_id']}.jpg"
        crop.save(crop_path, quality=97, optimize=True)
        crop_ocr = ocr_image(enhance_for_ocr(crop), page_segmentation_mode=6)
        crop_ocr_json = crop_ocr_dir / f"{unit['record_id']}.json"
        crop_ocr_text = crop_ocr_dir / f"{unit['record_id']}.txt"
        save_ocr_result(crop_ocr, crop_ocr_json, crop_ocr_text)
        review_records.append(
            {
                "record_id": unit["record_id"],
                "record_type": unit["record_type"],
                "layer": unit["layer"],
                "authorship": unit.get(
                    "authorship",
                    "participant_authored"
                    if unit["record_type"] == "sticky_note"
                    else "not_confirmed",
                ),
                "primary_photo": source_name,
                "duplicate_or_context_photos": "|".join(unit.get("related_photos", [])),
                "crop_path": str(crop_path),
                "normalized_box": json.dumps(unit["normalized_box"]),
                "source_marker_type": unit["source_marker_type"],
                "source_marker_observed": unit.get("source_marker_observed", ""),
                "source_marker_normalized": unit.get("source_marker_normalized", ""),
                "marker_confidence": unit.get("marker_confidence", ""),
                "bva_marker": unit.get("bva_marker", ""),
                "ocr_text_raw": crop_ocr["text"].replace("\n", " | "),
                "ocr_token_count": crop_ocr["token_count"],
                "ocr_mean_confidence": crop_ocr["mean_token_confidence"],
                "proposed_transcription": unit.get("proposed_transcription", ""),
                "transcription_confidence": unit.get("transcription_confidence", ""),
                "human_verified_transcription": "",
                "manual_review": True,
                "manual_review_reason": unit["manual_review_reason"],
                "review_notes": unit.get("review_notes", ""),
                "ocr_json_path": str(crop_ocr_json),
                "ocr_text_path": str(crop_ocr_text),
            }
        )
        crop.close()

    review_csv = review_dir / "transcription_review.csv"
    with review_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_records[0]))
        writer.writeheader()
        writer.writerows(review_records)
    (review_dir / "transcription_review.json").write_text(
        json.dumps(review_records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    contact_sheets = create_contact_sheets(review_records, output_dir)
    write_review_guide(output_dir, len(review_records))

    manifest = {
        "collection_id": spec["collection_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_authority": "Session Planner original photographs",
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "processing_lane": "Pipeline Documents image preparation and OCR staging",
        "ocr_lane": "local Tesseract through Poetry; no paid API",
        "provenance_notes": [
            "Individual sticky notes carry participant initials.",
            "PE pair-echo notes were participant-authored.",
            "ST shared-thread notes were participant-authored.",
            "The red-marker sidebar is the visible substantive capture of the 09:00-09:10 open conversation; only image-illegible or out-of-frame content is unavailable.",
        ],
        "source_image_count": len(source_records),
        "unique_source_image_count": len(seen_hashes),
        "exact_duplicate_count": sum(
            1 for record in source_records if record["duplicate_of"] is not None
        ),
        "evidence_unit_count": len(review_records),
        "sticky_unit_count": sum(
            1 for record in review_records if record["record_type"] == "sticky_note"
        ),
        "discussion_capture_count": sum(
            1 for record in review_records if record["record_type"] == "discussion_board"
        ),
        "manual_review_count": sum(
            1 for record in review_records if record["manual_review"]
        ),
        "review_csv": str(review_csv),
        "review_json": str(review_dir / "transcription_review.json"),
        "contact_sheets": contact_sheets,
        "source_records": source_records,
        "limitations": [
            "Handwriting OCR is incomplete and noisy even when token confidence is high.",
            "Proposed transcriptions were visually staged by Codex and are not human-verified.",
            "Participant initials, PE, and ST are provenance markers, not thematic codes.",
            "Crossed-out or illegible text is not reconstructed by inference.",
            "Prepared derivatives strip EXIF metadata; the source hashes point back to originals.",
            "This package does not establish Campaign analysis or SAS institutional interpretation.",
        ],
    }
    (output_dir / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        key: manifest[key]
        for key in (
            "collection_id",
            "source_image_count",
            "unique_source_image_count",
            "exact_duplicate_count",
            "evidence_unit_count",
            "sticky_unit_count",
            "discussion_capture_count",
            "manual_review_count",
            "review_csv",
        )
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
