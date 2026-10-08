"""Dashboard contracts: sourced identities and synthetic measurements never share a label."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from scout.contracts import Contract, Role, Score

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")]


class FormationSlot(Contract):
    id: Identifier
    label: str
    role: Role
    side: Literal["left", "centre", "right"]
    row: int
    x: float
    y: float


class FormationDefinition(Contract):
    id: Identifier
    slots: list[FormationSlot]
    edges: list[tuple[str, str]]


class LineupState(Contract):
    snapshot_id: Identifier
    formation_id: Identifier = "4-3-3"
    assignments: dict[Identifier, Identifier | None] = Field(max_length=11)
    bench: list[Identifier] = Field(default_factory=list, max_length=9)
    role_multiplier: float = Field(default=1.5, ge=1, le=3, allow_inf_nan=False, multiple_of=0.1)

    @model_validator(mode="after")
    def unique_players(self):
        players = [value for value in self.assignments.values() if value is not None] + self.bench
        if len(players) != len(set(players)):
            raise ValueError("A player can occupy only one lineup or bench location")
        return self


class SkillEvidence(Contract):
    key: str
    label: str
    raw_value: float | None
    unit: str
    percentile: Score | None
    peer_count: int
    lower_is_better: bool
    evidence: Literal["synthetic", "observed", "unavailable"] = "synthetic"


class SquadPlayer(Contract):
    id: Identifier
    name: str
    short_name: str
    number: int
    country_label: str
    category: Literal["Goalkeeper", "Defender", "Midfielder", "Forward"]
    roles: list[Role]
    planning_side: Literal["left", "centre", "right"]
    identity_evidence: Literal["observed"] = "observed"
    role_evidence: Literal["manual"] = "manual"
    source_url: str
    skills: list[SkillEvidence]
    club_logo_url: str | None = None
    portrait_url: str | None = None
    catalogue_id: str | None = None
    attribute_evidence: Literal["synthetic", "observed", "unavailable"] = "synthetic"
    performance_season: str | None = None
    ability_scores: dict[str, float | None] = Field(default_factory=dict)
    mapping_status: str | None = None


class SquadSummary(Contract):
    id: Identifier
    team: str
    league: str
    season: str
    snapshot_date: date
    snapshot_id: Identifier


class SquadSnapshot(SquadSummary):
    players: list[SquadPlayer]
    default_lineup: LineupState
    sources: list[str]
    feature_version: str
    peer_version: str
    club_logo_url: str | None = None
    rating_version: str
    chemistry_version: str
    peer_counts: dict[str, int]
    observation_window: str
    limitations: list[str]


class SkillContribution(Contract):
    skill: SkillEvidence
    emphasized: bool
    weight: float
    contribution: float | None


class PlayerRating(Contract):
    player_id: str
    role: Role
    score: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    normal_role_score: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    coverage: Score
    role_coverage: Score
    available: int
    defined: int
    total_weight: float
    skills: list[SkillContribution]
    warnings: list[str]
    role_z: float | None = None
    rating_unclipped: float | None = None
    percentile: float | None = None
    primary_role: str | None = None
    role_scores: dict[str, float | None] = Field(default_factory=dict)
    normalization_version: str = "magnitude-base50-no-upper-cap-v2"
    evidence: Literal["synthetic", "observed", "unavailable"] = "synthetic"
    ability_scores: dict[str, float | None] = Field(default_factory=dict)


class ChemistryComponent(Contract):
    key: str
    label: str
    score: float | None = Field(ge=0, le=10, allow_inf_nan=False)
    explanation: str
    evidence: Literal["synthetic", "unavailable"]


class ChemistryResult(Contract):
    player_a: str
    player_b: str
    score: float | None = Field(ge=0, le=10, allow_inf_nan=False)
    band: Literal["red", "yellow", "green", "unknown"]
    available: int
    defined: int = 5
    components: list[ChemistryComponent]
    evidence: Literal["synthetic"] = "synthetic"


class ChemistryEdge(Contract):
    slot_a: str
    slot_b: str
    chemistry: ChemistryResult


class DashboardEvaluation(Contract):
    lineup: LineupState
    ratings: dict[str, PlayerRating]
    edges: list[ChemistryEdge]
    team_rating: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    team_chemistry: float | None
    chemistry_scored_links: int
    chemistry_total_links: int
    completeness: int
    reserve_ids: list[str]
    feature_version: str
    peer_version: str
    rating_version: str
    chemistry_version: str
    evidence: Literal["synthetic"] = "synthetic"
    warnings: list[str]


class FormationChange(Contract):
    lineup: LineupState
    formation_id: Identifier
