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

# Capability meta-questions ("what can I ask you?") must not go through
# retrieval — random chunks would pollute the answer and the source list.
# Covers the most common phrasings; the system prompt's META rule is the
# fallback for languages not listed here.
META_PATTERNS = [
    "was kannst du",
    "welche fragen",
    "was für fragen",
    "womit kannst du",
    "wobei kannst du helfen",
    "welche themen",
    "what can you",
    "what questions",
    "which questions",
    "what topics",
    "how can you help",
    "哪些問題",
    "哪些问题",
    "什麼問題",
    "什么问题",
    "你能做什麼",
    "你能做什么",
    "哪些主題",
    "哪些主题",
    "jakie pytania",
    "w czym możesz",
    "hangi sorular",
    "hangi konular",
    "какие вопросы",
    "які питання",
    "чем ты можешь",
    "чим ти можеш",
    "ما الأسئلة",
    "ماذا يمكنك",
    "چه سوالاتی",
    "چه سؤالاتی",
    "câu hỏi nào",
    "bạn có thể giúp gì",
    "pertanyaan apa",
    "bisa bantu apa",
    "어떤 질문",
    "무엇을 할 수",
]


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

    def is_meta_question(self, message: str) -> bool:
        lowered = message.lower()
        return any(pattern in lowered for pattern in META_PATTERNS)
