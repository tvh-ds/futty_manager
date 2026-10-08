"""Monthly, fail-closed numeric refresh; no web scraping or synthetic backfill.

Trust boundary: provider responses / reviewed local imports -> strict records ->
immutable bronze, validated silver, feature gold -> independently activated data.
This dashboard release never authorizes publication of recruitment candidates.
"""
import hashlib
import json
import math
import os
import platform
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, StrictBool, StrictInt, ValidationError, model_validator

from scout.ability_contracts import AbilityProfile
from scout.ability_engine import (
    NORMALIZATION_VERSION,
    Population,
    evaluate_role,
    joint_hybrid,
    unrated_role,
    versatility,
)
from scout.contracts import Contract
from scout.ingestion import ApiFootball, QuotaExhausted
from scout.pitchapi import LIMITATIONS as PITCHAPI_LIMITATIONS
from scout.roles import API_LEAGUES
from scout.striker_features import ABILITIES, BY_KEY, FEATURE_VERSION, FEATURES, derive, measurement_statuses
from scout.striker_profiles import PROVISIONAL_VERSION, ROLE_WEIGHTS

Numeric = Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]
RAW_KEYS = {f.numerator for f in FEATURES} | {f.denominator for f in FEATURES} | {"aerial_duels_lost"}
RAW_KEYS -= {"finishing_delta", "aerial_duels_attempted"}


def scoring_environment():
    """Runtime versions belong to the immutable evaluation's provenance."""
    return {"python": platform.python_version(),
            **{name: version(name) for name in ("numpy", "scipy", "pydantic", "pyarrow")}}


def scoring_code_checksum():
    return hashlib.sha256(b"".join((Path(__file__).parent / name).read_bytes() for name in
        ["striker_features.py", "striker_profiles.py", "ability_engine.py", "calibration.py", "striker_refresh.py",
         "ability_contracts.py", "contracts.py", "roles.py", "pitchapi.py", "pitchapi_coverage.py"])).hexdigest()


def reject_json_constant(token):
    raise ValueError("Non-finite constants are not valid canonical JSON measurements")


def ordered_records(records):
    """Input/pagination order must not decide cohort arithmetic or role ties."""
    return [r.model_copy(update={"roles": [role for role in ROLE_WEIGHTS if role in r.roles],
                                 "totals": dict(sorted(r.totals.items()))})
            for r in sorted(records, key=lambda r: r.player_id)]


class ReviewedIdentity(Contract):
    player_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    roles: list[str] = Field(min_length=1, max_length=7)
    reviewed: StrictBool = False
    team_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def eligible_roles(self):
        if set(self.roles) - set(ROLE_WEIGHTS) or len(set(self.roles)) != len(self.roles):
            raise ValueError("Invalid or duplicate reviewed roles")
        return self


class StrikerSourceConfig(Contract):
    provider: Literal["api-football", "pitchapi"] = "api-football"
    enabled: StrictBool = False
    season: StrictInt = Field(default=2026, ge=2024)
    publication_approved: StrictBool = False
    observed_through: datetime | None = None
    identities: dict[str, ReviewedIdentity] = Field(default_factory=dict, max_length=10000)
    notes: str = Field(default="", max_length=2000)
    max_requests: StrictInt = Field(default=200, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_cutoff(self):
        if self.season > datetime.now(UTC).year:
            raise ValueError("Future source season")
        if self.observed_through is not None:
            if self.observed_through.tzinfo is None or self.observed_through > datetime.now(UTC):
                raise ValueError("Reviewed observation cutoff must be timezone-aware and not future")
        if self.enabled and self.observed_through is None:
            raise ValueError("Live collection requires a reviewed sporting observation cutoff")
        return self


class StrikerRecord(Contract):
    player_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    provider_player_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    team_id: str = Field(min_length=1, max_length=100)
    competition: str
    season: str = Field(pattern=r"^20[2-9][0-9]/[0-9]{2}$")
    roles: list[str] = Field(min_length=1, max_length=7)
    totals: dict[str, Numeric | None]
    source_urls: dict[str, str] = Field(max_length=50)
    observed_through: datetime
    retrieved_at: datetime
    identity_reviewed: StrictBool
    publication_approved: StrictBool
    measurement_version: Literal["canonical-v1", "pitchapi-measurements-v1"] = "canonical-v1"
    source_documents: list[str] = Field(default_factory=list, max_length=6000)

    @model_validator(mode="after")
    def validate_totals(self):
        if self.competition not in API_LEAGUES or int(self.season[:4]) < 2024:
            raise ValueError("Requires a top-five league and season 2024/25 or newer")
        if self.season[5:] != str(int(self.season[:4]) + 1)[-2:]:
            raise ValueError("Season end does not match season start")
        if int(self.season[:4]) > datetime.now(UTC).year:
            raise ValueError("Future season observations are unavailable")
        if set(self.roles) - set(ROLE_WEIGHTS) or "ST" not in self.roles:
            raise ValueError("Striker eligibility requires reviewed ST role; archetypes must be explicit")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("Duplicate eligible roles")
        if not self.identity_reviewed:
            raise ValueError("Cross-source identity mapping has not been reviewed")
        if any(not url.startswith("https://api.pitchapi.dev/v1/") for url in self.source_documents):
            raise ValueError("Invalid PitchAPI document citation")
        if set(self.totals) - RAW_KEYS:
            raise ValueError("Unknown raw measurement keys")
        if self.observed_through.tzinfo is None or self.retrieved_at.tzinfo is None:
            raise ValueError("Observation and retrieval times require timezone")
        if self.observed_through > self.retrieved_at or self.retrieved_at > datetime.now(UTC):
            raise ValueError("Invalid observation availability dates")
        # A retrieval timestamp in a later year cannot stand in for the date
        # through which this season's sporting observations are complete.
        start = int(self.season[:4])
        if not datetime(start, 7, 1, tzinfo=UTC) <= self.observed_through < datetime(start + 1, 8, 1, tzinfo=UTC):
            raise ValueError("Observation cutoff is outside the declared season window")
        if not self.totals.get("minutes"):
            raise ValueError("Missing minutes denominator")
        for key, value in self.totals.items():
            if value is not None and (key not in self.source_urls or not self.source_urls[key].startswith("https://")):
                raise ValueError("Every available raw value needs an HTTPS source citation")
        for a, b in [("shots_on_target", "shots"), ("shots_inside_box", "shots"),
                     ("headed_shots", "shots"), ("open_play_xg", "npxg"), ("non_penalty_shots", "shots"),
                     ("take_ons_successful", "take_ons_attempted"), ("passes_completed", "passes_attempted"),
                     ("duels_won", "duels_attempted"), ("non_penalty_goals", "non_penalty_shots")]:
            if self.totals.get(a) is not None and self.totals.get(b) is not None and self.totals[a] > self.totals[b]:
                raise ValueError(f"{a} exceeds {b}")
        if any(value is not None and not math.isfinite(value) for value in derive(self.totals).values()):
            raise ValueError("Derived measurements must be finite")
        won, lost = self.totals.get("aerial_duels_won"), self.totals.get("aerial_duels_lost")
        if won is not None and lost is not None and not math.isfinite(won + lost):
            raise ValueError("Derived aerial denominator must be finite")
        return self


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def evaluate_records(records, release_id, calculation_timestamp=None):
    """Pool top-five league peers with matching season, window and evidence definitions."""
    import numpy as np
    records = ordered_records(records)
    calculation_timestamp = calculation_timestamp or datetime.now(UTC).isoformat()
    profiles = {}
    derived = {r.player_id: derive(r.totals) for r in records}
    statuses = {r.player_id: measurement_statuses(r.totals, derived[r.player_id]) for r in records}
    for player, flags in statuses.items():
        for key, status in flags.items():
            if status == 'unrecorded_zero':
                derived[player][key] = 0.0
    groups, populations = {}, {}
    for peer in records:
        if peer.totals["minutes"] < 900 or any(v is None for k, v in derived[peer.player_id].items() if BY_KEY[k].direction):
            continue
        for role in peer.roles:
            excluded = tuple(k for k in BY_KEY if statuses[peer.player_id][k] == 'unrecorded_zero')
            key = (peer.season, peer.observed_through, role, peer.measurement_version, excluded)
            groups.setdefault(key, []).append(peer)
    for record in records:
        roles, calibrated, unavailable = [], {}, []
        for role in record.roles:
            weights = dict(zip(ABILITIES, ROLE_WEIGHTS[role], strict=True))
            label = role.replace("-", " ").title()
            if record.totals["minutes"] < 900:
                roles.append(unrated_role(role, label, ABILITIES, weights, derived[record.player_id], statuses[record.player_id]))
                unavailable.append(f"{role}: exposure below 900 minutes; measurements retained without calibration.")
                continue
            excluded = tuple(k for k in BY_KEY if statuses[record.player_id][k] == 'unrecorded_zero')
            cohort = (record.season, record.observed_through, role, record.measurement_version, excluded)
            peers = groups.get(cohort, [])
            if len(peers) < 30:
                roles.append(unrated_role(role, label, ABILITIES, weights, derived[record.player_id], statuses[record.player_id]))
                unavailable.append(f"{role}: {len(peers)} complete eligible peers; requires 30. Measurements retained without calibration.")
                continue
            if cohort not in populations:
                population_id = f"{release_id}-top-five-{role}"
                if record.measurement_version != "canonical-v1":
                    population_id += "-" + record.measurement_version
                if excluded:
                    population_id += '-mask-' + hashlib.sha256(json.dumps(excluded).encode()).hexdigest()[:12]
                populations[cohort] = Population(id=population_id, role_id=role,
                    values={f.key: np.array([derived[r.player_id][f.key] for r in peers]) for f in FEATURES},
                    exposure={d: np.array([r.totals.get(d) if d != "aerial_duels_attempted" else
                        r.totals['aerial_duels_won'] + r.totals['aerial_duels_lost'] if r.totals.get('aerial_duels_won') is not None and r.totals.get('aerial_duels_lost') is not None else None
                        for r in peers], dtype=float) for d in {f.denominator for f in FEATURES}},
                    season=record.season, competition="Top five European leagues", peer_ids=tuple(r.player_id for r in peers))
            population = populations[cohort]
            exposure = dict(record.totals)
            if record.totals.get("aerial_duels_won") is not None and record.totals.get("aerial_duels_lost") is not None:
                exposure["aerial_duels_attempted"] = record.totals["aerial_duels_won"] + record.totals["aerial_duels_lost"]
            scored, peer_z = evaluate_role(role, label, ABILITIES,
                weights, derived[record.player_id], exposure, population, statuses[record.player_id])
            roles.append(scored)
            calibrated[role] = scored, peer_z, population.peer_ids
        primary = max((r for r in roles if r.role_z is not None), key=lambda r: r.role_z, default=None)
        hybrid = None
        if "advanced-forward" in calibrated and "false-nine" in calibrated:
            pair = [calibrated[k] for k in ("advanced-forward", "false-nine")]
            hybrid = joint_hybrid([p[0] for p in pair], [p[1] for p in pair], [p[2] for p in pair])
        versatility_score, components = versatility(roles)
        profiles[record.player_id] = AbilityProfile(player_id=record.player_id, position="ST",
            primary_role_id=primary.role_id if primary else None, primary_rating=primary.rating if primary else None,
            primary_role_z=primary.role_z if primary else None, roles=roles, hybrids=[hybrid] if hybrid else [],
            versatility=versatility_score, versatility_components=components, season=record.season,
            competition=record.competition, minutes=record.totals["minutes"], evidence="observed",
            reference_population_id=release_id, normalization_version=NORMALIZATION_VERSION,
            weighting_version=PROVISIONAL_VERSION, feature_version=(FEATURE_VERSION if record.measurement_version == "canonical-v1"
                else FEATURE_VERSION + ":" + record.measurement_version),
            calculation_timestamp=calculation_timestamp, limitations=[
                "A rated role needs 30 compatible peers with the same zero-filled feature mask, 900 minutes, pooled top-five leagues and the same season/observation window.",
                "Only unrecorded_zero features redistribute their weights; genuine recorded zeros keep their weight shares.",
                "Uncalibrated reliability priors and manual archetype weights; no league-strength adjustment.",
                "Insufficient cohorts produce unavailable ratings, never demo values.",
                "Hybrid requires at least 30 joint eligible peer identities; versatility requires two eligible tactical roles.",
                f"Observed through {record.observed_through.isoformat()}; retrieved {record.retrieved_at.isoformat()}.",
                "Source citations are retained per raw field in the immutable bronze snapshot.",
                *(PITCHAPI_LIMITATIONS if record.measurement_version == "pitchapi-measurements-v1" else []), *unavailable],
            source_urls=sorted(set(record.source_urls.values()) | set(record.source_documents)), observed_through=record.observed_through.isoformat(),
            retrieved_at=record.retrieved_at.isoformat())
    return profiles


def publication_errors(records, profiles, config, report, now):
    """A current five-league release cannot be proved by one healthy cohort."""
    errors = []
    if len({r.measurement_version for r in records}) > 1:
        errors.append("Different measurement definitions cannot share a published calibration release")
    report["league_coverage"] = {}
    for league in API_LEAGUES:
        peers = [r for r in records if r.competition == league]
        rated = sum(any(role.role_id == "ST" and role.rating is not None for role in profiles[r.player_id].roles)
                    for r in peers)
        report["league_coverage"][league] = {"records": len(peers), "rated_strikers": rated,
            "minimum_required": 30, "observed_through": sorted({r.observed_through.isoformat() for r in peers})}
        if rated < 30:
            errors.append(f"{league}: fewer than 30 calibrated strikers")
    if report["quarantine"] or report.get("failure"):
        errors.append("Import or provider errors require review")
    if not config["publication_approved"] or not all(r.publication_approved for r in records):
        errors.append("Public-use approval missing")
    if any(int(r.season[:4]) != config["season"] for r in records):
        errors.append("Records do not match configured target season")
    if len({(r.season, r.observed_through) for r in records}) != 1:
        errors.append("A common season and observation cutoff is required across all five leagues")
    if any(now - r.retrieved_at > timedelta(days=45) for r in records):
        errors.append("Source retrieval older than 45 days")
    # Completed historical seasons may deliberately be imported, but a refresh
    # of the ongoing season must not relabel old observations as current.
    ongoing = now.year if now.month >= 7 else now.year - 1
    if config["season"] == ongoing and any(now - r.observed_through > timedelta(days=45) for r in records):
        errors.append("Current-season observation cutoff older than 45 days")
    if not profiles or any(not any(role.role_id == "ST" and role.rating is not None for role in p.roles)
                           for p in profiles.values()):
        errors.append("Complete calibrated ST measurements missing")
    return errors


def verified_release_profiles(directory, release_id, code_checksum, records, input_checksum, environment):
    """Verify the bounded, exact artifact set before parsing serving evidence."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    expected = {"bronze.json", "silver.parquet", "gold.parquet", "profiles.json"}
    if (manifest.get("id") != release_id or manifest.get("code_sha256") != code_checksum
            or set(manifest.get("files", {})) != expected or manifest.get("records") != len(records)
            or manifest.get("feature_version") != FEATURE_VERSION
            or manifest.get("weighting_version") != PROVISIONAL_VERSION
            or manifest.get("normalization_version") != NORMALIZATION_VERSION
            or manifest.get("input_sha256") != input_checksum or manifest.get("environment") != environment
            or manifest.get("publication_approved") is not all(r.publication_approved for r in records)):
        raise ValueError("Incompatible immutable striker manifest")
    for name, checksum in manifest["files"].items():
        path = directory / name
        if (not path.is_file() or path.stat().st_size > 200_000_000
                or hashlib.sha256(path.read_bytes()).hexdigest() != checksum):
            raise ValueError("Immutable striker artifact checksum mismatch")
    profiles = {k: AbilityProfile.model_validate(v) for k, v in
                json.loads((directory / "profiles.json").read_text(encoding="utf-8")).items()}
    if set(profiles) != {r.player_id for r in records}:
        raise ValueError("Striker profile identities do not match the import")
    for record in records:
        profile = profiles[record.player_id]
        if (profile.player_id != record.player_id or profile.evidence != "observed"
                or profile.season != record.season or profile.competition != record.competition
                or profile.observed_through != record.observed_through.isoformat()
                or profile.calculation_timestamp != manifest.get("calculation_timestamp")
                or profile.reference_population_id != release_id):
            raise ValueError("Striker profile provenance does not match the import")
    return profiles


def write_release_tables(directory, incoming, records, release_id, calculation_timestamp):
    """One construction path for a new batch and a recorded-epoch replay."""
    records = ordered_records(records)
    write_json(directory / "bronze.json", incoming)
    pq.write_table(pa.Table.from_pylist([{"player_id": r.player_id, "season": r.season,
                    "competition": r.competition, **{key: r.totals.get(key) for key in sorted(RAW_KEYS)}}
                    for r in records]), directory / "silver.parquet")
    pq.write_table(pa.Table.from_pylist([{"player_id": r.player_id, **derive(r.totals)} for r in records]),
                   directory / "gold.parquet")
    profiles = evaluate_records(records, release_id, calculation_timestamp)
    write_json(directory / "profiles.json", {k: v.model_dump(mode="json") for k, v in profiles.items()})
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("bronze.json", "silver.parquet", "gold.parquet", "profiles.json")}


def reproduce_release(source: Path, destination: Path):
    """Offline bitwise recovery check. Never change an active release pointer."""
    if destination.is_symlink() or destination.is_junction() or destination.exists():
        raise ValueError("Reproduction requires a new destination directory")
    if source.is_symlink() or source.is_junction():
        raise ValueError("Source release must not be a symbolic link")
    for name in ("bronze.json", "silver.parquet", "gold.parquet", "profiles.json", "manifest.json"):
        path = source / name
        if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size > 200_000_000:
            raise ValueError("Invalid or oversized reproduction source artifact")
    if (source / 'bronze.json').stat().st_size > 20_000_000:
        raise ValueError("Canonical bronze exceeds import size bound")
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    incoming = json.loads((source / 'bronze.json').read_text(encoding='utf-8'), parse_constant=reject_json_constant)
    if not isinstance(incoming, list) or len(incoming) > 10000:
        raise ValueError("Invalid canonical bronze record set")
    records, identities = [], set()
    for value in incoming:
        try:
            record = StrikerRecord.model_validate(value)
            if record.player_id not in identities:
                identities.add(record.player_id)
                records.append(record)
        except ValidationError:
            # Quarantined records stay in bronze but never enter fitted tables.
            continue
    code_checksum, environment = scoring_code_checksum(), scoring_environment()
    input_checksum = hashlib.sha256(json.dumps(incoming, sort_keys=True, allow_nan=False).encode()).hexdigest()
    release_id = manifest['id']
    verified_release_profiles(source, release_id, code_checksum, records, input_checksum, environment)
    files = write_release_tables(destination, incoming, records, release_id, manifest['calculation_timestamp'])
    if files != manifest['files']:
        write_json(destination / 'reproduction-status.json', {'matched': False,
            'release_id': release_id, 'mismatched_files': sorted(name for name in files if files[name] != manifest['files'][name])})
        raise ValueError("Reproduced artifacts do not match the immutable release")
    write_json(destination / 'manifest.json', manifest)
    verified_release_profiles(destination, release_id, code_checksum, records, input_checksum, environment)
    return {'matched': True, 'release_id': release_id, 'files': files,
            'activated': False, 'environment': environment}


def refresh(root=Path("data/strikers"), config_path=Path("config/striker-source.json"), import_path=None,
            pitchapi_cache: Path | None = None):
    now = datetime.now(UTC)
    report = {"checked_at": now.isoformat(), "cadence": "monthly", "activated": False,
        "source_status": {"fotmob": "Automated regular collection prohibited by published terms",
                          "fbref": "Advanced data removed; complete requested registry not established"},
        "quarantine": [], "records": 0, "missing_features": {}, "limitations": []}
    incoming = []
    try:
        config = StrikerSourceConfig.model_validate_json(config_path.read_text(encoding="utf-8")).model_dump(mode="json")
    except (OSError, ValueError) as error:
        report["failure"] = type(error).__name__
        report["limitations"].append("Source configuration invalid or unavailable. Previous release retained.")
        write_json(root / "refresh-status.json", report)
        return report
    if import_path is not None:
        try:
            if import_path.stat().st_size > 20_000_000:
                raise ValueError("Import exceeds 20 MB")
            incoming = json.loads(import_path.read_text(encoding="utf-8"), parse_constant=reject_json_constant)
            if not isinstance(incoming, list) or len(incoming) > 10000:
                raise ValueError("Expected at most 10,000 canonical numeric records")
        except (OSError, ValueError) as error:
            report["failure"] = type(error).__name__
            report["limitations"].append("Canonical import invalid or unavailable. Previous release retained.")
            write_json(root / "refresh-status.json", report)
            return report
    elif config.get("enabled") and config.get("provider") == "pitchapi":
        from scout.pitchapi import canonical_records, collect
        from scout.settings import Settings
        key = Settings().pitchapi_key.get_secret_value()
        if not key:
            report["limitations"].append("PitchAPI credential is not configured")
        else:
            try:
                measurements, coverage = collect(pitchapi_cache if pitchapi_cache is not None else
                    root / "provider" / "pitchapi" / str(config["season"]) / now.strftime("%Y-%m"),
                    key, season=config["season"], max_requests=config["max_requests"])
                report["pitchapi"] = coverage
                report["source_status"]["pitchapi"] = "Authenticated opt-in snapshots; measurement definitions versioned separately"
                report["limitations"].extend(coverage["limitations"])
                incoming = canonical_records(measurements, coverage, config)
                if coverage.get("failure"):
                    report["failure"] = coverage["failure"]
                if not coverage["complete"]:
                    report["limitations"].append(
                        "Quarantined source records require corrected snapshots; no partial season is activated."
                        if coverage.get("quarantine") else
                        "Season collection incomplete; resume cached collection. No partial season is activated.")
                elif not incoming:
                    report["limitations"].append("Full collection retained; explicit reviewed striker identities and team mappings are required.")
                if not config["identities"]:
                    report["limitations"].append("Reviewed striker/player/team identity mappings are not configured.")
                if not coverage.get('feature_coverage', {}).get('all_features_accepted'):
                    report['limitations'].append('Required feature coverage below 90%; no canonical rating import is accepted.')
            except (OSError, ValueError, TypeError, KeyError) as error:
                report["failure"] = type(error).__name__
                report["limitations"].append("PitchAPI collection failed; previous release retained.")
    elif config.get("enabled") and config.get("provider") == "api-football":
        key = os.getenv("SCOUT_API_FOOTBALL_KEY", "")
        if not key:
            report["limitations"].append("API-Football credential is not configured")
        else:
            client = ApiFootball(key, root / "provider" / now.strftime("%Y-%m"))
            try:
                # Conservative resumable backfill. Schema remains incomplete for xG/carrying/SCA.
                client.ingest(int(config["season"]))
                report["limitations"].append("Raw API-Football snapshots refreshed; richer xG, SCA and carrying measurements are still unavailable.")
            except QuotaExhausted:
                report["limitations"].append("Daily quota reached; resume the same month to complete the backfill")
            except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError) as error:
                report["failure"] = type(error).__name__
                report["limitations"].append("Provider collection failed. Previous release and resumable checkpoints retained.")
            if not report.get("failure"):
                try:
                    incoming = canonical_api_snapshots(root / "provider" / now.strftime("%Y-%m"), config)
                except (ValueError, TypeError, KeyError, AttributeError) as error:
                    report["failure"] = type(error).__name__
                    report["limitations"].append("Provider schema could not be mapped. Previous release retained; inspect private snapshots.")
    else:
        report["limitations"].append("Live provider not configured. No crawler or invented numeric fallback was run.")
    try:
        # Keep quarantine indices and retained bronze records in the same
        # canonical order, including rejected records.
        incoming = sorted(incoming, key=lambda value: json.dumps(value, sort_keys=True, allow_nan=False))
    except (ValueError, TypeError) as error:
        report["failure"] = type(error).__name__
        report["limitations"].append("Source records are not finite canonical JSON. Previous release retained.")
        write_json(root / "refresh-status.json", report)
        return report
    records, identities = [], set()
    for index, value in enumerate(incoming):
        try:
            record = StrikerRecord.model_validate(value)
            if record.player_id in identities:
                raise ValueError("Duplicate player identity: consolidate verified stints for the evaluation window")
            identities.add(record.player_id)
            records.append(record)
        except ValidationError as error:
            # Reports may leave private storage: never echo the rejected input.
            reason = '; '.join(f"{'/'.join(map(str, e['loc']))}: {e['msg']}"
                               for e in error.errors(include_input=False, include_url=False)[:5])
            report["quarantine"].append({"index": index, "reason": reason[:500]})
        except ValueError as error:
            report["quarantine"].append({"index": index, "reason": str(error)[:500]})
    report["records"] = len(records)
    records = ordered_records(records)
    for f in FEATURES:
        report["missing_features"][f.key] = sum(derive(r.totals)[f.key] is None for r in records)
    code_checksum = scoring_code_checksum()
    # Canonical imports retain every original record/value, including rejected
    # records, but row/object order is not a new source-data version.
    input_checksum = hashlib.sha256(json.dumps(incoming, sort_keys=True, allow_nan=False).encode()).hexdigest()
    environment = scoring_environment()
    checksum = hashlib.sha256(json.dumps([input_checksum, code_checksum, environment], sort_keys=True).encode()).hexdigest()
    release_id = f"strikers-{now.strftime('%Y%m')}-{checksum[:12]}"
    directory = root / "releases" / release_id
    if records and not (directory / "manifest.json").exists():
        files = write_release_tables(directory, incoming, records, release_id, now.isoformat())
        manifest = {"id": release_id, "files": files, "normalization_version": NORMALIZATION_VERSION,
                    "feature_version": FEATURE_VERSION, "weighting_version": PROVISIONAL_VERSION,
                    "input_sha256": input_checksum, "environment": environment,
                    "calculation_timestamp": now.isoformat(),
                    "code_sha256": code_checksum, "records": len(records),
                    "publication_approved": all(r.publication_approved for r in records)}
        write_json(directory / "manifest.json", manifest)
    elif records:
        report["limitations"].append("Identical immutable input already exists; artifacts were retained without overwrite")
    if records:
        try:
            profiles = verified_release_profiles(directory, release_id, code_checksum, records, input_checksum, environment)
            errors = publication_errors(records, profiles, config, report, now)
            report["publication_errors"] = errors
        except (OSError, ValueError, KeyError, TypeError) as error:
            report["failure"] = type(error).__name__
            errors = ["Immutable artifacts invalid or incompatible; previous release retained"]
            report["publication_errors"] = errors
        if not errors:
            old = json.loads((root / "active.json").read_text()) if (root / "active.json").exists() else None
            if not old or old["release_id"] != release_id:
                write_json(root / "active.json", {"release_id": release_id, "previous": old})
            report["activated"] = True
        else:
            report["limitations"].append("Publication gate withheld activation. Previous release retained; see publication_errors.")
    report["release_id"] = release_id if records else None
    write_json(root / "refresh-status.json", report)
    return report


def canonical_api_snapshots(root, config):
    """Conservative totals only. No guessed xG, pass totals or event context.

    Requires reviewed provider -> squad identities and detailed role overrides.
    Latest player/team/league row wins; conflicting transfers need an explicit
    consolidated import rather than mixing two season denominators.
    """
    incoming = {}
    for path in sorted(root.glob("*.json")):
        if path.name == "checkpoint.json":
            continue
        document = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_json_constant)
        if document.get("endpoint") != "players":
            continue
        for row in document["payload"].get("response", []):
            identity = config.get("identities", {}).get(str(row.get("player", {}).get("id")))
            if not identity or "ST" not in identity.get("roles", []):
                continue
            for stats in row.get("statistics", []):
                league = next((k for k, v in API_LEAGUES.items() if v == stats.get("league", {}).get("id")), None)
                if not league or stats.get("league", {}).get("season") != config["season"]:
                    continue
                totals = {"minutes": stats.get("games", {}).get("minutes")}
                for key, group, field in [
                    ("shots", "shots", "total"), ("shots_on_target", "shots", "on"),
                    ("assists", "goals", "assists"), ("key_passes", "passes", "key"),
                    ("take_ons_attempted", "dribbles", "attempts"), ("take_ons_successful", "dribbles", "success"),
                    ("duels_won", "duels", "won"), ("duels_attempted", "duels", "total"),
                    ("fouls_won", "fouls", "drawn"), ("interceptions", "tackles", "interceptions")]:
                    totals[key] = stats.get(group, {}).get(field)
                goals, penalties = stats.get("goals", {}).get("total"), stats.get("penalty", {}).get("scored")
                totals["non_penalty_goals"] = goals - penalties if goals is not None and penalties is not None else None
                season = config["season"]
                key = (identity["player_id"], stats["team"]["id"], league)
                candidate = {"player_id": identity["player_id"], "provider_player_id": str(row["player"]["id"]),
                    "name": row["player"]["name"], "team_id": str(stats["team"]["id"]), "competition": league,
                    "season": f"{season}/{str(season + 1)[-2:]}", "roles": identity["roles"], "totals": totals,
                    "source_urls": {k: f"https://v3.football.api-sports.io/players?id={row['player']['id']}&season={season}" for k, v in totals.items() if v is not None},
                    "observed_through": config.get("observed_through"), "retrieved_at": document["retrieved_at"],
                    "identity_reviewed": identity.get("reviewed", False) and str(stats["team"]["id"]) in identity.get("team_ids", []),
                    "publication_approved": config.get("publication_approved", False)}
                if key not in incoming or candidate["retrieved_at"] > incoming[key]["retrieved_at"]:
                    incoming[key] = candidate
    return list(incoming.values())


def active_profile(player_id, root=Path("data/strikers")):
    """Atomic pointer plus checksum verification; a corrupt release is never demo evidence."""
    pointer = root / "active.json"
    if not pointer.exists():
        return None
    release_id = json.loads(pointer.read_text())["release_id"]
    if not isinstance(release_id, str) or not __import__("re").fullmatch(r"strikers-\d{6}-[a-f0-9]{12}", release_id):
        raise ValueError("Invalid striker release pointer")
    path = root / "releases" / release_id
    manifest = json.loads((path / "manifest.json").read_text())
    file = path / "profiles.json"
    state = file.stat()
    data = load_verified_profiles(str(file), manifest["files"]["profiles.json"], state.st_mtime_ns, state.st_size)
    return AbilityProfile.model_validate(data[player_id]) if player_id in data else None


@lru_cache(maxsize=4)
def load_verified_profiles(path, checksum, modified, size):
    if size > 200_000_000:
        raise ValueError("Striker serving release exceeds 200 MB")
    file = Path(path)
    if hashlib.sha256(file.read_bytes()).hexdigest() != checksum:
        raise ValueError("Striker artifact checksum mismatch")
    return json.loads(file.read_text(encoding="utf-8"))
