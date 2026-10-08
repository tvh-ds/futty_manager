import json

import httpx
import pytest

from scout.understat_probe import LEAGUES, normalize, normalize_player_shots, probe, probe_player


def payload():
    return {'players': [{'id': '100', 'player_name': 'Source fixture', 'team_title': 'Fixture club',
        'position': 'F', 'time': '180', 'goals': '2', 'npg': '1', 'npxG': '1.5',
        'shots': '8', 'assists': '1', 'xA': '0.6', 'key_passes': '4'}],
        'dates': [{'isResult': True, 'datetime': '2026-09-20 15:00:00'},
                  {'isResult': False, 'datetime': '2027-05-20 15:00:00'}]}


def test_real_field_definitions_missingness_and_source_time():
    rows, quarantined, coverage = normalize(payload(), 'England', 2026,
        'https://understat.com/getLeagueData/EPL/2026', '2026-10-06T00:00:00Z')
    assert not quarantined
    assert rows[0]['features']['npg90'] == .5
    assert rows[0]['features']['npxg90'] == .75
    assert rows[0]['features']['finishing_delta90'] == -.25
    assert rows[0]['features']['xa90'] == .3
    assert rows[0]['features']['goals_per_shot'] is None  # No NP shot denominator.
    assert rows[0]['features']['sot_pct'] is None
    assert rows[0]['identity_reviewed'] is False and rows[0]['publication_approved'] is False
    assert coverage['completed_fixtures'] == 1
    assert coverage['latest_completed_fixture_source_time'] == '2026-09-20 15:00:00'
    assert len([n for n in coverage['available_feature_counts'].values() if n]) == 7


@pytest.mark.parametrize('value', ['nan', '-1', '1e309', True, [], 'SOURCE-SECRET'])
def test_invalid_numbers_quarantined_without_input_echo(value):
    document = payload()
    document['players'][0]['shots'] = value
    rows, quarantine, coverage = normalize(document, 'England', 2026, 'https://understat.com/', '2026-10-06T00:00:00Z')
    assert not rows and quarantine and coverage['validated_players'] == 0
    assert 'SOURCE-SECRET' not in json.dumps(quarantine)


def test_zero_minutes_does_not_create_zero_per90_or_eligibility():
    document = payload()
    document['players'][0]['time'] = '0'
    rows, _, coverage = normalize(document, 'England', 2026, 'https://understat.com/', '2026-10-06T00:00:00Z')
    assert all(v is None for v in rows[0]['features'].values())
    assert coverage['players_with_900_minutes'] == 0


def test_probe_fixed_hosts_private_snapshots_failures_and_no_activation(tmp_path):
    calls = []
    def respond(request):
        calls.append(request)
        assert request.url.host == 'understat.com'
        assert request.headers['X-Requested-With'] == 'XMLHttpRequest'
        return httpx.Response(404 if 'Ligue_1' in request.url.path else 200, json=payload())
    output = tmp_path / 'source-probe'
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report = probe(output, 2026, client)
        with pytest.raises(FileExistsError):
            probe(output, 2026, client)
    assert len(calls) == len(LEAGUES)
    assert report['leagues']['France']['failure'] == 'HTTPStatusError'
    assert report['leagues']['England']['validated_players'] == 1
    assert (output / 'EPL/bronze.json').exists() and (output / 'coverage.json').exists()
    assert not report['activated'] and not report['publication_approved']
    assert not (output / 'active.json').exists()


def shot_payload():
    league = payload()
    league['dates'][0]['id'] = '10'
    league['players'][0].update(shots='3', goals='2', npg='1', npxG='0.5')
    player = {'player': {'id': '100'}, 'shots': [
        {'id': '1', 'match_id': '10', 'season': '2026', 'player_id': '100',
         'situation': 'OpenPlay', 'shotType': 'Head', 'result': 'Goal', 'xG': '0.3'},
        {'id': '2', 'match_id': '10', 'season': '2026', 'player_id': '100',
         'situation': 'FromCorner', 'shotType': 'LeftFoot', 'result': 'SavedShot', 'xG': '0.2'},
        {'id': '3', 'match_id': '10', 'season': '2026', 'player_id': '100',
         'situation': 'Penalty', 'shotType': 'RightFoot', 'result': 'Goal', 'xG': '0.76'},
        {'id': '4', 'match_id': 'OTHER_LEAGUE', 'season': '2026', 'player_id': '100'},
        {'id': '5', 'match_id': '10', 'season': '2025', 'player_id': '100'}]}
    return league, player


def test_shots_exact_scope_penalty_denominator_and_preserved_unknowns():
    league, player = shot_payload()
    row = normalize_player_shots(player, league, 'England', 2026, '100', '2026-10-06T00:00:00Z')
    assert row['shot_count'] == 3
    assert row['features']['goals_per_shot'] == .5
    assert row['features']['npxg_per_shot'] == .25
    assert row['features']['open_xg90'] == .15
    assert row['features']['headed_shots90'] == .5
    assert row['features']['sot90'] is None and row['features']['box_shots90'] is None
    assert sum(v is not None for v in row['features'].values()) == 11
    assert not row['identity_reviewed'] and not row['publication_approved']


@pytest.mark.parametrize('mutation', ['duplicate', 'identity', 'count', 'npxg', 'enum', 'xg'])
def test_inconsistent_shot_evidence_rejected(mutation):
    league, player = shot_payload()
    if mutation == 'duplicate':
        player['shots'].append(player['shots'][0])
    elif mutation == 'identity':
        player['shots'][0]['player_id'] = 'OTHER'
    elif mutation == 'count':
        league['players'][0]['shots'] = '4'
    elif mutation == 'npxg':
        league['players'][0]['npxG'] = '0.9'
    elif mutation == 'enum':
        player['shots'][0]['situation'] = 'NewUnreviewedCategory'
    else:
        player['shots'][0]['xG'] = '1.1'
    with pytest.raises(ValueError):
        normalize_player_shots(player, league, 'England', 2026, '100', '2026-10-06T00:00:00Z')


def test_single_player_probe_snapshot_checksums_and_no_publication(tmp_path):
    league, player = shot_payload()
    snapshot = tmp_path / 'league.json'
    snapshot.write_text(json.dumps(league))
    def respond(request):
        assert str(request.url) == 'https://understat.com/getPlayerData/100'
        return httpx.Response(200, json=player)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        row = probe_player(tmp_path / 'player', snapshot, '100', season=2026, client=client)
        with pytest.raises(ValueError):
            probe_player(tmp_path / 'absent', snapshot, '999', season=2026, client=client)
    assert len(row['snapshot_sha256']) == 64 and len(row['league_snapshot_sha256']) == 64
    assert (tmp_path / 'player/measurements.json').exists()
    assert not (tmp_path / 'player/active.json').exists()


def test_previous_season_fixture_cannot_be_relabelled():
    league, player = shot_payload()
    league['dates'][0]['datetime'] = '2025-09-20 15:00:00'
    with pytest.raises(ValueError, match='outside requested performance season'):
        normalize_player_shots(player, league, 'England', 2026, '100', '2026-10-06T00:00:00Z')
