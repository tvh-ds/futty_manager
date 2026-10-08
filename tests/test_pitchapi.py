import json
from pathlib import Path

import httpx
import pytest

from scout.pitchapi import (
    LEAGUES,
    PitchAPI,
    RequestBudgetReached,
    canonical_records,
    collect,
    match_measurements,
    stat_totals,
)
from scout.settings import Settings
from scout.striker_refresh import StrikerRecord, StrikerSourceConfig, refresh


def match():
    return {'id': 'm_000001', 'time_utc': '2025-08-01T12:00:00Z', 'status': 'finished',
            'home_team': {'id': 't_000001'}, 'away_team': {'id': 't_000002'}}


def evidence():
    players = [{'player': {'id': 'p_000001', 'name': 'Test Player'}, 'team_id': 't_000001',
                'stats': [{'stats': {
                    'Minutes': {'key': 'minutes_played', 'stat': {'type': 'integer', 'value': 90}},
                    'Passing': {'key': 'accurate_passes', 'stat': {
                        'type': 'fractionWithPercentage', 'value': 8, 'total': 10}},
                }}]}]
    shot = {'id': 's_000001', 'player': {'id': 'p_000001'}, 'team_id': 't_000001',
            'situation': 'RegularPlay', 'event_type': 'Goal', 'shot_type': 'Header',
            'expected_goals': .2, 'is_on_target': True, 'is_inside_box': True, 'is_blocked': False}
    shots = {'match_id': 'm_000001', 'periods': [{'period': 'FirstHalf', 'shots': [shot]}]}
    return players, shots


def test_counts_and_unknowns():
    players, shots = evidence()
    row = match_measurements(players, None, shots, match())[0]['totals']
    assert row['shots'] == row['non_penalty_goals'] == row['headed_shots'] == 1
    assert row['npxg'] == .2
    assert row['passes_completed'] == 8 and row['passes_attempted'] == 10
    assert 'xa' not in row and 'touches_penalty_area' not in row
    del shots['periods'][0]['shots'][0]['is_blocked']
    assert match_measurements(players, None, shots, match())[0]['totals']['shots_on_target'] is None


def test_zero_shots_require_complete_response():
    players, shots = evidence()
    shots['periods'][0]['shots'] = []
    assert match_measurements(players, None, shots, match())[0]['totals']['npxg'] == 0
    with pytest.raises(ValueError):
        match_measurements(players, None, {}, match())


def test_invalid_measurement_and_scope():
    players, shots = evidence()
    players[0]['stats'][0]['stats']['Passing']['stat']['value'] = 11
    with pytest.raises(ValueError):
        stat_totals(players[0])
    players, shots = evidence()
    shots['periods'][0]['shots'][0]['team_id'] = 't_999999'
    with pytest.raises(ValueError):
        match_measurements(players, None, shots, match())


def test_cache_budget_and_no_secret_storage(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers['X-API-KEY'] == 'private-test-key'
        return httpx.Response(200, json={'data': {'leagues': []}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = PitchAPI('private-test-key', tmp_path, max_requests=1, client=client)
        api.get('/leagues')
        api.get('/leagues')
        with pytest.raises(RequestBudgetReached):
            api.get('/matches/m_000001/players')
        assert len(calls) == 1
    file = next(tmp_path.glob('*.json'))
    assert 'private-test-key' not in file.read_text()
    document = json.loads(file.read_text())
    document['document']['data'] = {'leagues': [1]}
    file.write_text(json.dumps(document))
    with pytest.raises(ValueError, match='checksum'):
        api.get('/leagues')


def test_retries_and_optional_analytics(tmp_path):
    statuses = [429, 503, 404]
    delays = []

    def handler(request):
        return httpx.Response(statuses.pop(0), headers={'Retry-After': '100'},
                              json={'error': {'code': 'ANALYTICS_UNAVAILABLE'}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = PitchAPI('test', tmp_path, client=client, sleep=delays.append)
        assert api.get('/matches/m_000001/advanced/players', optional=True)['unavailable']
    assert delays == [5, 5]


@pytest.mark.parametrize('bad_actor', [False, True])
def test_five_league_sample_resume_cannot_publish(tmp_path, bad_actor):
    catalogue = [{'id': f'l_{i:06}', 'country_code': code, 'name': name, 'seasons': ['2025/2026']}
                 for i, (code, name, _) in enumerate(LEAGUES.values(), 1)]
    players, shots = evidence()
    if bad_actor:
        shots['periods'][0]['shots'][0]['player']['id'] = 'p_999999'

    def handler(request):
        path = request.url.path
        if path.endswith('/leagues'):
            data = {'leagues': catalogue}
        elif '/leagues/' in path:
            lid = path.split('/')[-2]
            data = {'league': {'id': lid, 'season': '2025/2026'}, 'matches': [match()]}
        elif path.endswith('/advanced/players'):
            return httpx.Response(404, json={'error': {'code': 'ANALYTICS_UNAVAILABLE'}})
        elif path.endswith('/shots'):
            data = shots
        else:
            data = players
        return httpx.Response(200, json={'data': data})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows, report = collect(tmp_path, 'test', matches_per_league=1, client=client)
        assert len(rows) == (0 if bad_actor else 5) and len(report['leagues']) == 5
        assert bool(report.get('failure')) == bad_actor
        assert len(report['quarantine']) == (5 if bad_actor else 0)
        assert not report['complete'] and not report['activated']
        assert all(row['totals']['xa'] is None for row in rows)
        assert canonical_records(rows, report, {'identities': {}}) == []
        _, resumed = collect(tmp_path, 'test', matches_per_league=1, client=client)
        assert resumed['requests'] == 0


def test_credential_repr(monkeypatch):
    monkeypatch.setenv('SCOUT_PITCHAPI_KEY', 'private-test-key')
    settings = Settings(_env_file=None)
    assert settings.pitchapi_key.get_secret_value() == 'private-test-key'
    assert 'private-test-key' not in repr(settings)


def test_live_shapes_duplicates_unused_bench_and_minutes():
    players, shots = evidence()
    extra = {'key': 'defensive_actions', 'stat': {'type': 'integer', 'value': 1}}
    players[0]['stats'].append({'stats': {'Repeated display stat': extra, 'Shotmap': {
        'key': '', 'stat': {'type': 'boolean', 'value': 0}}}})
    players[0]['stats'].append({'stats': {'Repeated display stat': extra}})
    players[0]['stats'][0]['stats']['SOT'] = {
        'key': 'ShotsOnTarget', 'stat': {'type': 'integer', 'value': 1}}
    players.append({'player': {'id': 'p_000002', 'name': 'Unused substitute'},
                    'team_id': 't_000001', 'stats': []})
    advanced = {'match_id': 'm_000001', 'players': [{
        'player': {'id': 'p_000001'}, 'team_id': 't_000001', 'minutes_played': 96,
        'passing': None, 'carrying': None, 'creation': None, 'defending': None}]}
    del shots['periods'][0]['shots'][0]['is_blocked']
    rows = match_measurements(players, advanced, shots, match())
    assert len(rows) == 1 and rows[0]['totals']['minutes'] == 90
    assert rows[0]['totals']['shots_on_target'] == 1


def test_reviewed_mapping_and_versioned_canonical_record():
    config = StrikerSourceConfig.model_validate_json(
        Path('config/striker-source.pitchapi.json').read_text()).model_dump(mode='json')
    row = {'provider_player_id': 'p_000001', 'name': 'Test', 'provider_team_ids': ['t_000001'],
           'last_provider_team_id': 't_000001', 'competition': 'England', 'season': '2025/26',
           'totals': {'minutes': 900.0, 'npxg': 1.2}, 'retrieved_at': '2026-10-01T00:00:00Z',
           'source_urls': ['https://api.pitchapi.dev/v1/matches/m_000001/players',
                           'https://api.pitchapi.dev/v1/matches/m_000001/shots']}
    accepted = {'complete': True, 'feature_coverage': {'all_features_accepted': True}}
    assert canonical_records([row], accepted, config) == []
    config['identities'] = {'p_000001': {'player_id': 'reviewed-player', 'reviewed': True,
                                      'roles': ['ST'], 'team_ids': ['t_000001']}}
    record = StrikerRecord.model_validate(canonical_records([row], accepted, config)[0])
    assert record.measurement_version == 'pitchapi-measurements-v1'
    assert record.totals['npxg'] == 1.2 and record.source_documents == row['source_urls']
    config['identities']['p_000001']['team_ids'] = []
    assert canonical_records([row], accepted, config) == []


def test_pipeline_incomplete_collection_preserves_previous(tmp_path, monkeypatch):
    from scout import pitchapi
    monkeypatch.setenv('SCOUT_PITCHAPI_KEY', 'test')
    monkeypatch.setattr(pitchapi, 'collect', lambda *args, **kwargs: ([], {
        'complete': False, 'failure': 'RequestBudgetReached', 'limitations': ['Incomplete sample']}))
    root = tmp_path / 'strikers'
    root.mkdir()
    active = root / 'active.json'
    active.write_text('{"id":"previous"}')
    report = refresh(root, Path('config/striker-source.pitchapi.json'))
    assert report['failure'] == 'RequestBudgetReached' and not report['activated']
    assert active.read_text() == '{"id":"previous"}'
