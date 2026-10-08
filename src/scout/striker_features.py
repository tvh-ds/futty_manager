"""Versioned striker registry transcribed from Rating System/st_attributes.md.

Percentages use 0..100. Offsides are descriptive: the document explicitly
warns against treating attacking runs as a strong negative skill signal.
"""
from dataclasses import dataclass

from scout.position_config import WEIGHTING_VERSION as WEIGHTING_VERSION
from scout.position_config import registry

FEATURE_VERSION = "striker-features-v2"


def effective_weights(weights, statuses):
    """Redistribute only explicitly zero-filled weights, never recorded zeros."""
    retained = {k: w for k, w in weights.items() if statuses.get(k) != 'unrecorded_zero'}
    total = sum(retained.values())
    if total <= 0:
        return {k: 0.0 for k in weights}
    if len(retained) == len(weights):
        return dict(weights)
    original_total = sum(weights.values())
    return {k: w * original_total / total if k in retained else 0.0 for k, w in weights.items()}


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    numerator: str
    denominator: str = "minutes"
    unit: str = "per90"
    direction: int = 1


FEATURES = [
    Feature("npg90", "Non-penalty goals", "non_penalty_goals"),
    Feature("npxg90", "Non-penalty xG", "npxg"),
    Feature("finishing_delta90", "Goals above non-penalty xG", "finishing_delta"),
    Feature("shots90", "Shots", "shots"),
    Feature("sot90", "Shots on target", "shots_on_target"),
    Feature("sot_pct", "Shots on target %", "shots_on_target", "shots", "%"),
    Feature("goals_per_shot", "Non-penalty goals / shot", "non_penalty_goals", "non_penalty_shots", "ratio"),
    Feature("npxg_per_shot", "Non-penalty xG / shot", "npxg", "non_penalty_shots", "xG/shot"),
    Feature("box_shots90", "Shots inside the box", "shots_inside_box"),
    Feature("open_xg90", "Open-play xG", "open_play_xg"),
    Feature("headed_shots90", "Headed shots", "headed_shots"),
    Feature("box_touches90", "Opposition box touches", "touches_opposition_box"),
    Feature("offsides90", "Offsides (context only)", "offsides", direction=0),
    Feature("assists90", "Assists", "assists"),
    Feature("xa90", "Expected assists", "xa"),
    Feature("key_passes90", "Key passes", "key_passes"),
    Feature("sca90", "Shot-creating actions", "sca"),
    Feature("ppa90", "Passes into penalty area", "passes_into_penalty_area"),
    Feature("through_balls90", "Through balls", "through_balls"),
    Feature("pass_pct", "Pass completion %", "passes_completed", "passes_attempted", "%"),
    Feature("take_ons90", "Take-ons attempted", "take_ons_attempted"),
    Feature("successful_take_ons90", "Successful take-ons", "take_ons_successful"),
    Feature("take_on_pct", "Take-on success %", "take_ons_successful", "take_ons_attempted", "%"),
    Feature("box_carries90", "Carries into penalty area", "carries_into_penalty_area"),
    Feature("third_carries90", "Carries into final third", "carries_into_final_third"),
    Feature("carry_distance90", "Progressive carry distance", "progressive_carry_distance", unit="metres/90"),
    Feature("miscontrols90", "Miscontrols", "miscontrols", direction=-1),
    Feature("dispossessed90", "Dispossessed", "dispossessed", direction=-1),
    Feature("duels_won90", "Duels won", "duels_won"),
    Feature("duel_pct", "Duel success %", "duels_won", "duels_attempted", "%"),
    Feature("aerials_won90", "Aerial duels won", "aerial_duels_won"),
    Feature("aerial_pct", "Aerial success %", "aerial_duels_won", "aerial_duels_attempted", "%"),
    Feature("fouls_won90", "Fouls won", "fouls_won"),
    Feature("interceptions90", "Interceptions", "interceptions"),
    Feature("recoveries90", "Recoveries", "recoveries"),
    Feature("blocks90", "Blocks", "blocks"),
]
BY_KEY = {f.key: f for f in FEATURES}
ABILITIES, ST_WEIGHTS, _ = registry('ST')


def derive(raw: dict[str, float | None]) -> dict[str, float | None]:
    """Never replace missing denominators or unavailable event context with zero."""
    raw = dict(raw)
    raw["finishing_delta"] = (raw["non_penalty_goals"] - raw["npxg"]
                              if raw.get("non_penalty_goals") is not None and raw.get("npxg") is not None else None)
    raw["aerial_duels_attempted"] = (raw["aerial_duels_won"] + raw["aerial_duels_lost"]
                                   if raw.get("aerial_duels_won") is not None and raw.get("aerial_duels_lost") is not None else None)
    result = {}
    for f in FEATURES:
        a, b = raw.get(f.numerator), raw.get(f.denominator)
        result[f.key] = a / b * (90 if f.denominator == "minutes" else 100 if f.unit == "%" else 1) if a is not None and b and b > 0 else None
    return result


def measurement_statuses(raw, derived=None):
    """Explicit provenance classification; observed 0 never implies missing."""
    totals = dict(raw)
    totals['finishing_delta'] = (raw['non_penalty_goals'] - raw['npxg']
                                if raw.get('non_penalty_goals') is not None and raw.get('npxg') is not None else None)
    totals['aerial_duels_attempted'] = (raw['aerial_duels_won'] + raw['aerial_duels_lost']
                                      if raw.get('aerial_duels_won') is not None and raw.get('aerial_duels_lost') is not None else None)
    derived = derived or derive(raw)
    return {f.key: ('observed' if derived[f.key] is not None else 'unrecorded_zero'
                    if totals.get(f.numerator) is None or totals.get(f.denominator) is None else
                    'zero_exposure' if f.denominator == 'minutes' else 'not_applicable_zero_attempts') for f in FEATURES}
