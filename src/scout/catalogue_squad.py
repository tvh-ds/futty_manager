"""Map observed historical evidence onto the current Liverpool planning roster."""
from sqlalchemy.orm import Session

from scout.ability_contracts import AbilityProfile
from scout.ability_engine import unrated_role
from scout.player_catalogue import LIMITATIONS, SCORING_VERSION
from scout.position_config import DEFINITIONS, position_id, registry
from scout.squad_contracts import PlayerRating, SkillEvidence
from scout.squads import squad_snapshot
from scout.striker_features import ABILITIES, FEATURE_VERSION, WEIGHTING_VERSION


def mapped_snapshot(catalogue):
    snapshot = squad_snapshot().model_copy(deep=True)
    metadata = catalogue.metadata()
    with Session(catalogue.database) as session:
        manifest = catalogue.active(session).manifest
        snapshot.club_logo_url = manifest.get("liverpool_logo_url")
    for player in snapshot.players:
        player.club_logo_url = snapshot.club_logo_url
        player.attribute_evidence = "unavailable"
        player.skills = []
        player.ability_scores = dict.fromkeys(ABILITIES)
        player.performance_season = "2025/26"
        try:
            payload, _ = catalogue.payload(player.id, squad=True)
        except LookupError:
            player.mapping_status = "unmapped"
            continue
        player.catalogue_id, player.mapping_status = payload["id"], payload["mapping_status"]
        player.portrait_url, player.attribute_evidence = payload["portrait_url"], "observed"
        player.ability_scores = {a["name"]: a["rating"] for a in payload["abilities"]}
        player.skills = [SkillEvidence(key=key, label=f["label"], raw_value=f["value"], unit=f["unit"],
            percentile=None, peer_count=0, lower_is_better=DEFINITIONS[key].direction < 0,
            evidence="observed" if f["value"] is not None and f['status'] != 'unrecorded_zero' else "unavailable") for key, f in payload["features"].items()]
    snapshot.feature_version, snapshot.peer_version = manifest.get('feature_version', FEATURE_VERSION), metadata["catalogue_id"]
    snapshot.rating_version = SCORING_VERSION
    snapshot.observation_window = "Observed 2025/26 performance; Liverpool 2026/27 roster. Not live updates."
    snapshot.peer_counts = {"outfield": 0, "goalkeepers": 0}
    snapshot.limitations = LIMITATIONS + ["Liverpool lineup roles remain manual. Chemistry still uses demonstration inputs."]
    return snapshot


def mapped_rating(player, role, catalogue, assigned_position=None):
    try:
        payload, _ = catalogue.payload(player.id, squad=True)
    except LookupError:
        abilities, _, _ = registry(position_id(assigned_position or role.value))
        defined = len({k for weights in abilities.values() for k in weights})
        return PlayerRating(player_id=player.id, role=role, score=None, normal_role_score=None,
            coverage=0, role_coverage=0, available=0, defined=defined, total_weight=0, skills=[],
            warnings=["No verified performance identity mapping; no synthetic fallback."], evidence="unavailable",
            ability_scores=dict.fromkeys(abilities))
    assigned = position_id(assigned_position or role.value)
    natural = payload.get('rating_position', position_id(payload['position']))
    natural_overall = payload['overall']
    evaluation = payload.get('position_evaluations', {}).get(assigned)
    if evaluation:
        payload = {**payload, **evaluation}
    elif assigned != natural:
        abilities, _, _ = registry(assigned)
        payload = {**payload, 'abilities': [dict(name=name, rating=None) for name in abilities],
                   'numerical_features': 0, 'defined_features': len({k for w in abilities.values() for k in w})}
    scores = {a["name"]: a["rating"] for a in payload["abilities"]}
    overall = payload['overall'] if evaluation or assigned == natural else None
    defined = payload.get('defined_features', 36)
    reasons = [f"{a['name']}: {a['reason']}" for a in payload['abilities'] if a['rating'] is None and a.get('reason')]
    return PlayerRating(player_id=player.id, role=role, score=overall, normal_role_score=natural_overall,
        coverage=100 * payload["numerical_features"] / defined if defined else 0,
        role_coverage=100 * payload["numerical_features"] / defined if defined else 0,
        available=payload["numerical_features"], defined=defined, total_weight=1, skills=[],
        warnings=reasons + (["Assigned-position evaluation unavailable; rebuild the local catalogue."] if not evaluation and assigned != natural else []) + [
                  "Overall requires all six calibrated abilities. Only zero-filled unrecorded feature weights are redistributed; recorded zeros retain their shares.",
                  "Manual planning assignment; scores assess the assigned position, not tactical suitability."],
        evidence="observed", primary_role=natural,
        ability_scores=scores)


def mapped_profile(player_id, catalogue, assigned_position=None):
    try:
        return catalogue.ability_profile(player_id, squad=True, assigned_position=assigned_position)
    except LookupError:
        player = next(p for p in squad_snapshot().players if p.id == player_id)
        position = assigned_position or position_id(player.roles[0].value)
        abilities, weights, _ = registry(position)
        role = unrated_role(position, position+' · no observed mapping', abilities, weights, {}, definitions=DEFINITIONS)
        return AbilityProfile(player_id=player_id, position=position, primary_role_id=None, primary_rating=None,
            primary_role_z=None, roles=[role], season="2025/26", competition="Unavailable", minutes=0,
            evidence="unavailable", reference_population_id="unmapped", normalization_version="magnitude-base50-no-upper-cap-v2",
            weighting_version=WEIGHTING_VERSION, feature_version=FEATURE_VERSION,
            calculation_timestamp="2026-10-06T00:00:00Z", limitations=["No observed identity mapping; no synthetic fallback."])
