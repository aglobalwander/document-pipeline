#!/usr/bin/env python3
"""Extract SHAPE America 2024 standards into clean source data.

This script intentionally stops before Drupal migration shaping. Hub owns
taxonomy/entity reference mapping, UUID assignment, and import packaging.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


def import_fitz():
    try:
        import fitz as pymupdf

        return pymupdf
    except ModuleNotFoundError:
        project_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            ["poetry", "env", "info", "-p"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        venv_path = result.stdout.strip()
        site_packages = (
            Path(venv_path)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
        if site_packages.exists():
            sys.path.append(str(site_packages))
            import fitz as pymupdf

            return pymupdf
        raise


fitz = import_fitz()


PE_FILENAME = "SHAPE_America_National_Physical_Education_Standards.pdf"
HEALTH_FILENAME = "2024_National_Health_Education_Standards_Educator_Kit.pdf"
PE_SOURCE_URL = "https://www.shapeamerica.org/standards/pe/"
HEALTH_SOURCE_URL = (
    "https://www.shapeamerica.org/Common/Uploaded%20files/Document_manager/"
    "standards/he/2024_National_Health_Education_Standards_Educator_Kit.pdf"
)

DEFAULT_INPUT_DIR = Path("data/input/pdfs/shape")
DEFAULT_OUTPUT_DIR = Path("data/output/standards/shape_2024/clean")

EXTRACTION_METHOD = "pymupdf_blocks_v1"

FRAMEWORK_CONFIG = {
    "shape_pe": {
        "title": "SHAPE America National Physical Education Standards",
        "source_filename": PE_FILENAME,
        "source_url": PE_SOURCE_URL,
        "expected_counts": {"standards": 4, "indicators": 210},
        "min_standard_page": 1,
        "max_standard_number": 4,
    },
    "shape_health": {
        "title": "SHAPE America National Health Education Standards",
        "source_filename": HEALTH_FILENAME,
        "source_url": HEALTH_SOURCE_URL,
        "expected_counts": {"standards": 8, "indicators": 172},
        "min_standard_page": 11,
        "max_standard_number": 8,
    },
}

GRADE_SPAN_LABELS = {
    "2": "PreK-2",
    "5": "3-5",
    "8": "6-8",
    "12": "9-12",
}

CLEAN_ROW_FIELDS = [
    "framework_key",
    "source_type",
    "source_code",
    "source_text",
    "parent_source_code",
    "parent_heading",
    "grade_span_label",
    "rationale",
    "page_number",
    "source_document",
    "source_url",
    "source_sha256",
    "source_kind",
    "extraction_method",
]

STANDARD_HEADING_RE = re.compile(
    r"^(?:STANDARD|Standard)\s+(?P<number>\d+)\s*:?\s*(?P<title>.+?)\s*$"
)
INDICATOR_CODE_RE = re.compile(r"\b(?P<code>[1-8]\.(?:2|5|8|12)\.\d+)\b")
GRADE_LABEL_RE = re.compile(r"\bGrades?\s+(?:PreK-2|3-5|6-8|9-12)\b", re.IGNORECASE)


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_indicator_text(text: str) -> str:
    text = GRADE_LABEL_RE.sub(" ", text)
    text = re.sub(r"Performance Indicators by Grade Span:?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"Copyright .*?shapeamerica\.org.*$", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPO Box 225,.*$", " ", text)
    return clean_text(text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_health_pdf(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return destination

    request = urllib.request.Request(
        HEALTH_SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            destination.write_bytes(response.read())
    except Exception:
        subprocess.run(
            ["curl", "-L", "-A", "Mozilla/5.0", "-sS", "-o", str(destination), HEALTH_SOURCE_URL],
            check=True,
        )

    if destination.stat().st_size == 0:
        raise RuntimeError(f"Downloaded empty Health standards PDF: {destination}")
    return destination


def classify_shape_pdf(pdf_path: Path) -> str:
    name = pdf_path.name
    if name == PE_FILENAME or name == HEALTH_FILENAME or name == "shape_health_2024.pdf":
        return "official_standard"
    return "research_corpus"


def extract_pdf_pages(pdf_path: Path) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            blocks = []
            for block in page.get_text("blocks"):
                text = clean_text(block[4])
                if text:
                    blocks.append(
                        {
                            "x0": float(block[0]),
                            "y0": float(block[1]),
                            "text": text,
                        }
                    )
            blocks.sort(key=lambda item: (round(item["y0"], 1), round(item["x0"], 1)))
            pages.append(
                {
                    "page_number": page_index,
                    "width": float(page.rect.width),
                    "height": float(page.rect.height),
                    "blocks": blocks,
                    "text": "\n".join(block["text"] for block in blocks),
                }
            )
    return pages


def _standard_source_code(framework_key: str, standard_number: str) -> str:
    return f"{framework_key}.standard.{standard_number}"


def _empty_standard_row(
    framework_key: str,
    standard_number: str,
    title: str,
    page_number: int,
    pdf_path: Path,
    source_url: str,
    source_sha256: str,
) -> dict[str, Any]:
    return {
        "framework_key": framework_key,
        "source_type": "standard",
        "source_code": _standard_source_code(framework_key, standard_number),
        "standard_number": standard_number,
        "source_text": title,
        "parent_source_code": "",
        "parent_heading": "",
        "grade_span_label": "",
        "rationale": "",
        "page_number": page_number,
        "source_document": pdf_path.name,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "source_kind": "official_standard",
        "extraction_method": EXTRACTION_METHOD,
    }


def iter_indicator_segments(block_text: str) -> list[tuple[str, str]]:
    matches = list(INDICATOR_CODE_RE.finditer(block_text))
    segments: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        code = match.group("code")
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(block_text)
        source_text = clean_indicator_text(block_text[match.end() : next_start])
        if source_text:
            segments.append((code, source_text))
    return segments


def extract_standard_source(framework_key: str, pdf_path: Path, source_url: str | None = None) -> dict[str, Any]:
    if framework_key not in FRAMEWORK_CONFIG:
        raise ValueError(f"Unsupported SHAPE framework key: {framework_key}")
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    config = FRAMEWORK_CONFIG[framework_key]
    source_url = source_url or str(config["source_url"])
    source_sha256 = sha256_file(pdf_path)
    pages = extract_pdf_pages(pdf_path)
    max_standard_number = int(config["max_standard_number"])
    min_standard_page = int(config["min_standard_page"])

    standards_by_number: dict[str, dict[str, Any]] = {}
    indicators_by_code: dict[str, dict[str, Any]] = {}
    current_standard_number = ""

    for page in pages:
        page_number = int(page["page_number"])
        for block in page["blocks"]:
            block_text = block["text"]

            if page_number >= min_standard_page:
                heading_match = STANDARD_HEADING_RE.match(block_text)
                if heading_match:
                    standard_number = heading_match.group("number")
                    if 1 <= int(standard_number) <= max_standard_number:
                        current_standard_number = standard_number
                        standards_by_number[standard_number] = _empty_standard_row(
                            framework_key=framework_key,
                            standard_number=standard_number,
                            title=clean_text(heading_match.group("title")),
                            page_number=page_number,
                            pdf_path=pdf_path,
                            source_url=source_url,
                            source_sha256=source_sha256,
                        )
                        continue

                if current_standard_number and block_text.startswith("Rationale:"):
                    standards_by_number[current_standard_number]["rationale"] = clean_text(
                        block_text.removeprefix("Rationale:")
                    )
                    continue

            for code, source_text in iter_indicator_segments(block_text):
                standard_number, grade_span_key, _ = code.split(".", 2)
                if int(standard_number) > max_standard_number:
                    continue
                parent_source_code = _standard_source_code(framework_key, standard_number)
                parent = standards_by_number.get(standard_number)
                parent_heading = parent["source_text"] if parent else ""
                rationale = parent["rationale"] if parent else ""
                indicators_by_code[code] = {
                    "framework_key": framework_key,
                    "source_type": "indicator",
                    "source_code": code,
                    "source_text": source_text,
                    "parent_source_code": parent_source_code,
                    "parent_heading": parent_heading,
                    "grade_span_label": GRADE_SPAN_LABELS[grade_span_key],
                    "rationale": rationale,
                    "page_number": page_number,
                    "source_document": pdf_path.name,
                    "source_url": source_url,
                    "source_sha256": source_sha256,
                    "source_kind": "official_standard",
                    "extraction_method": EXTRACTION_METHOD,
                }

    standards = [
        standards_by_number[number]
        for number in sorted(standards_by_number, key=lambda value: int(value))
    ]
    indicators = [
        indicators_by_code[code]
        for code in sorted(
            indicators_by_code,
            key=lambda value: tuple(int(part) for part in value.split(".")),
        )
    ]
    validation = validate_clean_source(
        framework_key=framework_key,
        standards=standards,
        indicators=indicators,
        expected_counts=dict(config["expected_counts"]),
    )
    return {
        "framework_key": framework_key,
        "title": config["title"],
        "source_kind": "official_standard",
        "source_document": pdf_path.name,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "page_count": len(pages),
        "extraction_method": EXTRACTION_METHOD,
        "expected_counts": dict(config["expected_counts"]),
        "standards": standards,
        "indicators": indicators,
        "validation": validation,
    }


def validate_clean_source(
    framework_key: str,
    standards: list[dict[str, Any]],
    indicators: list[dict[str, Any]],
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    issues: list[str] = []
    if len(standards) != expected_counts["standards"]:
        issues.append(
            f"{framework_key}: expected {expected_counts['standards']} standards, found {len(standards)}"
        )
    if len(indicators) != expected_counts["indicators"]:
        issues.append(
            f"{framework_key}: expected {expected_counts['indicators']} indicators, found {len(indicators)}"
        )

    indicator_codes = [row["source_code"] for row in indicators]
    duplicate_codes = sorted({code for code in indicator_codes if indicator_codes.count(code) > 1})
    if duplicate_codes:
        issues.append(f"{framework_key}: duplicate indicator source codes: {', '.join(duplicate_codes)}")

    standard_codes = {row["source_code"] for row in standards}
    missing_parent = [
        row["source_code"]
        for row in indicators
        if row["parent_source_code"] not in standard_codes
    ]
    if missing_parent:
        issues.append(f"{framework_key}: indicators missing parent standards: {', '.join(missing_parent)}")

    missing_page_refs = [row["source_code"] for row in indicators if not row["page_number"]]
    if missing_page_refs:
        issues.append(f"{framework_key}: indicators missing page references: {', '.join(missing_page_refs)}")

    return {
        "ok": not issues,
        "issues": issues,
        "counts": {
            "standards": len(standards),
            "indicators": len(indicators),
        },
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLEAN_ROW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_page_artifacts(pdf_path: Path, pages: list[dict[str, Any]], output_dir: Path, source_kind: str) -> dict[str, str]:
    subdir = "research_corpus" if source_kind == "research_corpus" else "source_text"
    text_path = output_dir / subdir / "text" / f"{pdf_path.stem}.txt"
    markdown_path = output_dir / subdir / "markdown" / f"{pdf_path.stem}.md"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    text_parts = []
    markdown_parts = [f"# {pdf_path.stem}"]
    for page in pages:
        page_number = page["page_number"]
        text_parts.append(f"--- Page {page_number} ---")
        text_parts.append(page["text"])
        markdown_parts.append(f"\n## Page {page_number}\n")
        markdown_parts.append(page["text"])

    text_path.write_text("\n\n".join(text_parts) + "\n", encoding="utf-8")
    markdown_path.write_text("\n\n".join(markdown_parts) + "\n", encoding="utf-8")
    return {"text": str(text_path), "markdown": str(markdown_path)}


def write_clean_outputs(
    output_dir: Path,
    sources: list[dict[str, Any]],
    source_pdf_paths: list[Path],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []

    for source in sources:
        framework_key = source["framework_key"]
        rows = source["standards"] + source["indicators"]
        write_json(output_dir / f"{framework_key}_clean_standards.json", source)
        write_csv(output_dir / f"{framework_key}_clean_standards.csv", rows)

    for pdf_path in source_pdf_paths:
        source_kind = classify_shape_pdf(pdf_path)
        pages = extract_pdf_pages(pdf_path)
        page_outputs = write_page_artifacts(pdf_path, pages, output_dir, source_kind)
        matching_source = next(
            (source for source in sources if source["source_document"] == pdf_path.name),
            None,
        )
        manifest_entries.append(
            {
                "source_document": pdf_path.name,
                "source_kind": source_kind,
                "source_url": matching_source["source_url"] if matching_source else "",
                "source_sha256": sha256_file(pdf_path),
                "page_count": len(pages),
                "extraction_method": EXTRACTION_METHOD,
                "page_artifacts": page_outputs,
                "clean_standard_rows": (
                    len(matching_source["standards"]) + len(matching_source["indicators"])
                    if matching_source
                    else 0
                ),
            }
        )

    validation_report = {
        source["framework_key"]: source["validation"]
        for source in sources
    }
    manifest = {
        "collection": "shape_2024",
        "created_by": Path(__file__).name,
        "pipeline_boundary": (
            "Clean extraction only. Hub owns standards entity structure, taxonomy mapping, "
            "entity references, UUIDs, and migration imports."
        ),
        "sources": manifest_entries,
    }
    write_json(output_dir / "source_manifest.json", manifest)
    write_json(output_dir / "validation_report.json", validation_report)
    return {"manifest": manifest, "validation_report": validation_report}


def collect_shape_pdfs(input_dir: Path, health_pdf: Path) -> list[Path]:
    pdfs = sorted(input_dir.glob("*.pdf"))
    if health_pdf.exists() and health_pdf not in pdfs:
        pdfs.append(health_pdf)
    return sorted(pdfs, key=lambda path: path.name)


def build_outputs(input_dir: Path, output_dir: Path, health_pdf: Path | None = None) -> dict[str, Any]:
    pe_pdf = input_dir / PE_FILENAME
    health_pdf = health_pdf or output_dir / "source_pdfs" / HEALTH_FILENAME
    health_pdf = fetch_health_pdf(health_pdf)

    sources = [
        extract_standard_source("shape_pe", pe_pdf, PE_SOURCE_URL),
        extract_standard_source("shape_health", health_pdf, HEALTH_SOURCE_URL),
    ]
    source_pdf_paths = collect_shape_pdfs(input_dir, health_pdf)
    return write_clean_outputs(output_dir, sources, source_pdf_paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--health-pdf", type=Path, default=None)
    args = parser.parse_args(argv)

    result = build_outputs(args.input_dir, args.output_dir, args.health_pdf)
    failed = [
        key
        for key, report in result["validation_report"].items()
        if not report["ok"]
    ]
    if failed:
        print(json.dumps(result["validation_report"], indent=2), file=sys.stderr)
        return 1
    print(f"Wrote SHAPE clean extraction outputs to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
