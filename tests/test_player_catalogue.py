from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from scout.api import create_app
from scout.catalogue_squad import mapped_profile, mapped_rating, mapped_snapshot
from scout.contracts import Role
from scout.database import ActiveCatalogue, Base, CataloguePlayer, CatalogueRelease, EvidenceImport, connect
from scout.player_catalogue import PlayerCatalogue, corroborates, normalized_name, score_catalogue
from scout.real_data import feature_rows
from scout.settings import Settings
from scout.striker_features import ABILITIES, FEATURES


def source(name="Cody Gakpo", minutes=1000, **totals):
    return SimpleNamespace(name=name, league="England", payload={"totals": {"minutes": minutes,
        "shots": 20, "non_penalty_goals": 3, "assists": 2, **totals}, "source_position": "Striker"})


def test_corroboration_requires_name_league_exposure_and_counts():
    assert corroborates(source(), source(minutes=1010))
    assert not corroborates(source(), source(name="Other Player"))
    assert not corroborates(source(), source(minutes=500))
    assert not corroborates(source(), source(shots=21))
    assert not corroborates(source(minutes=0), source(minutes=0))
    assert normalized_name("Alisson") == normalized_name("Alisson Becker")
    assert normalized_name("Ronald Araújo") == normalized_name("Ronald Araujo")


def test_strict_parent_scores_withhold_physicality_and_overall():
    players = []
    for i in range(40):
        raw = {f.numerator: 2 + i for f in FEATURES}
        raw.update(minutes=900 + 30 * i, shots=20 + i, shots_on_target=5 + i / 3,
                   non_penalty_goals=2 + i / 10, npxg=3 + i / 9, non_penalty_shots=19 + i,
                   passes_attempted=400 + i, passes_completed=300 + i,
                   take_ons_attempted=30 + i, take_ons_successful=10 + i,
                   duels_attempted=80 + i, duels_won=40 + i,
                   aerial_duels_attempted=30 + i, aerial_duels_won=10 + i, aerial_duels_lost=20,
                   dispossessed=None)
        features = {k: {**v, "provider": "fixture", "measurement_version": "fixture"} for k, v in feature_rows(raw).items()}
        players.append({"id": str(i), "position": "ST", "league": "England", "minutes": raw["minutes"],
                        "features": features, "abilities": [], "ability_detail": {}, "overall": None})
    score_catalogue(players)
    assert all(p["overall"] is None for p in players)
    for p in players:
        assert len(p["abilities"]) == 6
        assert next(a for a in p["abilities"] if a["name"] == "Physicality")["rating"] is None
        assert next(a for a in p["abilities"] if a["name"] == "Finishing")["rating"] is not None
    players[0].update(position="GK", abilities=[], ability_detail={})
    score_catalogue([players[0]])
    assert all(a["rating"] is None for a in players[0]["abilities"])


@pytest.fixture
def catalogue(tmp_path):
    database = connect(f"sqlite:///{tmp_path / 'catalogue.db'}")
    Base.metadata.create_all(database)
    features = {key: {**f, "key": key, "label": key, "provider": "opta", "source_url": "https://dataviz.theanalyst.com/test",
                      "measurement_version": "fixture"} for key, f in feature_rows({"minutes": 1000, "shots": 20}).items()}
    payload = {"id": "gakpo", "name": "Cody Gakpo", "short_name": "Gakpo", "league": "England", "team": "Liverpool FC",
               "position": "ST", "minutes": 1000, "overall": None, "portrait_url": None, "portrait_source": None,
               "mapping_status": "corroborated", "numerical_features": 1, "supported_features": 1,
               "rating_status": "strict_observed_model", "abilities": [{"name": name, "abbreviation": name[:3],
                    "rating": None, "available": 0, "defined": len(weights)} for name, weights in ABILITIES.items()],
               "features": features, "ability_detail": {}, "sources": [], "other_stints": []}
    with Session(database) as s, s.begin():
        s.add(EvidenceImport(id="evidence", manifest={}))
        s.flush()
        s.add(CatalogueRelease(id="catalogue", import_id="evidence", manifest={"total": 1, "squad_mappings": {
            "lfc-cody-gakpo": "gakpo"}, "created_at": "2026-10-06T00:00:00Z"}))
        s.flush()
        s.add(CataloguePlayer(catalogue_id="catalogue", id="gakpo", name="Cody Gakpo", league="England",
                              team="Liverpool FC", position="ST", overall=None, payload=payload))
        s.add(ActiveCatalogue(slot="local", catalogue_id="catalogue"))
    yield PlayerCatalogue(database)
    database.dispose()


def test_squad_mapping_has_no_synthetic_fallback(catalogue):
    squad = mapped_snapshot(catalogue)
    assert squad.team == "Liverpool" and squad.season == "2026/27"
    gakpo = next(p for p in squad.players if p.id == "lfc-cody-gakpo")
    assert gakpo.attribute_evidence == "observed"
    assert next(s for s in gakpo.skills if s.key == "shots90").raw_value == 1.8
    isak = next(p for p in squad.players if p.id == "lfc-alexander-isak")
    assert isak.attribute_evidence == "unavailable" and isak.skills == []
    assert mapped_rating(isak, Role.ST, catalogue).score is None
    assert mapped_profile(isak.id, catalogue).evidence == "unavailable"


def test_unknown_position_does_not_break_squad_evaluation(catalogue):
    with Session(catalogue.database) as s, s.begin():
        row = s.get(CataloguePlayer, ('catalogue','gakpo'))
        row.payload = {**row.payload,'position':'Unknown','defined_features':0,'numerical_features':0}
    squad = mapped_snapshot(catalogue)
    player = next(p for p in squad.players if p.id=='lfc-cody-gakpo')
    rating = mapped_rating(player,Role.ST,catalogue)
    assert rating.score is None and rating.coverage==0


def test_catalogue_filters_and_private_api(catalogue):
    assert catalogue.search(league="England", team="Liverpool FC", position="ST")["total"] == 1
    assert catalogue.search(minimum=1)["total"] == 0
    assert catalogue.search(rating_status="unrated")["total"] == 1
    assert catalogue.search(name="% OR 1=1")["total"] == 0
    assert catalogue.detail("gakpo")["features"][0]["provider"] == "opta"
    with TestClient(create_app(Settings(database_url=str(catalogue.database.url), serve_private_evidence=True))) as c:
        assert c.get("/catalogue").status_code == 200
        assert c.get("/catalogue/players?minimum=90&maximum=10").status_code == 422
        assert c.get("/catalogue/players?limit=61").status_code == 422
        assert c.get("/catalogue/players/gakpo/abilities").json()["evidence"] == "observed"
        snapshot = c.get("/squads/liverpool-men").json()
        assert len(snapshot["players"]) == 31
        assert c.post("/squads/liverpool-men/evaluate", json=snapshot["default_lineup"]).json()["team_rating"] is None
