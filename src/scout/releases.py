import hashlib
import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from scout.contracts import DatasetRelease, Evidence, PlayerStint, Role, Team
from scout.database import ActiveRelease, PlayerRow, ReleaseRow, TeamRow
from scout.engine import RecruitmentEngine
from scout.roles import TOP_FIVE


def serialized(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def validate_release(release: DatasetRelease, players: list[PlayerStint], teams: list[Team]):
    if not players or not teams:
        raise ValueError("Release must contain teams and players")
    if len({player.id for player in players}) != len(players) or len({team.id for team in teams}) != len(teams):
        raise ValueError("Duplicate canonical identities")
    known_teams = {team.id for team in teams}
    if any(player.team_id not in known_teams or player.season != release.season for player in players):
        raise ValueError("Stints must reference a known team and the release season")
    if release.feature_version != "role-features-v1" or release.scoring_version != "evidence-ranking-v1":
        raise ValueError("Incompatible feature/scoring version")
    if release.kind == "real":
        if not release.publication_approved or not release.publication_evidence:
            raise ValueError("Public display permission must be documented")
        if int(release.season[:4]) < 2024 or set(release.leagues) != set(TOP_FIVE):
            raise ValueError("Real candidate releases require all five leagues from 2024/25")
        if set(player.league for player in players) != set(TOP_FIVE):
            raise ValueError("Declared league coverage must match actual player records")
        if set().union(*(set(player.roles) for player in players)) != set(Role):
            raise ValueError("All eight role families must be represented")
        if any(player.role_evidence in (Evidence.SYNTHETIC, Evidence.UNAVAILABLE)
               or any(metric.evidence in (Evidence.SYNTHETIC, Evidence.UNAVAILABLE) or not metric.source_field
                      for metric in player.metrics.values())
               or Evidence.SYNTHETIC in player.attribute_evidence.values() for player in players):
            raise ValueError("Real releases require sourced observations and non-synthetic role evidence")
        if any(team.style_evidence == Evidence.SYNTHETIC for team in teams):
            raise ValueError("Synthetic team evidence cannot enter a real release")
        if any(not player.metrics for player in players):
            raise ValueError("Real releases require at least one sourced metric per stint")
        for league in TOP_FIVE:
            roles = set().union(*(set(player.roles) for player in players if player.league == league and player.minutes >= 450))
            if roles != set(Role):
                raise ValueError(f"Insufficient role/exposure coverage in {league}")
    RecruitmentEngine(release, players, teams)


def write_bundle(root: Path, release: DatasetRelease, players: list[PlayerStint], teams: list[Team]):
    validate_release(release, players, teams)
    payload = {"release": release.model_dump(mode="json"),
               "players": [player.model_dump(mode="json") for player in sorted(players, key=lambda item: item.id)],
               "teams": [team.model_dump(mode="json") for team in sorted(teams, key=lambda item: item.id)]}
    content = serialized(payload)
    checksum = hashlib.sha256(content).hexdigest()
    destination = root / release.id
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "bundle.json"
    if path.exists() and path.read_bytes() != content:
        raise ValueError("Release IDs are immutable; use a new version")
    temporary = destination / "bundle.tmp"
    temporary.write_bytes(content)
    os.replace(temporary, path)
    (destination / "sha256.txt").write_text(checksum, encoding="utf-8")
    return path


def read_bundle(path: Path):
    content = path.read_bytes()
    expected = (path.parent / "sha256.txt").read_text(encoding="utf-8").strip()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("Release artifact checksum mismatch")
    payload = json.loads(content)
    release = DatasetRelease.model_validate(payload["release"])
    players = [PlayerStint.model_validate(item) for item in payload["players"]]
    teams = [Team.model_validate(item) for item in payload["teams"]]
    validate_release(release, players, teams)
    return release, players, teams, expected


def publish(engine, path: Path):
    release, players, teams, checksum = read_bundle(path)
    if release.kind == "historical":
        raise ValueError("Historical research cannot become the active candidate release")
    with Session(engine) as session, session.begin():
        existing = session.get(ReleaseRow, release.id)
        if existing and existing.checksum != checksum:
            raise ValueError("Cannot replace an immutable published release")
        if not existing:
            session.add(ReleaseRow(id=release.id, manifest=release.model_dump(mode="json"), checksum=checksum))
            session.flush()
            session.add_all([TeamRow(release_id=release.id, id=team.id, payload=team.model_dump(mode="json")) for team in teams])
            session.add_all([PlayerRow(release_id=release.id, id=player.id, team_id=player.team_id,
                                      league=player.league, payload=player.model_dump(mode="json")) for player in players])
            session.flush()
        active = session.get(ActiveRelease, "main")
        if active:
            active.release_id = release.id
        else:
            session.add(ActiveRelease(slot="main", release_id=release.id))
    return release.id


def rollback(engine, release_id: str):
    with Session(engine) as session, session.begin():
        row = session.get(ReleaseRow, release_id)
        if row is None:
            raise ValueError("Release does not exist")
        if row.manifest["kind"] == "historical":
            raise ValueError("Historical research cannot become the active candidate release")
        active = session.get(ActiveRelease, "main")
        if active is None:
            raise ValueError("No active release to roll back")
        active.release_id = release_id
