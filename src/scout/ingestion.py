import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

from scout.contracts import Evidence, MetricObservation, PlayerStint, Role, Team
from scout.roles import API_LEAGUES, TOP_FIVE


class QuotaExhausted(RuntimeError):
    pass


class ApiFootball:
    def __init__(self, key: str, root: Path, daily_budget: int = 90, client: httpx.Client | None = None):
        if not key:
            raise ValueError("Set SCOUT_API_FOOTBALL_KEY in the environment; never paste keys into chat")
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.daily_budget = daily_budget
        self.client = client or httpx.Client(base_url="https://v3.football.api-sports.io", timeout=30,
                                           headers={"x-apisports-key": key}, follow_redirects=False)
        self.state_path = root / "checkpoint.json"

    def _state(self):
        state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        day = datetime.now(UTC).date().isoformat()
        if state.get("day") != day:
            state = {"day": day, "used": 0, "completed": state.get("completed", {})}
        return state

    def _save(self, state):
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        temporary.replace(self.state_path)

    def get(self, endpoint: str, params: dict, refresh: bool = False):
        if endpoint not in {"status", "leagues", "teams", "players", "fixtures"}:
            raise ValueError("Unsupported provider endpoint")
        request_id = hashlib.sha256(json.dumps([endpoint, params], sort_keys=True).encode()).hexdigest()
        state = self._state()
        cached = state["completed"].get(request_id)
        if cached and not refresh:
            path = self.root / cached
            return json.loads(path.read_text(encoding="utf-8"))["payload"]
        for attempt in range(3):
            state = self._state()
            if state["used"] >= self.daily_budget:
                raise QuotaExhausted("Daily provider budget exhausted; checkpoint retained for tomorrow")
            state["used"] += 1
            self._save(state)
            response = self.client.get(f"/{endpoint}", params=params)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    raise QuotaExhausted("Provider quota/service unavailable; retry later")
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            if len(response.content) > 10_000_000:
                raise ValueError("Provider response exceeds snapshot limit")
            payload = response.json()
            if payload.get("errors"):
                raise ValueError("Provider rejected the request; inspect account entitlements without logging credentials")
            checksum = hashlib.sha256(response.content).hexdigest()
            name = f"{request_id}-{checksum}.json"
            snapshot = {"endpoint": endpoint, "params": params, "retrieved_at": datetime.now(UTC).isoformat(),
                        "checksum": checksum, "payload": payload}
            (self.root / name).write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            state = self._state()
            state["completed"][request_id] = name
            self._save(state)
            return payload
        raise RuntimeError("Provider retry exhausted")

    def probe(self, season: int):
        report = {"season": f"{season}/{str(season + 1)[-2:]}", "provider": "API-Football",
                  "publication_status": "unverified", "candidate_release_approved": False,
                  "checked_at": datetime.now(UTC).isoformat(), "leagues": {}}
        for league, league_id in API_LEAGUES.items():
            try:
                payload = self.get("leagues", {"id": league_id, "season": season})
                records = payload.get("response", [])
                seasons = [item for record in records for item in record.get("seasons", []) if item.get("year") == season]
                sample = self.get("players", {"league": league_id, "season": season, "page": 1})
                coverage = seasons[0].get("coverage", {}) if seasons else {}
                report["leagues"][league] = {"season_accessible": bool(seasons and sample.get("response")),
                    "coverage": coverage, "sample_player_count": len(sample.get("response", [])),
                    "player_pages": sample.get("paging", {}).get("total", 0),
                    "role_resolution": "Detailed outfield roles require reviewed overrides; broad provider positions are insufficient",
                    "rich_attributes": "Footedness, tracking and pressure reception not established by this probe"}
            except (httpx.HTTPError, ValueError, QuotaExhausted) as error:
                report["leagues"][league] = {"season_accessible": False, "failure": type(error).__name__}
        report["technical_season_access"] = season >= 2024 and all(
            report["leagues"][league].get("season_accessible", False) for league in TOP_FIVE)
        return report

    def ingest(self, season: int):
        for league_id in API_LEAGUES.values():
            self.get("teams", {"league": league_id, "season": season})
            self.get("fixtures", {"league": league_id, "season": season})
            page = 1
            while True:
                response = self.get("players", {"league": league_id, "season": season, "page": page})
                if page >= response.get("paging", {}).get("total", 1):
                    break
                page += 1


def canonicalize(root: Path, season: int, role_overrides: dict[str, list[str]]):
    players, teams, quarantine = {}, {}, []
    season_label = f"{season}/{str(season + 1)[-2:]}"
    reverse_leagues = {value: key for key, value in API_LEAGUES.items()}
    snapshots = []
    for path in root.glob("*.json"):
        if path.name == "checkpoint.json":
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("params", {}).get("season") == season:
            snapshots.append(document)
    for snapshot in sorted(snapshots, key=lambda item: item["retrieved_at"]):
        league = reverse_leagues.get(snapshot["params"].get("league"))
        if not league:
            continue
        if snapshot["endpoint"] == "teams":
            for item in snapshot["payload"].get("response", []):
                team = item.get("team", {})
                teams[str(team["id"])] = Team(id=str(team["id"]), name=team["name"], league=league)
        elif snapshot["endpoint"] == "players":
            for record in snapshot["payload"].get("response", []):
                person = record.get("player", {})
                for stats in record.get("statistics", []):
                    if stats.get("league", {}).get("id") != API_LEAGUES[league] or stats.get("league", {}).get("season") != season:
                        continue
                    identity = f"{person.get('id')}-{stats.get('team', {}).get('id')}-{season}"
                    try:
                        games = stats.get("games", {})
                        minutes = games.get("minutes")
                        if not minutes or minutes <= 0:
                            raise ValueError("No minutes denominator")
                        roles = role_overrides.get(str(person["id"]))
                        evidence = Evidence.MANUAL
                        if not roles and games.get("position") == "Goalkeeper":
                            roles, evidence = [Role.GK.value], Evidence.OBSERVED
                        if not roles:
                            raise ValueError("Detailed role unresolved; add reviewed role override")
                        metrics = {}
                        fields = {"tackles_p90": ("tackles", "total"), "interceptions_p90": ("tackles", "interceptions"),
                                  "goals_p90": ("goals", "total"), "assists_p90": ("goals", "assists"),
                                  "shots_p90": ("shots", "total"), "dribbles_p90": ("dribbles", "success")}
                        for key, (category, name) in fields.items():
                            count = stats.get(category, {}).get(name)
                            if count is not None:
                                metrics[key] = MetricObservation(value=count * 90 / minutes, numerator=count,
                                                                source_field=f"{category}.{name}")
                        saves = stats.get("goals", {}).get("saves")
                        conceded = stats.get("goals", {}).get("conceded")
                        if roles == [Role.GK.value] and saves is not None and conceded is not None and saves + conceded > 0:
                            metrics["save_pct"] = MetricObservation(value=saves / (saves + conceded), unit="ratio",
                                numerator=saves, denominator=saves + conceded, source_field="goals.saves / (goals.saves + goals.conceded)")
                        players[identity] = PlayerStint(id=identity, player_id=str(person["id"]), name=person["name"],
                            team_id=str(stats["team"]["id"]), league=league, season=season_label,
                            age=None, roles=roles, role_evidence=evidence, minutes=minutes, metrics=metrics)
                    except (ValidationError, ValueError, KeyError, TypeError) as error:
                        quarantine.append({"identity": identity, "reason": str(error), "snapshot": snapshot["checksum"]})
    return list(players.values()), list(teams.values()), quarantine
