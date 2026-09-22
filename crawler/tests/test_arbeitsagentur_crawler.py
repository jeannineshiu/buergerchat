from arbeitsagentur_crawler import classify_topic, extract_page

# Shaped like a real arbeitsagentur.de press release (checked 2026-09-22):
# an image-credit h1 ("Bildnachweis") comes before the article heading, and
# contact details sit in an <aside class="ba-copytext"> inside <main>.
PRESS_RELEASE = """
<html><head><title>Arbeitslosigkeit steigt saisonal bedingt | Bundesagentur für Arbeit</title></head>
<body>
  <header><h1>Bundesagentur für Arbeit</h1></header>
  <main>
    <nav class="ba-breadcrumb"><a href="/">Startseite</a></nav>
    <h1>Bildnachweis</h1>
    <h1>Arbeitslosigkeit steigt saisonal bedingt</h1>
    <p>Die Arbeitslosigkeit in Ost- und Waldhessen ist im Februar gestiegen.</p>
    <aside class="ba-copytext">Ansprechpartnerin für die Region Fulda ist Monika Krebs, Telefon 0661 17-149.</aside>
    <script>track()</script>
  </main>
  <footer>Impressum</footer>
</body></html>
"""


class TestExtractPage:
    def test_title_comes_from_title_tag_not_first_h1(self):
        # The first h1 is an image credit on most pages: taking it would title
        # every record "Bildnachweis" (portal_crawler's h1-first rule did, 5/5).
        title, _ = extract_page(PRESS_RELEASE)
        assert title == "Arbeitslosigkeit steigt saisonal bedingt"

    def test_aside_content_is_kept(self):
        # Unlike the portal sites, asides here carry real content: contact
        # persons and phone numbers (portal_crawler drops asides, -18% text).
        _, content = extract_page(PRESS_RELEASE)
        assert "Monika Krebs, Telefon 0661 17-149" in content

    def test_chrome_is_removed(self):
        _, content = extract_page(PRESS_RELEASE)
        assert "Startseite" not in content
        assert "track()" not in content
        assert "Impressum" not in content
        assert content.startswith("Bildnachweis Arbeitslosigkeit steigt")

    def test_h1_is_the_fallback_without_a_title_tag(self):
        title, _ = extract_page("<html><body><main><h1>Kindergeld</h1><p>Text</p></main></body></html>")
        assert title == "Kindergeld"


class TestClassifyTopic:
    def test_keywords_map_to_topics(self):
        assert classify_topic("https://www.arbeitsagentur.de/familie-und-kinder/kinderzuschlag") == "kindergeld"
        assert classify_topic("https://www.arbeitsagentur.de/arbeitslos-arbeit-finden") == "arbeitslos"
        assert classify_topic("https://www.arbeitsagentur.de/vor-ort/mainz/presse/20-jahre-jobcenter") == "buergergeld"

    def test_first_matching_topic_wins(self):
        # "familie-und-kinder" is in the path, but kindergeld is checked first.
        assert classify_topic("https://www.arbeitsagentur.de/familie-und-kinder/kindergeld") == "kindergeld"

    def test_unrelated_pages_are_skipped(self):
        assert classify_topic("https://www.arbeitsagentur.de/unternehmen/personalfragen") is None
