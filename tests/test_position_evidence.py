import json
import sqlite3

from scout.position_evidence import MasterFeatures


def test_keeper_raw_aggregation_deduplicates_and_weights_percentages(tmp_path):
    path = tmp_path / "master.sqlite"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE players(master_row TEXT,league TEXT,names_json TEXT,sources_json TEXT)")
    c.execute(
        "CREATE TABLE observations(provider TEXT,player_id TEXT,league TEXT,season TEXT,master_row TEXT,field TEXT,scope TEXT,sample TEXT,status TEXT,value_json TEXT)"
    )
    c.execute("INSERT INTO players VALUES(?,?,?,?)", ("gk", "England", '["Keeper"]', '["pitchapi:p1"]'))

    def add(field, sample, value, scope="appearance", status="numeric"):
        c.execute(
            "INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("pitchapi", "p1", "England", "2025/26", "gk", field, scope, sample, status, json.dumps(value)),
        )

    add("identity.squad_position_detailed", "id", "Goalkeeper", "identity", "categorical")
    for sample, minutes, attempts, accuracy in [("m1", 60, 10, 60), ("m2", 30, 30, 80)]:
        add("stats.minutes_played.value", sample, minutes)
        add("stats.minutes_played.value", sample, minutes)  # repeated snapshot is not another appearance
        add("advanced.goalkeeping.distributions", sample, attempts)
        add("advanced.goalkeeping.distribution_accuracy", sample, accuracy)
        add("advanced.goalkeeping.claims_won", sample, 0)  # recorded zero remains present
    c.commit()
    c.close()
    bundle = MasterFeatures(path).keeper_appearances()["gk"][0][1]
    assert bundle["minutes"] == 90
    assert bundle["advanced.goalkeeping.distributions"] == 40
    assert bundle["advanced.goalkeeping.distribution_accuracy"] == 75
    assert bundle["advanced.goalkeeping.claims_won"] == 0
