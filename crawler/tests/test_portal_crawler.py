from portal_crawler import SITES, Site, classify_topic, extract_page, url_allowed


def make_site(**overrides) -> Site:
    defaults = dict(name="test", host="www.example.de", topic_rules=[], default_topic="thema")
    defaults.update(overrides)
    return Site(**defaults)


class TestUrlAllowed:
    def test_same_host_required(self):
        site = make_site()
        assert url_allowed(site, "https://www.example.de/seite")
        assert url_allowed(site, "https://example.de/seite")  # www-less variant
        assert not url_allowed(site, "https://www.other.de/seite")

    def test_host_check_is_case_insensitive(self):
        # bamf.de's <base> tag says www.BAMF.de — cost us a whole crawl once.
        site = make_site(host="www.bamf.de")
        assert url_allowed(site, "https://www.BAMF.de/DE/Themen/x.html")

    def test_exclude_prefixes(self):
        site = make_site(url_exclude=["/DE/Service/"])
        assert not url_allowed(site, "https://www.example.de/DE/Service/suche.html")
        assert url_allowed(site, "https://www.example.de/DE/Themen/x.html")

    def test_include_regex(self):
        site = make_site(url_include=r"/dienstleistung/\d+/$")
        assert url_allowed(site, "https://www.example.de/dienstleistung/120686/")
        assert not url_allowed(site, "https://www.example.de/dienstleistung/120686/pdf/")

    def test_binary_extensions_rejected(self):
        site = make_site()
        for ext in (".pdf", ".jpg", ".xml", ".zip"):
            assert not url_allowed(site, f"https://www.example.de/datei{ext}")


class TestClassifyTopic:
    def test_first_matching_rule_wins(self):
        site = make_site(topic_rules=[("kindergeld", "kindergeld"), ("geld", "sonstiges")])
        assert classify_topic(site, "https://x.de/kindergeld-info") == "kindergeld"

    def test_default_topic_fallback(self):
        site = make_site(default_topic="steuern")
        assert classify_topic(site, "https://x.de/whatever") == "steuern"

    def test_none_default_means_skip(self):
        site = make_site(default_topic=None)
        assert classify_topic(site, "https://x.de/whatever") is None


class TestExtractPage:
    HTML = """
    <html><head><title>Seitentitel - Portal - Unterseite</title>
    <base href="https://www.EXAMPLE.de/"/></head>
    <body>
      <nav>Hauptmenü Punkt1 Punkt2</nav>
      <div class="c-breadcrumb">Sie sind hier: Start</div>
      <main>
        <h1>Wohngeld beantragen</h1>
        <p>Wohngeld ist ein Zuschuss zur Miete für Menschen mit wenig Einkommen.</p>
        <a href="DE/Themen/wohngeld.html">Mehr</a>
      </main>
      <footer>Impressum</footer>
    </body></html>
    """

    def test_h1_preferred_over_title(self):
        title, _, _, _ = extract_page(self.HTML)
        assert title == "Wohngeld beantragen"

    def test_nav_breadcrumb_footer_stripped(self):
        _, content, _, _ = extract_page(self.HTML)
        assert "Hauptmenü" not in content
        assert "Sie sind hier" not in content
        assert "Impressum" not in content
        assert "Zuschuss zur Miete" in content

    def test_links_and_base_href_returned(self):
        _, _, links, base = extract_page(self.HTML)
        assert "DE/Themen/wohngeld.html" in links
        assert base == "https://www.EXAMPLE.de/"

    def test_title_falls_back_to_title_tag(self):
        html = "<html><head><title>Nur  Titel | Site</title></head><body><p>Text</p></body></html>"
        title, _, _, _ = extract_page(html)
        assert title == "Nur Titel"


class TestSiteConfigs:
    def test_all_sites_have_discovery_mechanism(self):
        for site in SITES.values():
            assert site.sitemap_url or site.seed_urls, site.name

    def test_bfs_sites_have_path_prefix(self):
        for site in SITES.values():
            if not site.sitemap_url:
                assert site.bfs_path_prefix, site.name

    def test_robots_crawl_delays_preserved(self):
        # These delays come from the sites' robots.txt — do not lower them.
        assert SITES["bzst"].crawl_delay >= 30
        assert SITES["drv"].crawl_delay >= 12
