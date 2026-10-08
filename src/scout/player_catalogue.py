"""Audited identity mapping and real attribute cards; never fabricate a rating."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scout.ability_contracts import AbilityProfile
from scout.ability_engine import (
    NORMALIZATION_VERSION,
    cached_distribution,
    display,
    percentile,
    unrated_role,
)
from scout.calibration import calibrate_ability, calibrate_composite
from scout.card_identity import COUNTRY_LABELS
from scout.catalogue_contracts import CardAbility, PlayerCardData
from scout.database import (
    ActiveCatalogue,
    ActiveEvidence,
    CataloguePlayer,
    CatalogueRelease,
    SourceRecord,
)
from scout.position_config import CONFIG, DEFINITIONS, position_id, registry
from scout.position_config import FEATURE_VERSION as POSITION_FEATURE_VERSION
from scout.position_config import WEIGHTING_VERSION as POSITION_WEIGHTING_VERSION
from scout.position_evidence import MasterFeatures
from scout.real_data import PRIORITY, digest, feature_rows, name_key, read_json
from scout.striker_features import (
    BY_KEY,
    FEATURE_VERSION,
    WEIGHTING_VERSION,
    effective_weights,
)

MAPPING_VERSION = "corroborated-source-identities-v1"
SCORING_VERSION = "observed-assigned-position-top-five-pooled-v6"
ABBREVIATIONS = ["FIN", "BOX", "LNK", "CAR", "PHY", "DEF"]
POSITIONS = {"Central Defender": "CB", "Full Back": "FB/WB", "Wing Back": "FB/WB",
             "Defensive Midfielder": "DM", "Central Midfielder": "CM", "Attacking Midfielder": "AM",
             "Winger": "W", "Striker": "ST", "Second Striker": "ST"}
# Explicitly documented name variants; not arbitrary fuzzy matching.
ALIASES = {"alisson": "alissonbecker", "josephgomez": "joegomez", "georgimamardashvili": "giorgimamardashvili"}
LIMITATIONS = [
    "Observed 2025/26 performance snapshots, not live statistics. Catalogue teams are performance-season clubs.",
    "Cross-provider links are algorithmically corroborated, not human-reviewed. Ambiguous links remain separate.",
    "Nine grouped position registries use provisional reviewed weights. Broad winger evidence supports LW/RW only; LM/RM requires distinct position evidence.",
    "Ratings require 900 minutes and at least 30 compatible position peers with the same effective feature weights across the top five leagues; no league-strength adjustment.",
    "Goalkeeper appearance features require matched season exposure; partial windows and zero-variance abilities remain unrated.",
    "Only explicitly zero-filled unrecorded features redistribute weight proportionally. Recorded zeros retain weight; undefined zero-attempt ratios remain N/A.",
    "Shrinkage priors and supplied ability weights are provisional, not calibrated predictions of match performance.",
    "Partial PitchAPI backfills and differing provider definitions remain visible in feature provenance.",
    "Understat evidence is private; this catalogue is not a public candidate release.",
]


def normalized_name(name):
    key = name_key(name)
    return ALIASES.get(key, key)


def pitch_metadata(root):
    """Extract original provider portraits and club facts from verified snapshots."""
    paths = sorted((root / "snapshots").glob("*.json"))
    inventory = digest([(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in paths])
    cache = root / "player-card-metadata-v2.json"
    if cache.exists():
        saved = read_json(cache)
        if saved.get("inventory") == inventory and saved.get("checksum") == digest(saved["metadata"]):
            people, teams, logos, checksum = saved["metadata"]
            if all(re.fullmatch(r"https://cdn\.pitchapi\.dev/images/players/[a-f0-9]{64}\.webp", p["portrait_url"])
                   for p in people.values()):
                return people, teams, logos, checksum
    people, teams, logos, checksums = {}, {}, {}, []
    def walk(value):
        if isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, dict):
            identifier = value.get("id")
            if isinstance(identifier, str) and identifier.startswith("p_") and isinstance(value.get("name"), str):
                image = value.get("image_url")
                if isinstance(image, str) and re.fullmatch(r"https://cdn\.pitchapi\.dev/images/players/[a-f0-9]{64}\.webp", image):
                    people[identifier] = {"name": value["name"], "portrait_url": image}
            if isinstance(identifier, str) and identifier.startswith("t_") and isinstance(value.get("name"), str):
                teams[identifier] = value["name"]
                image = value.get("image_url")
                if isinstance(image, str) and re.fullmatch(r"https://cdn\.pitchapi\.dev/images/teams/[a-f0-9]{64}\.webp", image):
                    logos[identifier] = image
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)
    for path in paths:
        saved = read_json(path)
        if not isinstance(saved.get("url"), str) or not saved["url"].startswith("https://api.pitchapi.dev/v1/"):
            raise ValueError("Unexpected cached source")
        # Images are present in ordinary player feeds and league match metadata.
        if saved["url"].endswith("/shots") or "/advanced/" in saved["url"]:
            continue
        checksum = hashlib.sha256(json.dumps(saved["document"], sort_keys=True, allow_nan=False).encode()).hexdigest()
        if saved.get("sha256") != checksum:
            raise ValueError("PitchAPI metadata snapshot checksum mismatch")
        checksums.append(checksum)
        walk(saved["document"])
    metadata = [people, teams, logos, digest(checksums)]
    cache.write_text(json.dumps({"inventory": inventory, "checksum": digest(metadata), "metadata": metadata}), encoding="utf-8")
    return tuple(metadata)


def position(record):
    facts = record.payload.get("identity_facts", {})
    if facts.get("squad_position") == "Goalkeeper":
        return "GK"
    return POSITIONS.get(record.payload.get("source_position"), "Unknown")


def corroborates(anchor, candidate, clubs=None):
    """Do not infer identity from a matching name alone or join partial stints."""
    if anchor.league != candidate.league or normalized_name(anchor.name) != normalized_name(candidate.name):
        return False
    a, b = anchor.payload["totals"], candidate.payload["totals"]
    minutes = a.get("minutes"), b.get("minutes")
    if any(n is None or n <= 0 for n in minutes) or abs(minutes[0] - minutes[1]) > max(45, .02 * minutes[0]):
        return False
    keys = [k for k in ("shots", "non_penalty_goals", "assists") if a.get(k) is not None and b.get(k) is not None]
    if position(anchor) == "GK":
        def club_key(value):
            return normalized_name(re.sub(r"\s+(?:FC|AFC)$", "", value or "", flags=re.I))
        team = candidate.payload.get("source_team_title")
        if not team and clubs:
            ids = candidate.payload.get("provider_team_ids", [])
            if len(ids) == 1:
                team = clubs.get(ids[0])
        anchor_team = anchor.payload.get("identity_facts", {}).get("contestantName")
        return bool(anchor_team and team and club_key(anchor_team) == club_key(team))
    return len(keys) >= 2 and all(a[k] == b[k] for k in keys)


def selected_features(records):
    observations = {r.id: feature_rows(r.payload["totals"]) for r in records}
    result = {}
    for key in BY_KEY:
        choices = [(observations[r.id][key], r) for r in records]
        choices.sort(key=lambda item: (item[0]["status"] not in ("observed", "not_applicable_zero_attempts"),
                                       PRIORITY.index(item[1].provider), item[1].id))
        value, record = choices[0]
        if value['status'] == 'missing_measurement':
            value = {**value, 'value': 0.0, 'status': 'unrecorded_zero'}
        result[key] = {**value, "key": key, "label": BY_KEY[key].label, "provider": record.provider,
            "record_id": record.id, "measurement_version": record.payload["measurement_version"],
            "source_url": record.payload["source_urls"][0], "alternatives": [
                {**v, "provider": r.provider, "record_id": r.id} for v, r in choices[1:]]}
    return result


def score_catalogue(players):
    """Position-local, five-league pooled calibration with compatible evidence."""
    for player in players:
        player['abilities'], player['ability_detail'], player['overall'] = [], {}, None
        player.setdefault('rating_position', position_id(player['position']))
    for position in CONFIG['positions']:
        abilities, overall_weights, abbreviations = registry(position)
        members = [p for p in players if p['rating_position'] == position]
        # Master identities count once in reference cohorts, even when unresolved
        # catalogue source copies still remain available for evidence inspection.
        canonical = {}
        for p in sorted(members, key=lambda p: (not p['id'].startswith('player-opta-'), p['id'])):
            canonical.setdefault(p.get('master_row') or p['id'], p['id'])
        for name, weights in abilities.items():
            directional = [k for k in weights if DEFINITIONS[k].direction]
            groups = defaultdict(list)
            for player in members:
                if player['minutes'] < CONFIG['minimum_minutes'] or canonical[player.get('master_row') or player['id']] != player['id']:
                    continue
                features = player['features']
                if set(weights) - features.keys():
                    continue
                active = effective_weights(weights, {k: features[k].get('status') for k in weights})
                used = [k for k in directional if active[k] > 0]
                if used and all(features[k]['value'] is not None and np.isfinite(features[k]['value'])
                    and features[k]['status'] == 'observed' and features[k]['denominator'] is not None
                    and features[k]['denominator'] > 0 for k in used):
                    signature = tuple((k, active[k], features[k]['provider'], features[k]['measurement_version']) for k in used)
                    groups[signature].append(player)
            for group in groups.values():
                if len(group) < CONFIG['minimum_peers']:
                    continue
                values = {k: np.array([p['features'][k]['value'] for p in group],dtype=float) for k in directional}
                calibrated = calibrate_ability(weights, values,
                    {k: np.array([p['features'][k]['denominator'] for p in group],dtype=float) for k in directional},
                    {k: group[0]['features'][k].get('status') for k in weights}, definitions=DEFINITIONS)
                active = calibrated.weights
                peer_raw, latent = calibrated.composite.peer_raw, calibrated.composite.peer_z
                if position != 'ST' and np.std(peer_raw) <= 1e-12:
                    continue
                ids = [p['id'] for p in group]
                for i, player in enumerate(group):
                    player['ability_detail'][name] = {'raw': float(peer_raw[i]), 'z': float(latent[i]),
                        'rating': display(float(latent[i])), 'percentile': percentile(float(latent[i]), latent),
                        'peer_ids': ids, 'peer_z': latent.tolist(), 'effective_weights': active,
                        'excluded_zero_filled': [k for k in weights if group[0]['features'][k].get('status')=='unrecorded_zero'],
                        'feature_stats': {k: {'stable': float(stat.stable_peers[i]), 'reliability': float(stat.peer_reliability[i]),
                            'z': float(stat.peer_z[i]), 'mean': stat.mean,
                            'percentile': (100-percentile(float(values[k][i]),values[k])) if DEFINITIONS[k].direction<0
                                else percentile(float(values[k][i]),values[k])}
                            for k,stat in calibrated.features.items()}}
            for player in members:
                detail = player['ability_detail'].get(name)
                available = sum(player['features'].get(k,{}).get('status')=='observed' for k in weights)
                player['abilities'].append(CardAbility(name=name, abbreviation=abbreviations[name],
                    rating=detail['rating'] if detail else None, available=available, defined=len(weights),
                    peer_count=len(detail['peer_ids']) if detail else 0,
                    reason=('Zero-filled feature weights redistributed proportionally' if detail and detail['excluded_zero_filled'] else None)
                    if detail else 'Below 900 minutes' if player['minutes']<CONFIG['minimum_minutes'] else
                    'Missing features, partial window, duplicate identity or insufficient compatible peers').model_dump())
        for player in members:
            details = player['ability_detail']
            if len(details) != 6:
                continue
            peer_maps = {q: dict(zip(d['peer_ids'], d['peer_z'],strict=True)) for q,d in details.items()}
            common = sorted(set.intersection(*(set(m) for m in peer_maps.values())))
            if len(common)<CONFIG['minimum_peers']:
                continue
            composite = calibrate_composite(overall_weights, {q:d['z'] for q,d in details.items()},
                {q:np.array([m[i] for i in common]) for q,m in peer_maps.items()})
            if position!='ST' and np.std(composite.peer_raw)<=1e-12:
                continue
            player['overall'] = display(composite.z)
            player['overall_z'] = composite.z
            player['overall_raw'] = composite.raw
            player['overall_percentile'] = percentile(composite.z, composite.peer_z)
            player['overall_rank'] = 1+int(np.sum(composite.peer_z>composite.z))
            player['overall_peer_ids'] = common
    for player in players:
        if not player['abilities']:
            player['abilities'] = [CardAbility(name=a['name'],abbreviation=a['abbreviation'],rating=None,
                available=0,defined=len(a['features']),reason='Recorded position unavailable').model_dump()
                for a in CONFIG['positions']['ST']['abilities']]


def build_catalogue(database, pitch_root):
    photos, clubs, logos, metadata_checksum = pitch_metadata(pitch_root)
    with Session(database) as session:
        pointer = session.get(ActiveEvidence, "local")
        if not pointer:
            raise ValueError("Import real source evidence first")
        batch = pointer.import_id
        records = session.scalars(select(SourceRecord).where(SourceRecord.import_id == batch)).all()
    opta_groups = defaultdict(list)
    for r in records:
        if r.provider == "opta":
            opta_groups[r.payload["provider_player_id"]].append(r)
    anchors = [max(group, key=lambda r: ((r.payload["totals"].get("minutes") or 0), r.id)) for group in opta_groups.values()]
    candidates, by_name = defaultdict(list), defaultdict(list)
    for r in anchors:
        by_name[(r.league, normalized_name(r.name))].append(r)
    linked, audit = set(), []
    for r in records:
        if r.provider == "opta":
            continue
        options = by_name[(r.league, normalized_name(r.name))]
        accepted = [a for a in options if corroborates(a, r, clubs)]
        if len(accepted) == 1:
            candidates[accepted[0].id].append(r)
            linked.add(r.id)
            audit.append({"anchor": accepted[0].id, "record": r.id,
                          "method": "unique_name_league_exposure_plus_attack_counts_or_goalkeeper_club",
                          "status": "corroborated_not_human_reviewed"})
    used_sources = defaultdict(list)
    for r in records:
        if r.provider == "opta":
            used_sources[r.payload["provider_player_id"]].append(r)
    players = []
    for anchor in [*anchors, *[r for r in records if r.provider != "opta" and r.id not in linked]]:
        group = [anchor, *candidates.get(anchor.id, [])]
        # Never pick an arbitrary provider record if duplicate matches are found.
        counts = Counter(r.provider for r in group)
        group = [r for r in group if r == anchor or counts[r.provider] == 1]
        feature_map = selected_features(group)
        pitch = next((r for r in group if r.provider == "pitchapi"), None)
        photo = photos.get(pitch.payload["provider_player_id"], {}) if pitch else {}
        team = anchor.payload.get("identity_facts", {}).get("contestantName") or anchor.payload.get("source_team_title")
        if not team and pitch:
            team = clubs.get(pitch.payload.get("provider_team_ids", [None])[-1]) if pitch.payload.get("provider_team_ids") else None
        team_ids = pitch.payload.get("provider_team_ids", []) if pitch else []
        team_id = next((i for i in team_ids if normalized_name(clubs.get(i, "")) == normalized_name(team or "")), team_ids[0] if len(team_ids) == 1 else None)
        identifier = "player-" + anchor.provider + "-" + digest(anchor.payload["provider_player_id"])[:24]
        if anchor.provider != "opta":
            identifier += "-" + anchor.league.lower()
        player = {"id": identifier, "name": anchor.name, "short_name": anchor.name.split()[-1],
            "league": anchor.league, "team": team or "Team unverified", "position": position(anchor),
            "minutes": anchor.payload["totals"].get("minutes") or 0, "overall": None,
            "abilities": [], "ability_detail": {}, "features": feature_map,
            "country_label": None, "club_logo_url": logos.get(team_id),
            "portrait_url": photo.get("portrait_url"), "portrait_source": "PitchAPI" if photo else None,
            "mapping_status": "corroborated" if len(group) > 1 else "source_only",
            "numerical_features": sum(f["value"] is not None and f['status'] != 'unrecorded_zero' for f in feature_map.values()),
            "supported_features": sum(f["status"] in ("observed", "not_applicable_zero_attempts") for f in feature_map.values()),
            "rating_status": "redistributed_observed_model", "sources": [
                {"id": r.id, "provider": r.provider, "name": r.name, "league": r.league,
                 "provider_player_id": r.payload["provider_player_id"], "identity_facts": r.payload.get("identity_facts", {}), "totals": r.payload["totals"],
                 "scope": r.payload["aggregation_scope"], "retrieved_at": r.payload["retrieved_at"],
                 "source_urls": r.payload["source_urls"]} for r in group],
            "other_stints": [r.id for r in used_sources.get(anchor.payload["provider_player_id"], []) if r.id != anchor.id]}
        players.append(player)
    master_features = MasterFeatures()
    for player in players:
        master_features.attach(player)
    score_catalogue(players)
    from scout.squads import ROSTER
    roster_countries = {normalized_name(row[1]): row[4] for row in ROSTER}
    for player in players:
        player["country_label"] = roster_countries.get(normalized_name(player["name"]))
        reviewed = COUNTRY_LABELS.get((player["league"], player["name"]))
        if reviewed:
            player["country_label"], player["country_source_url"] = reviewed
    squad_map, unmapped = {}, []
    for slug, name, *_ in ROSTER:
        possible = [p for p in players if normalized_name(p["name"]) == normalized_name(name)]
        # Corroborated Opta identity wins over its unresolved provider copies.
        primary = [p for p in possible if p["id"].startswith("player-opta-")]
        if len(primary) == 1 or len(possible) == 1:
            squad_map["lfc-" + slug] = (primary or possible)[0]["id"]
        else:
            unmapped.append("lfc-" + slug)
    from scout.assigned_positions import build_assignments
    build_assignments(players, squad_map, master_features)
    manifest = {"import_id": batch, "mapping_version": MAPPING_VERSION, "scoring_version": SCORING_VERSION,
        "feature_version": POSITION_FEATURE_VERSION, "weighting_version": POSITION_WEIGHTING_VERSION, "config_sha256": CONFIG["checksum"], "rating_config": CONFIG, "master_snapshot": str(master_features.path), "position_ratings": {role: {"players": sum(p["rating_position"] == role for p in players), "rated": sum(p["rating_position"] == role and p["overall"] is not None for p in players)} for role in CONFIG["positions"]}, "metadata_checksum": metadata_checksum,
        "liverpool_logo_url": next((logos[i] for i, title in clubs.items() if normalized_name(title) in ("liverpool", "liverpoolfc") and i in logos), None),
        "total": len(players), "linked_source_records": len(linked), "mapping_audit": audit,
        "squad_mappings": squad_map, "unmapped_squad_players": unmapped,
        "portraits": sum(p["portrait_url"] is not None for p in players),
        "rated_overall": sum(p["overall"] is not None for p in players), "limitations": LIMITATIONS,
        "created_at": datetime.now(UTC).isoformat(),
        "transform_sha256": hashlib.sha256(b''.join(Path(__file__).with_name(name).read_bytes()
            for name in ('player_catalogue.py', 'calibration.py', 'striker_features.py', 'position_config.py', 'position_evidence.py', 'assigned_positions.py'))).hexdigest()}
    catalogue_id = "catalogue-" + digest({k: v for k, v in manifest.items() if k != "created_at"})[:32]
    manifest["catalogue_id"] = catalogue_id
    with Session(database) as session, session.begin():
        if not session.get(CatalogueRelease, catalogue_id):
            session.add(CatalogueRelease(id=catalogue_id, import_id=batch, manifest=manifest))
            session.flush()
            session.execute(CataloguePlayer.__table__.insert(), [{"catalogue_id": catalogue_id,
                **{key: p[key] for key in ("id", "name", "league", "team", "position", "overall")},
                "payload": p} for p in players])
        session.merge(ActiveCatalogue(slot="local", catalogue_id=catalogue_id))
    return manifest


class PlayerCatalogue:
    def __init__(self, database):
        self.database = database

    def active(self, session):
        active = session.get(ActiveCatalogue, "local")
        if not active:
            raise LookupError("Build the real player catalogue first")
        return session.get(CatalogueRelease, active.catalogue_id)

    def metadata(self):
        with Session(self.database) as s:
            release = self.active(s)
            rows = s.execute(select(CataloguePlayer.league, CataloguePlayer.team, CataloguePlayer.position)
                             .where(CataloguePlayer.catalogue_id == release.id).distinct()).all()
            return {"catalogue_id": release.id, "total": release.manifest["total"],
                "leagues": sorted({r.league for r in rows}), "teams": {league: sorted({r.team for r in rows if r.league == league})
                    for league in sorted({r.league for r in rows})}, "positions": sorted({r.position for r in rows}),
                "squad_mappings": release.manifest["squad_mappings"], "limitations": LIMITATIONS}

    @staticmethod
    def card(payload):
        return PlayerCardData.model_validate({k: v for k, v in payload.items() if k in PlayerCardData.model_fields})

    def search(self, name=None, league=None, team=None, position=None, minimum=None, maximum=None,
               rating_status="all", sort="name", offset=0, limit=24):
        with Session(self.database) as s:
            release = self.active(s)
            query = select(CataloguePlayer).where(CataloguePlayer.catalogue_id == release.id)
            for column, value in ((CataloguePlayer.league, league), (CataloguePlayer.team, team), (CataloguePlayer.position, position)):
                if value:
                    query = query.where(column == value)
            if name:
                query = query.where(CataloguePlayer.name.icontains(name, autoescape=True))
            if minimum is not None:
                query = query.where(CataloguePlayer.overall >= minimum)
            if maximum is not None:
                query = query.where(CataloguePlayer.overall <= maximum)
            if rating_status != "all":
                query = query.where(CataloguePlayer.overall.is_not(None) if rating_status == "rated" else CataloguePlayer.overall.is_(None))
            total = s.scalar(select(func.count()).select_from(query.subquery()))
            ordering = CataloguePlayer.overall.desc().nulls_last() if sort == "rating" else CataloguePlayer.name.asc()
            records = s.scalars(query.order_by(ordering, CataloguePlayer.id).offset(offset).limit(limit)).all()
            return {"catalogue_id": release.id, "total": total, "offset": offset, "limit": limit,
                    "items": [self.card(r.payload) for r in records]}

    def payload(self, identity, squad=False):
        with Session(self.database) as s:
            release = self.active(s)
            if squad:
                identity = release.manifest["squad_mappings"].get(identity)
            row = s.get(CataloguePlayer, (release.id, identity)) if identity else None
            if not row:
                raise LookupError("Player identity has no imported mapping")
            return row.payload, release

    def detail(self, identity):
        payload, release = self.payload(identity)
        return {**self.card(payload).model_dump(), "catalogue_id": release.id,
                "features": [{k: v for k, v in f.items() if k in (
                    "key", "label", "value", "unit", "status", "provider", "numerator", "denominator", "source_url", "measurement_version")}
                    for f in payload["features"].values()], "sources": payload["sources"], "limitations": LIMITATIONS}

    def ability_profile(self, identity, squad=False, assigned_position=None):
        p, release = self.payload(identity, squad)
        if assigned_position:
            evaluation = p.get('position_evaluations', {}).get(assigned_position)
            if not evaluation:
                raise ValueError('Assigned position evaluation is not available; rebuild the local catalogue')
            p = {**p, **dict.fromkeys(('overall_z','overall_raw','overall_percentile','overall_rank')),
                 'overall_peer_ids': [], **evaluation, 'position': assigned_position}
        from types import SimpleNamespace
        config = release.manifest.get('rating_config', CONFIG)
        definitions = {key: SimpleNamespace(key=key, **value) for key,value in config['features'].items()}
        position = p.get('rating_position', position_id(p['position']))
        abilities, weights, _ = registry(position, config)
        if not abilities:
            abilities, weights, _ = registry('ST', config)
        ids = set().union(*(set(d["peer_ids"]) for d in p["ability_detail"].values()))
        with Session(self.database) as session:
            peers = session.scalars(select(CataloguePlayer).where(CataloguePlayer.catalogue_id == release.id,
                                                                 CataloguePlayer.id.in_(ids))).all() if ids else []
        peer_values = {row.id: row.payload["features"] for row in peers}
        role = unrated_role(position, config['positions'].get(position, {'label':'Unknown'})['label']+(' · assigned position' if assigned_position else ' · observed position'), abilities, weights,
                            {k: v["value"] for k, v in p["features"].items()},
                            {k: v['status'] for k, v in p['features'].items()}, definitions=definitions)
        for ability in role.abilities:
            detail = p["ability_detail"].get(ability.name)
            if not detail:
                continue
            ability.raw, ability.z, ability.rating = detail["raw"], detail["z"], detail["rating"]
            ability.rating_unclipped = 50 + 15 * ability.z
            ability.percentile = detail["percentile"]
            for feature in ability.features:
                feature.weight = detail.get('effective_weights', {}).get(feature.key, feature.weight)
                stat = detail["feature_stats"].get(feature.key)
                if stat:
                    feature.stabilized_value, feature.reliability = stat["stable"], stat["reliability"]
                    feature.z, feature.peer_mean = stat["z"], stat["mean"]
                    feature.percentile, feature.peer_count = stat["percentile"], len(detail["peer_ids"])
                    values = tuple(peer_values[i][feature.key]["value"] for i in detail["peer_ids"])
                    feature.density, feature.quantiles = cached_distribution(values)
            role.population_size = max(role.population_size, len(detail["peer_ids"]))
        role.rating = p["overall"]
        role.role_z = p.get('overall_z')
        role.role_composite_raw = p.get('overall_raw')
        role.percentile = p.get('overall_percentile')
        role.rank = p.get('overall_rank')
        role.population_size = len(p['overall_peer_ids']) if p.get('overall_peer_ids') else role.population_size
        role.rating_unclipped = 50 + 15*role.role_z if role.role_z is not None else None
        return AbilityProfile(player_id=identity, position=p["position"], primary_role_id=position if p['overall'] is not None else None,
            primary_rating=p["overall"], primary_role_z=role.role_z, roles=[role], season="2025/26", competition='Top-five leagues pooled · '+position,
            minutes=p["minutes"], evidence="observed", reference_population_id=release.id + "-" + digest(
                {name: sorted(d["peer_ids"]) for name, d in p["ability_detail"].items()})[:12],
            normalization_version=NORMALIZATION_VERSION, weighting_version=release.manifest.get('weighting_version', WEIGHTING_VERSION),
            feature_version=release.manifest.get('feature_version', FEATURE_VERSION), calculation_timestamp=release.manifest["created_at"],
            source_urls=sorted({f["source_url"] for f in p["features"].values()}), limitations=LIMITATIONS)
