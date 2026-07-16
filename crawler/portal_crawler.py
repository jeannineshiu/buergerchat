"""Configurable crawler for the federal portal sites that extend the knowledge
base beyond arbeitsagentur.de: familienportal.de (family benefits), bzst.de
(Steuer-ID/taxes), deutsche-rentenversicherung.de (Rente), bmwsb.bund.de
(Wohngeld), bamf.de (Aufenthalt/migration).

One crawler, one SITES config — the sites are all title+<main> pages (mostly
the Government Site Builder CMS), so per-site code would be five copies of the
same thing. Discovery is sitemap-driven where a sitemap exists; bamf.de has
neither robots.txt nor an XML sitemap, so it gets a same-host BFS restricted
to /DE/Themen/ instead.

Politeness: per-site delay honors robots.txt Crawl-delay (bzst: 30s, DRV: 12s
— checked 2026-07); robots Disallow prefixes are baked into url_exclude.
Incremental like the arbeitsagentur crawler: re-running skips URLs already in
the output JSONL. Usage: python portal_crawler.py [site ...] [--limit N]
"""

import gzip
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "BuergerChat-Bot/1.0 (educational project)"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

REQUEST_TIMEOUT = 20.0
MIN_CONTENT_CHARS = 200
XML_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@dataclass
class Site:
    name: str
    host: str
    topic_rules: list[tuple[str, str]]  # (url substring, topic), first match wins
    default_topic: str | None = None  # None: skip pages no rule matches
    sitemap_url: str | None = None
    seed_urls: list[str] = field(default_factory=list)  # BFS mode when no sitemap
    bfs_path_prefix: str = ""  # BFS follows only links under this path
    bfs_max_depth: int = 3
    url_include: str = ""  # regex a URL must match ("" = all)
    url_exclude: list[str] = field(default_factory=list)  # path prefixes (robots Disallow)
    crawl_delay: float = 1.5  # seconds between requests (robots Crawl-delay)


SITES = {
    "familienportal": Site(
        name="familienportal",
        host="familienportal.de",
        sitemap_url="https://familienportal.de/service-sitemap-2d1561ac60e5b904d0e1fb1fa87a8adc-sitemap_index.xml",
        url_include=r"/familienportal/",
        topic_rules=[
            ("kindergeld", "kindergeld"),
            ("kinderzuschlag", "kindergeld"),
            ("elterngeld", "familie-und-kinder"),
        ],
        default_topic="familie-und-kinder",
    ),
    "bzst": Site(
        name="bzst",
        host="www.bzst.de",
        sitemap_url="https://www.bzst.de/Sitemap_Basepage.xml",
        # Citizen-facing pages only: with the 30s Crawl-delay the site demands,
        # the /DE/Unternehmen/ bulk (VAT, withholding …) is neither affordable
        # nor on-topic.
        url_include=r"/DE/Privatpersonen/",
        url_exclude=["/SiteGlobals/", "/DE/Service/", "/EN/Service/", "/SharedDocs/Downloads/Schuetzenswertes/"],
        topic_rules=[("kindergeld", "kindergeld")],
        default_topic="steuern",
        crawl_delay=30.0,
    ),
    "drv": Site(
        name="drv",
        host="www.deutsche-rentenversicherung.de",
        sitemap_url="https://www.deutsche-rentenversicherung.de/Sitemap_Index.xml",
        url_include=(
            r"/DE/.*(rente|altersvorsorge|erwerbsminderung|hinterblieben|grundsicherung"
            r"|reha|versichert|beitr)"
        ),
        url_exclude=["/SiteGlobals/", "/cae/", "/DE/Service/", "/EN/Service/", "/FR/Service/"],
        topic_rules=[],
        default_topic="rente",
        crawl_delay=12.0,
    ),
    "bmwsb": Site(
        name="bmwsb",
        host="www.bmwsb.bund.de",
        sitemap_url="https://www.bmwsb.bund.de/Sitemap_Index.xml",
        url_include=r"wohngeld|wohnraum|mietrecht",
        url_exclude=["/SiteGlobals/", "/DE/Service/", "/EN/Service/", "/DE/_cug/", "/SharedDocs/_cug"],
        topic_rules=[],
        default_topic="wohngeld",
    ),
    "bamf": Site(
        name="bamf",
        host="www.bamf.de",
        seed_urls=[
            "https://www.bamf.de/DE/Themen/MigrationAufenthalt/migrationaufenthalt-node.html",
            "https://www.bamf.de/DE/Themen/Integration/integration-node.html",
            "https://www.bamf.de/DE/Themen/AsylFluechtlingsschutz/asylfluechtlingsschutz-node.html",
        ],
        bfs_path_prefix="/DE/Themen/",
        bfs_max_depth=3,
        topic_rules=[("integration", "aufenthalt")],
        default_topic="aufenthalt",
    ),
}


def classify_topic(site: Site, url: str) -> str | None:
    lowered = url.lower()
    for keyword, topic in site.topic_rules:
        if keyword in lowered:
            return topic
    return site.default_topic


def url_allowed(site: Site, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc not in (site.host, site.host.removeprefix("www.")):
        return False
    if any(parsed.path.startswith(prefix) for prefix in site.url_exclude):
        return False
    if site.url_include and not re.search(site.url_include, url, re.IGNORECASE):
        return False
    if parsed.path.lower().endswith((".pdf", ".jpg", ".png", ".mp4", ".xml", ".zip")):
        return False
    return True


def fetch_sitemap_urls(client: httpx.Client, sitemap_url: str) -> list[str]:
    response = client.get(sitemap_url)
    response.raise_for_status()
    raw = response.content
    if sitemap_url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    root = ElementTree.fromstring(raw)

    child_maps = [el.text for el in root.findall("sm:sitemap/sm:loc", XML_NS) if el.text]
    if child_maps:
        urls: list[str] = []
        for loc in child_maps:
            # Skip non-page sitemaps (news, images, videos, job offers).
            if re.search(r"news|image|video|joboffer|press", loc, re.IGNORECASE):
                continue
            urls.extend(fetch_sitemap_urls(client, loc))
        return urls

    return [el.text for el in root.findall("sm:url/sm:loc", XML_NS) if el.text]


def extract_page(html: str) -> tuple[str, str, list[str]]:
    """Returns (title, content, same-page links) — links feed the BFS mode."""
    soup = BeautifulSoup(html, "html.parser")

    links = [a.get("href") for a in soup.find_all("a", href=True)]

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "form", "aside"]):
        tag.decompose()
    # GSB/portal chrome that lives outside <nav> tags: menus, breadcrumbs,
    # skip links, cookie banners. Class-substring matching is crude but the
    # leading boilerplate otherwise becomes the first RAG chunk of every page.
    for tag in soup.select(
        '[class*="nav"], [class*="menu"], [class*="breadcrumb"], [class*="skiplink"], '
        '[class*="cookie"], [class*="servicemeta"], [id*="breadcrumb"]'
    ):
        tag.decompose()

    # Unlike arbeitsagentur.de (multiple stray h1s), these portals carry the
    # real page heading in a single h1; <title> is the fallback since it drags
    # site-name prefixes ("BMWSB - Homepage - …") along.
    h1_tag = soup.find("h1")
    title = h1_tag.get_text(strip=True) if h1_tag else ""
    if not title and soup.title:
        raw = " ".join(soup.title.get_text(strip=True).split())
        title = raw.split("|")[0].strip()

    main = soup.find("main") or soup.body or soup
    content = " ".join(main.get_text(separator=" ", strip=True).split())

    return title, content, links


def load_crawled_urls(output_path: str) -> set[str]:
    if not os.path.exists(output_path):
        return set()
    urls = set()
    with open(output_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                urls.add(json.loads(line)["url"])
    return urls


def sleep(site: Site) -> None:
    time.sleep(site.crawl_delay * random.uniform(0.9, 1.2))


def fetch_page(client: httpx.Client, url: str) -> str | None:
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[error] {url}: {exc}", file=sys.stderr)
        return None
    if "text/html" not in response.headers.get("content-type", ""):
        return None
    return response.text


def write_record(out_file, site: Site, url: str, title: str, content: str) -> None:
    record = {
        "url": url,
        "title": title,
        "content": content,
        "topic": classify_topic(site, url),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
    }
    out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    out_file.flush()


def crawl_sitemap_site(client: httpx.Client, site: Site, out_file, done: set[str], limit: int | None) -> int:
    urls = fetch_sitemap_urls(client, site.sitemap_url)
    urls = [u for u in urls if url_allowed(site, u) and classify_topic(site, u) and u not in done]
    if limit:
        urls = urls[:limit]
    print(f"[{site.name}] {len(urls)} urls to crawl (delay {site.crawl_delay}s)")

    written = 0
    for i, url in enumerate(urls, start=1):
        html = fetch_page(client, url)
        if html:
            title, content, _ = extract_page(html)
            if len(content) >= MIN_CONTENT_CHARS:
                write_record(out_file, site, url, title, content)
                written += 1
                print(f"[{site.name} {i}/{len(urls)}] saved: {url}")
        sleep(site)
    return written


def crawl_bfs_site(client: httpx.Client, site: Site, out_file, done: set[str], limit: int | None) -> int:
    queue: list[tuple[str, int]] = [(u, 0) for u in site.seed_urls]
    seen = set(site.seed_urls)
    written = 0

    while queue:
        if limit and written >= limit:
            break
        url, depth = queue.pop(0)
        html = fetch_page(client, url)
        sleep(site)
        if html is None:
            continue

        title, content, links = extract_page(html)
        if url not in done and len(content) >= MIN_CONTENT_CHARS and classify_topic(site, url):
            write_record(out_file, site, url, title, content)
            written += 1
            print(f"[{site.name} depth={depth}] saved ({written}): {url}")

        if depth >= site.bfs_max_depth:
            continue
        for href in links:
            absolute = urljoin(url, href).split("#")[0].split(";jsessionid")[0]
            parsed = urlparse(absolute)
            if (
                absolute not in seen
                and parsed.path.startswith(site.bfs_path_prefix)
                and url_allowed(site, absolute)
            ):
                seen.add(absolute)
                queue.append((absolute, depth + 1))
    return written


def main() -> None:
    argv = sys.argv[1:]
    limit = None
    if "--limit" in argv:
        i = argv.index("--limit")
        limit = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]

    names = args or list(SITES)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for name in names:
        site = SITES[name]
        output_path = os.path.join(OUTPUT_DIR, f"portal_{site.name}.jsonl")
        done = load_crawled_urls(output_path)

        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT, follow_redirects=True
        ) as client, open(output_path, "a", encoding="utf-8") as out_file:
            if site.sitemap_url:
                written = crawl_sitemap_site(client, site, out_file, done, limit)
            else:
                written = crawl_bfs_site(client, site, out_file, done, limit)
        print(f"[{site.name}] done: {written} new records ({len(done)} already crawled)")


if __name__ == "__main__":
    main()
