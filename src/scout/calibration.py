"""Shared numerical calibration; callers own cohort selection and provenance."""
from dataclasses import dataclass

import numpy as np

from scout.striker_features import BY_KEY, effective_weights

SHRINKAGE = {'minutes': 450, 'shots': 30, 'non_penalty_shots': 30,
             'passes_attempted': 200, 'take_ons_attempted': 30,
             'duels_attempted': 50, 'aerial_duels_attempted': 30}


def percentile(value, peers):
    peers = np.asarray(peers)
    peers = peers[np.isfinite(peers)]
    return float(100 * (np.sum(peers < value) + .5 * np.sum(peers == value)) / len(peers)) if len(peers) else None


def standardize(value, peers):
    peers = np.asarray(peers)
    peers = peers[np.isfinite(peers)]
    if len(peers) < 2 or value is None or not np.isfinite(value):
        return None
    sd = float(np.std(peers, ddof=0))
    mean = float(np.mean(peers))
    if sd > 1e-12:
        return (float(value) - mean) / sd
    return 0.0 if abs(float(value) - mean) <= 1e-12 else None


def display(z):
    return float(max(1, 50 + 15 * z)) if z is not None else None


def shrink(value, exposure, mean, k):
    if value is None or exposure is None or not np.isfinite(value) or exposure <= 0:
        return None, None
    reliability = exposure / (exposure + k)
    return reliability * value + (1 - reliability) * mean, reliability


def peer_standardize(values):
    sd = float(np.std(values))
    return (values - np.mean(values)) / sd if sd > 1e-12 else np.zeros(len(values))


@dataclass
class FeatureCalibration:
    mean: float
    stable_peers: np.ndarray
    peer_reliability: np.ndarray
    peer_z: np.ndarray
    stable: float | None
    reliability: float | None
    z: float | None


@dataclass
class CompositeCalibration:
    raw: float | None
    z: float | None
    peer_raw: np.ndarray
    peer_z: np.ndarray


@dataclass
class AbilityCalibration:
    composite: CompositeCalibration
    features: dict[str, FeatureCalibration]
    weights: dict[str, float]


def calibrate_ability(weights, peer_values, peer_exposures, statuses=None, values=None, exposures=None, definitions=None):
    """Calibrate one ability on caller-selected, aligned observations.

    Peer exposures are keyed by feature so provider-local denominators survive.
    Optional subject values use those same definitions; no cohort is inferred.
    Only explicitly zero-filled features redistribute weights.
    """
    definitions = definitions or BY_KEY
    active = effective_weights(weights, statuses or {})
    count = len(next(iter(peer_values.values())))
    peer_raw, raw = np.zeros(count), 0.0
    complete = any(active[k] > 0 and definitions[k].direction for k in weights)
    result = {}
    for key, observations in peer_values.items():
        if not active[key]:
            continue
        definition = definitions[key]
        observations = np.asarray(observations, dtype=float)
        n = np.asarray(peer_exposures[key], dtype=float)
        if observations.ndim != 1 or n.shape != observations.shape or len(n) != count:
            raise ValueError('Calibration peers must be aligned')
        mean = float(np.mean(observations))
        prior = SHRINKAGE.get(definition.denominator, 30)
        reliability = n / (n + prior)
        stable_peers = reliability * observations + (1 - reliability) * mean
        zs = definition.direction * peer_standardize(stable_peers)
        stable, subject_r = shrink((values or {}).get(key), (exposures or {}).get(key),
                                  mean, prior)
        subject_z = standardize(stable, stable_peers)
        z = definition.direction * subject_z if subject_z is not None else None
        peer_raw += active[key] * zs
        if values is not None and definition.direction and z is None:
            complete = False
        if z is not None:
            raw += active[key] * z
        result[key] = FeatureCalibration(mean, stable_peers, reliability, zs, stable, subject_r, z)
    # Subject adapters supply every active directional feature.
    if values is not None and any(active[k] and definitions[k].direction and k not in result for k in weights):
        complete = False
    raw = raw if values is not None and complete else None
    composite = CompositeCalibration(raw, standardize(raw, peer_raw), peer_raw, peer_standardize(peer_raw))
    return AbilityCalibration(composite, result, active)


def calibrate_composite(weights, values, peer_values):
    """Compose already-calibrated latent scores; callers align peer identities."""
    raw = sum(weights[k] * values[k] for k in weights) if all(values[k] is not None for k in weights) else None
    shapes = {np.asarray(peer_values[k]).shape for k in weights}
    if len(shapes) != 1:
        raise ValueError('Composite peers must be aligned')
    peers = sum(weights[k] * np.asarray(peer_values[k]) for k in weights)
    return CompositeCalibration(raw, standardize(raw, peers), peers, peer_standardize(peers))
