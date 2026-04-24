#!/usr/bin/env python3
"""Archive Stephen Taylor's public USEME-AI site into dated local snapshots.

The site is currently a JavaScript single-page app. This script stores the
entry HTML plus the referenced JS/CSS bundles, then extracts a lightweight
JSON view of the embedded route inventory and site updates feed so the KM
workflow can diff future changes without manually re-parsing the bundle.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)
DEFAULT_BASE_DIR = Path(
    "/Users/scottwilliams/Development/_02_platforms/pipeline-documents/"
    "data/input/stephen/ifyouuseme.ai"
)
HOME_URL = "https://ifyouuseme.ai/"
SITE_UPDATES_URL = "https://ifyouuseme.ai/site-updates"
ROBOTS_URL = "https://ifyouuseme.ai/robots.txt"


@dataclass
class DownloadRecord:
    url: str
    relative_path: str
    content_type: str
    bytes_written: int


def fetch_bytes(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read(), response.headers.get_content_type()


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def asset_urls_from_html(html: str, base_url: str) -> list[str]:
    matches = re.findall(
        r'(?:src|href)="([^"]*index-[^"]+\.(?:js|css))"',
        html,
        flags=re.IGNORECASE,
    )
    return [urljoin(base_url, match) for match in matches]


def extract_site_updates(js_text: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r'\{date:"(?P<date>[^"]+)",title:"(?P<title>[^"]+)",'
        r'description:"(?P<description>[^"]+)",link:"(?P<link>[^"]+)"\}'
    )
    return [match.groupdict() for match in pattern.finditer(js_text)]


def extract_routes(js_text: str) -> list[dict[str, str]]:
    pattern = re.compile(r'path:"(?P<path>/[^"]+)",label:"(?P<label>[^"]+)"')
    seen: set[tuple[str, str]] = set()
    routes: list[dict[str, str]] = []
    for match in pattern.finditer(js_text):
        key = (match.group("path"), match.group("label"))
        if key in seen:
            continue
        seen.add(key)
        routes.append({"path": key[0], "label": key[1]})
    return routes


def relative_asset_path(url: str) -> Path:
    parsed = urlparse(url)
    return Path(parsed.path.lstrip("/"))


def save_downloads(snapshot_dir: Path, urls: Iterable[str]) -> list[DownloadRecord]:
    records: list[DownloadRecord] = []
    for url in urls:
        payload, content_type = fetch_bytes(url)
        rel_path = relative_asset_path(url)
        write_bytes(snapshot_dir / rel_path, payload)
        records.append(
            DownloadRecord(
                url=url,
                relative_path=str(rel_path),
                content_type=content_type,
                bytes_written=len(payload),
            )
        )
    return records


def build_manifest(
    snapshot_dir: Path,
    downloads: list[DownloadRecord],
    site_updates: list[dict[str, str]],
    routes: list[dict[str, str]],
) -> dict[str, object]:
    return {
        "source_urls": [HOME_URL, SITE_UPDATES_URL, ROBOTS_URL],
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_dir": str(snapshot_dir),
        "downloads": [asdict(record) for record in downloads],
        "site_updates_count": len(site_updates),
        "routes_count": len(routes),
        "latest_site_update": site_updates[0] if site_updates else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=DEFAULT_BASE_DIR,
        help="Root directory where dated snapshots should be stored.",
    )
    parser.add_argument(
        "--snapshot-date",
        default=date.today().isoformat(),
        help="Date label for the snapshot directory, in YYYY-MM-DD format.",
    )
    args = parser.parse_args()

    snapshot_dir = args.base_dir / args.snapshot_date
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    downloads: list[DownloadRecord] = []

    home_bytes, home_content_type = fetch_bytes(HOME_URL)
    home_text = home_bytes.decode("utf-8", "replace")
    write_bytes(snapshot_dir / "index.html", home_bytes)
    downloads.append(
        DownloadRecord(
            url=HOME_URL,
            relative_path="index.html",
            content_type=home_content_type,
            bytes_written=len(home_bytes),
        )
    )

    updates_bytes, updates_content_type = fetch_bytes(SITE_UPDATES_URL)
    updates_text = updates_bytes.decode("utf-8", "replace")
    write_bytes(snapshot_dir / "site-updates.html", updates_bytes)
    downloads.append(
        DownloadRecord(
            url=SITE_UPDATES_URL,
            relative_path="site-updates.html",
            content_type=updates_content_type,
            bytes_written=len(updates_bytes),
        )
    )

    robots_bytes, robots_content_type = fetch_bytes(ROBOTS_URL)
    write_bytes(snapshot_dir / "robots.txt", robots_bytes)
    downloads.append(
        DownloadRecord(
            url=ROBOTS_URL,
            relative_path="robots.txt",
            content_type=robots_content_type,
            bytes_written=len(robots_bytes),
        )
    )

    asset_urls = asset_urls_from_html(home_text, HOME_URL) + asset_urls_from_html(
        updates_text,
        SITE_UPDATES_URL,
    )
    downloads.extend(save_downloads(snapshot_dir, sorted(set(asset_urls))))

    js_text = ""
    for record in downloads:
        if record.relative_path.endswith(".js"):
            js_text = (snapshot_dir / record.relative_path).read_text(
                encoding="utf-8",
                errors="replace",
            )
            break

    site_updates = extract_site_updates(js_text)
    routes = extract_routes(js_text)

    write_bytes(
        snapshot_dir / "site_updates.json",
        json.dumps(site_updates, indent=2, ensure_ascii=True).encode("utf-8"),
    )
    write_bytes(
        snapshot_dir / "routes.json",
        json.dumps(routes, indent=2, ensure_ascii=True).encode("utf-8"),
    )

    manifest = build_manifest(snapshot_dir, downloads, site_updates, routes)
    write_bytes(
        snapshot_dir / "manifest.json",
        json.dumps(manifest, indent=2, ensure_ascii=True).encode("utf-8"),
    )

    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
