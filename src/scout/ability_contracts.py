from typing import Literal

from pydantic import Field

from scout.contracts import Contract


class FeatureDistribution(Contract):
    key: str
    label: str
    unit: str
    direction: int
    weight: float
    base_weight: float | None = None
    evidence_status: str = 'observed'
    value: float | None
    stabilized_value: float | None
    peer_mean: float | None
    z: float | None
    percentile: float | None
    reliability: float | None
    peer_count: int
    density: list[tuple[float, float]]
    quantiles: list[tuple[float, float]]


class AbilityScore(Contract):
    name: str
    raw: float | None
    z: float | None
    rating_unclipped: float | None
    rating: float | None
    percentile: float | None
    available: int
    defined: int
    features: list[FeatureDistribution]


class RoleScore(Contract):
    role_id: str
    label: str
    role_composite_raw: float | None
    role_z: float | None
    rating_unclipped: float | None
    rating: float | None
    percentile: float | None
    rank: int | None
    population_size: int
    gap_to_next_z: float | None
    gap_to_previous_z: float | None
    abilities: list[AbilityScore]
    weights: dict[str, float]


class AbilityProfile(Contract):
    player_id: str
    position: str
    primary_role_id: str | None
    primary_rating: float | None
    primary_role_z: float | None
    roles: list[RoleScore]
    hybrids: list[RoleScore] = Field(default_factory=list)
    versatility: float | None = None
    versatility_components: dict[str, float] = Field(default_factory=dict)
    minimum_minutes: int = 900
    season: str
    competition: str
    minutes: float
    evidence: Literal["synthetic", "observed", "unavailable"]
    reference_population_id: str
    normalization_version: str
    weighting_version: str
    feature_version: str
    calculation_timestamp: str
    source_urls: list[str] = Field(default_factory=list)
    observed_through: str | None = None
    retrieved_at: str | None = None
    limitations: list[str]
