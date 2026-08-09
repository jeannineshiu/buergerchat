from bs4 import BeautifulSoup

from gesetze_crawler import clean_cell, extract_sections, render_table, title_unit


def make_table(rows: list[list[str]]) -> BeautifulSoup:
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return BeautifulSoup(f"<table>{body}</table>", "html.parser").table


class TestCleanCell:
    def test_rejoins_headers_broken_across_lines(self):
        # The site typesets narrow columns as "Regel- bedarfsstufe 1"; leaving
        # that split makes the column unreachable by any "Regelbedarfsstufe" query.
        assert clean_cell("Regel- bedarfsstufe 1") == "Regelbedarfsstufe 1"

    def test_keeps_ergaenzungsstrich(self):
        # "Vater- und Mutterschaft" is a real construct — the hyphen stays.
        assert clean_cell("Vater- und Mutterschaft") == "Vater- und Mutterschaft"
        assert clean_cell("Ehe- oder Lebenspartner") == "Ehe- oder Lebenspartner"

    def test_leaves_ordinary_compounds_alone(self):
        assert clean_cell("Steuer-ID") == "Steuer-ID"

    def test_collapses_whitespace(self):
        assert clean_cell("gültig   ab\n 1. Januar") == "gültig ab 1. Januar"


class TestRenderTable:
    def test_every_figure_keeps_its_column_and_period(self):
        table = make_table([
            ["gültig ab", "Regel- bedarfsstufe 1", "Regel- bedarfsstufe 2"],
            ["1. Januar 2026", "563", "506"],
        ])
        assert render_table(table, "Euro") == [
            "Regelbedarfsstufe 1, gültig ab 1. Januar 2026: 563 Euro",
            "Regelbedarfsstufe 2, gültig ab 1. Januar 2026: 506 Euro",
        ]

    def test_skips_empty_cell_markers(self):
        table = make_table([
            ["gültig im Kalenderjahr", "erstes Halbjahr", "zweites Halbjahr"],
            ["2019", "100 Euro", "–"],
        ])
        assert render_table(table) == [
            "erstes Halbjahr, gültig im Kalenderjahr 2019: 100 Euro",
        ]

    def test_does_not_repeat_a_unit_the_cell_already_carries(self):
        table = make_table([["Jahr", "Betrag"], ["2019", "100 Euro"]])
        assert render_table(table, "Euro") == ["Betrag, Jahr 2019: 100 Euro"]

    def test_header_only_table_yields_nothing(self):
        assert render_table(make_table([["Jahr", "Betrag"]])) == []


class TestTitleUnit:
    def test_reads_the_unit_from_the_anlage_title(self):
        assert title_unit("Regelbedarfsstufen nach § 28 in Euro") == "Euro"

    def test_no_unit_when_the_title_does_not_name_one(self):
        assert title_unit("Definition der Qualifikationsgruppen") == ""


LAW_HTML = """
<html><body>
<span class="jnlangue">Zwölftes Buch Sozialgesetzbuch</span>
<div class="jnnorm" id="inhalt">
  <span class="jnenbez">Inhaltsübersicht</span>
  <div class="jnhtml">Erstes Kapitel …</div>
</div>
<div class="jnnorm" id="p28">
  <span class="jnenbez">§ 28</span><span class="jnentitel">Ermittlung der Regelbedarfe</span>
  <div class="jnhtml">Die Höhe der Regelbedarfe wird neu ermittelt.</div>
</div>
<div class="jnnorm" id="anlage28">
  <span class="jnenbez">Anlage</span>
  <span class="jnentitel">(zu § 28)Regelbedarfsstufen nach § 28 in Euro</span>
  <div class="jnhtml">
    <table>
      <tr><td>gültig ab</td><td>Regel- bedarfsstufe 1</td></tr>
      <tr><td>1. Januar 2026</td><td>563</td></tr>
    </table>
    Regelbedarfsstufe 1: Für jede erwachsene Person.
  </div>
</div>
</body></html>
"""


class TestExtractSections:
    def sections(self):
        return extract_sections(LAW_HTML, "SGB XII", "https://example.de/sgb_12/x.html", "rente")

    def test_keeps_paragraphs_and_anlagen_but_not_the_table_of_contents(self):
        titles = [record["title"] for record in self.sections()]
        assert titles == [
            "SGB XII § 28 Ermittlung der Regelbedarfe",
            "SGB XII Anlage (zu § 28) Regelbedarfsstufen nach § 28 in Euro",
        ]

    def test_anlage_table_is_rendered_row_wise(self):
        anlage = self.sections()[1]
        # The amount has to stay attached to its column and its date — a plain
        # get_text() would leave "gültig ab Regel- bedarfsstufe 1 1. Januar 2026 563".
        assert "Regelbedarfsstufe 1, gültig ab 1. Januar 2026: 563 Euro" in anlage["content"]

    def test_anlage_keeps_the_prose_around_the_table(self):
        assert "Für jede erwachsene Person" in self.sections()[1]["content"]

    def test_paragraph_content_is_untouched(self):
        assert self.sections()[0]["content"] == "Die Höhe der Regelbedarfe wird neu ermittelt."

    def test_records_carry_anchor_topic_and_law(self):
        anlage = self.sections()[1]
        assert anlage["url"] == "https://example.de/sgb_12/x.html#anlage28"
        assert anlage["topic"] == "rente"
        assert anlage["law"] == "Zwölftes Buch Sozialgesetzbuch"
