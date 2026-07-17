from router import QueryRouter

router = QueryRouter()


class TestClassify:
    def test_buergergeld_variants(self):
        assert router.classify("Was ist Bürgergeld?") == "buergergeld"
        assert router.classify("wie viel buergergeld bekomme ich") == "buergergeld"
        assert router.classify("Grundsicherung beantragen") == "buergergeld"
        assert router.classify("Wo ist mein Jobcenter?") == "buergergeld"

    def test_new_topics(self):
        assert router.classify("Wann kann ich in Rente gehen?") == "rente"
        assert router.classify("Wie beantrage ich Wohngeld?") == "wohngeld"
        assert router.classify("Was ist die Steuer-ID?") == "steuern"
        assert router.classify("Aufenthaltstitel verlängern") == "aufenthalt"
        assert router.classify("Ich will die Einbürgerung beantragen") == "aufenthalt"

    def test_kindergeld_includes_familienkasse(self):
        assert router.classify("Wo ist die Familienkasse?") == "kindergeld"

    def test_default_topic(self):
        assert router.classify("Hallo, wie geht es dir?") == "allgemein"


class TestWantsAuthority:
    def test_authority_intent(self):
        assert router.wants_authority("Welche Behörde ist zuständig?")
        assert router.wants_authority("Wo beantrage ich Kindergeld?")
        assert router.wants_authority("Wo ist mein Jobcenter?")

    def test_contact_details_request_is_authority_intent(self):
        # Regression: these two turns from a real session never triggered
        # the PVOG lookup, so the bot claimed to have no contact details
        # despite knowing the user's PLZ.
        assert router.wants_authority("gib mir die kontakt daten wie telefon nummer oder email")
        assert router.wants_authority("wo soll ich mich melden? Ich wohne in 10365 Berlin")
        assert router.wants_authority("Wie ist die Adresse der Elterngeldstelle?")
        assert router.wants_authority("What is the phone number of the office?")

    def test_no_intent_on_knowledge_question(self):
        assert not router.wants_authority("Was ist Bürgergeld?")
        assert not router.wants_authority("Wie hoch ist das Kindergeld?")

    def test_bare_amt_substring_does_not_trigger(self):
        # "amt" inside other words (gesamt, Amtsgericht-adjacent prose)
        # must not count as authority intent.
        assert not router.wants_authority("Wie hoch ist der Gesamtbetrag?")


class TestExtractPlz:
    def test_finds_plz(self):
        assert router.extract_plz("Ich wohne in 81667 München") == "81667"
        assert router.extract_plz("10115") == "10115"

    def test_no_plz(self):
        assert router.extract_plz("Ich wohne in München") is None

    def test_ignores_longer_numbers(self):
        assert router.extract_plz("Meine Nummer ist 123456789") is None


class TestIsMetaQuestion:
    def test_common_languages(self):
        assert router.is_meta_question("Welche Fragen kann ich dir stellen?")
        assert router.is_meta_question("What can you do?")
        assert router.is_meta_question("我可以問你哪些問題")
        assert router.is_meta_question("Jakie pytania mogę ci zadać?")
        assert router.is_meta_question("어떤 질문을 할 수 있나요?")

    def test_regular_questions_are_not_meta(self):
        assert not router.is_meta_question("Was ist Bürgergeld?")
        assert not router.is_meta_question("Wo beantrage ich Kindergeld?")
