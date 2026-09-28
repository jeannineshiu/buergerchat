"""SourceList: numbered context in, (answer, sources) out — a source is only
a page the answer draws on (CONTEXT.md). No index, no model: chunks are
plain objects and the model's reply is a string."""

from types import SimpleNamespace

from behoerde import BehoerdeResult
from sources import AUTHORITY_HEADER, SourceList

URLS = ["https://example.org/a", "https://example.org/b", "https://example.org/c"]


def chunk(url, title, content="Inhalt"):
    return SimpleNamespace(url=url, title=title, content=content)


def pages():
    return [chunk(url, f"Seite {i}", f"Inhalt {i}") for i, url in enumerate(URLS)]


def urls(sources):
    return [s["url"] for s in sources]


FAMILIENKASSE = BehoerdeResult(authority_name="Familienkasse", service_name="Kindergeld", website="https://fk.example")


class TestContext:
    def test_blocks_are_numbered_in_rank_order(self):
        assert SourceList(pages()).context_text() == (
            "[1] Seite 0\nInhalt 0\n\n[2] Seite 1\nInhalt 1\n\n[3] Seite 2\nInhalt 2"
        )

    def test_authority_block_comes_first_without_a_number(self):
        text = SourceList(pages(), FAMILIENKASSE).context_text()
        assert text.startswith(f"{AUTHORITY_HEADER}\nFamilienkasse (zuständig für: Kindergeld)")
        assert "\n\n[1] Seite 0" in text

    def test_directive_asks_for_the_quellen_line(self):
        assert "QUELLEN: 1, 3" in SourceList(pages()).directive()

    def test_no_chunks_means_no_directive(self):
        assert SourceList([], FAMILIENKASSE).directive() is None


class TestUsedSources:
    def test_only_cited_pages_are_listed_and_marker_stripped(self):
        answer, sources = SourceList(pages()).resolve("Die Antwort.\n\nQUELLEN: 3, 1")
        assert answer == "Die Antwort."
        # Retrieval order, not the order the model listed them in.
        assert urls(sources) == [URLS[0], URLS[2]]

    def test_missing_marker_keeps_every_retrieved_page(self):
        answer, sources = SourceList(pages()).resolve("Die Antwort.")
        assert answer == "Die Antwort."
        assert urls(sources) == URLS

    def test_unreadable_marker_is_stripped_but_keeps_every_page(self):
        answer, sources = SourceList(pages()).resolve("Die Antwort.\nQUELLEN: die Seite der Familienkasse")
        assert answer == "Die Antwort."
        assert urls(sources) == URLS

    def test_none_used_lists_only_the_authority(self):
        answer, sources = SourceList(pages(), FAMILIENKASSE).resolve("Die Antwort.\nQUELLEN: -")
        assert answer == "Die Antwort."
        assert urls(sources) == ["https://fk.example"]

    def test_out_of_range_numbers_are_ignored(self):
        _, sources = SourceList(pages()).resolve("Die Antwort.\nQUELLEN: 2, 99")
        assert urls(sources) == [URLS[1]]

    def test_marker_with_native_digits_and_fullwidth_colon(self):
        answer, sources = SourceList(pages()).resolve("الجواب\nQUELLEN： ٢")
        assert answer == "الجواب"
        assert urls(sources) == [URLS[1]]

    def test_retry_that_drops_the_marker_keeps_the_first_list(self):
        answer, sources = SourceList(pages()).resolve("Antwort ย\nQUELLEN: 2", retry_reply="Antwort")
        assert answer == "Antwort"
        assert urls(sources) == [URLS[1]]

    def test_retry_with_its_own_marker_wins(self):
        answer, sources = SourceList(pages()).resolve("Antwort ย\nQUELLEN: 2", retry_reply="Antwort\nQUELLEN: 3")
        assert answer == "Antwort"
        assert urls(sources) == [URLS[2]]

    def test_answer_text_strips_the_marker(self):
        assert SourceList(pages()).answer_text("Die Antwort.\nQUELLEN: 1") == "Die Antwort."

    def test_without_chunks_the_reply_is_left_alone(self):
        source_list = SourceList([])
        assert source_list.answer_text("Hallo!\nQUELLEN: 1") == "Hallo!\nQUELLEN: 1"
        assert source_list.resolve("Hallo!") == ("Hallo!", [])


class TestDedupe:
    def test_chunks_of_one_page_list_it_once(self):
        _, sources = SourceList([
            chunk("https://example.org/kindergeld", "Kindergeld", "Teil eins"),
            chunk("https://example.org/kindergeld", "Kindergeld", "Teil zwei"),
        ]).resolve("Antwort")
        assert urls(sources) == ["https://example.org/kindergeld"]

    def test_syndicated_copies_list_the_first_in_rank_order(self):
        # arbeitsagentur.de publishes one article under per-Ort URLs, and
        # copies differ by stray whitespace in the title.
        _, sources = SourceList([
            chunk("https://example.org/vor-ort/x/kindergeld", "Kindergeld"),
            chunk("https://example.org/vor-ort/y/kindergeld", "Kindergeld "),
            chunk("https://example.org/vor-ort/z/kindergeld", "kindergeld"),
        ]).resolve("Antwort")
        assert urls(sources) == ["https://example.org/vor-ort/x/kindergeld"]

    def test_untitled_pages_are_deduped_by_url_only(self):
        _, sources = SourceList([chunk(URLS[0], ""), chunk(URLS[1], None)]).resolve("Antwort")
        assert urls(sources) == URLS[:2]


class TestAuthoritySource:
    def test_authority_is_the_first_source(self):
        _, sources = SourceList(pages(), FAMILIENKASSE).resolve("Antwort\nQUELLEN: 1")
        assert sources == [
            {"title": "Familienkasse — Kindergeld", "url": "https://fk.example"},
            {"title": "Seite 0", "url": URLS[0]},
        ]

    def test_authority_not_duplicated_when_also_retrieved(self):
        authority = BehoerdeResult(authority_name="Familienkasse", service_name="Kindergeld", website=URLS[0])
        _, sources = SourceList(pages(), authority).resolve("Antwort")
        assert urls(sources) == URLS
        assert sources[0]["title"] == "Familienkasse — Kindergeld"

    def test_authority_is_listed_without_retrieval(self):
        _, sources = SourceList([], FAMILIENKASSE).resolve("Antwort")
        assert urls(sources) == ["https://fk.example"]
