"""Crawler for arbeitsagentur.de citizen-service pages.

Flow: parse sitemap-portal.xml -> filter URLs by topic keywords -> fetch each
page -> extract title/content -> write JSONL (one record per page).
"""

import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

SITEMAP_URL = "https://www.arbeitsagentur.de/sitemap-portal.xml"
BASE_HOST = "www.arbeitsagentur.de"
USER_AGENT = "BuergerChat-Bot/1.0 (educational project)"
# Absolute path, anchored to this file's location — a relative path here
# silently writes to the wrong place depending on the caller's cwd (has
# happened twice: crawler/crawler/output/... instead of crawler/output/...).
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "arbeitsagentur.jsonl")

REQUEST_TIMEOUT = 15.0
SLEEP_MIN = 1.0
SLEEP_MAX = 2.0
MIN_CONTENT_CHARS = 200  # below this, treat page as JS-rendered/empty and skip

TOPIC_KEYWORDS = {
    "buergergeld": ["buergergeld", "grundsicherung", "jobcenter", "bedarfsgemeinschaft"],
    "kindergeld": ["kindergeld", "kinderzuschlag"],
    "arbeitslos": ["arbeitslos", "arbeitsuche"],
    "familie-und-kinder": ["familie", "elterngeld", "elternzeit", "kita", "alleinerziehend"],
}

XML_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def classify_topic(url: str) -> str | None:
    lowered = url.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return topic
    return None


def fetch_sitemap_urls(client: httpx.Client, sitemap_url: str) -> list[str]:
    response = client.get(sitemap_url)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)

    # Sitemap index: recurse into each child sitemap.
    sitemap_locs = [el.text for el in root.findall("sm:sitemap/sm:loc", XML_NS)]
    if sitemap_locs:
        urls: list[str] = []
        for loc in sitemap_locs:
            if not loc:
                continue
            urls.extend(fetch_sitemap_urls(client, loc))
        return urls

    return [el.text for el in root.findall("sm:url/sm:loc", XML_NS) if el.text]


def is_pdf(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def extract_page(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    # <title> (e.g. "Kindergeld und Kinderzuschlag | Bundesagentur für Arbeit")
    # is more reliable than <h1> here: the page markup has multiple h1s
    # (nav landmark, image-credit sections, etc.) with no way to tell them
    # apart from the real heading without hand-tuned per-template rules.
    title = ""
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True).split("|")[0].strip()

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    if not title:
        h1_tag = soup.find("h1")
        title = h1_tag.get_text(strip=True) if h1_tag else ""

    main = soup.find("main") or soup.body or soup
    content = " ".join(main.get_text(separator=" ", strip=True).split())

    return title, content


def crawl(urls: list[str], output_path: str, append: bool = False) -> None:
    headers = {"User-Agent": USER_AGENT}
    written = 0
    skipped_pdf = 0
    skipped_thin = 0
    skipped_error = 0

    mode = "a" if append else "w"
    with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client, \
            open(output_path, mode, encoding="utf-8") as out_file:
        for i, url in enumerate(urls, start=1):
            if is_pdf(url):
                skipped_pdf += 1
                continue

            topic = classify_topic(url)
            if topic is None:
                continue

            try:
                response = client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[error] {url}: {exc}", file=sys.stderr)
                skipped_error += 1
                time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                continue

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                skipped_pdf += 1
                time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                continue

            title, content = extract_page(response.text)
            if len(content) < MIN_CONTENT_CHARS:
                skipped_thin += 1
                time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                continue

            record = {
                "url": url,
                "title": title,
                "content": content,
                "topic": topic,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
            print(f"[{i}/{len(urls)}] saved ({topic}): {url}")

            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

    print(
        f"done: {written} saved, {skipped_pdf} skipped (pdf/non-html), "
        f"{skipped_thin} skipped (thin/JS content), {skipped_error} errors"
    )


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


def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        all_urls = fetch_sitemap_urls(client, SITEMAP_URL)

    all_urls = [u for u in all_urls if urlparse(u).netloc == BASE_HOST]
    relevant_urls = [u for u in all_urls if classify_topic(u) is not None]

    already_crawled = load_crawled_urls(OUTPUT_PATH)
    new_urls = [u for u in relevant_urls if u not in already_crawled]

    print(
        f"sitemap: {len(all_urls)} total urls, {len(relevant_urls)} match topic filters, "
        f"{len(already_crawled)} already crawled, {len(new_urls)} new"
    )

    crawl(new_urls, OUTPUT_PATH, append=bool(already_crawled))


if __name__ == "__main__":
    main()
