import json
from pathlib import Path

import duckdb
import pyarrow as arrow
import pyarrow.parquet as parquet

from scout.engine import RecruitmentEngine


def rows_for_layers(release, players, teams):
    engine = RecruitmentEngine(release, players, teams)
    silver = [{"stint_id": player.id, "player_id": player.player_id, "team_id": player.team_id,
               "league": player.league, "season": player.season, "minutes": player.minutes,
               "payload": player.model_dump_json()} for player in players]
    gold = [{"stint_id": stint_id, "role": role.value, "coverage": profile.coverage,
             "feature_version": release.feature_version, "release_id": release.id,
             "profile_json": profile.model_dump_json()} for (stint_id, role), profile in engine.profiles.items()]
    team_rows = [{"team_id": team.id, "league": team.league, "payload": team.model_dump_json()} for team in teams]
    return silver, gold, team_rows


def build_local(root: Path, release, players, teams):
    silver, gold, team_rows = rows_for_layers(release, players, teams)
    for layer, name, rows in (("bronze", "canonical_input", [{"release_json": release.model_dump_json(),
            "players_json": json.dumps([player.model_dump(mode="json") for player in players]),
            "teams_json": json.dumps([team.model_dump(mode="json") for team in teams])}]),
            ("silver", "player_stints", silver), ("silver", "teams", team_rows), ("gold", "role_profiles", gold)):
        folder = root / release.id / layer
        folder.mkdir(parents=True, exist_ok=True)
        parquet.write_table(arrow.Table.from_pylist(rows), folder / f"{name}.parquet")
    with duckdb.connect() as connection:
        result = connection.execute("SELECT COUNT(*), COUNT(DISTINCT stint_id) FROM read_parquet(?)",
                                    [str(root / release.id / "silver/player_stints.parquet")]).fetchone()
    if result != (len(players), len(players)):
        raise ValueError("Silver uniqueness validation failed")
    return {"engine": "arrow-duckdb", "players": len(players), "profiles": len(gold),
            "release_id": release.id}


def build_spark(root: Path, release, players, teams, spark=None, catalog: str | None = None):
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as functions
    if spark is None:
        from delta import configure_spark_with_delta_pip
        builder = SparkSession.builder.master("local[2]").appName("Scout").config(
            "spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension").config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        builder = builder.config("spark.jars.ivy", str(Path(".cache/ivy").resolve())).config(
            "spark.local.dir", str(Path(".cache/spark").resolve())).config("spark.ui.enabled", "false")
        spark = configure_spark_with_delta_pip(builder).getOrCreate()
    silver, gold, teams_rows = rows_for_layers(release, players, teams)
    datasets = {"silver_player_stints": silver, "silver_teams": teams_rows, "gold_role_profiles": gold,
                "bronze_input": [{"release_json": release.model_dump_json(),
                                  "players_json": json.dumps([player.model_dump(mode="json") for player in players]),
                                  "teams_json": json.dumps([team.model_dump(mode="json") for team in teams])}]}
    for name, rows in datasets.items():
        frame = spark.createDataFrame(rows)
        if name == "silver_player_stints":
            duplicates = frame.groupBy("stint_id").count().filter(functions.col("count") > 1).count()
            if duplicates:
                raise ValueError("Duplicate silver stints")
            frame.createOrReplaceTempView("scout_stints")
            spark.sql("SELECT league, season, SUM(minutes) AS exposure_minutes FROM scout_stints GROUP BY league, season").createOrReplaceTempView("scout_coverage")
        if catalog:
            import re
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", catalog):
                raise ValueError("Catalog target must be catalog.schema with safe identifiers")
            frame.write.format("delta").mode("overwrite").saveAsTable(f"{catalog}.{name}")
        else:
            frame.write.format("delta").mode("overwrite").save(str(root / release.id / name))
    return {"engine": "spark-delta", "players": len(players), "profiles": len(gold), "release_id": release.id}
