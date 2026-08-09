"""Crawler for gesetze-im-internet.de — scoped to the laws relevant to buergerchat.

No sitemap on this site. Each law's "Gesamtausgabe" (single-page full text)
URL was found by hand via the alphabetical index (Teilliste_S.html /
Teilliste_B.html) and is hardcoded below — the site adds new laws rarely
enough that this doesn't need to be automated.

Output is chunked per Paragraph (§), not per law: a law page is one big
HTML document but each <div class="jnnorm"> block is a single section, and
RAG retrieval works better over section-sized chunks than a 400 KB blob.

Anlagen are kept too, not just §-sections. They carry the actual amounts:
SGB XII "Anlage (zu § 28) Regelbedarfsstufen nach § 28 in Euro" is the only
official source for what Grundsicherungsgeld/Bürgergeld pays — § 20 SGB II
merely points at it and the RBSFV only sets percentages. Their tables are
rendered row by row (see render_table) because flattening a table with
get_text() yields a wall of bare numbers with nothing tying a figure to its
year or its column.

Note: pages are served as ISO-8859-1, not UTF-8 — decoding as UTF-8 corrupts
every umlaut/eszett.
"""

import json
import os
import random
import re
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup, NavigableString

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
    ("SGB VI", "https://www.gesetze-im-internet.de/sgb_6/", "BJNR122610989.html", "rente"),
    ("SGB XII", "https://www.gesetze-im-internet.de/sgb_12/", "BJNR302300003.html", "rente"),
    ("WoGG", "https://www.gesetze-im-internet.de/wogg/", "BJNR185610008.html", "wohngeld"),
    ("AufenthG", "https://www.gesetze-im-internet.de/aufenthg_2004/", "BJNR195010004.html", "aufenthalt"),
]


def fetch_law_html(client: httpx.Client, base_url: str, filename: str) -> str:
    response = client.get(base_url + filename)
    response.raise_for_status()
    response.encoding = "iso-8859-1"
    return response.text


# Empty-cell markers used in the Anlage tables ("no amount for this period").
EMPTY_CELLS = {"", "-", "–", "—"}
# Words that follow a German Ergänzungsstrich ("Vater- und Mutterschaft"),
# where the trailing hyphen is meaningful and must not be joined away.
HYPHEN_KEEP_NEXT = {"und", "oder", "bzw", "sowie", "beziehungsweise"}


def clean_cell(text: str) -> str:
    """Collapse whitespace and rejoin words broken across a table header line.

    The site typesets narrow headers as "Regel- bedarfsstufe 1"; without
    rejoining, no query for "Regelbedarfsstufe" can ever match the column.
    Real hyphenated compounds ("Steuer-ID") have no space after the hyphen,
    so they are untouched — except the Ergänzungsstrich, which does.
    """
    text = " ".join(text.split())
    return re.sub(
        r"-\s+(?=([a-zäöüß]+))",
        lambda m: "- " if m.group(1) in HYPHEN_KEEP_NEXT else "",
        text,
    )


def render_table(table, unit: str = "") -> list[str]:
    """Render a table as one self-contained sentence per cell.

    A row like ["1. Januar 2026", "563", ...] under headers
    ["gültig ab", "Regelbedarfsstufe 1", ...] becomes
    "Regelbedarfsstufe 1, gültig ab 1. Januar 2026: 563 Euro" — every figure
    stays attached to its column and its period even after the 800-char
    chunker cuts the table apart.
    """
    rows = [
        [clean_cell(cell.get_text(" ", strip=True)) for cell in tr.find_all(["td", "th"])]
        for tr in table.find_all("tr")
    ]
    rows = [row for row in rows if any(cell not in EMPTY_CELLS for cell in row)]
    if len(rows) < 2:
        return []

    header, *body = rows
    lines = []
    for row in body:
        row_label = row[0]
        for column, value in zip(header[1:], row[1:]):
            if value in EMPTY_CELLS:
                continue
            # Some tables spell the unit per cell ("100 Euro"), others only in
            # the Anlage title ("... in Euro") — don't end up with "100 Euro Euro".
            if unit and unit.lower() not in value.lower():
                value = f"{value} {unit}"
            lines.append(f"{column}, {header[0]} {row_label}: {value}")
    return lines


def extract_with_tables(jnhtml, unit: str = "") -> str:
    """Text of a block, with its tables rendered row-wise instead of flattened.

    Only used for Anlagen: §-sections use tables for layout, where row-wise
    rendering would produce nonsense.
    """
    for table in jnhtml.find_all("table"):
        lines = render_table(table, unit)
        table.replace_with(NavigableString(" " + ". ".join(lines) + ". " if lines else " "))
    return " ".join(jnhtml.get_text(separator=" ", strip=True).split())


def title_unit(entitel: str) -> str:
    """"Regelbedarfsstufen nach § 28 in Euro" -> "Euro"."""
    match = re.search(r"\bin (Euro)\b", entitel)
    return match.group(1) if match else ""


def extract_sections(html: str, law_code: str, page_url: str, topic: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    law_title_tag = soup.find("span", class_="jnlangue")
    law_title = law_title_tag.get_text(strip=True) if law_title_tag else law_code

    records = []
    for norm in soup.find_all("div", class_="jnnorm"):
        enbez_tag = norm.find("span", class_="jnenbez")
        enbez = enbez_tag.get_text(strip=True) if enbez_tag else ""
        is_anlage = enbez.startswith("Anlage")
        if not enbez.startswith("§") and not is_anlage:
            continue  # skips Inhaltsübersicht/Rahmen, keeps sections and Anlagen

        entitel_tag = norm.find("span", class_="jnentitel")
        entitel = entitel_tag.get_text(strip=True) if entitel_tag else ""
        # Anlage titles run the reference into the name: "(zu § 28)Regelbedarfsstufen".
        entitel = re.sub(r"\)(?=\S)", ") ", entitel)

        jnhtml = norm.find("div", class_="jnhtml")
        if not jnhtml:
            continue
        if is_anlage:
            content = extract_with_tables(jnhtml, title_unit(entitel))
        else:
            content = " ".join(jnhtml.get_text(separator=" ", strip=True).split())
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
