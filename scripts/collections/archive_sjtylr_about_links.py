#!/usr/bin/env python3
"""Archive Stephen Taylor's sjtylr.net About-page bibliography.

The About page is Taylor's own curated map of older and newer public writing.
This script preserves the page, indexes the linked resources by section, and
fetches local copies of sjtylr.net pages linked from that bibliography.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)
DEFAULT_BASE_DIR = Path(
    "/Users/scottwilliams/Development/_02_platforms/pipeline-documents/"
    "data/input/stephen/sjtylr.net"
)
ABOUT_URL = "https://sjtylr.net/about/"
ROBOTS_URL = "https://sjtylr.net/robots.txt"
SITEMAP_URL = "https://sjtylr.net/sitemap.xml"
FETCHABLE_NETLOCS = {"sjtylr.net", "www.sjtylr.net"}
STOP_SECTIONS = {
    "short third-person biography",
    "even briefer bio",
    "my cv at a glance",
}


@dataclass
class LinkRecord:
    url: str
    text: str
    section: str
    domain: str
    relation: str
    status: str = "indexed"
    local_path: str | None = None
    page_title: str | None = None
    published_date: str | None = None
    error: str | None = None


@dataclass
class DownloadRecord:
    url: str
    relative_path: str
    content_type: str
    bytes_written: int
    status: str
    error: str | None = None


class AboutLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.current_section = "Page Header / Bio"
        self.links: list[LinkRecord] = []
        self._heading_tag: str | None = None
        self._heading_text: list[str] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag in {"h2", "h3", "h4"}:
            self._heading_tag = tag
            self._heading_text = []
        if tag == "a" and attr_map.get("href"):
            self._link_href = attr_map["href"]
            self._link_text = []

    def handle_data(self, data: str) -> None:
        if self._heading_tag:
            self._heading_text.append(data)
        if self._link_href:
            self._link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._heading_tag and tag == self._heading_tag:
            heading = clean_text(" ".join(self._heading_text))
            if heading:
                self.current_section = heading
            self._heading_tag = None
            self._heading_text = []
            return

        if tag == "a" and self._link_href:
            url = urljoin(self.base_url, self._link_href)
            text = clean_text(" ".join(self._link_text)) or url
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            relation = classify_relation(domain)
            if parsed.scheme in {"http", "https"}:
                self.links.append(
                    LinkRecord(
                        url=url,
                        text=text,
                        section=self.current_section,
                        domain=domain,
                        relation=relation,
                    )
                )
            self._link_href = None
            self._link_text = []


def clean_text(value: str) -> str:
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def classify_relation(domain: str) -> str:
    if domain in FETCHABLE_NETLOCS:
        return "sjtylr.net"
    if domain in {"i-biology.net", "www.i-biology.net", "ibiologystephen.wordpress.com"}:
        return "taylor-adjacent-site"
    if domain.endswith("wab.edu"):
        return "wab-hosted-resource"
    return "external-reference"


def fetch_bytes(url: str) -> tuple[bytes, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        final_url = response.geturl()
        return response.read(), response.headers.get_content_type(), final_url


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def safe_filename(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", path).strip("-")
    if parsed.query:
        query_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", parsed.query).strip("-")
        slug = f"{slug}__{query_slug}"
    return f"{slug or 'index'}.html"


def extract_title(html: str) -> str | None:
    for pattern in (
        r"<h1[^>]*>(?P<title>.*?)</h1>",
        r"<title[^>]*>(?P<title>.*?)</title>",
    ):
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = re.sub(r"<[^>]+>", " ", match.group("title"))
            return clean_text(title)
    return None


def extract_published_date(html: str) -> str | None:
    patterns = (
        r'<time[^>]+datetime="(?P<date>[^"]+)"',
        r'<meta[^>]+property="article:published_time"[^>]+content="(?P<date>[^"]+)"',
        r'<meta[^>]+content="(?P<date>[^"]+)"[^>]+property="article:published_time"',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group("date")
    parsed = urlparse_from_html_canonical_date(html)
    return parsed


def urlparse_from_html_canonical_date(html: str) -> str | None:
    match = re.search(r"https?://sjtylr\.net/(\d{4})/(\d{2})/(\d{2})/", html)
    if not match:
        return None
    return "-".join(match.groups())


def dedupe_links(links: Iterable[LinkRecord]) -> list[LinkRecord]:
    seen: set[tuple[str, str]] = set()
    result: list[LinkRecord] = []
    for link in links:
        key = (link.url.rstrip("/"), link.section)
        if key in seen:
            continue
        seen.add(key)
        section_key = link.section.lower()
        if section_key in STOP_SECTIONS:
            continue
        result.append(link)
    return result


def parse_about_links(html: str) -> list[LinkRecord]:
    parser = AboutLinkParser(ABOUT_URL)
    parser.feed(html)
    links = dedupe_links(parser.links)
    return [
        link
        for link in links
        if link.section
        not in {
            "9 responses to “About Stephen”",
            "Share this:",
        }
    ]


def fetch_sjtylr_pages(snapshot_dir: Path, links: list[LinkRecord]) -> list[DownloadRecord]:
    downloads: list[DownloadRecord] = []
    page_dir = snapshot_dir / "pages"
    for link in links:
        if link.domain not in FETCHABLE_NETLOCS:
            continue
        if "/wp-admin/" in urlparse(link.url).path or "/wp-login" in urlparse(link.url).path:
            continue
        rel_path = Path("pages") / safe_filename(link.url)
        try:
            payload, content_type, final_url = fetch_bytes(link.url)
            write_bytes(snapshot_dir / rel_path, payload)
            html = payload.decode("utf-8", "replace")
            link.local_path = str(rel_path)
            link.status = "fetched"
            link.page_title = extract_title(html)
            link.published_date = extract_published_date(html)
            if final_url.rstrip("/") != link.url.rstrip("/"):
                link.error = f"redirected_to={final_url}"
            downloads.append(
                DownloadRecord(
                    url=link.url,
                    relative_path=str(rel_path),
                    content_type=content_type,
                    bytes_written=len(payload),
                    status="success",
                )
            )
        except (HTTPError, URLError, TimeoutError) as exc:
            link.status = "fetch_failed"
            link.error = str(exc)
            downloads.append(
                DownloadRecord(
                    url=link.url,
                    relative_path=str(page_dir / safe_filename(link.url)),
                    content_type="",
                    bytes_written=0,
                    status="failed",
                    error=str(exc),
                )
            )
    return downloads


def write_markdown_index(path: Path, links: list[LinkRecord]) -> None:
    sections: dict[str, list[LinkRecord]] = {}
    for link in links:
        sections.setdefault(link.section, []).append(link)

    lines = [
        "# Stephen Taylor About-Page Link Index",
        "",
        f"Snapshot source: {ABOUT_URL}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This index preserves Taylor's own category structure from his About page.",
        "Local HTML copies are fetched only for `sjtylr.net` pages; external links are indexed by URL and relation.",
        "",
    ]
    for section, records in sections.items():
        lines.extend([f"## {section}", ""])
        for record in records:
            date_label = f" ({record.published_date})" if record.published_date else ""
            title = record.page_title or record.text
            local = f"; local: `{record.local_path}`" if record.local_path else ""
            status = f"; status: {record.status}" if record.status != "indexed" else ""
            lines.append(
                f"- [{title}]({record.url}){date_label} - {record.relation}{status}{local}"
            )
        lines.append("")
    write_bytes(path, "\n".join(lines).encode("utf-8"))


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

    for url, filename in (
        (ABOUT_URL, "about.html"),
        (ROBOTS_URL, "robots.txt"),
        (SITEMAP_URL, "sitemap.xml"),
    ):
        try:
            payload, content_type, _ = fetch_bytes(url)
            write_bytes(snapshot_dir / filename, payload)
            downloads.append(
                DownloadRecord(
                    url=url,
                    relative_path=filename,
                    content_type=content_type,
                    bytes_written=len(payload),
                    status="success",
                )
            )
        except (HTTPError, URLError, TimeoutError) as exc:
            downloads.append(
                DownloadRecord(
                    url=url,
                    relative_path=filename,
                    content_type="",
                    bytes_written=0,
                    status="failed",
                    error=str(exc),
                )
            )

    about_html = (snapshot_dir / "about.html").read_text(
        encoding="utf-8",
        errors="replace",
    )
    links = parse_about_links(about_html)
    downloads.extend(fetch_sjtylr_pages(snapshot_dir, links))

    link_dicts = [asdict(link) for link in links]
    write_bytes(
        snapshot_dir / "about_link_index.json",
        json.dumps(link_dicts, indent=2, ensure_ascii=True).encode("utf-8"),
    )
    write_markdown_index(snapshot_dir / "about_link_index.md", links)

    manifest = {
        "source_urls": [ABOUT_URL, ROBOTS_URL, SITEMAP_URL],
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_dir": str(snapshot_dir),
        "downloads": [asdict(record) for record in downloads],
        "link_count": len(links),
        "fetched_sjtylr_pages": sum(
            1 for link in links if link.status == "fetched" and link.domain in FETCHABLE_NETLOCS
        ),
        "section_count": len({link.section for link in links}),
        "relation_counts": {
            relation: sum(1 for link in links if link.relation == relation)
            for relation in sorted({link.relation for link in links})
        },
    }
    write_bytes(
        snapshot_dir / "manifest.json",
        json.dumps(manifest, indent=2, ensure_ascii=True).encode("utf-8"),
    )

    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
