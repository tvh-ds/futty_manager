"""Magnitude-first scoring. Percentiles never enter a rating calculation."""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.stats import gaussian_kde

from scout.ability_contracts import AbilityScore, FeatureDistribution, RoleScore
from scout.calibration import (
    SHRINKAGE as SHRINKAGE,
)
from scout.calibration import (
    calibrate_ability,
    calibrate_composite,
)
from scout.calibration import (
    display as display,
)
from scout.calibration import (
    percentile as percentile,
)
from scout.calibration import (
    shrink as shrink,
)
from scout.calibration import (
    standardize as standardize,
)
from scout.striker_features import BY_KEY, effective_weights

NORMALIZATION_VERSION = "magnitude-base50-no-upper-cap-v2"
@dataclass
class Population:
    id: str
    values: dict[str, np.ndarray]
    exposure: dict[str, np.ndarray]
    season: str
    competition: str
    role_id: str
    minimum_minutes: int = 900
    peer_ids: tuple[str, ...] = ()


def distribution(peers):
    peers = np.asarray(peers)
    peers = peers[np.isfinite(peers)]
    if not len(peers):
        return [], []
    quantiles = [(float(x), float(q)) for x, q in zip(np.quantile(peers, np.linspace(0, 1, 101)), np.linspace(0, 100, 101), strict=True)]
    if np.ptp(peers) < 1e-12:
        return [(float(peers[0]), 1.0)], quantiles
    grid = np.linspace(float(peers.min()), float(peers.max()), 65)
    kde = gaussian_kde(peers)
    return [(float(x), float(y)) for x, y in zip(grid, kde(grid), strict=True)], quantiles


@lru_cache(maxsize=512)
def cached_distribution(values):
    return distribution(np.array(values))


def evaluate_role(role_id, label, abilities, weights, values, exposures, population, feature_statuses=None):
    """Fit every stage on the same frozen role/period/exposure peer cohort.

    Only explicitly unrecorded_zero features redistribute weight; recorded
    zeros participate normally. Other unavailable values cannot be scored.
    Offsides remain visible, with direction zero until context is specified.
    """
    peer_quality = {}
    feature_statuses = feature_statuses or {}
    qualities = []
    peer_count = len(next(iter(population.values.values())))
    for name, features in abilities.items():
        calibrated = calibrate_ability(features,
            {k: population.values[k] for k in features},
            {k: population.exposure[BY_KEY[k].denominator] for k in features}, feature_statuses, values,
            {k: exposures.get(BY_KEY[k].denominator) for k in features})
        active = calibrated.weights
        feature_views = []
        for key, base_weight in features.items():
            weight = active[key]
            definition = BY_KEY[key]
            if feature_statuses.get(key) == 'unrecorded_zero':
                feature_views.append(FeatureDistribution(key=key, label=definition.label, unit=definition.unit,
                    direction=definition.direction, weight=0, base_weight=base_weight, evidence_status='unrecorded_zero',
                    value=values.get(key), stabilized_value=None, peer_mean=None, z=None, percentile=None,
                    reliability=None, peer_count=0, density=[], quantiles=[]))
                continue
            peers = np.asarray(population.values[key], dtype=float)
            stat = calibrated.features[key]
            value = values.get(key)
            density, quantiles = cached_distribution(tuple(float(v) for v in peers))
            p = percentile(value, peers) if value is not None else None
            if definition.direction < 0 and p is not None:
                p = 100 - p
            feature_views.append(FeatureDistribution(key=key, label=definition.label, unit=definition.unit,
                direction=definition.direction, weight=weight, base_weight=base_weight,
                evidence_status=feature_statuses.get(key, 'observed'), value=value, stabilized_value=stat.stable,
                peer_mean=stat.mean, z=stat.z,
                percentile=p, reliability=stat.reliability, peer_count=peer_count, density=density, quantiles=quantiles))
        composite = calibrated.composite
        qz = composite.z
        peer_quality[name] = composite.peer_z
        qualities.append(AbilityScore(name=name, raw=composite.raw, z=qz,
            rating_unclipped=50 + 15 * qz if qz is not None else None, rating=display(qz),
            percentile=percentile(qz, peer_quality[name]) if qz is not None else None,
            available=sum(f.value is not None and f.evidence_status != 'unrecorded_zero' for f in feature_views), defined=len(features), features=feature_views))
    composite = calibrate_composite(weights, {q.name: q.z for q in qualities}, peer_quality)
    raw, z, peer_role = composite.raw, composite.z, composite.peer_z
    greater = peer_role[peer_role > z] if z is not None else []
    lower = peer_role[peer_role < z] if z is not None else []
    result = RoleScore(role_id=role_id, label=label, role_composite_raw=raw, role_z=z,
        rating_unclipped=50 + 15 * z if z is not None else None, rating=display(z),
        percentile=percentile(z, peer_role) if z is not None else None,
        rank=1 + len(greater) if z is not None else None, population_size=peer_count,
        gap_to_next_z=float(z - max(lower)) if len(lower) else None,
        gap_to_previous_z=float(min(greater) - z) if len(greater) else None,
        abilities=qualities, weights=weights)
    return result, peer_role


def unrated_role(role_id, label, abilities, weights, values, feature_statuses=None, definitions=None):
    """Preserve measurements without inventing a calibrated peer population."""
    definitions = definitions or BY_KEY
    scores = []
    feature_statuses = feature_statuses or {}
    for name, features in abilities.items():
        active = effective_weights(features, feature_statuses)
        views = [FeatureDistribution(key=key, label=definitions[key].label,
            unit=definitions[key].unit, direction=definitions[key].direction, weight=active[key], base_weight=weight,
            evidence_status=feature_statuses.get(key, 'observed'),
            value=values.get(key), stabilized_value=None, peer_mean=None, z=None,
            percentile=None, reliability=None, peer_count=0, density=[], quantiles=[])
            for key, weight in features.items()]
        scores.append(AbilityScore(name=name, raw=None, z=None, rating_unclipped=None,
            rating=None, percentile=None, available=sum(f.value is not None and f.evidence_status != 'unrecorded_zero' for f in views),
            defined=len(views), features=views))
    return RoleScore(role_id=role_id, label=label, role_composite_raw=None, role_z=None,
        rating_unclipped=None, rating=None, percentile=None, rank=None, population_size=0,
        gap_to_next_z=None, gap_to_previous_z=None, abilities=scores, weights=weights)


def hybrid_score(role_id, components, peers, weights):
    """Re-standardize weighted latent role scores against a joint eligible cohort."""
    if len(components) != len(weights) or abs(sum(weights) - 1) > 1e-8:
        raise ValueError("Hybrid weights must match components and sum to one")
    if any(c.role_z is None for c in components):
        return None
    raw = sum(w * c.role_z for w, c in zip(weights, components, strict=True))
    peer_raw = sum(w * p for w, p in zip(weights, peers, strict=True))
    z = standardize(raw, peer_raw)
    if z is None:
        return None
    pz = (peer_raw - np.mean(peer_raw)) / np.std(peer_raw) if np.std(peer_raw) > 1e-12 else np.zeros(len(peer_raw))
    return RoleScore(role_id=role_id, label=role_id.replace("-", " ").title(), role_composite_raw=raw,
        role_z=z, rating_unclipped=50 + 15 * z, rating=display(z), percentile=percentile(z, pz),
        rank=1 + int(np.sum(pz > z)), population_size=len(pz), gap_to_next_z=None, gap_to_previous_z=None,
        abilities=[], weights={c.role_id: w for c, w in zip(components, weights, strict=True)})


def joint_hybrid(components, peer_scores, peer_ids):
    """Align real peer identities before combining independently calibrated z."""
    mappings = [dict(zip(ids, z, strict=True)) for ids, z in zip(peer_ids, peer_scores, strict=True)]
    common = sorted(set(mappings[0]).intersection(*[set(m) for m in mappings[1:]]))
    if len(common) < 30:
        return None
    return hybrid_score("advanced-forward-false-nine", components,
                        [np.array([m[i] for i in common]) for m in mappings], [.5, .5])


def versatility(roles):
    valid = [r for r in roles if r.role_id != "ST" and r.role_z is not None]
    if len(valid) < 2:
        return None, {}
    primary = max(valid, key=lambda r: r.role_z)
    secondary = [r for r in valid if r.role_id != primary.role_id]
    breadth = sum(r.role_z >= 0 for r in secondary) / len(secondary)
    quality = float(np.mean([min(1, max(0, (r.role_z + 1) / 3)) for r in secondary]))
    consistency = float(np.mean([max(0, 1 - abs(primary.role_z - r.role_z) / 3) for r in secondary]))
    return 100 * (.4 * breadth + .4 * quality + .2 * consistency), {
        "breadth": breadth, "secondary_quality": quality, "consistency": consistency}
