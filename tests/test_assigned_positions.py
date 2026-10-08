from copy import deepcopy

import pytest
from test_position_ratings import players_for

from scout.assigned_positions import score_assignment
from scout.formations import formations
from scout.player_catalogue import score_catalogue
from scout.position_config import CONFIG, position_id, registry


def test_assignment_changes_registry_without_changing_reference_membership():
    cm = players_for("CM")
    cb = players_for("CB")
    score_catalogue(cm + cb)
    subject = deepcopy(cm[3])
    subject["features"].update(deepcopy(cb[3]["features"]))
    subject["id"] = "out-of-position-subject"
    cm_result = score_assignment(deepcopy(subject), cm + cb, "CM")
    cb_result = score_assignment(deepcopy(subject), cm + cb, "CB")
    assert [a["name"] for a in cm_result["abilities"]] == list(registry("CM")[0])
    assert [a["name"] for a in cb_result["abilities"]] == list(registry("CB")[0])
    assert cm_result["overall"] is not None and cb_result["overall"] is not None
    assert cm_result["overall"] != cb_result["overall"]
    assert all(set(d["peer_ids"]) == {p["id"] for p in cb} for d in cb_result["ability_detail"].values())
    assert all(p["rating_position"] == "CM" for p in cm)


def test_missing_feature_mask_is_applied_to_observed_reference_features():
    peers = players_for("CM")
    score_catalogue(peers)
    subject = deepcopy(peers[0])
    subject["features"]["pos_progdist"].update(status="unrecorded_zero", value=0)
    result = score_assignment(subject, peers, "CM")
    detail = result["ability_detail"]["Ball Progression"]
    assert detail["effective_weights"]["pos_progdist"] == 0
    assert sum(detail["effective_weights"].values()) == pytest.approx(1)
    assert len(detail["peer_ids"]) == 40
    assert peers[0]["features"]["pos_progdist"]["status"] == "observed"


def test_assignment_retains_exposure_and_goalkeeper_population_boundaries():
    peers = players_for("GK", 29) + players_for("CM", 40)
    score_catalogue(peers)
    assert score_assignment(deepcopy(peers[0]), peers, "GK")["overall"] is None
    subject = deepcopy(peers[-1])
    subject["minutes"] = 899
    result = score_assignment(subject, peers, "CM")
    assert result["overall"] is None
    assert all(a["reason"] == "Below 900 minutes" for a in result["abilities"])


def test_every_preset_slot_maps_to_the_correct_scoring_registry():
    for formation in formations():
        for slot in formation.slots:
            assert position_id(slot.label) in CONFIG["positions"]
            if slot.label in ("LM", "RM"):
                assert position_id(slot.label) == "LM_RM"
