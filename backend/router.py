"""Rule-based topic classification for incoming chat queries.

Placeholder for a future model-based router; keyword matching is enough
until the RAG pipeline (and real query volume) exists to justify more.
"""

TOPIC_KEYWORDS = {
    "buergergeld": ["buergergeld", "bürgergeld", "grundsicherung"],
    "kindergeld": ["kindergeld", "kinderzuschlag"],
    "arbeitslos": ["arbeitslos", "arbeitsuche", "arbeitslosengeld"],
    "familie-und-kinder": ["familie", "kinder", "elterngeld"],
}

DEFAULT_TOPIC = "allgemein"


class QueryRouter:
    def classify(self, message: str) -> str:
        lowered = message.lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return topic
        return DEFAULT_TOPIC
