#!/usr/bin/env python3
"""Extract readable markdown for Stephen Taylor's About-page bibliography."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path


DEFAULT_INPUT_ROOT = Path(
    "/Users/scottwilliams/Development/_02_platforms/pipeline-documents/"
    "data/input/stephen/sjtylr.net"
)
DEFAULT_OUTPUT_ROOT = Path(
    "/Users/scottwilliams/Development/_02_platforms/pipeline-documents/"
    "data/output/stephen/sjtylr.net"
)
CURATED_SECTIONS = {
    "Inquiry & Learning",
    "International-Mindedness and Global Engagement (IMaGE)",
    "Curriculum",
    "Learners and the ATLs",
    "Pedagogy & Practice",
    "Project Zero: Coaching & Resourcing",
    "Educational Technology",
    "On the MYP & DP: Curriculum, Assessment & Practice",
    "Service Learning",
    "Professional Learning",
}


@dataclass
class ExtractionRecord:
    url: str
    title: str
    section: str
    relation: str
    output_path: str
    status: str
    word_count: int = 0
    error: str | None = None


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:120] or "untitled"


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def extraction_targets(records: list[dict[str, object]]) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in records:
        section = str(record.get("section") or "")
        relation = str(record.get("relation") or "")
        url = str(record.get("url") or "").rstrip("/")
        if section not in CURATED_SECTIONS:
            continue
        if relation not in {"sjtylr.net", "taylor-adjacent-site", "wab-hosted-resource"}:
            continue
        if not url or url in seen:
            continue
        seen.add(url)
        targets.append(record)
    return targets


def run_defuddle(url: str) -> tuple[str, str | None]:
    result = subprocess.run(
        ["defuddle", "parse", url, "--md"],
        text=True,
        capture_output=True,
        check=False,
        timeout=90,
    )
    if result.returncode != 0:
        return "", result.stderr.strip() or result.stdout.strip() or "defuddle failed"
    return result.stdout, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", default=date.today().isoformat())
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max target count for test runs. 0 means all targets.",
    )
    args = parser.parse_args()

    input_dir = args.input_root / args.snapshot_date
    output_dir = args.output_root / args.snapshot_date / "markdown"
    output_dir.mkdir(parents=True, exist_ok=True)

    records = json.loads((input_dir / "about_link_index.json").read_text())
    targets = extraction_targets(records)
    if args.limit:
        targets = targets[: args.limit]

    extraction_records: list[ExtractionRecord] = []
    for index, target in enumerate(targets, start=1):
        url = str(target["url"])
        section = str(target.get("section") or "Unsectioned")
        relation = str(target.get("relation") or "unknown")
        title = str(target.get("page_title") or target.get("text") or url)
        filename = f"{index:03d}-{slugify(section)}-{slugify(title)}.md"
        output_path = output_dir / filename
        markdown, error = run_defuddle(url)
        if error:
            extraction_records.append(
                ExtractionRecord(
                    url=url,
                    title=title,
                    section=section,
                    relation=relation,
                    output_path=str(output_path),
                    status="failed",
                    error=error,
                )
            )
            continue

        header = "\n".join(
            [
                "---",
                f"title: {json.dumps(title, ensure_ascii=False)}",
                f"source_url: {json.dumps(url, ensure_ascii=False)}",
                f"section: {json.dumps(section, ensure_ascii=False)}",
                f"relation: {relation}",
                f"extracted_at_utc: {datetime.now(timezone.utc).isoformat()}",
                "---",
                "",
            ]
        )
        output_path.write_text(header + markdown.strip() + "\n", encoding="utf-8")
        extraction_records.append(
            ExtractionRecord(
                url=url,
                title=title,
                section=section,
                relation=relation,
                output_path=str(output_path),
                status="success",
                word_count=word_count(markdown),
            )
        )

    manifest = {
        "source_index": str(input_dir / "about_link_index.json"),
        "output_dir": str(output_dir),
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_count": len(targets),
        "success_count": sum(1 for record in extraction_records if record.status == "success"),
        "failed_count": sum(1 for record in extraction_records if record.status == "failed"),
        "total_words": sum(record.word_count for record in extraction_records),
        "records": [asdict(record) for record in extraction_records],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0 if manifest["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
