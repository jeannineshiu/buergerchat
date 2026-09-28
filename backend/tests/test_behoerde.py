"""BehoerdeFinder against a stubbed PVOG API (httpx.MockTransport — no
network). The stub models the quirks the real API showed: data hanging at
city-level ARS while the PLZ resolves deeper, and federal descriptions
that only name hotlines."""

import httpx

from behoerde import (
    BehoerdeFinder,
    BehoerdeResult,
    is_relevant,
    key_terms,
    strip_stopwords,
    HAMBURG_JOBCENTER_BY_STADTTEIL,
    HAMBURG_STADTTEILE,
    _district_of,
    _is_federal,
)

BERLIN_DEEP_ARS = "110010001001"
BERLIN_CITY_ARS = "110000000000"
MUENCHEN_ARS = "091620000000"
HAMBURG_ARS = "020000000000"


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

    def test_hamburg_stadtteil_picks_its_bezirks_office(self):
        # 20095 resolves to the city ARS only, with Stadtteile as quoted
        # names; offices are titled by Bezirk. The first unit PVOG lists
        # (Altona) used to win for a Hamburg-Mitte address.
        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[
                    {"ars": HAMBURG_ARS, "plz": "20038", "name": "Hamburg, Freie und Hansestadt"},
                    {"ars": HAMBURG_ARS, "plz": "20095", "name": "Hamburg 'Hamburg-Altstadt'"},
                    {"ars": HAMBURG_ARS, "plz": "20095", "name": "Hamburg 'St. Georg'"},
                ])
            if "/v7/servicedescriptions/" in path:
                content = [{
                    "id": "L2.LB.1",
                    "name": "Sozialhilfe, Grundsicherung im Alter und bei dauerhafter Erwerbsminderung beantragen",
                    "ars": [HAMBURG_ARS],
                }]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            if path.endswith("/v2/organisationunits/titles"):
                return httpx.Response(200, json=[
                    {"id": "L2.OE.1", "title": "Bezirksamt Altona - Soziales Dienstleistungszentrum Altona - Grundsicherung", "role": {"code": "03"}},
                    {"id": "L2.OE.2", "title": "Bezirksamt Eimsbüttel - Fachamt Grundsicherung und Soziales", "role": {"code": "03"}},
                    {"id": "L2.OE.3", "title": "Bezirksamt Hamburg-Mitte - Fachamt Grundsicherung und Soziales", "role": {"code": "03"}},
                ])
            if path.endswith("/v5/organisationunits/detail"):
                titles = {
                    "L2.OE.1": "Bezirksamt Altona - Soziales Dienstleistungszentrum Altona - Grundsicherung",
                    "L2.OE.2": "Bezirksamt Eimsbüttel - Fachamt Grundsicherung und Soziales",
                    "L2.OE.3": "Bezirksamt Hamburg-Mitte - Fachamt Grundsicherung und Soziales",
                }
                return httpx.Response(200, json={
                    "title": titles[request.url.params.get("q")],
                    "location": {
                        "addresses": [{"type": "Hausanschrift", "street": "Teststr. 3", "zip": "20095", "city": "Hamburg"}],
                        "communications": [],
                    },
                    "internetAddresses": [],
                })
            raise AssertionError(path)

        finder = make_finder(handler)
        result = finder.find("20095", "Wo beantrage ich Grundsicherung im Alter?", topic="rente")
        assert result is not None
        assert result.authority_name == "Bezirksamt Hamburg-Mitte - Fachamt Grundsicherung und Soziales"

    def _hamburg_jobcenter_handler(self, locations):
        # The Jobcenter's 17 units as live PVOG lists them (2026-09-28):
        # named by Stadtteil, or by Bezirk without the "Hamburg-" prefix.
        standorte = [
            "Altona", "Barmbek", "Bergedorf", "Billstedt", "Bramfeld", "Eimsbüttel",
            "Hamburg-Nord", "Harburg", "Lokstedt", "Mitte", "Mümmelmannsberg",
            "Osdorf", "Rahlstedt", "St. Pauli", "Süderelbe", "Wandsbek", "Wilhelmsburg",
        ]
        titles = {
            f"L3.OE.{i}": f"Jobcenter team.arbeit.hamburg - Standort {s}"
            for i, s in enumerate(standorte)
        }

        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=locations)
            if "/v7/servicedescriptions/" in path:
                content = [{"id": "L3.LB.1", "name": "Bürgergeld beantragen", "ars": [HAMBURG_ARS]}]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            if path.endswith("/v2/organisationunits/titles"):
                return httpx.Response(200, json=[
                    {"id": oe, "title": title, "role": {"code": "03"}} for oe, title in titles.items()
                ])
            if path.endswith("/v5/organisationunits/detail"):
                return httpx.Response(200, json={
                    "title": titles[request.url.params.get("q")],
                    "location": {
                        "addresses": [{"type": "Hausanschrift", "street": "Teststr. 4", "zip": "20097", "city": "Hamburg"}],
                        "communications": [],
                    },
                    "internetAddresses": [],
                })
            raise AssertionError(path)

        return handler

    def test_hamburg_jobcenter_standort_named_by_bezirk_without_prefix(self):
        # 20095 is Bezirk Hamburg-Mitte, but its Standort is titled just
        # "Mitte" — the Bezirk match fails and Altona (listed first) won.
        handler = self._hamburg_jobcenter_handler([
            {"ars": HAMBURG_ARS, "plz": "20095", "name": "Hamburg 'Hamburg-Altstadt'"},
            {"ars": HAMBURG_ARS, "plz": "20095", "name": "Hamburg 'St. Georg'"},
        ])
        result = make_finder(handler).find("20095", "Wo ist mein Jobcenter?", topic="buergergeld")
        assert result is not None
        assert result.authority_name == "Jobcenter team.arbeit.hamburg - Standort Mitte"

    def test_hamburg_jobcenter_standort_follows_its_own_zustaendigkeit(self):
        # Horn lies in Bezirk Hamburg-Mitte, but team.arbeit.hamburg sends
        # it to Standort Billstedt; Niendorf (Eimsbüttel) goes to Lokstedt.
        horn = self._hamburg_jobcenter_handler([
            {"ars": HAMBURG_ARS, "plz": "22119", "name": "Hamburg 'Horn'"},
        ])
        result = make_finder(horn).find("22119", "Wo ist mein Jobcenter?", topic="buergergeld")
        assert result.authority_name == "Jobcenter team.arbeit.hamburg - Standort Billstedt"

        niendorf = self._hamburg_jobcenter_handler([
            {"ars": HAMBURG_ARS, "plz": "22455", "name": "Hamburg 'Niendorf'"},
        ])
        result = make_finder(niendorf).find("22455", "Wo ist mein Jobcenter?", topic="buergergeld")
        assert result.authority_name == "Jobcenter team.arbeit.hamburg - Standort Lokstedt"

    def test_hamburg_billstedt_standort_depends_on_the_plz(self):
        # 22115 belongs to Standort Mümmelmannsberg; its 22113/22117 cases
        # are served at Standort Billstedt's address for now.
        for plz, standort in [("22115", "Mümmelmannsberg"), ("22117", "Billstedt"), ("22111", "Billstedt")]:
            handler = self._hamburg_jobcenter_handler([
                {"ars": HAMBURG_ARS, "plz": plz, "name": "Hamburg 'Billstedt'"},
            ])
            result = make_finder(handler).find(plz, "Wo ist mein Jobcenter?", topic="buergergeld")
            assert result.authority_name == f"Jobcenter team.arbeit.hamburg - Standort {standort}", plz

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
                return httpx.Response(200, json={
                    "title": "Familienkasse Hotline",
                    "location": {"communications": [{"code": "02", "value": "+49 800 4555530"}]},
                    "internetAddresses": [],
                })
            raise AssertionError(path)

        finder = make_finder(handler)
        result = finder.find("10115", "Kindergeld", topic="kindergeld")
        assert result is not None
        assert result.authority_name == "Familienkasse Hotline"
        assert result.street is None
        assert result.phone == "+49 800 4555530"


class TestRelevanceGuard:
    """PVOG always answers with its nearest rows, never with "no match" —
    so an off-topic query used to come back with a confident address."""

    def unrelated_stub(self, expect_queries=None):
        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[{"ars": BERLIN_CITY_ARS, "plz": "10115"}])
            if "/v7/servicedescriptions/" in path:
                if expect_queries is not None:
                    expect_queries.append(request.url.params.get("q"))
                content = [{
                    "id": "B1.LB.1",
                    "name": "Einen Streit bei der Schlichtungsstelle der BaFin schlichten",
                    "ars": ["000000000000"],
                }]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            raise AssertionError(f"lookup should stop before {path}")

        return handler

    def test_unrelated_leistung_is_not_offered_as_the_authority(self):
        finder = make_finder(self.unrelated_stub())
        assert finder.find("10115", "Wo beantrage ich Wohngeld?", topic="wohngeld") is None

    def test_foreign_language_question_matches_no_german_service(self):
        # "Which office is responsible?" names no German service — a
        # postcode alone cannot determine a Behörde, yet PVOG answered it
        # with the BaFin arbitration board in Bonn, address included.
        finder = make_finder(self.unrelated_stub())
        assert finder.find("10115", "Which office is responsible?", topic="allgemein") is None

    def test_query_without_content_words_is_not_searched_at_all(self):
        # Nothing specific was named, so there is nothing to verify a hit
        # against — the lookup must not even ask.
        queries = []
        finder = make_finder(self.unrelated_stub(queries))
        assert finder.find("10115", "Wo ist das Amt?", topic="allgemein") is None
        assert queries == []

    def test_word_buried_inside_a_title_word_is_no_match(self):
        # "Wann kann ich in Rente gehen?" in München: the Rentenversicherung
        # has no address in PVOG, and a local row for "gehen" used to beat
        # it — "Veranstaltungsraum; Anzeige einer vorübergehenden
        # Verwendung", Landeshauptstadt München, Marienplatz 8.
        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[{"ars": MUENCHEN_ARS, "plz": "80331", "name": "München"}])
            if "/v7/servicedescriptions/" in path:
                if "rente" in request.url.params.get("q").lower():
                    content = [{"id": "B1.LB.3", "name": "Regelaltersrente beantragen", "ars": ["000000000000"]}]
                else:
                    content = [{
                        "id": "L3.LB.1",
                        "name": "Veranstaltungsraum; Anzeige einer vorübergehenden Verwendung",
                        "ars": [MUENCHEN_ARS],
                    }]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            if path.endswith("/v2/organisationunits/titles"):
                lb_id = request.url.params.get("lbId")
                return httpx.Response(200, json=[{"id": lb_id + ".OE", "title": "x", "role": {"code": "01"}}])
            if path.endswith("/v5/organisationunits/detail"):
                if request.url.params.get("q") == "L3.LB.1.OE":
                    return httpx.Response(200, json={
                        "title": "Landeshauptstadt München",
                        "location": {"addresses": [{"type": "Hausanschrift", "street": "Marienplatz 8", "zip": "80331", "city": "München"}]},
                        "internetAddresses": [],
                    })
                return httpx.Response(200, json={
                    "title": "Auskunfts- und Beratungsstellenfinder der Deutschen Rentenversicherung",
                    "location": {},
                    "internetAddresses": [{"uri": "https://www.deutsche-rentenversicherung.de"}],
                })
            raise AssertionError(path)

        finder = make_finder(handler)
        result = finder.find("80331", "Wann kann ich in Rente gehen?", topic="rente")
        assert result is not None
        assert result.authority_name == "Auskunfts- und Beratungsstellenfinder der Deutschen Rentenversicherung"

    def test_searches_the_key_word_on_its_own_too(self):
        # PVOG's ranking is thrown off by the words around the service name:
        # "bekomme Personalausweis" returns one unrelated certificate
        # service, "Personalausweis" the actual Bürgeramt service.
        queries = []
        finder = make_finder(self.unrelated_stub(queries))
        finder.find("10115", "Wo bekomme ich einen Personalausweis?", topic="allgemein")
        assert "Personalausweis" in queries


class TestUnusableUnits:
    def units_stub(self, detail):
        def handler(request):
            path = request.url.path
            if path.endswith("/v3/locations/details"):
                return httpx.Response(200, json=[{"ars": BERLIN_CITY_ARS, "plz": "10115"}])
            if "/v7/servicedescriptions/" in path:
                content = [{"id": "L1.LB.2", "name": "Kindergeld Informationen", "ars": [BERLIN_CITY_ARS]}]
                return httpx.Response(200, json={"serviceDescriptions": {"content": content}})
            if path.endswith("/v2/organisationunits/titles"):
                return httpx.Response(200, json=[{"id": "L1.OE.7", "title": "Informationen", "role": {"code": "03"}}])
            if path.endswith("/v5/organisationunits/detail"):
                return httpx.Response(200, json=detail)
            raise AssertionError(path)

        return handler

    def test_unit_without_any_contact_detail_is_skipped(self):
        # A Hamburg entry lists a unit called "Informationen" with no
        # address, phone or website; being local, it used to beat the
        # Familienkasse. A name alone helps nobody.
        finder = make_finder(self.units_stub({
            "title": "Informationen", "location": {}, "internetAddresses": [],
        }))
        assert finder.find("10115", "Kindergeld", topic="kindergeld") is None

    def test_placeholder_address_is_dropped_but_contact_kept(self):
        # Same entry, seen through /v5: street "siehe oben", zip "-----".
        finder = make_finder(self.units_stub({
            "title": "Informationen",
            "location": {
                "addresses": [{"type": "Hausanschrift", "street": "siehe oben", "zip": "-----", "city": "-"}],
                "communications": [{"code": "02", "value": "+49 40 1"}],
            },
            "internetAddresses": [],
        }))
        result = finder.find("10115", "Kindergeld", topic="kindergeld")
        assert result is not None
        assert result.street is None and result.zip is None
        assert result.phone == "+49 40 1"


class TestTopicQueries:
    def test_every_router_topic_has_pvog_queries(self):
        # A router topic without a TOPIC_QUERIES entry falls back to the raw
        # user message, which for contact-style questions ("gib mir die
        # kontakt daten") matches nothing in PVOG. familie-und-kinder was
        # missing and Elterngeld lookups silently failed.
        from behoerde import TOPIC_QUERIES
        from router import TOPIC_KEYWORDS

        assert set(TOPIC_KEYWORDS) <= set(TOPIC_QUERIES)

    def test_grundsicherung_im_alter_replaces_rente_queries(self):
        # "Altersrente beantragen" finds the Rentenversicherung, but
        # Grundsicherung im Alter is the Sozialamt's service.
        # Nothing else is searched either: where PVOG has no local row, the
        # rente queries find a pension office and the bare key word
        # "Grundsicherung" a Bundesagentur service (seen for PLZ 49477).
        for message in ("Grundsicherung im Alter beantragen", "Grundsicherung wegen Erwerbsminderung"):
            queries = BehoerdeFinder()._queries_for(message, "rente")
            assert queries == ["Grundsicherung im Alter und bei Erwerbsminderung"]

    def test_registering_a_home_searches_pvogs_own_word(self):
        # PVOG calls it "Wohnsitz anmelden"; the key word "Wohnung" rejected
        # that row and offered the Steueramt (Zweitwohnungssteuer) in Köln.
        for message in (
            "Wo melde ich meine Wohnung an?",
            "Wo kann ich meine Wohnung anmelden?",
            "Anmeldung der Wohnung in Köln",
            "Wie melde ich mich um?",
            "Ich bin umgezogen, wo muss ich mich ummelden?",
            "Wo muss ich meinen Umzug melden?",
        ):
            assert BehoerdeFinder()._queries_for(message, "allgemein") == ["Wohnsitz anmelden"], message
        # "um … zu" is not ummelden, and a Wohnung alone is not registering one.
        for message in (
            "Wo melde ich mich um Bürgergeld zu bekommen?",
            "Wo beantrage ich Wohngeld für meine Wohnung?",
        ):
            assert "Wohnsitz anmelden" not in BehoerdeFinder()._queries_for(message, "allgemein"), message

    def test_plain_rente_question_keeps_topic_queries_first(self):
        queries = BehoerdeFinder()._queries_for("Wann kann ich in Rente gehen?", "rente")
        # "Altersrente beantragen" ranked the Landwirtschaftliche
        # Alterskasse (SVLFG, Kassel) first for a Berlin PLZ.
        assert queries[0] == "Regelaltersrente beantragen"
        # "gehen" is no service — it must not be searched on its own.
        assert "gehen" not in queries
        # Erwerbsminderungsrente is the Rentenversicherung's, not the Sozialamt's.
        queries = BehoerdeFinder()._queries_for("Erwerbsminderungsrente beantragen", "rente")
        assert queries[0] == "Regelaltersrente beantragen"


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

    def test_district_of_falls_back_to_quoted_name_outside_city_states(self):
        assert _district_of({"ars": "091620000000", "name": "München 'Altstadt-Lehel'"}) == "Altstadt-Lehel"
        assert _district_of({"ars": "091620000000", "name": "München"}) is None

    def test_district_of_maps_hamburg_stadtteil_to_bezirk(self):
        assert _district_of({"ars": "020000000000", "name": "Hamburg 'Hammerbrook'"}) == "Hamburg-Mitte"
        assert _district_of({"ars": "020000000000", "name": "Hamburg 'Ottensen'"}) == "Altona"
        assert _district_of({"ars": "020000000000", "name": "Hamburg 'Kleingartenanlage'"}) is None
        assert _district_of({"ars": "020000000000", "name": "Hamburg, Freie und Hansestadt"}) is None

    def test_hamburg_jobcenter_table_covers_every_stadtteil(self):
        # Spellings must be PVOG's (the Bezirk table's), or a Stadtteil
        # silently falls back to its Bezirk.
        assert set(HAMBURG_JOBCENTER_BY_STADTTEIL) <= set(HAMBURG_STADTTEILE)
        unmapped = set(HAMBURG_STADTTEILE) - set(HAMBURG_JOBCENTER_BY_STADTTEIL)
        assert unmapped == {"Billstedt", "Eimsbüttel", "Heimfeld"}

    def test_strip_stopwords(self):
        assert strip_stopwords("Wo kann ich meine Wohnung anmelden?") == "Wohnung anmelden"

    def test_strip_stopwords_drops_plz_digits(self):
        assert "81667" not in strip_stopwords("Jobcenter? Ich wohne in 81667 München")

    def test_strip_stopwords_never_returns_empty(self):
        assert strip_stopwords("wo kann ich") == "wo kann ich"

    def test_key_terms_picks_the_most_specific_word(self):
        assert key_terms("Wo beantrage ich Wohngeld") == ["Wohngeld"]
        # Generic service vocabulary must not become the key term, or every
        # "… beantragen" row in the register would count as a match.
        assert key_terms("melde Wohnsitz") == ["Wohnsitz"]

    def test_key_terms_empty_when_nothing_specific_was_asked(self):
        assert key_terms("Wo ist das Amt") == []

    def test_is_relevant_matches_compounds_and_folds_umlauts(self):
        assert is_relevant("Bürgergeld / Grundsicherungsgeld; Beantragung", ["buergergeld"])
        assert is_relevant("Wohngeld - Mietzuschuss beantragen", key_terms("Wohngeld"))
        assert not is_relevant("Arbeitslos melden", key_terms("melde Wohnsitz"))
        assert not is_relevant("Kindergeld beantragen", [])

    def test_is_relevant_needs_the_term_at_a_word_edge(self):
        # Compound parts sit at the start or end of a word ("Altersrente",
        # "Rentenbezug"); a hit in the middle is a coincidence.
        assert is_relevant("Altersrente für langjährig Versicherte", ["Rente"])
        assert is_relevant("Rentenbezug der Künstlersozialkasse melden", ["Rente"])
        assert not is_relevant("Eine Kennnummer für Betriebe zur Haltung von Legehennen beantragen", ["gehen"])
        assert not is_relevant("Veranstaltungsraum; Anzeige einer vorübergehenden Verwendung", ["gehen"])

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
