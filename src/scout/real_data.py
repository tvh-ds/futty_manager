"""Transactional, provenance-preserving import of the three collected sources.

Source aggregates are not silently converted to team stints or merged by name.
Only documented identity links permit combined views. Source-local numerators
and denominators always stay together, including when another source is used
as a fallback. This is private evidence intake, not public release publication.
"""
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scout.database import ActiveEvidence, EvidenceImport, IdentityLink, SourceFeature, SourceRecord
from scout.striker_features import FEATURE_VERSION, FEATURES, derive

IMPORT_VERSION = "combined-evidence-v1"
LEAGUES = {"England", "Spain", "Germany", "Italy", "France"}
SOURCE_HOSTS = {"pitchapi": "api.pitchapi.dev", "opta": "dataviz.theanalyst.com", "understat": "understat.com"}
PRIORITY = ("opta", "pitchapi", "understat")
LIMITATIONS = [
    "Private local evidence; this import does not activate a public candidate release or player ratings.",
    "Provider rows are not unique players. Unreviewed identity candidates remain separate.",
    "PitchAPI has five quarantined match feeds; its season aggregates are incomplete.",
    "Opta contains unused squad members and two quarantined exposure conflicts.",
    "Understat publication permission is unverified; its observations remain private.",
    "Provider definitions and exposure can differ. Each selected feature retains its own denominator and provenance.",
    "The registry defines ST features only; fouls won remains missing. N/A does not become a numeric rating.",
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def read_json(path: Path):
    if path.stat().st_size > 100_000_000:
        raise ValueError("Evidence input exceeds size limit")
    def reject_constant(_):
        raise ValueError("Non-finite JSON number")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(path.read_bytes(), parse_constant=reject_constant, object_pairs_hook=unique_object)


def record_id(provider, row):
    return provider + "-" + digest([row["competition"], row["provider_player_id"],
                                  row.get("provider_team_id")])[:32]


def numeric(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid nonnegative raw measurement")
    return float(value)


def feature_rows(totals):
    raw = {key: numeric(value) for key, value in totals.items()}
    if len(raw) > 200 or any(not re.fullmatch(r"[a-z][a-z0-9_]{0,59}", key) for key in raw):
        raise ValueError("Invalid raw measurement keys")
    if raw.get("non_penalty_goals") is not None and raw.get("npxg") is not None:
        raw["finishing_delta"] = raw["non_penalty_goals"] - raw["npxg"]
    if raw.get("aerial_duels_attempted") is None and raw.get("aerial_duels_lost") is not None and raw.get("aerial_duels_won") is not None:
        raw["aerial_duels_attempted"] = raw["aerial_duels_won"] + raw["aerial_duels_lost"]
    # derive() derives attempts from won/lost. Preserve a source's explicit attempts
    # when lost is absent by deriving its complement only if internally consistent.
    if raw.get("aerial_duels_attempted") is not None and raw.get("aerial_duels_won") is not None:
        if raw["aerial_duels_won"] > raw["aerial_duels_attempted"]:
            raise ValueError("Aerial wins exceed attempts")
        if raw.get("aerial_duels_lost") is None:
            raw["aerial_duels_lost"] = raw["aerial_duels_attempted"] - raw["aerial_duels_won"]
    values = derive(raw)
    result = {}
    for feature in FEATURES:
        a, b = raw.get(feature.numerator), raw.get(feature.denominator)
        if a is None or b is None:
            status = "missing_measurement"
        elif b == 0:
            if feature.denominator != "minutes" and a != 0:
                raise ValueError("Positive numerator with zero attempts")
            status = "zero_exposure" if feature.denominator == "minutes" else "not_applicable_zero_attempts"
        else:
            if feature.unit in ("%", "ratio") and a > b:
                raise ValueError("Successes exceed attempts")
            status = "observed"
        result[feature.key] = {"value": values[feature.key], "status": status, "unit": feature.unit,
            "numerator": a, "denominator": b, "numerator_field": feature.numerator,
            "denominator_field": feature.denominator, "feature_version": FEATURE_VERSION}
    return result


def normalize(provider, row):
    if not isinstance(row, dict) or row.get("competition") not in LEAGUES:
        raise ValueError("Unknown competition")
    if row.get("season") not in ("2025/26", "2025/2026"):
        raise ValueError("Wrong performance season")
    for field in ("provider_player_id", "name", "retrieved_at", "source_url"):
        if not isinstance(row.get(field), str) or not 0 < len(row[field]) <= (2048 if field == "source_url" else 200):
            raise ValueError("Missing or invalid identity/provenance")
    from datetime import datetime
    if datetime.fromisoformat(row["retrieved_at"]).tzinfo is None:
        raise ValueError("Retrieval timestamp requires timezone")
    urls = row.get("source_urls", [row["source_url"]])
    if not isinstance(urls, list) or not 1 <= len(urls) <= 2000:
        raise ValueError("Invalid provenance URL list")
    for url in [row["source_url"], *urls]:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != SOURCE_HOSTS[provider] or parsed.username or parsed.password or parsed.query:
            raise ValueError("Unexpected source host or credential-bearing URL")
    if not isinstance(row.get("totals"), dict):
        raise ValueError("Missing raw measurements")
    features = feature_rows(row["totals"])
    team = row.get("provider_team_id")
    if team is not None and (not isinstance(team, str) or len(team) > 100):
        raise ValueError("Invalid source team")
    payload = {"provider_player_id": row["provider_player_id"], "provider_team_id": team,
        "provider_team_ids": row.get("provider_team_ids", []), "source_team_title": row.get("source_team_title"),
        "source_position": row.get("source_position"), "source_urls": urls,
        "retrieved_at": row["retrieved_at"], "totals": row["totals"],
        "measurement_version": row.get("measurement_version", "understat-league-probe-v1"),
        "aggregation_scope": "player_team_season" if provider == "opta" else "player_league_season",
        "season_complete": row.get("complete_season") if provider == "pitchapi" else None,
        "publication_approved": provider in ("opta", "pitchapi"),
        "identity_status": "source_only", "evidence": "observed"}
    return {"id": record_id(provider, row), "provider": provider, "name": row["name"],
            "league": row["competition"], "season": "2025/26", "payload": payload}, features


def name_key(name):
    normalized = unicodedata.normalize("NFKD", name.casefold())
    return "".join(c for c in normalized if c.isalnum() and not unicodedata.combining(c))


def prepare(roots: dict[str, Path], identity_file: Path | None = None):
    if set(roots) != set(SOURCE_HOSTS):
        raise ValueError("All three source roots are required")
    records, features, inputs, quarantine, source_reports = {}, {}, [], [], {}
    for provider, root in sorted(roots.items()):
        source_report = read_json(root / "coverage.json")
        source_reports[provider] = source_report
        inputs.append({"provider": provider, "path": str((root / "coverage.json").resolve()),
                       "sha256": hashlib.sha256((root / "coverage.json").read_bytes()).hexdigest()})
        files = [root / "measurements.json"] if provider == "pitchapi" else sorted(root.glob("*/measurements.json"))
        if not files or any(not p.is_file() for p in files):
            raise ValueError(f"Missing measurements for {provider}")
        leagues = set()
        for path in files:
            rows = read_json(path)
            if not isinstance(rows, list) or len(rows) > 10000:
                raise ValueError("Invalid measurement collection")
            inputs.append({"provider": provider, "path": str(path.resolve()),
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(rows)})
            identity_facts = {}
            if provider != "pitchapi":
                bronze = path.parent / "bronze.json"
                bronze_checksum = hashlib.sha256(bronze.read_bytes()).hexdigest()
                league = rows[0]["competition"] if rows else None
                expected = source_report.get("leagues", {}).get(league, {}).get("snapshot_sha256")
                if expected != bronze_checksum:
                    raise ValueError("Bronze checksum disagrees with source collection report")
                inputs.append({"provider": provider, "path": str(bronze.resolve()), "sha256": bronze_checksum})
                if provider == "opta":
                    document = read_json(bronze)
                    for section in ("attack", "goalkeeping"):
                        for person in document.get(section, {}).get("overall", []):
                            key = (str(person.get("player_uuid")), str(person.get("team_uuid")))
                            identity_facts[key] = {field: person.get(field) for field in (
                                "date_of_birth", "first_name", "last_name", "contestantName", "squad_position",
                                "squad_position_detailed", "player_id", "team_id")}
            for index, row in enumerate(rows):
                try:
                    item, values = normalize(provider, row)
                except (ValueError, TypeError, KeyError, OverflowError):
                    quarantine.append({"provider": provider, "file": str(path), "row": index,
                                       "reason": "invalid_identity_provenance_or_measurements"})
                    continue
                if item["id"] in records:
                    raise ValueError("Duplicate source aggregate; import refused")
                item["payload"]["identity_facts"] = identity_facts.get((row["provider_player_id"], row.get("provider_team_id")), {})
                records[item["id"]], features[item["id"]] = item, values
                leagues.add(item["league"])
        if leagues != LEAGUES:
            raise ValueError(f"Missing valid league catalogue for {provider}")
    links = read_json(identity_file) if identity_file else []
    if not isinstance(links, list) or len(links) > len(records):
        raise ValueError("Invalid identity link file")
    used, canonical_groups = set(), defaultdict(list)
    for link in links:
        if (not isinstance(link, dict) or set(link) != {"record_id", "canonical_id", "reviewer", "evidence"}
                or link["record_id"] not in records or link["record_id"] in used
                or not isinstance(link["canonical_id"], str)
                or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", link["canonical_id"])
                or not isinstance(link["reviewer"], str) or not 1 <= len(link["reviewer"]) <= 200
                or not isinstance(link["evidence"], str) or not 10 <= len(link["evidence"]) <= 4000):
            raise ValueError("Identity link must reference a source record and document review evidence")
        used.add(link["record_id"])
        canonical_groups[link["canonical_id"]].append(records[link["record_id"]])
    for group in canonical_groups.values():
        if len({r["league"] for r in group}) != 1 or len({r["provider"] for r in group}) != len(group):
            raise ValueError("A combined profile needs one aggregate per provider within one league-season; reconcile transfers first")
    counts = Counter(r["provider"] for r in records.values())
    groups = defaultdict(list)
    for record in records.values():
        groups[(record["league"], name_key(record["name"]))].append(record)
    candidates = [{"league": league, "name": group[0]["name"], "record_ids": sorted(r["id"] for r in group),
                   "status": "unreviewed_name_candidate"}
                  for (league, _), group in sorted(groups.items()) if len({r["provider"] for r in group}) > 1]
    coverage = {}
    for provider in SOURCE_HOSTS:
        for league in sorted(LEAGUES):
            ids = [r["id"] for r in records.values() if r["provider"] == provider and r["league"] == league
                   and (r["payload"]["totals"].get("minutes") or 0) > 0]
            coverage[f"{provider}:{league}"] = {"positive_minute_records": len(ids), "features": {
                f.key: {"numeric": sum(features[i][f.key]["status"] == "observed" for i in ids),
                        "not_applicable": sum(features[i][f.key]["status"] == "not_applicable_zero_attempts" for i in ids),
                        "supported_pct": round(100 * sum(features[i][f.key]["status"] in
                            ("observed", "not_applicable_zero_attempts") for i in ids) / len(ids), 2) if ids else 0}
                for f in FEATURES}}
    manifest = {"schema_version": IMPORT_VERSION, "feature_version": FEATURE_VERSION, "season": "2025/26",
        "inputs": inputs, "records": len(records), "source_counts": dict(counts),
        "source_collection_status": {p: {key: report.get(key) for key in (
            "complete", "failure", "source_validation_passed", "publication_approved", "quarantine")}
            for p, report in source_reports.items()},
        "feature_observations": len(records) * len(FEATURES), "reviewed_links": len(links),
        "identity_candidates": candidates, "quarantine": quarantine, "coverage": coverage,
        "scope": "private_local", "publication_approved": False, "limitations": LIMITATIONS,
        "transform_sha256": digest({"importer": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "features": hashlib.sha256(Path(__file__).with_name("striker_features.py").read_bytes()).hexdigest()})}
    manifest["id"] = "evidence-" + digest({"manifest": manifest, "links": links})[:32]
    return manifest, records, features, links


def import_evidence(engine, roots, identity_file=None):
    manifest, records, features, links = prepare(roots, identity_file)
    batch = manifest["id"]
    with Session(engine) as session, session.begin():
        if session.get(EvidenceImport, batch) is None:
            session.add(EvidenceImport(id=batch, manifest=manifest))
            session.flush()
            session.execute(SourceRecord.__table__.insert(), [{"import_id": batch, **r} for r in records.values()])
            rows = [{"import_id": batch, "record_id": rid, "key": key,
                     "value": value["value"], "status": value["status"], "payload": value}
                    for rid, values in features.items() for key, value in values.items()]
            for offset in range(0, len(rows), 5000):
                session.execute(SourceFeature.__table__.insert(), rows[offset:offset + 5000])
            if links:
                session.execute(IdentityLink.__table__.insert(), [{"import_id": batch,
                    "record_id": link["record_id"], "canonical_id": link["canonical_id"],
                    "review": {"reviewer": link["reviewer"], "evidence": link["evidence"]}} for link in links])
        # Independent pointer: cannot overwrite the published candidate release.
        session.merge(ActiveEvidence(slot="local", import_id=batch))
    return manifest


class RealDataEngine:
    """SQL-backed real feature serving, including reviewed combined profiles."""
    def __init__(self, database):
        self.database = database

    def active(self, session):
        pointer = session.get(ActiveEvidence, "local")
        if pointer is None:
            raise LookupError("No real evidence import is active")
        return pointer.import_id

    def catalogue(self, provider=None, league=None, name=None, offset=0, limit=50):
        with Session(self.database) as session:
            batch = self.active(session)
            query = select(SourceRecord).where(SourceRecord.import_id == batch)
            if provider:
                query = query.where(SourceRecord.provider == provider)
            if league:
                query = query.where(SourceRecord.league == league)
            if name:
                query = query.where(SourceRecord.name.icontains(name, autoescape=True))
            total = session.scalar(select(func.count()).select_from(query.subquery()))
            rows = session.scalars(query.order_by(SourceRecord.name, SourceRecord.id).offset(offset).limit(limit)).all()
            return {"import_id": batch, "total_source_records": total, "offset": offset, "limit": limit,
                    "items": [{"id": r.id, "name": r.name, "provider": r.provider, "league": r.league,
                               "season": r.season, "minutes": r.payload["totals"].get("minutes"),
                               "source_position": r.payload["source_position"],
                               "identity_status": r.payload["identity_status"]} for r in rows]}

    def manifest(self):
        with Session(self.database) as session:
            return session.get(EvidenceImport, self.active(session)).manifest

    def profile(self, identity):
        with Session(self.database) as session:
            batch = self.active(session)
            direct = session.get(SourceRecord, (batch, identity))
            links = session.scalars(select(IdentityLink).where(IdentityLink.import_id == batch,
                                                              IdentityLink.canonical_id == identity)).all()
            records = [direct] if direct else [session.get(SourceRecord, (batch, link.record_id)) for link in links]
            if not records:
                raise LookupError("Source record or reviewed canonical identity not found")
            alternatives = defaultdict(list)
            for record in records:
                values = session.scalars(select(SourceFeature).where(SourceFeature.import_id == batch,
                                                                     SourceFeature.record_id == record.id)).all()
                for value in values:
                    alternatives[value.key].append({**value.payload, "provider": record.provider,
                        "record_id": record.id, "measurement_version": record.payload["measurement_version"],
                        "source_urls": record.payload["source_urls"], "retrieved_at": record.payload["retrieved_at"],
                        "publication_approved": record.payload["publication_approved"]})
            selected = {}
            for key, choices in alternatives.items():
                choices.sort(key=lambda c: (c["status"] not in ("observed", "not_applicable_zero_attempts"),
                                            PRIORITY.index(c["provider"]), c["record_id"]))
                selected[key] = {**choices[0], "alternatives": choices[1:],
                    "definition_reconciliation": "source_specific_not_equivalent" if len(choices) > 1 else "single_source"}
            return {"id": identity, "name": records[0].name, "import_id": batch,
                    "performance_season": "2025/26", "feature_version": FEATURE_VERSION,
                    "identity_status": "reviewed" if links and not direct else "source_only",
                    "features": selected, "raw_sources": [{"record_id": r.id, "provider": r.provider,
                        "league": r.league, **r.payload} for r in records],
                    "numeric_features": sum(f["status"] == "observed" for f in selected.values()),
                    "supported_features": sum(f["status"] in ("observed", "not_applicable_zero_attempts") for f in selected.values()),
                    "overall_rating": None, "rating_status": "not_calibrated",
                    "publication_approved": False, "limitations": LIMITATIONS}
