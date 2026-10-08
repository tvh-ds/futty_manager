"""Frozen pre-refactor outputs, plus equality for identical eligible evidence."""
import json
from pathlib import Path

import numpy as np
import pytest

from scout.ability_engine import Population, evaluate_role
from scout.player_catalogue import score_catalogue
from scout.real_data import feature_rows
from scout.striker_features import ABILITIES, BY_KEY, FEATURES, ST_WEIGHTS


def evidence(filled=False):
    players = []
    for i in range(40):
        raw = {f.numerator: 2 + i for f in FEATURES}
        raw.update(minutes=900+30*i, shots=20+i, shots_on_target=5+i/3, non_penalty_goals=2+i/10,
            npxg=3+i/9, non_penalty_shots=19+i, passes_attempted=400+i, passes_completed=300+i,
            take_ons_attempted=30+i, take_ons_successful=10+i, duels_attempted=80+i, duels_won=40+i,
            aerial_duels_attempted=30+i, aerial_duels_won=10+i, aerial_duels_lost=20,
            fouls_won=None if filled else i % 5)
        features = {k: {**v, 'provider': 'fixture', 'measurement_version': 'fixture'}
            for k, v in feature_rows(raw).items()}
        if filled:
            features['fouls_won90'].update(value=0, status='unrecorded_zero')
        players.append({'id': str(i), 'position': 'ST', 'league': ['England','Spain','Germany','Italy','France'][i%5],
            'minutes': raw['minutes'], 'features': features, 'abilities': [], 'ability_detail': {}, 'overall': None})
    return players


def outputs(filled):
    players = evidence(filled)
    score_catalogue(players)
    population = Population('fixture', {k: np.array([p['features'][k]['value'] for p in players]) for k in BY_KEY},
        {d: np.array([p['features'][next(k for k in BY_KEY if BY_KEY[k].denominator == d)]['denominator']
            for p in players]) for d in {f.denominator for f in FEATURES}}, '2025/26', 'Top five', 'ST')
    roles = []
    for p in players:
        features = p['features']
        result, _ = evaluate_role('ST', 'Striker', ABILITIES, ST_WEIGHTS,
            {k: v['value'] for k, v in features.items()},
            {d: features[next(k for k in BY_KEY if BY_KEY[k].denominator == d)]['denominator']
                for d in population.exposure}, population, {k: v['status'] for k, v in features.items()})
        roles.append(result)
    return players, roles


@pytest.mark.parametrize('filled', [False, True])
def test_frozen_outputs_and_same_evidence_parity(filled, monkeypatch):
    # Freeze the historical coefficients as well as outputs: the user has
    # explicitly replaced the live weights, not the calibration arithmetic.
    from scout.position_config import CONFIG
    historical = {
        'Finishing':dict(zip(ABILITIES['Finishing'],[.20,.18,.14,.08,.10,.10,.10,.10],strict=True)),
        'Link-Up / Creation':dict(zip(ABILITIES['Link-Up / Creation'],[.12,.22,.18,.18,.12,.08,.10],strict=True)),
        'Carrying / 1v1':dict(zip(ABILITIES['Carrying / 1v1'],[.08,.18,.16,.20,.12,.10,.08,.08],strict=True)),
        'Physicality':dict(duels_won90=.24,duel_pct=.24,aerials_won90=.18,aerial_pct=.18,fouls_won90=.10,dispossessed90=.06),
    }
    for name,weights in historical.items():
        monkeypatch.setitem(ABILITIES,name,weights)
        ability=next(a for a in CONFIG['positions']['ST']['abilities'] if a['name']==name)
        monkeypatch.setitem(ability,'features',weights)
    baseline = json.loads(Path(__file__).with_name('fixtures').joinpath('calibration-baseline.json').read_text())
    players, roles = outputs(filled)
    expected = baseline[str(filled)]
    for i, (p, role) in enumerate(zip(players, roles, strict=True)):
        assert p['overall'] == pytest.approx(expected['catalogue'][i]['overall'], abs=1e-10)
        assert role.rating == pytest.approx(expected['role'][i]['overall'], abs=1e-10)
        assert p['overall'] == pytest.approx(role.rating, abs=1e-10)
        for ability in role.abilities:
            actual = p['ability_detail'][ability.name]
            assert actual['rating'] == pytest.approx(expected['catalogue'][i]['abilities'][ability.name], abs=1e-10)
            assert ability.rating == pytest.approx(expected['role'][i]['abilities'][ability.name], abs=1e-10)
            assert actual['rating'] == pytest.approx(ability.rating, abs=1e-10)
            for f in ability.features:
                if f.direction and f.weight:
                    assert actual['feature_stats'][f.key]['z'] == pytest.approx(f.z, abs=1e-10)
