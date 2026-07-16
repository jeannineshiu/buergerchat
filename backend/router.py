"""Rule-based topic classification for incoming chat queries.

Placeholder for a future model-based router; keyword matching is enough
until the RAG pipeline (and real query volume) exists to justify more.
"""

import re

TOPIC_KEYWORDS = {
    "buergergeld": ["buergergeld", "bürgergeld", "grundsicherung", "jobcenter"],
    "kindergeld": ["kindergeld", "kinderzuschlag", "familienkasse"],
    "arbeitslos": ["arbeitslos", "arbeitsuche", "arbeitslosengeld"],
    "familie-und-kinder": ["familie", "kinder", "elterngeld", "unterhaltsvorschuss", "mutterschaft"],
    "rente": ["rente", "altersvorsorge", "erwerbsminderung", "hinterbliebene", "witwenrente"],
    "wohngeld": ["wohngeld", "mietzuschuss", "lastenzuschuss"],
    "steuern": ["steuer", "finanzamt", "identifikationsnummer"],
    "aufenthalt": [
        "aufenthalt",
        "visum",
        "visa",
        "niederlassungserlaubnis",
        "einbürgerung",
        "einbuergerung",
        "ausländerbehörde",
        "auslaenderbehoerde",
        "asyl",
        "blaue karte",
        "integrationskurs",
    ],
}

DEFAULT_TOPIC = "allgemein"

# Signals that the user wants to know WHICH authority is responsible /
# where to go — orthogonal to the topic ("Wo beantrage ich Kindergeld?"
# is topic kindergeld + authority intent).
AUTHORITY_KEYWORDS = [
    "zuständig",
    "zustaendig",
    "behörde",
    "behoerde",
    "welches amt",
    "jobcenter",
    "familienkasse",
    "bürgeramt",
    "buergeramt",
    "wo beantrage",
    "wo kann ich beantragen",
    "wohin",
    "anlaufstelle",
    "welche stelle",
    "an wen",
    "in meiner nähe",
    "in meiner naehe",
]

PLZ_PATTERN = re.compile(r"\b\d{5}\b")


class QueryRouter:
    def classify(self, message: str) -> str:
        lowered = message.lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return topic
        return DEFAULT_TOPIC

    def wants_authority(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in AUTHORITY_KEYWORDS)

    def extract_plz(self, message: str) -> str | None:
        match = PLZ_PATTERN.search(message)
        return match.group(0) if match else None
