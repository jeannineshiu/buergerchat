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
    # Authority names double as intent triggers in ANY language: the
    # frontend's follow-up suggestions embed the German name ("我的
    # Elterngeldstelle 在哪裡？"), which is also how users naturally ask.
    "elterngeldstelle",
    "wohngeldstelle",
    "wohngeldamt",
    "agentur für arbeit",
    "agentur fuer arbeit",
    "arbeitsagentur",
    "rentenversicherung",
    "finanzamt",
    "einbürgerungsbehörde",
    "einbuergerungsbehoerde",
    "beratungsstelle",
    # Asking for contact details or where to report IS asking for the
    # responsible authority ("gib mir die kontakt daten wie telefon nummer",
    # "wo soll ich mich melden?") — without these the PVOG lookup never
    # fired and the bot claimed to have no contact information.
    "kontakt",
    "telefon",
    "e-mail",
    "email",
    "adresse",
    "anschrift",
    "öffnungszeiten",
    "oeffnungszeiten",
    "sprechzeiten",
    "mich melden",
    "wo melde",
    "contact",
    "phone",
    "address",
    "which office",
    "opening hours",
    "where should i go",
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

# Pure small talk (greeting/thanks/goodbye) with no actual question — must
# match the ENTIRE normalized message, not a substring, so a real question
# that happens to start with "hi" ("hi, wo ist mein Jobcenter?") still goes
# through retrieval. Deliberately short list: only unambiguous phrasings
# that are never also the start of a real question.
CHITCHAT_PATTERNS = {
    # German
    "hallo", "hi", "hey", "servus", "moin", "guten tag", "guten morgen",
    "guten abend", "danke", "danke schön", "vielen dank", "dankeschön",
    "tschüss", "tschüs", "auf wiedersehen", "bis bald", "ciao",
    # English
    "hello", "hi there", "hey there", "good morning", "good afternoon",
    "good evening", "thanks", "thank you", "thanks a lot", "many thanks",
    "bye", "goodbye", "see you", "see ya",
    # Turkish
    "merhaba", "selam", "günaydın", "iyi günler", "iyi akşamlar",
    "teşekkürler", "teşekkür ederim", "çok teşekkürler", "hoşça kal",
    "görüşürüz",
    # Arabic
    "مرحبا", "أهلا", "السلام عليكم", "صباح الخير", "مساء الخير", "شكرا",
    "شكرا جزيلا", "مع السلامة", "إلى اللقاء",
    # Persian
    "سلام", "صبح بخیر", "عصر بخیر", "ممنون", "متشکرم", "خیلی ممنون",
    "خداحافظ",
    # Ukrainian
    "привіт", "добрий день", "доброго ранку", "добрий вечір", "дякую",
    "дуже дякую", "до побачення", "бувай",
    # Russian
    "привет", "добрый день", "доброе утро", "добрый вечер", "спасибо",
    "большое спасибо", "до свидания", "пока",
    # Polish
    "cześć", "witam", "dzień dobry", "dobry wieczór", "dziękuję",
    "dziękuję bardzo", "do widzenia", "pa",
    # Traditional / Simplified Chinese
    "你好", "哈囉", "早安", "午安", "晚安", "謝謝", "謝謝你", "非常感謝", "再見",
    "早上好", "谢谢", "谢谢你", "非常感谢", "再见",
    # Vietnamese
    "xin chào", "chào bạn", "chào buổi sáng", "cảm ơn", "cảm ơn bạn",
    "cảm ơn nhiều", "tạm biệt",
    # Indonesian
    "halo", "hai", "selamat pagi", "selamat siang", "selamat malam",
    "terima kasih", "terima kasih banyak", "sampai jumpa",
    # Korean
    "안녕", "안녕하세요", "좋은 아침", "감사합니다", "고마워요", "정말 감사합니다",
    "안녕히 가세요", "잘 가",
}

_CHITCHAT_STRIP = " \t\n!！?？.。,，~～"


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

    def is_chitchat(self, message: str) -> bool:
        normalized = message.strip().lower().strip(_CHITCHAT_STRIP)
        return normalized in CHITCHAT_PATTERNS
