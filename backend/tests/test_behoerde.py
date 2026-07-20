"""BehoerdeFinder against a stubbed PVOG API (httpx.MockTransport — no
network). The stub models the quirks the real API showed: data hanging at
city-level ARS while the PLZ resolves deeper, and federal descriptions
that only name hotlines."""

import httpx

from behoerde import BehoerdeFinder, BehoerdeResult, strip_stopwords, _district_of, _is_federal

BERLIN_DEEP_ARS = "110010001001"
BERLIN_CITY_ARS = "110000000000"


def make_finder(handler) -> BehoerdeFinder:
    finder = BehoerdeFinder()
    finder.client = httpx.Client(
        base_url="https://pvog.test/api", transport=httpx.MockTransport(handler)
    )
    return finder


def pvog_stub(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    params = request.url.params

    if path.endswith("/v3/locations/details"):
        return httpx.Response(200, json=[
            {"ars": BERLIN_CITY_ARS, "plz": "10178", "name": "Berlin, Stadt"},
            {"ars": BERLIN_DEEP_ARS, "plz": "10115", "name": "Berlin Mitte"},
        ])

    if "/v7/servicedescriptions/" in path:
        ars = path.rsplit("/", 1)[1]
        if ars == BERLIN_DEEP_ARS:
            # Deep ARS only sees the federal description.
            content = [{"id": "B1.LB.1", "name": "Bürgergeld beantragen", "ars": ["000000000000"]}]
        else:
            content = [
                {"id": "B1.LB.1", "name": "Bürgergeld beantragen", "ars": ["000000000000"]},
                {"id": "L1.LB.2", "name": "Bürgergeld; Beantragung", "ars": [BERLIN_CITY_ARS]},
            ]
        return httpx.Response(200, json={"serviceDescriptions": {"content": content}})

    if path.endswith("/v2/organisationunits/titles"):
        lb_id = params.get("lbId")
        ars = params.get("ars")
        if lb_id == "L1.LB.2" and ars == BERLIN_CITY_ARS:
            return httpx.Response(200, json=[
                {"id": "L1.OE.7", "title": "Jobcenter Berlin Mitte", "role": {"code": "01"}},
            ])
        if lb_id == "B1.LB.1":
            return httpx.Response(200, json=[
                {"id": "B1.OE.9", "title": "BA Hotline", "role": {"code": "03"}},
            ])
        return httpx.Response(200, json=[])

    if path.endswith("/v5/organisationunits/detail"):
        oe_id = params.get("q")
        if oe_id == "L1.OE.7":
            return httpx.Response(200, json={
                "title": "Jobcenter Berlin Mitte",
                "location": {
                    "addresses": [
                        {"type": "Hausanschrift", "street": "Teststr. 1", "zip": "10115", "city": "Berlin"}
                    ],
                    "communications": [{"code": "02", "value": "+49 30 123"}],
                },
                "internetAddresses": [{"uri": "https://jobcenter.example"}],
            })
        return httpx.Response(200, json={
            "title": "BA Hotline",
            "location": {"addresses": [], "communications": []},
            "internetAddresses": [],
        })

    raise AssertionError(f"unexpected path {path}")


class TestFind:
    def test_walks_ars_up_and_prefers_local_authority(self):
        finder = make_finder(pvog_stub)
        result = finder.find("10115", "Wo ist mein Jobcenter?", topic="buergergeld")
        assert result is not None
        assert result.authority_name == "Jobcenter Berlin Mitte"
        assert result.street == "Teststr. 1"
        assert result.phone == "+49 30 123"

    def test_unknown_plz_returns_none(self):
        def handler(request):
            if request.url.path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[])
            raise AssertionError("should stop after empty location lookup")

        finder = make_finder(handler)
        assert finder.find("99999", "Jobcenter", topic="buergergeld") is None

    def test_http_error_returns_none_instead_of_raising(self):
        def handler(request):
            return httpx.Response(500)

        finder = make_finder(handler)
        assert finder.find("10115", "Jobcenter", topic="buergergeld") is None

    def test_prefers_unit_naming_the_users_district(self):
        # Berlin registers one city-level Leistung with every Bezirk's
        # office attached; the Bezirk (digits 4-5 of the location ARS)
        # is the signal for the right one — the quoted location name is
        # only the Ortsteil ("Alt-Treptow"), which must NOT be needed.
        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[
                    {"ars": BERLIN_CITY_ARS, "plz": "10178", "name": "Berlin, Stadt"},
                    {"ars": "110090009009", "plz": "12435", "name": "Berlin 'Alt-Treptow'"},
                ])
            if "/v7/servicedescriptions/" in path:
                content = [{"id": "L1.LB.5", "name": "Elterngeld beantragen", "ars": [BERLIN_CITY_ARS]}]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            if path.endswith("/v2/organisationunits/titles"):
                return httpx.Response(200, json=[
                    {"id": "L1.OE.1", "title": "Jugendamt - Familienservicebüro", "role": {"code": "01"}},
                    {"id": "L1.OE.2", "title": "Jugendamt Spandau - Elterngeldstelle", "role": {"code": "01"}},
                    {"id": "L1.OE.3", "title": "Jugendamt Treptow-Köpenick - Elterngeldstelle", "role": {"code": "01"}},
                ])
            if path.endswith("/v5/organisationunits/detail"):
                titles = {
                    "L1.OE.1": "Jugendamt - Familienservicebüro",
                    "L1.OE.2": "Jugendamt Spandau - Elterngeldstelle",
                    "L1.OE.3": "Jugendamt Treptow-Köpenick - Elterngeldstelle",
                }
                return httpx.Response(200, json={
                    "title": titles[request.url.params.get("q")],
                    "location": {
                        "addresses": [{"type": "Hausanschrift", "street": "Teststr. 2", "zip": "12435", "city": "Berlin"}],
                        "communications": [],
                    },
                    "internetAddresses": [],
                })
            raise AssertionError(path)

        finder = make_finder(handler)
        result = finder.find("12435", "Elterngeld", topic="familie-und-kinder")
        assert result is not None
        assert result.authority_name == "Jugendamt Treptow-Köpenick - Elterngeldstelle"

    def test_federal_hotline_is_fallback_when_no_local_data(self):
        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[{"ars": BERLIN_CITY_ARS, "plz": "10115"}])
            if "/v7/servicedescriptions/" in path:
                content = [{"id": "B1.LB.1", "name": "Kindergeld beantragen", "ars": ["000000000000"]}]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            if path.endswith("/v2/organisationunits/titles"):
                return httpx.Response(200, json=[{"id": "B1.OE.9", "title": "Familienkasse Hotline", "role": {"code": "03"}}])
            if path.endswith("/v5/organisationunits/detail"):
                return httpx.Response(200, json={"title": "Familienkasse Hotline", "location": {}, "internetAddresses": []})
            raise AssertionError(path)

        finder = make_finder(handler)
        result = finder.find("10115", "Kindergeld", topic="kindergeld")
        assert result is not None
        assert result.authority_name == "Familienkasse Hotline"
        assert result.street is None


class TestTopicQueries:
    def test_every_router_topic_has_pvog_queries(self):
        # A router topic without a TOPIC_QUERIES entry falls back to the raw
        # user message, which for contact-style questions ("gib mir die
        # kontakt daten") matches nothing in PVOG. familie-und-kinder was
        # missing and Elterngeld lookups silently failed.
        from behoerde import TOPIC_QUERIES
        from router import TOPIC_KEYWORDS

        assert set(TOPIC_KEYWORDS) <= set(TOPIC_QUERIES)


class TestHelpers:
    def test_district_of_berlin_ars(self):
        assert _district_of({"ars": "110090009009", "name": "Berlin 'Alt-Treptow'"}) == "Treptow-Köpenick"
        assert _district_of({"ars": "110110011011", "name": "Berlin 'Lichtenberg'"}) == "Lichtenberg"
        # City-level ARS has Bezirk "00" — no district.
        assert _district_of({"ars": "110000000000", "name": "Berlin, Stadt"}) is None

    def test_district_of_ignores_quoted_ortsteil_in_berlin(self):
        # "Kol. Einigkeit" is an Ortsteil, never an office title — inside
        # Berlin only the ARS table counts.
        assert _district_of({"ars": "110000000000", "name": "Berlin 'Kol. Einigkeit'"}) is None

    def test_district_of_falls_back_to_quoted_name_outside_berlin(self):
        assert _district_of({"ars": "020000000000", "name": "Hamburg 'Altona'"}) == "Altona"
        assert _district_of({"ars": "091620000000", "name": "München"}) is None

    def test_strip_stopwords(self):
        assert strip_stopwords("Wo kann ich meine Wohnung anmelden?") == "Wohnung anmelden"

    def test_strip_stopwords_drops_plz_digits(self):
        assert "81667" not in strip_stopwords("Jobcenter? Ich wohne in 81667 München")

    def test_strip_stopwords_never_returns_empty(self):
        assert strip_stopwords("wo kann ich") == "wo kann ich"

    def test_is_federal(self):
        assert _is_federal({"ars": ["000000000000"]})
        assert not _is_federal({"ars": ["110000000000"]})
        assert not _is_federal({})

    def test_context_block_and_source(self):
        result = BehoerdeResult(
            authority_name="Jobcenter X",
            service_name="Bürgergeld beantragen",
            street="Weg 1",
            zip="10115",
            city="Berlin",
            phone="+49 30 1",
            website="https://x.example",
        )
        block = result.context_block()
        assert "Jobcenter X" in block and "Weg 1, 10115 Berlin" in block
        assert result.source() == {
            "title": "Jobcenter X — Bürgergeld beantragen",
            "url": "https://x.example",
        }

    def test_source_falls_back_without_website(self):
        result = BehoerdeResult(authority_name="A", service_name="B")
        assert result.source()["url"].startswith("https://servicesuche.bund.de")
