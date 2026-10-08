from scout.historical import prepare_shots


def test_shots_exclude_shootouts_quarantine_missing_geometry_and_preserve_dates():
    shot = {"id": "valid", "type": {"name": "Shot"}, "period": 1, "location": [110, 40],
            "shot": {"outcome": {"name": "Goal"}, "body_part": {"name": "Head"}}}
    invalid = {**shot, "id": "missing", "location": None}
    shootout = {**shot, "id": "shootout", "period": 5}
    shots, quarantine = prepare_shots([{"match_id": 1, "match_date": "2023-01-01"}], {1: [shot, invalid, shootout, shot]})
    assert len(shots) == 1
    assert shots[0]["distance"] == 10
    assert shots[0]["header"] == shots[0]["goal"] == 1
    assert shots[0]["match_date"] == "2023-01-01"
    assert len(quarantine) == 2
