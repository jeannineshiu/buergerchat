"""Live lookup of the responsible authority (zuständige Stelle) via the
official PVOG Suchdienst API (FITKO, https://pvog.fitko.net/suchdienst/api).

Responsibility depends on where the user lives (~11,000 Kommunen), so this
is queried live per request instead of being crawled into the FAISS index.
The API is public — no key or registration required.

Lookup chain: PLZ → ARS (Amtlicher Regionalschlüssel) → Leistungen matching
the query → organisation units per Leistung → unit detail with address.
Every failure path returns None; /chat must keep working without PVOG.
"""

from dataclasses import dataclass

import httpx

PVOG_BASE_URL = "https://pvog.fitko.net/suchdienst/api"
REQUEST_TIMEOUT = 8.0

# Zuständigkeitsrolle codes: 01 = Zuständige Stelle, 03 = Ansprechpunkt.
ROLE_RESPONSIBLE = "01"

# Per-topic search terms hit better than the raw user message. Bürgergeld is
# being renamed to Grundsicherungsgeld (2026-07-01); PVOG still uses the old
# name, so both terms are tried in order until one returns results.
TOPIC_QUERIES = {
    "buergergeld": ["Bürgergeld beantragen", "Grundsicherungsgeld beantragen"],
    "kindergeld": ["Kindergeld beantragen"],
    "arbeitslos": ["Arbeitslosengeld beantragen"],
    "familie-und-kinder": ["Elterngeld beantragen", "Unterhaltsvorschuss beantragen"],
    "rente": ["Altersrente beantragen", "Rente beantragen"],
    "wohngeld": ["Wohngeld beantragen"],
    "steuern": ["Steuerliche Identifikationsnummer"],
    "aufenthalt": ["Aufenthaltserlaubnis beantragen", "Aufenthaltstitel"],
}

# Question words and filler dilute the PVOG full-text search ("Wo kann ich
# meine Wohnung anmelden?" matches worse than "Wohnung anmelden").
STOPWORDS = {
    "wo", "wie", "was", "wer", "wann", "welche", "welches", "welcher",
    "kann", "muss", "möchte", "will", "soll", "darf",
    "ich", "man", "mein", "meine", "meinen", "mich", "mir", "wir", "uns",
    "der", "die", "das", "ein", "eine", "einen", "einem", "einer",
    "und", "oder", "in", "an", "bei", "für", "zu", "nach", "von",
    "ist", "sind", "sich", "es", "denn", "bitte", "hier",
}

# Max organisation units whose detail we fetch while looking for an address.
MAX_DETAIL_LOOKUPS = 4

FALLBACK_SOURCE_URL = "https://servicesuche.bund.de/"


def _is_federal(leistung: dict) -> bool:
    return "000000000000" in (leistung.get("ars") or [])


def strip_stopwords(query: str) -> str:
    words = [
        w
        for w in query.replace("?", " ").replace(",", " ").split()
        # Digit tokens are PLZs or house numbers — location noise, not
        # part of the service name being searched.
        if w.lower() not in STOPWORDS and not w.isdigit()
    ]
    return " ".join(words) or query


@dataclass
class BehoerdeResult:
    authority_name: str
    service_name: str
    street: str | None = None
    zip: str | None = None
    city: str | None = None
    phone: str | None = None
    website: str | None = None

    def context_block(self) -> str:
        parts = [f"{self.authority_name} (zuständig für: {self.service_name})"]
        if self.street or self.city:
            address = ", ".join(p for p in [self.street, f"{self.zip or ''} {self.city or ''}".strip()] if p)
            parts.append(f"Adresse: {address}")
        if self.phone:
            parts.append(f"Telefon: {self.phone}")
        if self.website:
            parts.append(f"Website: {self.website}")
        return "\n".join(parts)

    def source(self) -> dict:
        return {
            "title": f"{self.authority_name} — {self.service_name}",
            "url": self.website or FALLBACK_SOURCE_URL,
        }


class BehoerdeFinder:
    def __init__(self, base_url: str = PVOG_BASE_URL):
        self.client = httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT)

    def find(self, plz: str, query: str, topic: str | None = None) -> BehoerdeResult | None:
        try:
            return self._find(plz, query, topic)
        except httpx.HTTPError:
            return None

    def _get(self, path: str, params: dict) -> httpx.Response:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response

    def _find(self, plz: str, query: str, topic: str | None) -> BehoerdeResult | None:
        queries = TOPIC_QUERIES.get(topic or "", []) + [strip_stopwords(query)]
        fallback: BehoerdeResult | None = None

        # Zuständigkeit data can hang at any ARS level (Berlin registers at
        # city level, not at the Bezirk the PLZ resolves to), so walk from
        # the most specific ARS up to Kreis and Land level. Land/Kommune
        # descriptions name the concrete local authority; federal ones
        # ("000000000000") mostly point at hotlines and only serve as
        # fallback once no local authority was found anywhere.
        for ars in self._candidate_ars(plz):
            for q in queries:
                leistungen = self._search_leistungen(ars, q)
                local = [l for l in leistungen if not _is_federal(l)]
                result = self._best_authority(ars, local[:3])
                if result and result.street:
                    return result
                if fallback is None:
                    fallback = result or self._best_authority(
                        ars, [l for l in leistungen if _is_federal(l)][:2]
                    )
        return fallback

    def _candidate_ars(self, plz: str) -> list[str]:
        locations = self._get("/v3/locations/details", {"plz": plz, "limit": 10}).json()
        if not locations:
            return []
        exact = [loc for loc in locations if loc.get("plz") == plz]
        ars = (exact or locations)[0].get("ars")
        if not ars:
            return []
        # ARS layout: Land(2) Reg.-Bezirk(1) Kreis(2) Verband(4) Gemeinde(3).
        candidates = [ars, ars[:5] + "0" * 7, ars[:2] + "0" * 10]
        return list(dict.fromkeys(candidates))

    def _search_leistungen(self, ars: str, query: str) -> list[dict]:
        payload = self._get(f"/v7/servicedescriptions/{ars}", {"q": query, "size": 5}).json()
        return payload.get("serviceDescriptions", {}).get("content", [])

    def _best_authority(self, ars: str, leistungen: list[dict]) -> BehoerdeResult | None:
        # Federal descriptions often only name a hotline/finder without an
        # address, while Land/Kommune ones name the concrete Jobcenter or
        # Bürgeramt — so prefer a unit with a physical address, then a
        # "Zuständige Stelle" (role 01) without one, then anything else.
        fallback: BehoerdeResult | None = None
        lookups = 0

        for leistung in leistungen[:3]:
            lbid = leistung.get("id")
            service_name = leistung.get("name") or ""
            if not lbid:
                continue
            units = self._get("/v2/organisationunits/titles", {"ars": ars, "lbId": lbid}).json()
            units.sort(key=lambda u: (u.get("role") or {}).get("code") != ROLE_RESPONSIBLE)

            for unit in units:
                if lookups >= MAX_DETAIL_LOOKUPS:
                    return fallback
                lookups += 1
                result = self._unit_detail(unit["id"], service_name)
                if result is None:
                    continue
                if result.street:
                    return result
                if fallback is None:
                    fallback = result
        return fallback

    def _unit_detail(self, oe_id: str, service_name: str) -> BehoerdeResult | None:
        response = self.client.get("/v5/organisationunits/detail", params={"q": oe_id})
        if response.status_code != 200:
            return None
        detail = response.json()
        location = detail.get("location") or {}

        address = next(
            (a for a in location.get("addresses", []) if a.get("type") == "Hausanschrift"),
            next(iter(location.get("addresses", [])), {}),
        )
        phone = next(
            (c.get("value") for c in location.get("communications", []) if c.get("code") == "02"),
            None,
        )
        website = next((i.get("uri") for i in detail.get("internetAddresses", []) if i.get("uri")), None)

        return BehoerdeResult(
            authority_name=detail.get("title") or "Zuständige Stelle",
            service_name=service_name,
            street=address.get("street"),
            zip=address.get("zip"),
            city=address.get("city"),
            phone=phone,
            website=website,
        )
