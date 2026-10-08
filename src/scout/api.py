import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from scout.boundaries import SECURITY_HEADERS, RequestBoundary
from scout.briefs import interpret
from scout.catalogue_contracts import PlayerCatalogueDetail, PlayerCatalogueMetadata, PlayerCataloguePage
from scout.contracts import (
    Contract,
    DatasetIndex,
    InterpretedBrief,
    PlayerDetail,
    PlayerStint,
    RecommendationResult,
    RecruitmentBrief,
    Role,
    RoleSpecification,
    ScenarioRequest,
    ScenarioResult,
    Team,
    TeamDetail,
)
from scout.database import ReleaseRow, connect, load_active
from scout.engine import RecruitmentEngine
from scout.formations import formations
from scout.roles import METRIC_LABELS, ROLE_SPECS
from scout.settings import Settings
from scout.squad_contracts import (
    DashboardEvaluation,
    FormationChange,
    FormationDefinition,
    LineupState,
    PlayerRating,
    SquadSnapshot,
    SquadSummary,
)
from scout.squads import SQUAD_ID, change_formation, evaluate_lineup, player_rating, squad_snapshot

logger = logging.getLogger("scout.api")


class InterpretRequest(Contract):
    text: str = Field(min_length=3, max_length=3000)


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    database = connect(settings.database_url)
    from scout.player_catalogue import PlayerCatalogue
    catalogue = PlayerCatalogue(database) if settings.serve_private_evidence else None

    def current_snapshot():
        if catalogue:
            from scout.catalogue_squad import mapped_snapshot
            try:
                return mapped_snapshot(catalogue)
            except LookupError:
                raise HTTPException(503, "Real player catalogue is not ready; build it locally first") from None
        return squad_snapshot()

    def current_rating(player, role, multiplier):
        if catalogue:
            from scout.catalogue_squad import mapped_rating
            return mapped_rating(player, role, catalogue)
        return player_rating(player, role, multiplier)

    @asynccontextmanager
    async def lifespan(app):
        import os
        if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
            from azure.monitor.opentelemetry import configure_azure_monitor
            configure_azure_monitor()
        app.state.database = database
        app.state.engine = None
        app.state.release_id = None
        yield
        database.dispose()

    application = FastAPI(title="Scout Recruitment API", version="1.0.0", lifespan=lifespan)
    application.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                               allow_methods=["GET", "POST"], allow_headers=["Content-Type"], allow_credentials=False)
    buckets = defaultdict(deque)
    semaphore = asyncio.Semaphore(1)

    @application.middleware("http")
    async def boundaries(request: Request, call_next):
        started = time.monotonic()
        address = request.client.host if request.client else "unknown"
        if request.method == "POST":
            bucket = buckets[address]
            while bucket and bucket[0] < started - 60:
                bucket.popleft()
            if len(bucket) >= settings.request_limit:
                return JSONResponse({"detail": "Request limit reached; try again shortly"}, status_code=429,
                                    headers={"Retry-After": "60"})
            bucket.append(started)
            if len(buckets) > 10000:
                for key in list(buckets):
                    if not buckets[key] or buckets[key][-1] < started - 60:
                        del buckets[key]
        response = await call_next(request)
        response.headers["Server-Timing"] = f"api;dur={(time.monotonic() - started) * 1000:.1f}"
        return response

    @application.exception_handler(Exception)
    async def unexpected_error(request, error):
        logger.error("request_failed", extra={"path": request.url.path, "error_type": type(error).__name__})
        return JSONResponse({"detail": "Service temporarily unavailable"}, status_code=503, headers=SECURITY_HEADERS)

    def engine(request: Request):
        try:
            with Session(database) as session:
                from scout.database import ActiveRelease
                active = session.get(ActiveRelease, "main")
                release_id = active.release_id if active else None
            if not release_id:
                raise HTTPException(503, "No validated release is active. Run the data pipeline and publish a release.")
            if request.app.state.release_id != release_id:
                release, players, teams = load_active(database)
                if release.kind == "synthetic" and not settings.allow_synthetic:
                    raise HTTPException(503, "A real-data release is required for this deployment")
                request.app.state.engine = RecruitmentEngine(release, players, teams)
                request.app.state.release_id = release_id
            return request.app.state.engine
        except HTTPException:
            raise
        except Exception as error:
            logger.error("release_load_failed", extra={"error_type": type(error).__name__})
            raise HTTPException(503, "Validated data is unavailable") from None

    @application.get("/health/live")
    def live():
        return {"status": "alive"}

    @application.get("/health/ready")
    def ready(recruitment=Depends(engine)):
        return {"status": "ready", "release_id": recruitment.release.id, "kind": recruitment.release.kind}

    @application.get("/datasets", response_model=DatasetIndex)
    def datasets(recruitment=Depends(engine)):
        with Session(database) as session:
            from sqlalchemy import select
            releases = session.scalars(select(ReleaseRow).order_by(ReleaseRow.created_at.desc())).all()
        return {"active": recruitment.release, "releases": [row.manifest for row in releases]}

    @application.get("/roles", response_model=list[RoleSpecification])
    def roles():
        return [{"id": role.value, "label": spec.label, "style_metrics": list(spec.style),
                 "quality_metrics": spec.quality, "metric_labels": METRIC_LABELS} for role, spec in ROLE_SPECS.items()]

    @application.get("/teams", response_model=list[Team])
    def teams(recruitment=Depends(engine)):
        return list(recruitment.teams.values())

    @application.get("/teams/{team_id}", response_model=TeamDetail)
    def team(team_id: str, recruitment=Depends(engine)):
        if team_id not in recruitment.teams:
            raise HTTPException(404, "Team not found")
        return {"team": recruitment.teams[team_id], "players": [player for player in recruitment.players.values() if player.team_id == team_id], "release": recruitment.release}

    @application.get("/players", response_model=list[PlayerStint])
    def players(role: Role | None = None, query: str = Query(default="", max_length=100),
                limit: int = Query(default=100, ge=1, le=300), recruitment=Depends(engine)):
        return [player for player in recruitment.players.values()
                if (role is None or role in player.roles) and query.casefold() in player.name.casefold()][:limit]

    @application.get("/players/{player_id}", response_model=PlayerDetail)
    def player(player_id: str, recruitment=Depends(engine)):
        if player_id not in recruitment.players:
            raise HTTPException(404, "Player not found")
        return {"player": recruitment.players[player_id], "profiles": [recruitment.profile(player_id, role) for role in recruitment.players[player_id].roles], "release": recruitment.release}

    @application.post("/recommendations", response_model=RecommendationResult)
    def recommendations(brief: RecruitmentBrief, recruitment=Depends(engine)):
        try:
            results = recruitment.recommend(brief)
        except KeyError:
            raise HTTPException(404, "Team or replacement player not found") from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return {"release": recruitment.release, "brief": brief, "recommendations": results,
                "limitations": ["Statistical quality is a role/league-relative proxy", "Missing ranking components are omitted and available weights renormalized", "Overall score is reduced when role evidence is sparse"]}

    @application.post("/briefs/interpret", response_model=InterpretedBrief)
    async def interpret_brief(body: InterpretRequest):
        async with semaphore:
            return await interpret(body.text, settings.ollama_enabled, settings.ollama_model)

    @application.post("/scenarios/simulate", response_model=ScenarioResult)
    def simulate(body: ScenarioRequest, recruitment=Depends(engine)):
        try:
            return recruitment.simulate(body)
        except KeyError:
            raise HTTPException(404, "Scenario player or team not found") from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @application.get("/squads", response_model=list[SquadSummary])
    def squads():
        return [SquadSummary.model_validate(squad_snapshot().model_dump(include=set(SquadSummary.model_fields)))]

    @application.get("/squads/{squad_id}", response_model=SquadSnapshot)
    def squad(squad_id: str):
        if squad_id != SQUAD_ID:
            raise HTTPException(404, "Squad not available")
        return current_snapshot()

    @application.get("/formations", response_model=list[FormationDefinition])
    def formation_catalog():
        return formations()

    from scout.ability_contracts import AbilityProfile

    @application.get("/squads/{squad_id}/players/{player_id}/abilities", response_model=AbilityProfile)
    def striker_abilities(squad_id: str, player_id: str, position: str | None = Query(None, max_length=10)):
        from scout.striker_profiles import player_profile
        if squad_id != SQUAD_ID:
            raise HTTPException(404, "Squad not available")
        player = next((p for p in squad_snapshot().players if p.id == player_id), None)
        if player is None:
            raise HTTPException(404, "Player not found")
        if not catalogue and Role.ST not in player.roles:
            raise HTTPException(422, "Rigorous ability registry is currently configured only for striker planning roles")
        try:
            if catalogue:
                from scout.catalogue_squad import mapped_profile
                from scout.position_config import CONFIG, position_id
                assigned = position_id(position) if position else None
                if assigned and (assigned not in CONFIG['positions'] or (assigned == 'GK') != (Role.GK in player.roles)):
                    raise HTTPException(422, 'Invalid assignment or goalkeeper/outfield exchange')
                return mapped_profile(player_id, catalogue, assigned)
            return player_profile(player_id)
        except (ValueError, OSError, KeyError):
            raise HTTPException(503, "Position release could not be verified; evidence has not been replaced") from None

    @application.get("/squads/{squad_id}/position-ratings", response_model=dict[str, PlayerRating])
    def squad_position_ratings(squad_id: str, role: Role, multiplier: float = Query(1.5, ge=1, le=3, multiple_of=0.1), position: str | None = Query(None, max_length=10)):
        if squad_id != SQUAD_ID:
            raise HTTPException(404, "Squad not available")
        from scout.catalogue_squad import mapped_rating
        from scout.position_config import CONFIG, position_id
        assigned = position_id(position or role.value)
        if assigned not in CONFIG['positions'] or (assigned == 'GK') != (role == Role.GK):
            raise HTTPException(422, 'Invalid assignment or goalkeeper/outfield exchange')
        return {player.id: mapped_rating(player, role, catalogue, assigned) if catalogue else current_rating(player, role, multiplier) for player in current_snapshot().players
                if (role == Role.GK) == (Role.GK in player.roles)}

    @application.post("/squads/{squad_id}/evaluate", response_model=DashboardEvaluation)
    def squad_evaluation(squad_id: str, body: LineupState):
        if squad_id != SQUAD_ID:
            raise HTTPException(404, "Squad not available")
        try:
            from scout.catalogue_squad import mapped_rating
            assigned_rating = (lambda player, role, position, multiplier: mapped_rating(player, role, catalogue, position)) if catalogue else None
            result = evaluate_lineup(body, current_rating, current_snapshot(), assigned_rating)
            if catalogue:
                result.warnings = ["Observed 2025/26 attributes; unavailable ratings stay unscored. Chemistry remains demonstration data."]
            return result
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @application.post("/squads/{squad_id}/formation", response_model=LineupState)
    def squad_formation(squad_id: str, body: FormationChange):
        if squad_id != SQUAD_ID:
            raise HTTPException(404, "Squad not available")
        try:
            return change_formation(body.lineup, body.formation_id)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    # Explicit opt-in keeps privately imported Understat evidence out of the
    # default public deployment. Enable only on the local development API.
    if settings.serve_private_evidence:
        from typing import Literal

        from scout.real_data import RealDataEngine
        evidence = RealDataEngine(database)

        @application.get("/catalogue", response_model=PlayerCatalogueMetadata)
        def player_catalogue_metadata():
            try:
                return catalogue.metadata()
            except LookupError:
                raise HTTPException(503, "Real player catalogue is not ready; build it locally first") from None

        @application.get("/catalogue/players", response_model=PlayerCataloguePage)
        def player_catalogue(name: str | None = Query(None, max_length=100),
                             league: str | None = Query(None, max_length=50),
                             team: str | None = Query(None, max_length=200),
                             position: str | None = Query(None, max_length=20),
                             minimum: float | None = Query(None, ge=0, allow_inf_nan=False),
                             maximum: float | None = Query(None, ge=0, allow_inf_nan=False),
                             rating_status: Literal["all", "rated", "unrated"] = "all",
                             sort: Literal["name", "rating"] = "name",
                             offset: int = Query(0, ge=0), limit: int = Query(24, ge=1, le=60)):
            if minimum is not None and maximum is not None and minimum > maximum:
                raise HTTPException(422, "Minimum OVR cannot exceed maximum OVR")
            try:
                return catalogue.search(name, league, team, position, minimum, maximum, rating_status, sort, offset, limit)
            except LookupError:
                raise HTTPException(503, "Real player catalogue is not ready; build it locally first") from None

        @application.get("/catalogue/players/{identity}", response_model=PlayerCatalogueDetail)
        def catalogue_player(identity: str):
            try:
                return catalogue.detail(identity)
            except LookupError:
                raise HTTPException(404, "Player is not in the imported catalogue") from None

        @application.get("/catalogue/players/{identity}/abilities", response_model=AbilityProfile)
        def catalogue_abilities(identity: str):
            try:
                return catalogue.ability_profile(identity)
            except LookupError:
                raise HTTPException(404, "Player is not in the imported catalogue") from None

        @application.get("/data/import")
        def evidence_import():
            try:
                return evidence.manifest()
            except LookupError:
                raise HTTPException(503, "No real evidence import is active") from None

        @application.get("/data/players")
        def evidence_players(provider: Literal["opta", "pitchapi", "understat"] | None = None,
                             league: Literal["England", "Spain", "Germany", "Italy", "France"] | None = None,
                             name: str | None = Query(None, max_length=100),
                             offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
            try:
                return evidence.catalogue(provider, league, name, offset, limit)
            except LookupError:
                raise HTTPException(503, "No real evidence import is active") from None

        @application.get("/data/players/{identity}/features")
        def evidence_features(identity: str):
            if len(identity) > 100:
                raise HTTPException(422, "Invalid identity")
            try:
                return evidence.profile(identity)
            except LookupError:
                raise HTTPException(404, "Imported source record or reviewed identity not found") from None

    application.add_middleware(RequestBoundary)
    return application


app = create_app()
