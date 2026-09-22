"""Turn planning: decides what kind of answer one /chat turn gets.

A turn is one user message plus the conversation so far. Planning resolves
everything that can be split across turns ("Wo ist mein Jobcenter?" → bot
asks for the PLZ → "10115"): topic, PLZ and authority intent fall back to
the user's history, the Behörden-Finder is asked when intent and PLZ are
both known, and short follow-ups get a retrieval query enriched with the
previous question. The result is a TurnPlan, which RAGPipeline.answer()
turns into a prompt — see CONTEXT.md for the vocabulary.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from behoerde import BehoerdeFinder, BehoerdeResult
from router import DEFAULT_TOPIC, QueryRouter


class Kind(Enum):
    CHITCHAT = "chitchat"  # greeting / thanks / bye: one friendly sentence
    META = "meta"  # "what can you do?": answered from the system prompt
    ASK_FOR_TOPIC = "ask_for_topic"  # authority wanted, but for what? ask back
    ANSWER = "answer"  # retrieve and answer


@dataclass(frozen=True)
class NotRequested:
    """The turn doesn't ask which Behörde is responsible."""


@dataclass(frozen=True)
class NeedsPlz:
    """Authority wanted, no PLZ anywhere in the conversation: ask for it."""


@dataclass(frozen=True)
class Found:
    result: BehoerdeResult


@dataclass(frozen=True)
class NotFound:
    """The lookup ran and came back empty: the answer must not invent one."""


AuthorityOutcome = NotRequested | NeedsPlz | Found | NotFound


@dataclass(frozen=True)
class TurnPlan:
    kind: Kind
    message: str
    language: str = "de"
    history: tuple[dict, ...] = ()
    topic: str = DEFAULT_TOPIC
    # Always NotRequested unless kind is ANSWER.
    authority: AuthorityOutcome = NotRequested()
    # None: retrieval embeds the message itself.
    retrieval_query: str | None = None
    # German translation of exactly the text retrieval embeds, when routing
    # already paid for it; None lets retrieval translate on its own.
    retrieval_query_de: str | None = None

    @classmethod
    def direct(cls, message: str, language: str = "de", topic: str = DEFAULT_TOPIC) -> "TurnPlan":
        """A standalone question, no history and no authority lookup: what
        the evals ask."""
        return cls(Kind.ANSWER, message, language, topic=topic)


# (text, language) → German text; RAGPipeline.to_german in production.
Translate = Callable[[str, str], str]


class TurnPlanner:
    def __init__(self, router: QueryRouter, finder: BehoerdeFinder, translate: Translate):
        self._router = router
        self._finder = finder
        self._translate = translate

    def plan(self, message: str, language: str = "de", history=()) -> TurnPlan:
        """history: [{role: user|assistant, content}], oldest first."""
        history = tuple(history)
        router = self._router

        if router.is_chitchat(message):
            # Pure small talk ("hi", "danke", "bye") — skip retrieval, same as
            # meta-questions, so no LLM call burns an embedding + top-5 search
            # (and no stray chunks leak into a source list that shouldn't exist).
            return TurnPlan(Kind.CHITCHAT, message, language, history)
        if router.is_meta_question(message):
            return TurnPlan(Kind.META, message, language, history)

        user_history = [m["content"] for m in history if m["role"] == "user"]

        # Topic and authority keywords are German/English only, so routing also
        # looks at the German translation — the same one retrieval embeds, so a
        # first-turn question costs no extra call. Translations are cached per
        # turn; for de/en messages to_german() is a no-op.
        translations: dict[str, str] = {}

        def german(text: str) -> str:
            if text not in translations:
                translations[text] = self._translate(text, language)
            return translations[text]

        def classify(text: str, translate: bool = True) -> str:
            found = router.classify(text)
            if found == DEFAULT_TOPIC and translate:
                found = router.classify(german(text))
            return found

        def asks_for_authority(text: str, translate: bool = True) -> bool:
            return router.wants_authority(text) or (
                translate and router.wants_authority(german(text))
            )

        # History messages are only translated for the last two user turns —
        # each translation is a model call, and older turns rarely decide.
        recent_history = user_history[-2:]

        message_topic = classify(message)
        topic = message_topic
        if topic == DEFAULT_TOPIC:
            for i, past in enumerate(reversed(user_history)):
                past_topic = classify(past, translate=i < len(recent_history))
                if past_topic != DEFAULT_TOPIC:
                    topic = past_topic
                    break

        # Short follow-ups ("erkläre das nochmal", "用中文講一次", a bare PLZ)
        # carry no searchable meaning — embedding them retrieves noise. Enrich
        # the retrieval query with the previous question; the prompt still shows
        # the user's actual message.
        retrieval_query = None
        if message_topic == DEFAULT_TOPIC and user_history and len(message) <= 80:
            retrieval_query = f"{user_history[-1]}\n{message}"

        plz = router.extract_plz(message)
        if plz is None:
            for past in reversed(user_history):
                plz = router.extract_plz(past)
                if plz:
                    break

        # Translating history just to detect intent only pays off once a PLZ
        # makes a lookup possible ("住房補助要去哪裡申請？" → "10115").
        wants_authority = asks_for_authority(message) or any(
            asks_for_authority(past, translate=plz is not None) for past in recent_history
        )

        authority: AuthorityOutcome = NotRequested()
        if wants_authority and plz:
            # A bare-PLZ follow-up carries no searchable text of its own — the
            # question it answers is the previous user message. PVOG is searched
            # in German either way.
            lookup_query = message
            if message.strip() == plz and user_history:
                lookup_query = user_history[-1]
            result = self._finder.find(plz, german(lookup_query), topic=topic)
            if result is not None:
                authority = Found(result)
            elif topic == DEFAULT_TOPIC:
                # A postcode alone does not determine a Behörde — responsibility
                # is per service. When the lookup came back empty and the message
                # never said what it is about ("Which office is responsible?
                # 10115"), ask rather than send the person off to a generic
                # search page.
                return TurnPlan(Kind.ASK_FOR_TOPIC, message, language, history)
            else:
                authority = NotFound()
        elif wants_authority:
            authority = NeedsPlz()

        return TurnPlan(
            Kind.ANSWER,
            message,
            language,
            history,
            topic=topic,
            authority=authority,
            retrieval_query=retrieval_query,
            # The routing translation is of the message, so it only applies
            # when the message is what retrieval embeds.
            retrieval_query_de=None if retrieval_query else translations.get(message),
        )
