import json

import httpx
import pytest

from scout.source_audit import Inventory, classify, combinations, family, normalized_inventory, ratio_status
from scout.source_audit_fetch import MAX_BYTES, fetch
from scout.source_site_probe import inspect


def test_signed_metrics_zero_and_missing_are_distinct():
    assert classify(-2.5) == "numeric"
    assert classify(0) == "numeric"
    assert classify(None) == "missing"
    assert classify(float("nan")) == "invalid"
    assert classify(False) == "categorical"
    assert ratio_status({"n": 0, "d": 0}, "n", "d") == "na"
    assert ratio_status({"n": 1, "d": 0}, "n", "d") == "invalid"
    assert ratio_status({"n": None, "d": 0}, "n", "d") is None


def test_duplicates_transfers_partial_appearances_and_conflicts():
    inv = Inventory("test")
    p, transferred, other = ("England", "p1"), ("Spain", "p1"), ("England", "p2")
    inv.players = {p, transferred, other}
    inv.expected.update({p: 2, transferred: 1, other: 1})
    inv.add("x", p, "m1", 0, group="attack")
    inv.add("x", p, "m1", 0, group="attack")
    inv.add("x", transferred, "m3", 2, group="attack")
    f = inv.fields["x"]
    counts = inv.counts(f, inv.players)
    assert counts["players"] == 2
    assert counts["numeric"] == 1
    assert counts["complete_supported"] == 0  # transfer does not hide incomplete England evidence
    inv.add("x", p, "m2", -1, group="attack")
    assert inv.counts(f, inv.players)["complete_supported"] == 1
    inv.add("x", p, "m1", 2, group="attack")
    assert inv.counts(f, inv.players)["invalid"] == 1
    assert inv.counts(f, inv.players)["complete_supported"] == 0


def test_na_is_supported_but_not_numeric():
    inv = Inventory("test")
    p = ("England", "p1")
    inv.players.add(p)
    inv.expected[p] = 1
    inv.add("ratio", p, "season", None, group="attack", status="na")
    result = inv.counts(inv.fields["ratio"], inv.players)
    assert result["complete_supported"] == 1
    assert result["complete_numeric"] == 0
    assert result["na"] == 1


def test_goalkeeper_population_is_not_silently_substituted():
    inv = Inventory("test")
    keeper, striker = ("England", "gk"), ("England", "st")
    inv.players = {keeper, striker}
    inv.keepers = {keeper}
    inv.expected.update({keeper: 1, striker: 1})
    inv.add("saves", keeper, "season", 0, group="goalkeeping")
    f = inv.report()["fields"]["saves"]
    assert f["all"]["supported_pct"] == 50
    assert f["applicable"]["supported_pct"] == 100


def test_wrong_season_rejected(tmp_path):
    (tmp_path / "measurements.json").write_text(json.dumps([
        {"competition": "England", "season": 2026, "totals": {"minutes": 90}, "provider_player_id": "p"}
    ]), encoding="utf-8")
    with pytest.raises(ValueError, match="Non-target"):
        normalized_inventory("pitchapi", tmp_path)


def test_combination_cannot_merge_unmatched_identities_or_source_definitions():
    inventories = {provider: Inventory(provider) for provider in ("opta", "pitchapi", "understat")}
    mapping = {}
    for league in ("England", "Spain", "Germany", "Italy", "France"):
        for provider, inv in inventories.items():
            person = (league, provider + league)
            inv.players.add(person)
            inv.expected[person] = 1
            inv.add("goals", person, "s", 1, group="attack")
            if provider == "opta":
                mapping[(provider, *person)] = "canonical-" + league
    first = combinations(inventories, mapping)
    pitch = next(r for r in first["ranked"] if r["sources"] == ["pitchapi"])
    assert pitch["reliable_general_families"] == 0
    for league in ("England", "Spain", "Germany", "Italy", "France"):
        mapping[("pitchapi", league, "pitchapi" + league)] = "canonical-" + league
    second = combinations(inventories, mapping)
    pitch = next(r for r in second["ranked"] if r["sources"] == ["pitchapi"])
    assert pitch["reliable_general_families"] == 1
    assert family("pitchapi", "stats.matchstats.headers.tackles.value") == "tackles"
    assert family("opta", "attack.overall.xg_per_shot") == "xg"


def test_html_preserves_player_ids_and_discovered_pagination():
    doc = inspect('<table><tr><th>Player</th><th>Goals</th></tr><tr><td><a href="/players?player_id=17">Name</a></td>'
        '<td>0</td></tr></table><select><option value="777">La Liga 25/26</option></select>'
        '<a href="/statistics?page=2">Next</a>')
    assert doc["tables"][0][1] == ["Name", "0"]
    assert doc["tables_links"][0][1][0]["href"].endswith("17")
    assert doc["options"] == [{"value": "777", "text": "La Liga 25/26"}]
    assert doc["links"][-1]["href"].endswith("page=2")


def test_nested_tables_and_image_labels_do_not_erase_parent_inventory():
    doc = inspect('<table><tr><th>Players</th><th><img alt="Yellow Card"></th></tr>'
        '<tr><td>Name<table><tr><td>nested</td></tr></table></td><td>0</td></tr></table>')
    assert ["Players", "Yellow Card"] in doc["tables"][-1]
    assert ["Name", "0"] in doc["tables"][-1]


def test_partial_missingness_is_reported_without_erasing_numeric_evidence():
    inv = Inventory('test')
    player = ('England', 'p')
    inv.players.add(player)
    inv.expected[player] = 2
    inv.add('goals', player, 'first', 0, group='attack')
    counts = inv.counts(inv.fields['goals'], inv.players)
    assert counts['numeric'] == counts['zero'] == counts['missing'] == counts['partial'] == 1
    assert counts['complete_supported'] == 0


def test_html_missing_markers_are_not_zero_attempt_na():
    from scout.source_table_audit import numeric
    assert numeric('-') == ('missing', None)
    assert numeric('N/A') == ('missing', None)  # no numerator/denominator evidence
    assert numeric('-1.4') == ('numeric', -1.4)
    assert numeric('0') == ('numeric', 0)


def test_pooled_coverage_cannot_hide_a_weak_league():
    inv = Inventory('opta')
    for league in ('England', 'Spain', 'Germany', 'Italy', 'France'):
        for index in range(10):
            player = (league, f'{league}-{index}')
            inv.players.add(player)
            inv.expected[player] = 1
            if league != 'France' or index < 8:
                inv.add('goals', player, 'season', 0, group='attack')
    result = combinations({'opta': inv}, {})['ranked'][0]
    assert result['families']['goals'][0]['pooled'] == 96
    assert result['families']['goals'][0]['coverage']['France'] == 80
    assert result['reliable_general_families'] == 0


def test_report_checksum_covers_actual_file_bytes_and_preserves_immutable_snapshots(tmp_path):
    import hashlib

    from scout.source_audit import persist_report
    result = {'field': 'signed metric', 'count': 3}
    digest = persist_report(tmp_path, result)
    path = tmp_path / f'audit-{digest}.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert persist_report(tmp_path, result) == digest
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='corrupt'):
        persist_report(tmp_path, result)


def test_existing_empty_numeric_cell_is_zero_but_absent_row_stays_absent():
    inv = Inventory('test')
    first, second, absent = ('England', 'a'), ('England', 'b'), ('England', 'c')
    inv.players = {first, second, absent}
    inv.expected.update({first: 1, second: 1, absent: 1})
    inv.add('shots', first, 'season', 2, group='attack')
    inv.add('shots', second, 'season', None, group='attack')
    inv.apply_empty_cell_policy()
    counts = inv.counts(inv.fields['shots'], inv.players)
    assert counts['numeric'] == 2
    assert counts['zero'] == 1
    assert counts['missing'] == 1
    assert absent not in inv.fields['shots'].observations
    from scout.source_table_audit import numeric
    assert numeric('', empty_zero=True) == ('numeric', 0)
    assert numeric('-', empty_zero=True) == ('numeric', 0)
    assert numeric('N/A', empty_zero=True) == ('missing', None)


def test_fetch_allowlist_redirect_and_bound(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"{}"))) as client:
        with pytest.raises(ValueError):
            fetch("http://localhost/private", tmp_path, client)
    def respond(request):
        if request.url.path == "/Statistics":
            return httpx.Response(301, headers={"location": "https://www.whoscored.com/statistics"})
        return httpx.Response(200, content=b"<html>public</html>")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = fetch("https://www.whoscored.com/Statistics", tmp_path, client)
        assert result["redirect_result"]["status"] == 200
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * (MAX_BYTES + 1)))) as client:
        assert fetch("https://www.whoscored.com/Statistics", tmp_path / "large", client)["error"] == "ValueError"


def test_browser_counts_require_all_players_and_preserve_column_meanings(tmp_path):
    import json

    from scout.source_counts import browser_inventory
    folder = tmp_path / 'browser-whoscored-20261007'
    folder.mkdir()
    panels = []
    for category, total, all_players in [('shots', 551, True), ('saves', 300, False)]:
        panels.append({'id': 'stage-top-player-stats-detailed', 'all_players_selected': all_players,
                       'text': f'Page 1/56 | Showing 1 - 10 of {total}',
                       'selectors': [{'id': 'category', 'value': category}],
                       'tables': [{'headers': ['Player', 'Total'], 'rows': [{'player': '/players/123/show/test'}]}]})
    (folder / 'england-detail.json').write_text(json.dumps({'season': '2025/2026', 'panels': panels,
                                                          'url': 'https://www.whoscored.com/statistics',
                                                          'retrieved_at': '2026-10-07'}), encoding='utf-8')
    result = browser_inventory(tmp_path)
    assert result['displayed_league_rows'] == {'England': 551}
    assert result['sample_unique_ids'] == 1
    assert result['columns'] == ['Player', 'saves.Total', 'shots.Total']
