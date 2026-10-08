import numpy as np
import pytest

from scout.ability_engine import evaluate_role
from scout.player_catalogue import score_catalogue
from scout.striker_features import ABILITIES, ST_WEIGHTS, effective_weights, measurement_statuses
from scout.striker_profiles import demo_population


def test_ratio_example_and_recorded_zero_do_not_infer_missingness():
    base = dict(a=.5,b=.2,c=.2,fouls=.1)
    result = effective_weights(base, {'fouls': 'unrecorded_zero'})
    assert result == pytest.approx(dict(a=5/9,b=2/9,c=2/9,fouls=0))
    assert effective_weights(base, {'fouls':'observed'}) == base
    assert effective_weights(base, dict.fromkeys(base, 'unrecorded_zero')) == dict.fromkeys(base, 0)


def test_physicality_excludes_only_flagged_zero_and_displays_effective_weights():
    pop = demo_population()
    values = {k: float(np.mean(v)) for k,v in pop.values.items()}
    exposures = {k:float(np.median(v)) for k,v in pop.exposure.items()}
    values['dispossessed90'] = 0
    recorded,_ = evaluate_role('ST','ST',ABILITIES,ST_WEIGHTS,values,exposures,pop,{'dispossessed90':'observed'})
    filled,_ = evaluate_role('ST','ST',ABILITIES,ST_WEIGHTS,values,exposures,pop,{'dispossessed90':'unrecorded_zero'})
    physical = next(a for a in filled.abilities if a.name=='Physicality')
    actual = next(a for a in recorded.abilities if a.name=='Physicality')
    weights = {f.key:f.weight for f in physical.features}
    assert weights['dispossessed90']==0 and weights['duels_won90']==pytest.approx(.10/.75)
    assert next(f for f in actual.features if f.key=='dispossessed90').weight==.25
    assert physical.rating is not None and actual.rating is not None
    excluded = next(f for f in physical.features if f.key=='dispossessed90')
    assert excluded.value==0 and excluded.z is None and excluded.percentile is None
    assert excluded.base_weight==.25 and physical.available==4


def test_missing_raw_measurement_is_flagged_but_recorded_zero_is_not():
    raw={'minutes':1000,'fouls_won':0}
    assert measurement_statuses(raw)['fouls_won90']=='observed'
    raw['fouls_won']=None
    assert measurement_statuses(raw)['fouls_won90']=='unrecorded_zero'
    assert measurement_statuses({'minutes':1000,'shots':0,'shots_on_target':0})['sot_pct']=='not_applicable_zero_attempts'


def test_real_catalogue_recalculates_partial_physicality_and_overall():
    from scout.real_data import feature_rows
    from scout.striker_features import FEATURES
    players=[]
    for i in range(40):
        raw={f.numerator:2+i for f in FEATURES}
        raw.update(minutes=900+30*i,shots=20+i,shots_on_target=5+i/3,non_penalty_goals=2+i/10,
                   npxg=3+i/9,non_penalty_shots=19+i,passes_attempted=400+i,passes_completed=300+i,
                   take_ons_attempted=30+i,take_ons_successful=10+i,duels_attempted=80+i,duels_won=40+i,
                   aerial_duels_attempted=30+i,aerial_duels_won=10+i,aerial_duels_lost=20,dispossessed=None)
        features={k:{**v,'provider':'fixture','measurement_version':'fixture'} for k,v in feature_rows(raw).items()}
        features['dispossessed90'].update(value=0,status='unrecorded_zero')
        league = ['England', 'Spain', 'Germany', 'Italy', 'France'][i % 5]
        players.append({'id':str(i),'position':'ST','league':league,'minutes':raw['minutes'],
                        'features':features,'abilities':[],'ability_detail':{},'overall':None})
    score_catalogue(players)
    assert all(p['overall'] is not None for p in players)
    # Eight peers per league cannot calibrate alone: all forty must be pooled.
    assert len(players[0]['ability_detail']['Physicality']['peer_ids']) == 40
    assert players[0]['ability_detail']['Physicality']['effective_weights']['duels_won90']==pytest.approx(.10/.75)
