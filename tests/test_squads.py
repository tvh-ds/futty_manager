from datetime import date

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from scout.api import create_app
from scout.contracts import Role
from scout.formations import formations
from scout.settings import Settings
from scout.squad_contracts import ChemistryComponent, LineupState
from scout.squads import (
    aggregate_chemistry,
    change_formation,
    chemistry_band,
    chemistry_measures,
    concurrent_minutes,
    demo_chemistry,
    evaluate_lineup,
    peer_population,
    percentile,
    score_player,
    shared_tenure_days,
    squad_snapshot,
)


def test_percentiles_ties_direction_and_populations():
    assert percentile(2, np.array([1, 2, 2, 3])) == 50
    assert percentile(7, np.array([7, 7])) == 50
    assert percentile(1, np.array([1, 2, 3, 4]), True) == 87.5
    assert percentile(None, np.array([1])) is None
    assert percentile(2, np.array([1, 2, 3, np.nan, np.inf])) == 50
    assert percentile(2, np.array([np.nan])) is None
    assert percentile(np.nan, np.array([1])) is None
    for keeper, count in [(False, 2100), (True, 500)]:
        leagues, peers = peer_population(keeper)
        assert all(n == count // 5 for n in np.unique(leagues, return_counts=True)[1])
        assert all(len(p) == count for p in peers.values())
    assert set(peer_population(True)[1]) != set(peer_population(False)[1])


def test_raw_magnitude_ignores_percentile_and_preserves_missingness():
    player = squad_snapshot().players[0].model_copy(deep=True)
    original = score_player(player, Role.GK, 1.5)[0]
    for skill in player.skills:
        skill.percentile = 1
    assert score_player(player, Role.GK, 1.5)[0] == original
    for skill in player.skills[:len(player.skills) // 2 + 1]:
        skill.raw_value = None
    assert score_player(player, Role.GK, 1.5)[0] is None


@pytest.mark.parametrize('value,band', [(3.33, 'red'), (3.334, 'red'), (3.335, 'yellow'),
                                     (6.66, 'yellow'), (6.665, 'green'), (10, 'green'), (None, 'unknown')])
def test_chemistry_rounding(value, band):
    assert chemistry_band(value) == band


def test_familiarity_formulas_missingness_and_interval_overlap():
    assert chemistry_measures(['A', 'B'], ['B'], 182.5, ['X'], ['X'], False, 5, 900) == [10, 5, 10, 5, 5]
    assert chemistry_measures(['A'], ['B'], 1000, ['X'], ['Y'], False, 14, 4000) == [0, 10, None, 0, 10]
    assert chemistry_measures(nationalities_a=['A'], nationalities_b=['B'], nationalities_complete=False)[0] is None
    assert chemistry_measures() == [None] * 5
    d = date.fromisoformat
    a = [('x', d('2024-01-01'), d('2025-01-01'))] * 2
    b = [('x', d('2024-07-01'), d('2025-02-01')),
         ('y', d('2024-01-01'), d('2025-01-01'))]
    assert shared_tenure_days(a, b) == 184
    assert concurrent_minutes([(0, 60), (0, 60)], [(45, 90)]) == 15
    assert concurrent_minutes([(0, 30)], [(40, 90)]) == 0
    with pytest.raises(ValueError):
        concurrent_minutes([(0, 900)], [])
    components = [ChemistryComponent(key=str(i), label=str(i), score=s,
                                    evidence='synthetic' if s is not None else 'unavailable', explanation='demo')
                  for i, s in enumerate([10, 5, None, None, None])]
    assert aggregate_chemistry('a', 'b', components).score is None
    components[2].score = 0
    assert aggregate_chemistry('a', 'b', components).score == 5
    assert demo_chemistry('a', 'b') == demo_chemistry('b', 'a')


def test_all_formations_preserve_identity_and_topology():
    lineup = squad_snapshot().default_lineup
    ids = set(lineup.assignments.values())
    for f in formations():
        changed = change_formation(lineup, f.id)
        assert set(changed.assignments.values()) == ids
        assert changed == change_formation(lineup, f.id)
        assert changed.bench == lineup.bench
        assert changed.assignments['GK'] == lineup.assignments['GK']
        assert len(f.slots) == 11 and len(set(f.edges)) == len(f.edges)
        slots = {s.id: s for s in f.slots}
        assert len([e for e in f.edges if 'GK' in e]) == 2
        assert all(abs(slots[a].row - slots[b].row) <= 1 for a, b in f.edges)
        assert evaluate_lineup(changed).completeness == 11
    missing = lineup.model_copy(deep=True)
    missing.assignments['ST'] = None
    assert evaluate_lineup(missing).team_rating is None
    assert evaluate_lineup(missing).completeness == 10


def test_squad_api_standalone_and_input_boundary(tmp_path):
    with TestClient(create_app(Settings(database_url=f'sqlite:///{tmp_path / "empty.db"}', serve_private_evidence=False))) as client:
        assert client.get('/health/ready').status_code == 503
        s = client.get('/squads/liverpool-men').json()
        assert len(s['players']) == 31 and s['season'] == '2026/27'
        assert client.get('/squads').json()[0]['snapshot_id'] == s['snapshot_id']
        assert len(client.get('/formations').json()) == 5
        keeper_ratings = client.get('/squads/liverpool-men/position-ratings?role=GK&multiplier=1.5')
        assert keeper_ratings.status_code == 200 and len(keeper_ratings.json()) == 5
        assert len(client.get('/squads/liverpool-men/position-ratings?role=CB').json()) == 26
        assert client.get('/squads/liverpool-men/position-ratings?role=CB&multiplier=1.55').status_code == 422
        assert client.get('/squads/no-such-team').status_code == 404
        lineup = s['default_lineup']
        e = client.post('/squads/liverpool-men/evaluate', json=lineup)
        assert e.status_code == 200 and e.json()['evidence'] == 'synthetic'
        assert e.json()['lineup'] == lineup
        for patch in [{'role_multiplier': 0.9}, {'role_multiplier': 1.55}, {'snapshot_id': 'old'},
                      {'assignments': {**lineup['assignments'], 'ST': lineup['assignments']['GK']}},
                      {'assignments': {**lineup['assignments'], 'ST': 'unknown'}},
                      {'bench': [lineup['assignments']['ST']]}, {'trusted_rating': 99}]:
            assert client.post('/squads/liverpool-men/evaluate', json={**lineup, **patch}).status_code == 422
        a = dict(lineup['assignments'])
        a['GK'], a['ST'] = a['ST'], a['GK']
        assert client.post('/squads/liverpool-men/evaluate', json={**lineup, 'assignments': a}).status_code == 422
        changed = client.post('/squads/liverpool-men/formation', json={'lineup': lineup, 'formation_id': '3-5-2'})
        assert changed.status_code == 200
        assert set(changed.json()['assignments'].values()) == set(lineup['assignments'].values())
        assert client.post('/squads/liverpool-men/formation', json={'lineup': lineup, 'formation_id': 'bad'}).status_code == 422


def test_uniqueness_contract():
    with pytest.raises(ValidationError):
        LineupState(snapshot_id='x', assignments={'a': 'same', 'b': 'same'})
