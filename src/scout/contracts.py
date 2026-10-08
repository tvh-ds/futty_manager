from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Score = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
MetricValue = Annotated[float, Field(allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Role(StrEnum):
    GK = "GK"
    CB = "CB"
    FB = "FB/WB"
    DM = "DM"
    CM = "CM"
    AM = "AM"
    W = "W"
    ST = "ST"


class Evidence(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    MANUAL = "manual"
    SYNTHETIC = "synthetic"
    UNAVAILABLE = "unavailable"


class MetricObservation(Contract):
    value: MetricValue
    unit: Literal["per90", "ratio", "scalar"] = "per90"
    evidence: Evidence = Evidence.OBSERVED
    numerator: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    denominator: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    source_field: str | None = None

    @model_validator(mode="after")
    def consistent_ratio(self):
        if self.unit == "per90" and not 0 <= self.value <= 10000:
            raise ValueError("per90 observation must be a bounded nonnegative rate")
        if self.unit == "ratio" and not 0 <= self.value <= 1:
            raise ValueError("ratio must be between zero and one")
        if self.unit == "ratio" and self.numerator is not None and self.denominator is not None:
            if self.denominator == 0 or self.numerator > self.denominator:
                raise ValueError("invalid ratio counts")
        return self


class PlayerStint(Contract):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    player_id: str
    name: str = Field(min_length=1, max_length=150)
    team_id: str
    league: str
    season: str
    age: int | None = Field(default=None, ge=15, le=55)
    foot: Literal["left", "right", "both"] | None = None
    roles: list[Role] = Field(min_length=1, max_length=8)
    role_evidence: Evidence
    minutes: int = Field(ge=0, le=15000)
    metrics: dict[str, MetricObservation]
    attributes: dict[str, bool | None] = Field(default_factory=dict)
    attribute_evidence: dict[str, Evidence] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent_exposure(self):
        import math
        for metric in self.metrics.values():
            if metric.unit == "per90" and metric.numerator is not None and self.minutes > 0:
                if not math.isclose(metric.value, metric.numerator * 90 / self.minutes, rel_tol=1e-5, abs_tol=1e-6):
                    raise ValueError("Per90 counts and minutes must agree with the reported rate")
        return self


class Team(Contract):
    id: str
    name: str
    league: str
    style_targets: dict[str, MetricValue] = Field(default_factory=dict)
    style_evidence: Evidence = Evidence.UNAVAILABLE


class DatasetRelease(Contract):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    kind: Literal["synthetic", "real", "historical"]
    season: str
    leagues: list[str]
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    feature_version: str = "role-features-v1"
    scoring_version: str = "evidence-ranking-v1"
    model_version: str = "shrunk-role-baseline-v1"
    limitations: list[str]
    publication_approved: bool = False
    publication_evidence: str | None = None


class RoleProfile(Contract):
    player_stint_id: str
    role: Role
    values: dict[str, float]
    percentiles: dict[str, Score]
    intervals: dict[str, tuple[float, float]]
    coverage: Score


class HardConstraints(Contract):
    min_age: int = Field(default=15, ge=15, le=55)
    max_age: int = Field(default=40, ge=15, le=55)
    min_minutes: int = Field(default=450, ge=0, le=15000)
    foot: Literal["left", "right", "both"] | None = None
    attributes: list[Literal["athletic", "high_line", "receives_under_pressure"]] = Field(
        default_factory=list, max_length=3
    )

    @model_validator(mode="after")
    def valid_age_range(self):
        if self.min_age > self.max_age:
            raise ValueError("minimum age exceeds maximum age")
        return self


class RecruitmentBrief(Contract):
    role: Role = Role.CB
    team_id: str | None = None
    replacement_id: str | None = None
    intended_style: dict[str, Annotated[float, Field(ge=0, le=10000, allow_inf_nan=False)]] = Field(
        default_factory=dict, max_length=30
    )
    constraints: HardConstraints = Field(default_factory=HardConstraints)
    preferences: dict[str, Annotated[float, Field(ge=0, le=5, allow_inf_nan=False)]] = Field(
        default_factory=dict, max_length=30
    )
    weights: dict[Literal["similarity", "quality", "tactical_fit", "replacement_fit", "coverage"],
                  Annotated[float, Field(ge=0, le=5, allow_inf_nan=False)]] = Field(
        default_factory=lambda: {"similarity": 1, "quality": 1, "tactical_fit": 1,
                                 "replacement_fit": 1, "coverage": 0.5}
    )
    limit: int = Field(default=20, ge=1, le=100)
    include_verification_required: bool = True

    @model_validator(mode="after")
    def positive_weights(self):
        if not any(self.weights.values()):
            raise ValueError("at least one ranking weight is required")
        return self


class Recommendation(Contract):
    player: PlayerStint
    score: Score
    components: dict[str, Score | None]
    status: Literal["eligible", "verification_required", "insufficient_evidence"]
    reasons: list[str]
    unknowns: list[str]
    profile: RoleProfile
    replacement_changes: dict[str, float]
    replacement_functions: dict[str, Literal["preserved", "improved", "compromised", "redistributed"]] = Field(default_factory=dict)


class ScenarioRequest(Contract):
    player_id: str
    team_id: str
    season_minutes: int = Field(default=2400, ge=0, le=4500)
    adaptation_mean: float = Field(default=0.9, ge=0.1, le=1.5, allow_inf_nan=False)
    adaptation_sd: float = Field(default=0.12, ge=0, le=0.5, allow_inf_nan=False)
    availability_mean: float = Field(default=0.85, ge=0, le=1, allow_inf_nan=False)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    samples: int = Field(default=2000, ge=200, le=10000)
    assignments: dict[str, Role] = Field(default_factory=dict, max_length=30)
    fees: dict[str, Annotated[float, Field(ge=0, le=1e9, allow_inf_nan=False)]] = Field(default_factory=dict)
    budget: float | None = Field(default=None, ge=0, le=1e10, allow_inf_nan=False)
    role_requirements: dict[Role, Annotated[int, Field(ge=0, le=10)]] = Field(default_factory=dict, max_length=8)


class ScenarioResult(Contract):
    release: DatasetRelease
    request: ScenarioRequest
    seed: int
    assumptions: dict[str, float | int]
    minutes_interval: tuple[float, float, float]
    outcomes: dict[str, tuple[float, float, float]]
    squad_coverage: dict[str, int]
    squad_gaps: list[str]
    total_fee: float | None
    budget_satisfied: bool | None
    limitations: list[str]


class DatasetIndex(Contract):
    active: DatasetRelease
    releases: list[DatasetRelease]


class RoleSpecification(Contract):
    id: Role
    label: str
    style_metrics: list[str]
    quality_metrics: dict[str, float]
    metric_labels: dict[str, str]


class TeamDetail(Contract):
    team: Team
    players: list[PlayerStint]
    release: DatasetRelease


class PlayerDetail(Contract):
    player: PlayerStint
    profiles: list[RoleProfile]
    release: DatasetRelease


class RecommendationResult(Contract):
    release: DatasetRelease
    brief: RecruitmentBrief
    recommendations: list[Recommendation]
    limitations: list[str]


class InterpretedBrief(Contract):
    brief: RecruitmentBrief
    method: Literal["structured_rules", "ollama"]
    warnings: list[str]
