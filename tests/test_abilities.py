import json
from datetime import UTC, datetime

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from scout.ability_engine import display, evaluate_role, percentile, shrink, standardize
from scout.api import create_app
from scout.contracts import Role
from scout.roles import API_LEAGUES
from scout.settings import Settings
from scout.squads import player_rating, squad_snapshot
from scout.striker_features import ABILITIES, BY_KEY, FEATURES, ST_WEIGHTS, derive
from scout.striker_profiles import demo_population, demo_profile
from scout.striker_refresh import StrikerRecord, active_profile, refresh


def test_rating_magnitude_without_upper_cap_ranking_and_ties():
    assert display(0) == 50
    assert display(3) == 95
    assert display(4) == 110
    assert display(8) == 170
    assert display(-4) == 1
    assert standardize(7, np.array([7, 7])) == 0
    assert standardize(8, np.array([7, 7])) is None
    assert percentile(7, np.array([7, 7])) == 50
    assert percentile(2, np.array([1, 2, 2, 3])) == 50
    assert standardize(10, np.array([1, 2, 3, 4])) > 6  # preserve genuine magnitude
    assert shrink(2, 450, 1, 450) == (1.5, .5)
    assert shrink(None, 450, 1, 450) == (None, None)


def test_registry_weights_and_exact_derived_units():
    assert len(FEATURES) == 36
    assert 'third_tackles90' not in BY_KEY
    assert ABILITIES['Defensive Activity'] == {'interceptions90': 3 / 13, 'recoveries90': 7 / 13, 'blocks90': 3 / 13}
    assert all(sum(w.values()) == pytest.approx(1) for w in ABILITIES.values())
    assert sum(ST_WEIGHTS.values()) == pytest.approx(1)
    assert ST_WEIGHTS['Defensive Activity'] == .10
    values = derive({"minutes": 180, "non_penalty_goals": 2, "npxg": 1.5,
        "non_penalty_shots": 8, "shots": 10, "shots_on_target": 4,
        "aerial_duels_won": 3, "aerial_duels_lost": 1})
    assert values["npg90"] == 1 and values["finishing_delta90"] == .25
    assert values["goals_per_shot"] == .25 and values["sot_pct"] == 40
    assert values["aerial_pct"] == 75
    assert values["open_xg90"] is None
    assert derive({"minutes": 0})["npg90"] is None
    assert BY_KEY["dispossessed90"].direction == -1
    assert BY_KEY["offsides90"].direction == 0


def test_restandardized_composites_and_missingness():
    population = demo_population()
    means = {k: float(np.mean(v)) for k, v in population.values.items()}
    exposure = {k: float(np.median(v)) for k, v in population.exposure.items()}
    rated, peer_z = evaluate_role("ST", "Striker", ABILITIES, ST_WEIGHTS, means, exposure, population)
    assert np.mean(peer_z) == pytest.approx(0, abs=1e-12)
    assert np.std(peer_z) == pytest.approx(1)
    assert rated.rating == pytest.approx(display(rated.role_z))
    assert rated.rating_unclipped == pytest.approx(50 + 15 * rated.role_z)
    means["npxg90"] = None
    missing, _ = evaluate_role("ST", "Striker", ABILITIES, ST_WEIGHTS, means, exposure, population)
    assert missing.rating is None
    assert missing.abilities[0].rating is None
    assert missing.abilities[0].features[1].value is None
    assert missing.abilities[1].rating is not None


def test_multiple_roles_primary_position_and_determinism():
    p = demo_profile("lfc-cody-gakpo")
    assert p == demo_profile("lfc-cody-gakpo")
    best = max(p.roles, key=lambda r: r.role_z)
    assert p.primary_role_id == best.role_id and p.primary_rating == best.rating
    assert p.hybrids and p.hybrids[0].role_z is not None
    assert p.versatility is not None
    player = next(v for v in squad_snapshot().players if v.id == p.player_id)
    st = player_rating(player, Role.ST, 1.5)
    assert st.score == p.roles[0].rating
    assert st.score == player_rating(player, Role.ST, 3).score  # supplied weights, no global overwrite
    assert player_rating(player, Role.W, 1.5).score != st.score


def record(i=0):
    raw = {k: float(100 + i * 2) for k in {f.numerator for f in FEATURES} if k != "finishing_delta"}
    raw.update(minutes=1500 + i, non_penalty_goals=6 + i % 4, npxg=7 + i % 5,
        non_penalty_shots=60 + i, shots=70 + i, shots_on_target=20 + i,
        shots_inside_box=50 + i, headed_shots=10, open_play_xg=6,
        passes_completed=500 + i, passes_attempted=700 + i,
        take_ons_successful=20 + i, take_ons_attempted=50 + i,
        duels_won=60 + i, duels_attempted=100 + i,
        aerial_duels_won=20 + i, aerial_duels_lost=20 + i)
    raw.pop("aerial_duels_attempted", None)
    now = datetime.now(UTC).isoformat()
    return {"player_id": f"test-{i}", "provider_player_id": str(i), "name": f"Test fixture {i}",
        "team_id": "test-team", "competition": "England", "season": "2026/27", "roles": ["ST"],
        "totals": raw, "source_urls": {k: "https://example.test/authorized-test-fixture" for k in raw},
        "observed_through": "2026-10-01T00:00:00Z", "retrieved_at": now,
        "identity_reviewed": True, "publication_approved": True}


def five_league_records():
    return [{**record(i + league_index * 30), "competition": league}
            for league_index, league in enumerate(API_LEAGUES) for i in range(30)]


def test_refresh_pools_top_five_peers_without_changing_player_competition():
    from scout.striker_refresh import evaluate_records

    leagues = list(API_LEAGUES)
    records = [StrikerRecord.model_validate({**record(i), 'competition': leagues[i % 5]})
               for i in range(40)]
    profiles = evaluate_records(records, 'pooled-test')
    assert all(p.primary_rating is not None for p in profiles.values())
    assert profiles['test-0'].competition == leagues[0]
    assert all(f.peer_count == 40 for a in profiles['test-0'].roles[0].abilities
               for f in a.features if f.direction)


def test_validation_denominators_identity_and_bounds():
    r = record()
    StrikerRecord.model_validate(r)
    for edit in [{"identity_reviewed": False}, {"season": "2026/28"}, {"roles": ["CB"]},
                 {"observed_through": "2025-10-01T00:00:00Z"}]:
        with pytest.raises(ValidationError):
            StrikerRecord.model_validate({**r, **edit})
    r["totals"]["shots_on_target"] = 1000
    with pytest.raises(ValidationError):
        StrikerRecord.model_validate(r)


@pytest.mark.parametrize('edit', [
    {'publication_approved': 'true'}, {'identity_reviewed': 1},
    {'roles': ['ST', 'ST']},
    {'totals': {'minutes': 1500, 'shots': True}},
    {'totals': {'minutes': 1e-300, 'shots': 1e300}},
    {'totals': {'minutes': 1500, 'aerial_duels_won': 1e308, 'aerial_duels_lost': 1e308}},
])
def test_import_rejects_coercion_duplicates_and_derived_overflow(edit):
    with pytest.raises(ValidationError):
        StrikerRecord.model_validate({**record(), **edit})


def test_refresh_gate_checksum_and_previous_release(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"enabled": False, "publication_approved": True}))
    source = tmp_path / "source.json"
    source.write_text(json.dumps(five_league_records()))
    root = tmp_path / "strikers"
    report = refresh(root, config, source)
    assert report["activated"] is True
    assert all(v["rated_strikers"] == 30 for v in report["league_coverage"].values())
    bytes_before = (root / "releases" / report["release_id"] / "profiles.json").read_bytes()
    assert refresh(root, config, source)["activated"] is True
    # Reordered source pages and JSON object keys are the same frozen release.
    # Retrieval timestamps must actually be identical for an identical-input
    # assertion; the helper intentionally records time at each invocation.
    original = json.loads(source.read_text())
    reordered = [{key: value[key] for key in reversed(value)} for value in reversed(original)]
    source.write_text(json.dumps(reordered))
    replay = refresh(root, config, source)
    assert replay['release_id'] == report['release_id'] and replay['activated']
    assert (root / "releases" / report["release_id"] / "profiles.json").read_bytes() == bytes_before
    assert active_profile("test-0", root).evidence == "observed"
    previous = (root / "active.json").read_text()
    from scout.striker_refresh import reproduce_release
    reproduction = tmp_path / 'reproduced-release'
    proof = reproduce_release(root / 'releases' / report['release_id'], reproduction)
    assert proof['matched'] and not proof['activated']
    assert (root / 'active.json').read_text() == previous
    for name in [*proof['files'], 'manifest.json']:
        assert (reproduction / name).read_bytes() == (root / 'releases' / report['release_id'] / name).read_bytes()
    bad = record()
    bad["totals"]["npxg"] = None
    source.write_text(json.dumps([bad]))
    rejected = refresh(root, config, source)
    assert rejected["activated"] is False
    assert (root / "active.json").read_text() == previous
    partial = json.loads((root / 'releases' / rejected['release_id'] / 'profiles.json').read_text())['test-0']
    assert partial['primary_rating'] is None
    features = partial['roles'][0]['abilities'][0]['features']
    assert features[0]['value'] == pytest.approx(6 / 1500 * 90)
    assert features[1]['value'] == 0
    assert features[1]['evidence_status'] == 'unrecorded_zero'
    assert features[1]['weight'] == 0
    assert all(f['peer_count'] == 0 and f['z'] is None for f in features)
    import hashlib

    from scout.striker_state import pack_state, restore_files, unpack_state
    snapshot = pack_state(root)
    restored = tmp_path / 'restored-state'
    restore_files(unpack_state(snapshot, hashlib.sha256(snapshot).hexdigest()), restored)
    assert (restored / 'active.json').read_text() == previous
    assert active_profile('test-0', restored) == active_profile('test-0', root)
    profiles = root / "releases" / report["release_id"] / "profiles.json"
    profiles.write_text('{}')
    with pytest.raises(ValueError, match="checksum"):
        active_profile("test-0", root)


def test_observed_striker_evidence_does_not_gain_fictional_winger_rating(monkeypatch):
    from scout import striker_refresh
    player = next(p for p in squad_snapshot().players if p.id == 'lfc-cody-gakpo')
    observed = demo_profile(player.id).model_copy(update={"evidence": "observed"})
    monkeypatch.setattr(striker_refresh, "active_profile", lambda player_id: observed)
    assert player_rating(player, Role.ST, 1.5).evidence == "observed"
    assert player_rating(player, Role.W, 1.5).score is None


def test_no_season_score_below_minimum_exposure():
    from scout.striker_refresh import evaluate_records
    samples = [StrikerRecord.model_validate(record(i)) for i in range(30)]
    samples[0].totals['minutes'] = 800
    profile = evaluate_records(samples, 'test-low-exposure')['test-0']
    assert profile.roles and all(r.rating is None for r in profile.roles)
    assert profile.roles[0].abilities[0].features[0].value == pytest.approx(6 / 800 * 90)
    assert profile.primary_rating is None


def test_measurement_versions_never_share_calibration_peers():
    from scout.striker_refresh import evaluate_records
    samples = [StrikerRecord.model_validate(record(i)) for i in range(30)]
    for sample in samples[15:]:
        sample.measurement_version = 'pitchapi-measurements-v1'
    profiles = evaluate_records(samples, 'test-separated-measurements')
    assert all(profile.primary_rating is None for profile in profiles.values())
    assert profiles['test-15'].feature_version.endswith(':pitchapi-measurements-v1')
    assert any('15 complete eligible peers' in reason for reason in profiles['test-15'].limitations)


def test_hybrid_cannot_calibrate_outlier_against_tied_peers():
    from scout.ability_engine import hybrid_score
    components = [r.model_copy(update={'role_z': 1.0}) for r in demo_profile('test-hybrid').roles[:2]]
    assert hybrid_score('test', components, [np.zeros(30), np.zeros(30)], [.5, .5]) is None


def test_quarantine_report_does_not_echo_untrusted_input(tmp_path):
    config = tmp_path / 'config.json'
    config.write_text('{"enabled":false}')
    invalid = record()
    invalid['unexpected_secret'] = 'DO-NOT-ECHO-THIS-INPUT'
    source = tmp_path / 'invalid.json'
    source.write_text(json.dumps([invalid]))
    report = refresh(tmp_path / 'state', config, source)
    assert report['quarantine']
    assert 'DO-NOT-ECHO-THIS-INPUT' not in json.dumps(report)


@pytest.mark.parametrize('failure', [ValueError, AttributeError])
def test_provider_failure_reports_status_and_keeps_active_release(tmp_path, monkeypatch, failure):
    from scout import striker_refresh

    class FailingProvider:
        def __init__(self, key, root):
            pass

        def ingest(self, season):
            raise failure('RESPONSE-CONTENT-MUST-NOT-BE-LOGGED')

    monkeypatch.setattr(striker_refresh, 'ApiFootball', FailingProvider)
    monkeypatch.setenv('SCOUT_API_FOOTBALL_KEY', 'test-only-placeholder')
    config = tmp_path / 'config.json'
    config.write_text('{"enabled":true,"provider":"api-football","season":2026,"observed_through":"2026-10-01T00:00:00Z"}')
    state = tmp_path / 'state'
    state.mkdir()
    pointer = '{"release_id":"strikers-202610-000000000001"}'
    (state / 'active.json').write_text(pointer)
    report = refresh(state, config)
    assert report['failure'] == failure.__name__ and not report['activated']
    assert (state / 'active.json').read_text() == pointer
    assert 'RESPONSE-CONTENT' not in (state / 'refresh-status.json').read_text()


def test_single_league_import_cannot_publish_as_five_league_release(tmp_path):
    config = tmp_path / 'config.json'
    config.write_text('{"enabled":false,"publication_approved":true,"season":2026}')
    source = tmp_path / 'source.json'
    source.write_text(json.dumps([record(i) for i in range(30)]))
    state = tmp_path / 'state'
    report = refresh(state, config, source)
    assert not report['activated'] and not (state / 'active.json').exists()
    assert report['league_coverage']['England']['rated_strikers'] == 30
    assert sum(v['rated_strikers'] for v in report['league_coverage'].values()) == 30
    assert 'France: fewer than 30 calibrated strikers' in report['publication_errors']


@pytest.mark.parametrize('configuration', [
    '{"enabled":"false"}', '{"publication_approved":"false"}',
    '{"season":true}', '{"enabled":true}', '{"unexpected_secret":"NEVER-LOG-THIS"}',
])
def test_source_config_is_strict_and_reports_failure_without_replacing_state(tmp_path, configuration):
    config = tmp_path / 'config.json'
    config.write_text(configuration)
    state = tmp_path / 'state'
    state.mkdir()
    pointer = '{"release_id":"strikers-202610-000000000001"}'
    (state / 'active.json').write_text(pointer)
    report = refresh(state, config)
    assert report['failure'] == 'ValidationError'
    assert (state / 'active.json').read_text() == pointer
    assert 'NEVER-LOG-THIS' not in json.dumps(report)


@pytest.mark.parametrize('payload', ['{BROKEN-SECRET-INPUT', '{}', '[{"minutes":NaN}]', '[{"minutes":Infinity}]'])
def test_malformed_import_reports_failure_and_preserves_previous_release(tmp_path, payload):
    config = tmp_path / 'config.json'
    config.write_text('{"enabled":false}')
    source = tmp_path / 'source.json'
    source.write_text(payload)
    state = tmp_path / 'state'
    state.mkdir()
    pointer = '{"release_id":"strikers-202610-000000000001"}'
    (state / 'active.json').write_text(pointer)
    report = refresh(state, config, source)
    assert report['failure'] and not report['activated']
    assert (state / 'active.json').read_text() == pointer
    assert 'BROKEN-SECRET' not in json.dumps(report)


def test_observed_profiles_are_exactly_reproducible_across_input_and_role_order():
    from scout.striker_refresh import evaluate_records
    samples = [StrikerRecord.model_validate({**record(i), 'roles': ['ST', 'advanced-forward', 'false-nine']})
               for i in range(30)]
    epoch = '2026-10-06T00:00:00+00:00'
    expected = evaluate_records(samples, 'fixed-fixture-release', epoch)
    shuffled = [r.model_copy(update={'roles': list(reversed(r.roles)),
                                    'totals': dict(reversed(list(r.totals.items())))})
                for r in reversed(samples)]
    actual = evaluate_records(shuffled, 'fixed-fixture-release', epoch)
    assert actual == expected
    assert actual['test-0'].hybrids and actual['test-0'].versatility is not None
    assert len({p.calculation_timestamp for p in actual.values()}) == 1


def test_immutable_release_records_input_and_runtime_environment(tmp_path, monkeypatch):
    from scout import striker_refresh
    config = tmp_path / 'config.json'
    config.write_text('{"enabled":false}')
    source = tmp_path / 'source.json'
    source.write_text(json.dumps([record()]))
    state = tmp_path / 'state'
    first = refresh(state, config, source)
    directory = state / 'releases' / first['release_id']
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert len(manifest['input_sha256']) == 64
    assert set(manifest['environment']) == {'python', 'numpy', 'scipy', 'pydantic', 'pyarrow'}
    assert json.loads((directory / 'profiles.json').read_text())['test-0']['calculation_timestamp'] == manifest['calculation_timestamp']
    changed = {**manifest['environment'], 'numpy': 'changed-runtime-test-fixture'}
    monkeypatch.setattr(striker_refresh, 'scoring_environment', lambda: changed)
    second = refresh(state, config, source)
    assert first['release_id'] != second['release_id']
    assert (directory / 'manifest.json').read_text() == json.dumps(manifest, indent=2, sort_keys=True)


def test_partial_silver_preserves_later_rows_and_reproduction_cli_never_activates(tmp_path):
    import pyarrow.parquet as pq
    from typer.testing import CliRunner

    from scout.cli import app
    config = tmp_path / 'config.json'
    config.write_text('{"enabled":false}')
    first = {**record(), 'player_id': 'a-partial', 'totals': {'minutes': 1000},
             'source_urls': {'minutes': 'https://example.test/fixture'}}
    second = {**record(1), 'player_id': 'z-complete'}
    source = tmp_path / 'source.json'
    source.write_text(json.dumps([second, first]))
    state = tmp_path / 'state'
    report = refresh(state, config, source)
    directory = state / 'releases' / report['release_id']
    rows = pq.read_table(directory / 'silver.parquet').to_pylist()
    assert [r['player_id'] for r in rows] == ['a-partial', 'z-complete']
    assert rows[0]['shots'] is None and rows[1]['shots'] == second['totals']['shots']
    target = tmp_path / 'reproduced'
    runner = CliRunner()
    result = runner.invoke(app, ['reproduce-strikers', str(directory), str(target)])
    assert result.exit_code == 0
    assert json.loads(result.stdout)['matched'] is True
    assert not (state / 'active.json').exists() and not (target / 'active.json').exists()
    content = (target / 'profiles.json').read_bytes()
    refused = runner.invoke(app, ['reproduce-strikers', str(directory), str(target)])
    assert refused.exit_code == 1 and (target / 'profiles.json').read_bytes() == content
    artifact = directory / 'gold.parquet'
    artifact.write_bytes(b'corrupt-test-fixture')
    corrupt_target = tmp_path / 'corrupt-reproduction'
    refused = runner.invoke(app, ['reproduce-strikers', str(directory), str(corrupt_target)])
    assert refused.exit_code == 1 and not corrupt_target.exists()


def test_publication_checks_observation_freshness_target_season_and_common_window():
    from types import SimpleNamespace

    from scout.striker_refresh import publication_errors
    samples = [StrikerRecord.model_validate(v) for v in five_league_records()]
    profiles = {r.player_id: SimpleNamespace(roles=[SimpleNamespace(role_id='ST', rating=50)]) for r in samples}
    now = datetime(2026, 10, 6, tzinfo=UTC)
    config = {'season': 2026, 'publication_approved': True}
    assert publication_errors(samples, profiles, config, {'quarantine': []}, now) == []
    for r in samples:
        r.observed_through = datetime(2026, 8, 1, tzinfo=UTC)
    errors = publication_errors(samples, profiles, config, {'quarantine': []}, now)
    assert 'Current-season observation cutoff older than 45 days' in errors
    samples[0].observed_through = datetime(2026, 10, 1, tzinfo=UTC)
    errors = publication_errors(samples, profiles, {**config, 'season': 2025}, {'quarantine': []}, now)
    assert 'Records do not match configured target season' in errors
    assert 'A common season and observation cutoff is required across all five leagues' in errors


def test_provider_cutoff_is_reviewed_and_team_mapping_is_required(tmp_path):
    from scout.striker_refresh import canonical_api_snapshots
    snapshot = {'endpoint': 'players', 'retrieved_at': '2026-10-06T00:00:00Z', 'payload': {'response': [
        {'player': {'id': 100, 'name': 'Test fixture'}, 'statistics': [
            {'team': {'id': 200}, 'league': {'id': API_LEAGUES['England'], 'season': 2026},
             'games': {'minutes': 1000}, 'shots': {'total': 20, 'on': 10}}]}]}}
    (tmp_path / 'snapshot.json').write_text(json.dumps(snapshot))
    identity = {'player_id': 'fixture-100', 'roles': ['ST'], 'reviewed': True}
    config = {'season': 2026, 'observed_through': '2026-10-01T00:00:00Z', 'identities': {'100': identity}}
    mapped = canonical_api_snapshots(tmp_path, config)[0]
    assert mapped['observed_through'] == '2026-10-01T00:00:00Z'
    assert mapped['retrieved_at'] == '2026-10-06T00:00:00Z'
    assert mapped['identity_reviewed'] is False
    with pytest.raises(ValidationError):
        StrikerRecord.model_validate(mapped)
    identity['team_ids'] = ['200']
    approved = canonical_api_snapshots(tmp_path, config)[0]
    assert StrikerRecord.model_validate(approved).identity_reviewed is True


@pytest.mark.parametrize('key,value', [('shots_inside_box', 1000), ('headed_shots', 1000), ('open_play_xg', 1000)])
def test_nested_shot_totals_cannot_exceed_their_parent_measurement(key, value):
    sample = record()
    sample['totals'][key] = value
    with pytest.raises(ValidationError):
        StrikerRecord.model_validate(sample)


def test_api_ability_contract_independent_of_candidate_db(tmp_path):
    client = TestClient(create_app(Settings(database_url=f"sqlite:///{tmp_path / 'unused.db'}", serve_private_evidence=False)))
    response = client.get('/squads/liverpool-men/players/lfc-alexander-isak/abilities')
    assert response.status_code == 200
    assert len(response.json()["roles"][0]["abilities"]) == 6
    assert response.json()["evidence"] == "synthetic"
    assert client.get('/squads/liverpool-men/players/lfc-alisson-becker/abilities').status_code == 422
