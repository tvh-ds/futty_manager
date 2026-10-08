import hashlib
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from scout.api import create_app
from scout.database import (
    ActiveEvidence,
    ActiveRelease,
    Base,
    EvidenceImport,
    ReleaseRow,
    SourceFeature,
    SourceRecord,
    connect,
)
from scout.real_data import LEAGUES, RealDataEngine, feature_rows, import_evidence, prepare
from scout.settings import Settings


@pytest.fixture
def evidence_sources(tmp_path):
    roots = {p: tmp_path / p for p in ("opta", "pitchapi", "understat")}
    for provider, root in roots.items():
        root.mkdir()
        collection, report = [], {"leagues": {}}
        for league in sorted(LEAGUES):
            row = {"provider_player_id": "123", "name": "Test Player", "competition": league,
                   "season": "2025/26", "retrieved_at": "2026-10-06T00:00:00+00:00",
                   "source_url": {"opta": "https://dataviz.theanalyst.com/test",
                                  "pitchapi": "https://api.pitchapi.dev/v1/test",
                                  "understat": "https://understat.com/test"}[provider],
                   "totals": {"minutes": 900, "shots": 10, "non_penalty_shots": 8,
                              "non_penalty_goals": 2, "npxg": 1.7,
                              "aerial_duels_won": 1, "aerial_duels_attempted": 2},
                   "features": {"shots90": 999999}}
            if provider == "opta":
                row["provider_team_id"] = "team123"
            collection.append(row)
            if provider != "pitchapi":
                folder = root / league
                folder.mkdir()
                bronze = json.dumps({"attack": {"overall": []}}).encode()
                (folder / "bronze.json").write_bytes(bronze)
                (folder / "measurements.json").write_text(json.dumps([row]), encoding="utf-8")
                report["leagues"][league] = {"snapshot_sha256": hashlib.sha256(bronze).hexdigest()}
        if provider == "pitchapi":
            (root / "measurements.json").write_text(json.dumps(collection), encoding="utf-8")
        (root / "coverage.json").write_text(json.dumps(report), encoding="utf-8")
    return roots


@pytest.fixture
def evidence_database(tmp_path):
    db = connect(f"sqlite:///{tmp_path / 'evidence.db'}")
    Base.metadata.create_all(db)
    yield db
    db.dispose()


def test_calculations_missingness_and_zero_attempts():
    result = feature_rows({"minutes": 900, "shots": 0, "shots_on_target": 0,
                           "non_penalty_goals": 2, "npxg": 3})
    assert result["finishing_delta90"]["value"] == pytest.approx(-.1)
    assert result["sot_pct"]["status"] == "not_applicable_zero_attempts"
    assert result["sot_pct"]["value"] is None
    assert result["fouls_won90"]["status"] == "missing_measurement"
    assert feature_rows({"minutes": 0, "shots": 0})["shots90"]["status"] == "zero_exposure"
    assert feature_rows({"aerial_duels_won": 2, "aerial_duels_attempted": 4})["aerial_pct"]["value"] == 50


@pytest.mark.parametrize("raw", [
    {"minutes": True}, {"shots": float("inf")}, {"shots": -1},
    {"shots": 0, "shots_on_target": 1}, {"shots": 2, "shots_on_target": 3},
])
def test_invalid_measurements_rejected(raw):
    with pytest.raises(ValueError):
        feature_rows(raw)


def test_idempotent_import_and_existing_release_preserved(evidence_sources, evidence_database):
    with Session(evidence_database) as s, s.begin():
        s.add(ReleaseRow(id="existing", manifest={}, checksum="0" * 64))
        s.flush()
        s.add(ActiveRelease(slot="main", release_id="existing"))
    first = import_evidence(evidence_database, evidence_sources)
    second = import_evidence(evidence_database, evidence_sources)
    assert first["id"] == second["id"]
    assert first["records"] == 15
    with Session(evidence_database) as s:
        assert s.scalar(select(func.count()).select_from(SourceRecord)) == 15
        assert s.scalar(select(func.count()).select_from(SourceFeature)) == 15 * 36
        assert s.get(ActiveRelease, "main").release_id == "existing"
    engine = RealDataEngine(evidence_database)
    item = engine.catalogue(provider="pitchapi")["items"][0]
    profile = engine.profile(item["id"])
    assert profile["features"]["shots90"]["value"] == 1  # Recomputed, not trusted cached 999999.
    assert profile["overall_rating"] is None
    assert not profile["publication_approved"]
    assert engine.catalogue(name="% ' OR 1=1 --")["total_source_records"] == 0


def test_reviewed_combination_retains_source_denominators(evidence_sources, evidence_database, tmp_path):
    _, records, _, _ = prepare(evidence_sources)
    selected = [r for r in records.values() if r["league"] == "England"]
    links = [{"record_id": r["id"], "canonical_id": "verified-player", "reviewer": "Test reviewer",
              "evidence": "Confirmed source IDs against independently verified identity facts."} for r in selected]
    path = tmp_path / "links.json"
    path.write_text(json.dumps(links))
    import_evidence(evidence_database, evidence_sources, path)
    profile = RealDataEngine(evidence_database).profile("verified-player")
    assert profile["identity_status"] == "reviewed"
    assert profile["features"]["shots90"]["provider"] == "opta"
    assert profile["features"]["shots90"]["denominator"] == 900
    assert len(profile["features"]["shots90"]["alternatives"]) == 2
    assert profile["features"]["fouls_won90"]["status"] == "missing_measurement"


def test_failed_import_rolls_back(evidence_sources, evidence_database, monkeypatch):
    class FailingSession(Session):
        def merge(self, *args, **kwargs):
            raise RuntimeError("simulated activation failure")
    monkeypatch.setattr("scout.real_data.Session", FailingSession)
    with pytest.raises(RuntimeError, match="activation"):
        import_evidence(evidence_database, evidence_sources)
    with Session(evidence_database) as s:
        assert s.scalar(select(func.count()).select_from(EvidenceImport)) == 0
        assert s.scalar(select(func.count()).select_from(SourceRecord)) == 0
        assert s.get(ActiveEvidence, "local") is None


def test_bronze_tamper_refused(evidence_sources):
    path = evidence_sources["opta"] / "England" / "bronze.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        prepare(evidence_sources)


def test_api_opt_in_and_filters(evidence_sources, evidence_database):
    import_evidence(evidence_database, evidence_sources)
    url = str(evidence_database.url)
    with TestClient(create_app(Settings(database_url=url, serve_private_evidence=True))) as client:
        response = client.get("/data/players", params={"provider": "opta", "league": "England"})
        assert response.status_code == 200
        assert response.json()["total_source_records"] == 1
        identity = response.json()["items"][0]["id"]
        assert client.get(f"/data/players/{identity}/features").json()["numeric_features"] > 0
        assert client.get("/data/players", params={"provider": "not-a-provider"}).status_code == 422
        assert client.get("/data/players", params={"limit": 101}).status_code == 422
    with TestClient(create_app(Settings(database_url=url, serve_private_evidence=False))) as client:
        assert client.get("/data/players").status_code == 404


def test_fresh_alembic_migration(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("SCOUT_DATABASE_URL", url)
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    db = connect(url)
    assert set(Base.metadata.tables).issubset(inspect(db).get_table_names())
    db.dispose()
