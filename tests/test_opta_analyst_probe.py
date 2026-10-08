import copy
import json

import httpx
import pytest

from scout.opta_analyst_probe import PageMetadata, fetch, normalize, probe


def payload():
    player = {'player_uuid': 'p' * 25, 'team_uuid': 't' * 25, 'player': 'Test player', 'mins_played': 900,
        'shots': 10, 'shots_on_target': 5, 'np_goals': 3, 'np_xg': 2.5, 'np_shots': 8,
        'xa': 1.2, 'assists': 2, 'passes': 100, 'successful_passes': 80, 'through_balls': 2,
        'ground_duels': 10, 'ground_duels_won': 6, 'aerial_duels': 5, 'aerial_duels_won': 2,
        'interceptions': 3, 'recoveries': 4, 'blocks': 1, 'offsides': 0, 'fouls_commited': 9}
    return {'attack': {'overall': [copy.deepcopy(player)], 'nonPenalty': [copy.deepcopy(player)]},
        'possession': {'chanceCreation': [copy.deepcopy(player)], 'passing': [copy.deepcopy(player)]},
        'defending': {'overall': [copy.deepcopy(player)], 'discipline': [copy.deepcopy(player)]},
        'carries': {'overall': [{**player, 'progressive_distance': -10}]}}


def test_counts_join_exact_identity_and_do_not_invent_features():
    rows, q = normalize(payload(), 'England', '2025/2026', 'fixture', 'fixture')
    assert not q
    row = rows[0]
    assert row['features']['xa90'] == pytest.approx(.12)
    assert row['totals']['duels_won'] == 8
    assert row['features']['duel_pct'] == pytest.approx(100 * 8 / 15)
    assert row['features']['aerial_pct'] == 40
    assert row['features']['fouls_won90'] is None  # Committed != won.
    assert row['features']['carry_distance90'] is None  # Signed distance != requested feature.
    assert 'third_tackles90' not in row['features']
    assert row['features']['offsides90'] == 0
    assert not row['identity_reviewed']


def test_separate_goalkeeper_inventory_is_imported_without_invented_shots():
    data = payload()
    data['goalkeeping'] = {'overall': [{'player_uuid': 'g' * 25, 'team_uuid': 't' * 25,
        'player': 'Test keeper', 'mins_played': 1800, 'saves_made': 50, 'goals_conceded': 20,
        'xgot_conceded': 24.5, 'squad_position_detailed': 'Goalkeeper'}]}
    rows, quarantine = normalize(data, 'England', '2025/2026', 'fixture', 'fixture')
    assert not quarantine and len(rows) == 2
    keeper = next(r for r in rows if r['name'] == 'Test keeper')
    assert keeper['totals']['saves_made'] == 50
    assert keeper['features']['shots90'] is None
    assert keeper['source_position'] == 'Goalkeeper'


def test_unused_numeric_identity_zero_minutes_and_zero_attempts():
    data = payload()
    for reports in data.values():
        for entries in reports.values():
            entries[0].update(player_uuid=1234, mins_played=0, shots=0, shots_on_target=0, np_shots=0)
    rows, q = normalize(data, 'England', '2025/2026', 'fixture', 'fixture')
    assert not q and rows[0]['identity_namespace'] == 'opta-numeric'
    assert rows[0]['features']['xa90'] is None
    assert rows[0]['features']['sot_pct'] is None
    assert rows[0]['features']['goals_per_shot'] is None


@pytest.mark.parametrize('change', ['exposure', 'negative', 'boolean', 'fraction', 'other_team'])
def test_inconsistent_or_missing_report_is_not_merged(change):
    data = payload()
    entry = data['possession']['passing'][0]
    if change == 'exposure':
        entry['mins_played'] = 800
    elif change == 'negative':
        entry['passes'] = -1
    elif change == 'boolean':
        entry['passes'] = True
    elif change == 'fraction':
        entry['successful_passes'] = 101
    else:
        entry['team_uuid'] = 'x' * 25
    rows, q = normalize(data, 'England', '2025/2026', 'fixture', 'fixture')
    if change == 'other_team':
        assert not q and rows[0]['features']['pass_pct'] is None
    else:
        assert not rows and q


def test_duplicate_report_rejects_source():
    data = payload()
    data['attack']['overall'] *= 2
    with pytest.raises(ValueError, match='Duplicate'):
        normalize(data, 'England', '2025/2026', 'fixture', 'fixture')


def test_fixed_hosts_bounded_responses_and_no_activation(tmp_path):
    calls = []
    def respond(request):
        calls.append(request)
        assert request.url.host == 'dataviz.theanalyst.com'
        assert 'authorization' not in request.headers
        return httpx.Response(200, json=payload())
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = probe(tmp_path / 'opta', 2025, client)
        with pytest.raises(ValueError):
            fetch(client, 'https://evil.example/player-stats.json')
        with pytest.raises(FileExistsError):
            probe(tmp_path / 'opta', 2025, client)
    assert len(calls) == 5 and result['requested_window_available']
    assert not result['activated'] and not result['coverage']['all_players']['all_features_accepted']
    assert json.loads((tmp_path / 'opta/coverage.json').read_text())['consent']


def test_page_metadata_requires_verified_season_and_safe_identifier():
    parser = PageMetadata()
    parser.feed('<div class="hub-navigation-container" data-attributes=\'{"nav_dropdown":{"selected":"2026/2027"}}\'></div>'
        '<script class="attributes">{"feed_resource":"soccerdata","tmcl":"aaaaaaaaaaaaaaaaaaaaaaaaa"}</script>')
    assert parser.validated() == ('a' * 25, '2026/2027')
    parser.tmcl = '../private'
    with pytest.raises(ValueError):
        parser.validated()
