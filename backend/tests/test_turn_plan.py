"""TurnPlanner with the real QueryRouter, a fake Behörden-Finder and a
table-driven fake translation — covers routing, the history fallbacks,
authority outcomes and how many translations a turn pays for."""

import pytest

from behoerde import BehoerdeResult
from router import QueryRouter
from turn_plan import Found, Kind, NeedsPlz, NotFound, NotRequested, TurnPlanner

# What the fake translation makes of non-German messages; anything else
# comes back unchanged (as to_german does for German text).
TRANSLATIONS = {
    "住房補助要去哪裡申請？10115": "Wo kann ich Wohngeld beantragen? 10115",
    "住房補助要去哪裡申請？": "Wo kann ich Wohngeld beantragen?",
    "兒童金可以補領嗎？": "Kann man Kindergeld nachträglich bekommen?",
    "Where do I get housing benefit? 10115": "Wo bekomme ich Wohngeld? 10115",
}

JOBCENTER = BehoerdeResult(authority_name="Jobcenter Test", service_name="X", website="https://jc.example")


class FakeFinder:
    """Finds the test Jobcenter for every PLZ except 99999 (PVOG empty)."""

    def __init__(self):
        self.calls = []

    def find(self, plz, query, topic=None):
        self.calls.append({"plz": plz, "query": query, "topic": topic})
        return None if plz == "99999" else JOBCENTER


@pytest.fixture()
def finder():
    return FakeFinder()


@pytest.fixture()
def translated():
    return []


@pytest.fixture()
def planner(finder, translated):
    def translate(text, language):
        translated.append(text)
        return TRANSLATIONS.get(text, text)

    return TurnPlanner(QueryRouter(), finder, translate)


def exchange(question, reply):
    return [{"role": "user", "content": question}, {"role": "assistant", "content": reply}]


class TestKind:
    def test_topical_question_is_answered(self, planner, finder):
        plan = planner.plan("Was ist Bürgergeld?")
        assert plan.kind is Kind.ANSWER
        assert plan.topic == "buergergeld"
        assert plan.authority == NotRequested()
        assert finder.calls == []  # no authority intent → no PVOG call

    def test_meta_question(self, planner):
        assert planner.plan("Welche Fragen kann ich dir stellen?").kind is Kind.META

    def test_chitchat(self, planner):
        assert planner.plan("Danke!").kind is Kind.CHITCHAT

    def test_question_starting_with_greeting_is_not_chitchat(self, planner):
        assert planner.plan("Hi, wo ist mein Jobcenter?").kind is Kind.ANSWER

    def test_history_is_carried_into_the_plan(self, planner):
        history = exchange("Wer bekommt Kindergeld?", "Eltern …")
        assert planner.plan("Danke!", history=history).history == tuple(history)


class TestAuthority:
    def test_intent_with_plz_is_looked_up(self, planner, finder):
        plan = planner.plan("Wo ist mein Jobcenter? Ich wohne in 81667")
        assert finder.calls[0]["plz"] == "81667"
        assert plan.authority == Found(JOBCENTER)

    def test_intent_without_plz_asks_for_it(self, planner, finder):
        plan = planner.plan("Wo beantrage ich Kindergeld?")
        assert plan.kind is Kind.ANSWER
        assert plan.authority == NeedsPlz()
        assert finder.calls == []

    def test_bare_plz_followup_uses_history(self, planner, finder):
        history = exchange("Wo beantrage ich Kindergeld?", "Bitte nennen Sie Ihre Postleitzahl.")
        plan = planner.plan("10115", history=history)
        # topic and lookup text come from the history, not the bare PLZ
        assert finder.calls == [
            {"plz": "10115", "query": "Wo beantrage ich Kindergeld?", "topic": "kindergeld"},
        ]
        assert plan.topic == "kindergeld"
        assert plan.authority == Found(JOBCENTER)

    def test_failed_lookup_is_not_found(self, planner):
        plan = planner.plan("Wo ist mein Jobcenter? PLZ 99999")
        assert plan.kind is Kind.ANSWER
        assert plan.authority == NotFound()

    def test_failed_lookup_without_a_topic_asks_what_it_is_about(self, planner):
        # A postcode alone does not determine a Behörde — responsibility is
        # per service. "Which office is responsible? 10115" used to be
        # answered with whatever PVOG's full-text search ranked first.
        # 99999 is the fake's "PVOG found nothing" postcode.
        plan = planner.plan("Which office is responsible? 99999")
        assert plan.kind is Kind.ASK_FOR_TOPIC
        assert plan.topic == "allgemein"
        assert plan.authority == NotRequested()


class TestTranslation:
    def test_non_german_authority_question_routes_on_translation(self, planner, finder, translated):
        # No Chinese keywords exist — the German translation carries both
        # the topic and the where-to-apply intent.
        plan = planner.plan("住房補助要去哪裡申請？10115", language="zh-Hant")
        assert plan.topic == "wohngeld"
        assert finder.calls == [
            {"plz": "10115", "query": "Wo kann ich Wohngeld beantragen? 10115", "topic": "wohngeld"},
        ]
        # retrieval reuses the translation instead of paying for it again
        assert plan.retrieval_query_de == "Wo kann ich Wohngeld beantragen? 10115"
        assert translated == ["住房補助要去哪裡申請？10115"]

    def test_english_question_routes_on_translation(self, planner, finder):
        # "housing benefit" is no topic keyword and "where do I get" no
        # intent phrase — only the German translation carries both.
        plan = planner.plan("Where do I get housing benefit? 10115", language="en")
        assert plan.topic == "wohngeld"
        assert finder.calls == [
            {"plz": "10115", "query": "Wo bekomme ich Wohngeld? 10115", "topic": "wohngeld"},
        ]

    def test_non_german_authority_question_without_plz_asks_for_it(self, planner, finder):
        plan = planner.plan("住房補助要去哪裡申請？", language="zh-Hant")
        assert plan.authority == NeedsPlz()
        assert finder.calls == []

    def test_bare_plz_followup_to_non_german_question(self, planner, finder):
        history = exchange("住房補助要去哪裡申請？", "請告訴我您的郵遞區號。")
        planner.plan("10115", language="zh-Hant", history=history)
        assert finder.calls == [
            {"plz": "10115", "query": "Wo kann ich Wohngeld beantragen?", "topic": "wohngeld"},
        ]

    def test_non_german_knowledge_question_does_not_trigger_lookup(self, planner, finder):
        plan = planner.plan("兒童金可以補領嗎？", language="zh-Hant")
        assert plan.topic == "kindergeld"
        assert plan.authority == NotRequested()
        assert finder.calls == []


class TestRetrievalQuery:
    def test_short_followup_enriches_retrieval_with_history(self, planner):
        # "say that in Chinese" carries no searchable meaning — retrieval
        # must reuse the previous question (the reported bug: random chunks).
        history = exchange("Wer bekommt Kindergeld?", "Kindergeld bekommen Eltern …")
        plan = planner.plan("用中文講一次", history=history)
        assert plan.retrieval_query == "Wer bekommt Kindergeld?\n用中文講一次"
        assert plan.message == "用中文講一次"  # prompt still shows the real message
        # the routing translation is of the message, not of the enriched query
        assert plan.retrieval_query_de is None

    def test_fresh_topical_question_keeps_plain_retrieval(self, planner):
        assert planner.plan("Was ist Bürgergeld?").retrieval_query is None
