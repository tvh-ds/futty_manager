from copy import deepcopy

import numpy as np
import pytest

from scout.player_catalogue import score_catalogue
from scout.position_config import CONFIG, load_config, registry, validate_config
from scout.position_evidence import measurement


def test_user_weights_are_exact_and_other_st_features_unchanged():
    abilities, ovr, _ = registry("ST")
    assert abilities["Physicality"] == dict(
        duels_won90=0.10, duel_pct=0.30, aerials_won90=0.10, aerial_pct=0.25, dispossessed90=0.25
    )
    assert abilities["Finishing"]["finishing_delta90"] == 0.30
    assert abilities["Finishing"]["npxg90"] == 0.15
    assert sum(abilities["Finishing"].values()) == pytest.approx(1)
    assert abilities["Finishing"]["npg90"] / abilities["Finishing"]["shots90"] == pytest.approx(2.5)
    for position in ["CAM", "LW_RW"]:
        scoring = registry(position)[0]["Scoring"]
        assert scoring["pos_finish"] == 0.30
        assert scoring["pos_npxg"] == 0.15
        assert sum(scoring.values()) == pytest.approx(1)
    assert abilities["Link-Up / Creation"]["key_passes90"] == 0.20
    assert abilities["Link-Up / Creation"]["pass_pct"] == 0.08
    assert abilities["Carrying / 1v1"]["take_on_pct"] == 0.20
    assert abilities["Carrying / 1v1"]["successful_take_ons90"] == 0.14
    assert ovr["Finishing"] == 0.27


def test_bad_config_is_rejected_and_checksum_changes(tmp_path):
    bad = deepcopy(CONFIG)
    bad["positions"]["CM"]["abilities"][0]["overall_weight"] = 0.9
    with pytest.raises(ValueError):
        validate_config(bad)
    bad = deepcopy(CONFIG)
    bad["positions"]["GK"]["abilities"][0]["features"] = {"invented": 1}
    with pytest.raises(ValueError):
        validate_config(bad)
    path = tmp_path / "bad.yaml"
    path.write_text("version: a\nversion: b\n")
    with pytest.raises(ValueError, match="Duplicate"):
        load_config(path)


def players_for(position, count=40):
    rng = np.random.default_rng(41)
    abilities, _, _ = registry(position)
    keys = {k for a in abilities.values() for k in a}
    rows = []
    for i in range(count):
        features = {
            k: dict(
                value=float(rng.lognormal()),
                denominator=1200 + i * 30,
                status="observed",
                provider="fixture",
                measurement_version="fixture",
            )
            for k in keys
        }
        rows.append(
            dict(
                id=f"{position}-{i}",
                position=position,
                league=["England", "Spain", "Germany", "Italy", "France"][i % 5],
                minutes=1200 + i * 30,
                features=features,
                overall=None,
            )
        )
    return rows


@pytest.mark.parametrize("position", CONFIG["positions"])
def test_all_position_models_pool_five_leagues_with_six_specific_abilities(position):
    rows = players_for(position)
    score_catalogue(rows)
    assert all(p["overall"] is not None for p in rows)
    expected = list(registry(position)[0])
    assert [a["name"] for a in rows[0]["abilities"]] == expected
    assert all(len(d["peer_ids"]) == 40 for d in rows[0]["ability_detail"].values())
    assert rows[0]["rating_position"] == position


def test_goalkeeper_cohort_cannot_be_padded_with_outfield_players():
    rows = players_for("GK", 29) + players_for("CB", 40)
    score_catalogue(rows)
    assert all(p["overall"] is None for p in rows[:29])
    assert all(p["overall"] is not None for p in rows[29:])


def test_n_a_and_partial_window_are_not_zero_filled_and_not_renormalized():
    for status in ["not_applicable_zero_attempts", "partial_window"]:
        rows = players_for("CM")
        for p in rows:
            p["features"]["pos_passpct"].update(value=None, status=status)
        score_catalogue(rows)
        assert all(p["overall"] is None for p in rows)
        assert "Retention / Circulation" not in rows[0]["ability_detail"]


def test_zero_variance_new_ability_is_withheld():
    rows = players_for("GK")
    for p in rows:
        for f in p["features"].values():
            f["value"] = 0
    score_catalogue(rows)
    assert all(p["overall"] is None for p in rows)


def test_same_provider_zero_attempts_and_signed_metric():
    na = measurement(
        "pos_dribblepct",
        {"take_ons_successful": 0, "take_ons_attempted": 0, "minutes": 1200},
        "opta",
        "https://example.test",
    )
    assert na["status"] == "not_applicable_zero_attempts" and na["value"] is None
    assert (
        measurement(
            "pos_dribblepct", {"take_ons_successful": 1, "minutes": 1200}, "opta", "https://example.test"
        )
        is None
    )
    signed = measurement(
        "pos_finish", {"np_goals_vs_xg": -4, "minutes": 1200}, "opta", "https://example.test"
    )
    assert signed["value"] == pytest.approx(-0.3)
