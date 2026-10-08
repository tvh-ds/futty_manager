"""Frozen illustrative striker populations; observed releases use a separate path."""
from functools import lru_cache

import numpy as np

from scout.ability_contracts import AbilityProfile
from scout.ability_engine import NORMALIZATION_VERSION, Population, evaluate_role, joint_hybrid, versatility
from scout.striker_features import ABILITIES, FEATURE_VERSION, FEATURES, ST_WEIGHTS, WEIGHTING_VERSION

PROVISIONAL_VERSION = "archetype-provisional-v1:" + WEIGHTING_VERSION
# User-authorized initial coefficients, not learned or football-validated.
ROLE_WEIGHTS = {
    "ST": tuple(ST_WEIGHTS.values()),
    "poacher": (.36, .30, .10, .08, .10, .06),
    "advanced-forward": (.30, .24, .12, .18, .10, .06),
    "target-forward": (.25, .25, .14, .06, .24, .06),
    "complete-forward": (.23, .19, .19, .16, .14, .09),
    "false-nine": (.18, .12, .30, .22, .08, .10),
    "pressing-forward": (.22, .17, .14, .14, .13, .20),
}


@lru_cache
def demo_population(role_id="ST"):
    """420 fictional role peers, 84 per league. Not the real player database."""
    rng = np.random.default_rng(191026)
    latent = rng.normal(0, 1, (420, 6))
    minutes = rng.integers(900, 3300, 420).astype(float)
    exposures = {"minutes": minutes, "shots": rng.integers(20, 130, 420).astype(float),
        "non_penalty_shots": rng.integers(18, 120, 420).astype(float),
        "passes_attempted": rng.integers(300, 1400, 420).astype(float),
        "take_ons_attempted": rng.integers(20, 150, 420).astype(float),
        "duels_attempted": rng.integers(50, 300, 420).astype(float),
        "aerial_duels_attempted": rng.integers(20, 120, 420).astype(float)}
    values = {}
    for i, f in enumerate(FEATURES):
        signal = .6 * latent[:, i % 6] + .8 * rng.normal(0, 1, 420)
        if f.unit == "%":
            values[f.key] = np.clip(60 + 14 * signal, 1, 99)
        elif f.key == "finishing_delta90":
            values[f.key] = .12 * signal
        else:
            mean = .4 if "xg" in f.key or f.key == "npg90" else .12 if f.unit in {"ratio", "xG/shot"} else 60 if "distance" in f.key else 2
            values[f.key] = mean * np.exp(.5 * signal)
    # Archetype cohorts differ by an explicitly illustrative profile filter.
    offset = list(ROLE_WEIGHTS).index(role_id)
    mask = np.ones(420, dtype=bool) if role_id == "ST" else latent[:, offset % 6] > -.65
    return Population(id=f"fictional-striker-role-peers-191026-v2-{role_id}",
        values={k: v[mask] for k, v in values.items()}, exposure={k: v[mask] for k, v in exposures.items()},
        role_id=role_id, season="2026/27", competition="Illustrative five-league role peers; no league-strength claim",
        peer_ids=tuple(str(i) for i in np.arange(420)[mask]))


@lru_cache(maxsize=64)
def demo_profile(player_id):
    base = demo_population()
    seed = int.from_bytes(__import__("hashlib").sha256(player_id.encode()).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    # These measured-looking values are fictional fixtures, never sourced facts.
    values = {f.key: float(np.quantile(base.values[f.key], rng.uniform(.55, .98) if f.direction >= 0 else rng.uniform(.1, .5))) for f in FEATURES}
    exposures = {k: float(np.median(v)) for k, v in base.exposure.items()}
    evaluations = [evaluate_role(key, "Striker · position" if key == "ST" else key.replace("-", " ").title(),
             ABILITIES, dict(zip(ABILITIES, w, strict=True)), values, exposures, demo_population(key))[0]
             for key, w in ROLE_WEIGHTS.items()]
    roles = evaluations
    primary = max(roles, key=lambda r: r.role_z if r.role_z is not None else -float("inf"))
    # A hybrid must calibrate on the same joint eligible players, not unrelated arrays.
    joint_keys = ("advanced-forward", "false-nine")
    joint_roles = [evaluate_role(key, key, ABILITIES, dict(zip(ABILITIES, ROLE_WEIGHTS[key], strict=True)),
                  values, exposures, demo_population(key)) for key in joint_keys]
    hybrid = joint_hybrid([r for r, _ in joint_roles], [p for _, p in joint_roles], [demo_population(k).peer_ids for k in joint_keys])
    versatility_score, components = versatility(roles)
    return AbilityProfile(player_id=player_id, position="ST", primary_role_id=primary.role_id,
        primary_rating=primary.rating, primary_role_z=primary.role_z, roles=roles, hybrids=[hybrid] if hybrid else [],
        versatility=versatility_score, versatility_components=components,
        season=base.season, competition=base.competition, minutes=exposures["minutes"], evidence="synthetic",
        reference_population_id=base.id, normalization_version=NORMALIZATION_VERSION,
        weighting_version=PROVISIONAL_VERSION, feature_version=FEATURE_VERSION,
        calculation_timestamp="2026-10-06T00:00:00Z", limitations=[
            "Every numeric measurement and peer is fictional; identities alone are sourced.",
            "Archetypes are manual striker-planning evaluations, not verified tactical suitability.",
            "Archetype weights, reliability priors and versatility formula are provisional, not calibrated.",
            "Broad ST weights follow the supplied file; Defensive Activity weights reflect the approved v2 feature removal.",
            "Offsides have zero directional contribution pending context.",
            "Defensive Activity measures recoveries, interceptions and blocks, not pressing effectiveness.",
            "Only explicitly zero-filled unrecorded features redistribute their weights; recorded zeros retain weight.",
            "No verified live source currently covers the complete requested feature set."])


def player_profile(player_id):
    from scout.striker_refresh import active_profile
    observed = active_profile(player_id)
    if observed is not None and observed.season != "2026/27":
        raise ValueError("Observed striker season is incompatible with this squad snapshot")
    return observed if observed is not None else demo_profile(player_id)
