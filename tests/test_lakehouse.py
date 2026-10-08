import json
import os

import pyarrow.parquet as parquet
import pytest

from scout.evaluation import brief_suite, evaluate
from scout.lakehouse import build_local, build_spark


def test_local_pipeline_writes_distinct_layers(tmp_path, cohort):
    release, players, teams = cohort
    result = build_local(tmp_path, release, players, teams)
    assert result["players"] == 240
    gold = parquet.read_table(tmp_path / release.id / "gold/role_profiles.parquet").to_pylist()
    assert {row["role"] for row in gold} == {role.value for player in players for role in player.roles}
    assert all(json.loads(row["profile_json"])["coverage"] <= 100 for row in gold)


def test_48_briefs_have_heldout_split(recruitment):
    cases = brief_suite(recruitment)
    assert len(cases) == 48
    assert sum(case["split"] == "test" for case in cases) == 32
    results = evaluate(recruitment, cases)
    assert all(case["ndcg_at_10"] is None for case in results["cases"])


@pytest.mark.skipif(os.getenv("SCOUT_TEST_SPARK") != "1", reason="Requires the Spark profile and Java 17")
def test_spark_matches_local_features(tmp_path, cohort):
    from pyspark.sql import SparkSession
    release, players, teams = cohort
    build_local(tmp_path / "local", release, players, teams)
    build_spark(tmp_path / "spark", release, players, teams)
    spark = SparkSession.getActiveSession()
    gold = spark.read.format("delta").load(str(tmp_path / "spark" / release.id / "gold_role_profiles")).collect()
    local = parquet.read_table(tmp_path / "local" / release.id / "gold/role_profiles.parquet").to_pylist()
    assert {row.stint_id: json.loads(row.profile_json) for row in gold} == {row["stint_id"]: json.loads(row["profile_json"]) for row in local}
