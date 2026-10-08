from typing import Literal

from scout.contracts import Contract


class CardAbility(Contract):
    name: str
    abbreviation: str
    rating: float | None
    available: int
    defined: int
    peer_count: int = 0
    reason: str | None = None


class PlayerCardData(Contract):
    id: str
    name: str
    short_name: str
    league: str
    team: str
    position: str
    minutes: float
    season: str = "2025/26"
    overall: float | None
    abilities: list[CardAbility]
    country_label: str | None = None
    club_logo_url: str | None = None
    portrait_url: str | None = None
    portrait_source: str | None = None
    mapping_status: str
    evidence: Literal["observed", "unavailable"] = "observed"
    numerical_features: int
    supported_features: int
    defined_features: int = 36
    rating_status: str


class PlayerCataloguePage(Contract):
    catalogue_id: str
    total: int
    offset: int
    limit: int
    items: list[PlayerCardData]


class PlayerCatalogueMetadata(Contract):
    catalogue_id: str
    total: int
    leagues: list[str]
    teams: dict[str, list[str]]
    positions: list[str]
    squad_mappings: dict[str, str]
    limitations: list[str]


class CatalogueFeature(Contract):
    key: str
    label: str
    value: float | None
    unit: str
    status: str
    provider: str
    numerator: float | None
    denominator: float | None
    source_url: str
    measurement_version: str


class PlayerCatalogueDetail(PlayerCardData):
    catalogue_id: str
    features: list[CatalogueFeature]
    sources: list[dict]
    limitations: list[str]
