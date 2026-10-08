import pytest

from scout.contracts import HardConstraints, RecruitmentBrief, Role, ScenarioRequest
from scout.engine import RecruitmentEngine, posterior
from scout.roles import ROLE_SPECS


@pytest.mark.parametrize("role", list(Role))
def test_every_role_has_usable_evidence(recruitment, role):
    results = recruitment.recommend(RecruitmentBrief(role=role))
    assert results
    assert all(role in item.player.roles for item in results)
    assert all(0 <= item.score <= 100 for item in results)
    assert all(item.profile.coverage > 25 for item in results)


def test_unknown_hard_requirements_are_not_verified(recruitment):
    brief = RecruitmentBrief(constraints=HardConstraints(foot="left", attributes=["high_line"]))
    results = recruitment.recommend(brief)
    assert results and all(item.status == "verification_required" for item in results)
    assert all(any("High line" in question for question in item.unknowns) for item in results)
    brief.include_verification_required = False
    assert recruitment.recommend(brief) == []


def test_missing_is_not_a_zero_quality_measurement(cohort):
    release, players, teams = cohort
    player = players[0].model_copy(deep=True)
    player.metrics = {}
    engine = RecruitmentEngine(release, [player], teams)
    result = engine.recommend(RecruitmentBrief(role=player.roles[0], constraints=HardConstraints(min_minutes=0)))[0]
    assert result.profile.values == {}
    assert result.components["quality"] is None
    assert result.status == "insufficient_evidence"


def test_shrinkage_and_intervals_use_exposure(cohort):
    player = next(player for player in cohort[1] if "goals_p90" in player.metrics)
    value, interval = posterior(player, "goals_p90", 0.4)
    assert min(player.metrics["goals_p90"].value, 0.4) <= value <= max(player.metrics["goals_p90"].value, 0.4)
    assert interval[0] < interval[1]


def test_replacement_excluded_and_changes_reported(recruitment):
    player = next(player for player in recruitment.players.values() if Role.CB in player.roles)
    results = recruitment.recommend(RecruitmentBrief(role=Role.CB, replacement_id=player.id))
    assert all(item.player.id != player.id for item in results)
    assert any(item.replacement_changes for item in results)


def test_seed_reproduces_entire_scenario(recruitment):
    player = next(iter(recruitment.players.values()))
    request = ScenarioRequest(player_id=player.id, team_id=player.team_id, seed=81)
    assert recruitment.simulate(request) == recruitment.simulate(request)
    request.seed = 82
    assert recruitment.simulate(request).minutes_interval != recruitment.simulate(request.model_copy(update={"seed": 81})).minutes_interval


def test_missing_fees_are_unknown(recruitment):
    player = next(iter(recruitment.players.values()))
    result = recruitment.simulate(ScenarioRequest(player_id=player.id, team_id=player.team_id, budget=1000))
    assert result.total_fee is None
    assert result.budget_satisfied is None


def test_one_identity_cannot_fill_two_slots(cohort):
    release, players, teams = cohort
    original = players[0]
    duplicate = original.model_copy(update={"id": "second-stint"})
    engine = RecruitmentEngine(release, [original, duplicate], teams)
    with pytest.raises(ValueError, match="multiple simultaneous"):
        engine.simulate(ScenarioRequest(player_id=original.id, team_id=original.team_id,
                       assignments={original.id: Role.GK, duplicate.id: Role.GK}))


def test_role_ontology_has_distinct_metrics():
    assert len(ROLE_SPECS) == 8
    assert "save_pct" in ROLE_SPECS[Role.GK].quality
    assert "goals_p90" in ROLE_SPECS[Role.ST].quality


def test_intended_style_is_editable_and_explicitly_manual(recruitment):
    results = recruitment.recommend(RecruitmentBrief(intended_style={"progressive_passes_p90": 5.0}))
    assert all(item.components["tactical_fit"] is not None for item in results)
    assert all(any("manually entered" in reason for reason in item.reasons) for item in results)
    with pytest.raises(ValueError, match="supported style"):
        recruitment.recommend(RecruitmentBrief(intended_style={"athletic_speed": 10}))


def test_role_requirements_expose_squad_shortfall(recruitment):
    player = next(iter(recruitment.players.values()))
    result = recruitment.simulate(ScenarioRequest(player_id=player.id, team_id=player.team_id,
                                                 role_requirements={Role.CB: 8}))
    assert "CB" in result.squad_gaps
