"""Crawler for gesetze-im-internet.de — scoped to 5 laws relevant to buergerchat.

No sitemap on this site. Each law's "Gesamtausgabe" (single-page full text)
URL was found by hand via the alphabetical index (Teilliste_S.html /
Teilliste_B.html) and is hardcoded below — the site adds new laws rarely
enough that this doesn't need to be automated.

Output is chunked per Paragraph (§), not per law: a law page is one big
HTML document but each <div class="jnnorm"> block is a single section, and
RAG retrieval works better over section-sized chunks than a 400 KB blob.

Note: pages are served as ISO-8859-1, not UTF-8 — decoding as UTF-8 corrupts
every umlaut/eszett.
"""

import json
import os
import random
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "BuergerChat-Bot/1.0 (educational project)"
# Absolute path, anchored to this file's location — see arbeitsagentur_crawler.py
# for why a relative path here is a trap (cwd-dependent, silently wrong).
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "gesetze.jsonl")

REQUEST_TIMEOUT = 15.0
SLEEP_MIN = 1.0
SLEEP_MAX = 2.0

# (law code, base index URL, Gesamtausgabe filename, topic)
LAWS = [
    ("SGB I", "https://www.gesetze-im-internet.de/sgb_1/", "BJNR030150975.html", "allgemein"),
    ("SGB II", "https://www.gesetze-im-internet.de/sgb_2/", "BJNR295500003.html", "buergergeld"),
    ("SGB VIII", "https://www.gesetze-im-internet.de/sgb_8/", "BJNR111630990.html", "familie-und-kinder"),
    ("SGB X", "https://www.gesetze-im-internet.de/sgb_10/", "BJNR114690980.html", "allgemein"),
    ("BKGG", "https://www.gesetze-im-internet.de/bkgg_1996/", "BJNR137800995.html", "kindergeld"),
]


def fetch_law_html(client: httpx.Client, base_url: str, filename: str) -> str:
    response = client.get(base_url + filename)
    response.raise_for_status()
    response.encoding = "iso-8859-1"
    return response.text


def extract_sections(html: str, law_code: str, page_url: str, topic: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    law_title_tag = soup.find("span", class_="jnlangue")
    law_title = law_title_tag.get_text(strip=True) if law_title_tag else law_code

    records = []
    for norm in soup.find_all("div", class_="jnnorm"):
        enbez_tag = norm.find("span", class_="jnenbez")
        enbez = enbez_tag.get_text(strip=True) if enbez_tag else ""
        if not enbez.startswith("§"):
            continue  # skips Inhaltsübersicht/Rahmen/Anlage blocks, keeps only real sections

        entitel_tag = norm.find("span", class_="jnentitel")
        entitel = entitel_tag.get_text(strip=True) if entitel_tag else ""

        jnhtml = norm.find("div", class_="jnhtml")
        content = " ".join(jnhtml.get_text(separator=" ", strip=True).split()) if jnhtml else ""
        if not content:
            continue

        anchor = norm.get("id", "")
        title = f"{law_code} {enbez} {entitel}".strip()

        records.append(
            {
                "url": f"{page_url}#{anchor}" if anchor else page_url,
                "title": title,
                "content": content,
                "topic": topic,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "law": law_title,
            }
        )
    return records


def crawl(output_path: str) -> None:
    headers = {"User-Agent": USER_AGENT}
    total_written = 0

    with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client, \
            open(output_path, "w", encoding="utf-8") as out_file:
        for law_code, base_url, filename, topic in LAWS:
            page_url = base_url + filename
            html = fetch_law_html(client, base_url, filename)
            sections = extract_sections(html, law_code, page_url, topic)

            for record in sections:
                out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_written += len(sections)

            print(f"{law_code}: {len(sections)} sections saved ({page_url})")
            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

    print(f"done: {total_written} sections saved across {len(LAWS)} laws")


def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    crawl(OUTPUT_PATH)


if __name__ == "__main__":
    main()
