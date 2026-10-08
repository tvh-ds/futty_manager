"""Versioned local squad dashboard, isolated from candidate publication."""
import hashlib
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

import numpy as np

from scout.contracts import Role
from scout.formations import formation, reassign
from scout.roles import METRIC_LABELS, ROLE_SPECS, TOP_FIVE
from scout.squad_contracts import (
    ChemistryComponent,
    ChemistryEdge,
    ChemistryResult,
    DashboardEvaluation,
    LineupState,
    PlayerRating,
    SkillContribution,
    SkillEvidence,
    SquadPlayer,
    SquadSnapshot,
)
from scout.striker_features import FEATURES as STRIKER_FEATURES

SNAPSHOT_ID = "liverpool-men-2026-27-20261006-v1"
SQUAD_ID = "liverpool-men"
FEATURE_VERSION = "demo-skills-v1"
PEER_VERSION = "fictional-five-league-peers-810-v1"
RATING_VERSION = "magnitude-base50-no-upper-cap-v2"
CHEMISTRY_VERSION = "equal-familiarity-demo-v1"
PROFILE_BASE = "https://www.liverpoolfc.com/teams/mens-team/"
SOURCES = [
    PROFILE_BASE + "alisson-becker",
    PROFILE_BASE + "ronald-araujo",
    PROFILE_BASE + "alexis-mac-allister",
    PROFILE_BASE + "victor-munoz",
    "https://www.liverpoolfc.com/news/liverpool-submit-premier-league-squad-list-2026-27?amp=1",
]

# Names, jersey numbers, official country tags and broad categories transcribed from
# the men's profile pages (including Other Players sections), checked 2026-10-06.
# Broad roles/side are MANUAL planning metadata, not sourced tactical conclusions.
ROSTER = [
    ("alisson-becker", "Alisson Becker", "Alisson", 1, "Brazil", "Goalkeeper", ["GK"], "centre"),
    ("giorgi-mamardashvili", "Giorgi Mamardashvili", "Mamardashvili", 25, "Georgia", "Goalkeeper", ["GK"], "centre"),
    ("freddie-woodman", "Freddie Woodman", "Woodman", 28, "England", "Goalkeeper", ["GK"], "centre"),
    ("vitezslav-jaros", "Vitezslav Jaros", "Jaros", 56, "Czechia", "Goalkeeper", ["GK"], "centre"),
    ("harvey-davies", "Harvey Davies", "Davies", 95, "England", "Goalkeeper", ["GK"], "centre"),
    ("joe-gomez", "Joe Gomez", "Gomez", 2, "England", "Defender", ["CB", "FB/WB"], "right"),
    ("virgil-van-dijk", "Virgil van Dijk", "Van Dijk", 4, "Netherlands", "Defender", ["CB"], "left"),
    ("jeremy-jacquet", "Jeremy Jacquet", "Jacquet", 5, "France", "Defender", ["CB"], "right"),
    ("milos-kerkez", "Milos Kerkez", "Kerkez", 6, "Hungary", "Defender", ["FB/WB"], "left"),
    ("conor-bradley", "Conor Bradley", "Bradley", 12, "Northern Ireland", "Defender", ["FB/WB"], "right"),
    ("giovanni-leoni", "Giovanni Leoni", "Leoni", 15, "Italy", "Defender", ["CB"], "centre"),
    ("kostas-tsimikas", "Kostas Tsimikas", "Tsimikas", 21, "Greece", "Defender", ["FB/WB"], "left"),
    ("jeremie-frimpong", "Jeremie Frimpong", "Frimpong", 30, "Netherlands", "Defender", ["FB/WB", "W"], "right"),
    ("ronald-araujo", "Ronald Araujo", "Araujo", 33, "Uruguay", "Defender", ["CB", "FB/WB"], "right"),
    ("luke-chambers", "Luke Chambers", "Chambers", 44, "England", "Defender", ["FB/WB", "CB"], "left"),
    ("wataru-endo", "Wataru Endo", "Endo", 3, "Japan", "Midfielder", ["DM", "CM"], "centre"),
    ("florian-wirtz", "Florian Wirtz", "Wirtz", 7, "Germany", "Midfielder", ["AM", "W", "CM"], "centre"),
    ("dominik-szoboszlai", "Dominik Szoboszlai", "Szoboszlai", 8, "Hungary", "Midfielder", ["CM", "AM"], "right"),
    ("alexis-mac-allister", "Alexis Mac Allister", "Mac Allister", 10, "Argentina", "Midfielder", ["CM", "DM"], "left"),
    ("ryan-gravenberch", "Ryan Gravenberch", "Gravenberch", 38, "Netherlands", "Midfielder", ["DM", "CM"], "centre"),
    ("trey-nyoni", "Trey Nyoni", "Nyoni", 42, "England", "Midfielder", ["CM", "AM"], "centre"),
    ("james-mcconnell", "James McConnell", "McConnell", 53, "England", "Midfielder", ["CM", "DM"], "centre"),
    ("alexander-isak", "Alexander Isak", "Isak", 9, "Sweden", "Forward", ["ST"], "centre"),
    ("federico-chiesa", "Federico Chiesa", "Chiesa", 14, "Italy", "Forward", ["W", "ST"], "right"),
    ("cody-gakpo", "Cody Gakpo", "Gakpo", 18, "Netherlands", "Forward", ["W", "ST"], "left"),
    ("hugo-ekitike", "Hugo Ekitike", "Ekitike", 22, "France", "Forward", ["ST", "W"], "centre"),
    ("victor-munoz", "Victor Munoz", "Munoz", 23, "Spain", "Forward", ["W"], "right"),
    ("bradley-barcola", "Bradley Barcola", "Barcola", 29, "France", "Forward", ["W"], "left"),
    ("lewis-koumas", "Lewis Koumas", "Koumas", 67, "Wales", "Forward", ["W", "ST"], "left"),
    ("rio-ngumoha", "Rio Ngumoha", "Ngumoha", 73, "England", "Forward", ["W"], "left"),
    ("jayden-danns", "Jayden Danns", "Danns", 76, "England", "Forward", ["ST"], "centre"),
]


def seeded_rng(identifier):
    return np.random.default_rng(int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:8], "big"))


def feature_keys(goalkeeper):
    roles = [Role.GK] if goalkeeper else [role for role in Role if role != Role.GK]
    return sorted(set().union(*(set(ROLE_SPECS[role].style) | set(ROLE_SPECS[role].quality) for role in roles)))


def emphasized_keys(role):
    return set(ROLE_SPECS[role].style) | set(ROLE_SPECS[role].quality)


def lower_is_better(key):
    return key in {"errors_p90", "turnovers_p90"}


def percentile(value, peers, lower=False):
    peers = np.asarray(peers, dtype=float)
    peers = peers[np.isfinite(peers)]
    if value is None or not np.isfinite(value) or not len(peers):
        return None
    score = 100 * (np.count_nonzero(peers < value) + 0.5 * np.count_nonzero(peers == value)) / len(peers)
    return float(100 - score if lower else score)


@lru_cache
def peer_population(goalkeeper):
    rng = np.random.default_rng(810 + int(goalkeeper))
    count = 500 if goalkeeper else 2100
    # Contiguous, equally sized league cohorts; all outfield roles share every
    # metric in this intentionally illustrative population.
    leagues = np.repeat(TOP_FIVE, count // 5)
    values = {}
    for key in feature_keys(goalkeeper):
        if key.endswith(("pct", "share")):
            data = rng.beta(5, 3, count)
        else:
            mean = 45 if key == "passes_p90" else 17 if key == "pressures_p90" else 0.12 if key == "errors_p90" else 0.3 if key in {"goals_p90", "assists_p90"} else 3.2
            data = rng.gamma(2, mean / 2, count)
        data.setflags(write=False)
        values[key] = data
    return leagues, values


def score_player(player, role, multiplier, unclipped=False):
    """Provisional non-ST positions use raw metric magnitude, never percentile.

    The multiplier remains a legacy planning control for provisional roles.
    Striker evaluation uses the versioned six-ability registry instead.
    """
    if role == Role.ST:
        from scout.striker_profiles import player_profile
        profile = player_profile(player.id)
        r = next((r for r in profile.roles if r.role_id == "ST"), None)
        available = sum(f.value is not None for q in r.abilities for f in q.features) if r else 0
        defined = sum(q.defined for q in r.abilities) if r else 38
        return ((r.rating_unclipped if unclipped else r.rating) if r and Role.ST in player.roles else None,
                available / defined * 100, available / defined * 100, 1, [])
    emphasized = emphasized_keys(role)
    if Role.ST in player.roles:
        from scout.striker_profiles import player_profile
        if player_profile(player.id).evidence == "observed":
            # Real ST evidence cannot be silently mixed with fictional W/other skills.
            return None, 0, 0, 0, []
    _, population = peer_population(role == Role.GK)
    # Fixed role-family subsets are illustrative; no claim about actual eligibility.
    indices = np.arange(len(next(iter(population.values()))))
    if role != Role.GK:
        offset = [r for r in Role if r != Role.GK].index(role)
        indices = indices[indices % 7 == offset]
    available = [skill for skill in player.skills if skill.raw_value is not None and skill.key in population]
    role_defined = [skill for skill in player.skills if skill.key in emphasized]
    role_available = [skill for skill in role_defined if skill.raw_value is not None and skill.key in population]
    coverage = 100 * len(available) / len(player.skills) if player.skills else 0
    role_coverage = 100 * len(role_available) / len(role_defined) if role_defined else 0
    total_weight = sum(multiplier if skill.key in emphasized else 1 for skill in available)
    sufficient = coverage >= 70 and role_coverage >= 50 and total_weight > 0
    from scout.ability_engine import display, standardize
    raw, peer_raw = 0.0, np.zeros(len(indices))
    z_values = {}
    for skill in available:
        peers = population[skill.key][indices]
        z = standardize(skill.raw_value, peers) * (-1 if skill.lower_is_better else 1)
        weight = multiplier if skill.key in emphasized else 1
        z_values[skill.key] = z
        raw += weight * z / total_weight
        sd = np.std(peers)
        peer_raw += weight / total_weight * ((peers - np.mean(peers)) / sd if sd > 1e-12 else np.zeros(len(peers))) * (-1 if skill.lower_is_better else 1)
    latent = standardize(raw, peer_raw) if sufficient else None
    score = (50 + 15 * latent if unclipped else display(latent)) if latent is not None else None
    contributions = [SkillContribution(skill=skill, emphasized=skill.key in emphasized,
        weight=multiplier if skill.key in emphasized else 1,
        contribution=(z_values[skill.key] * (multiplier if skill.key in emphasized else 1) / total_weight)
        if skill.key in z_values and total_weight else None) for skill in player.skills]
    return score, coverage, role_coverage, total_weight, contributions


def player_rating(player, role, multiplier):
    score, coverage, role_coverage, total, skills = score_player(player, role, multiplier)
    warnings = []
    if role not in player.roles:
        warnings.append("Outside manually assigned planning roles; no performance penalty is inferred")
    if score is None:
        warnings.append("Insufficient evidence for assigned position; striker abilities require complete weighted features and an adequate cohort")
    role_scores = {r.value: score_player(player, r, multiplier)[0] for r in player.roles}
    latent_ratings = {r.value: score_player(player, r, multiplier, unclipped=True)[0] for r in player.roles}
    evidence = "synthetic"
    if Role.ST in player.roles:
        from scout.striker_profiles import player_profile
        profile = player_profile(player.id)
        for r in profile.roles:
            role_scores[r.role_id], latent_ratings[r.role_id] = r.rating, r.rating_unclipped
        evidence = profile.evidence if role == Role.ST else "synthetic"
    primary = max((r for r, v in latent_ratings.items() if v is not None), key=lambda r: latent_ratings[r], default=None)
    z, unclipped, rank_pct = None, None, None
    if role == Role.ST and Role.ST in player.roles:
        st = next((r for r in profile.roles if r.role_id == "ST"), None)
        if st:
            z, unclipped, rank_pct = st.role_z, st.rating_unclipped, st.percentile
        warnings.append("Six-ability striker model; fixed supplied weights. Role multiplier does not alter ST weights.")
    else:
        warnings.append("Provisional position metrics; rigorous feature set has only been supplied for ST")
    return PlayerRating(player_id=player.id, role=role, score=score,
        normal_role_score=role_scores.get(primary), coverage=coverage,
        role_coverage=role_coverage, available=round(len(STRIKER_FEATURES) * coverage / 100) if role == Role.ST else sum(s.raw_value is not None for s in player.skills),
        defined=len(STRIKER_FEATURES) if role == Role.ST else len(player.skills), total_weight=total, skills=skills, warnings=warnings,
        role_z=z, rating_unclipped=unclipped, percentile=rank_pct, primary_role=primary, role_scores=role_scores, evidence=evidence)


def rounded(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def chemistry_band(score):
    if score is None:
        return "unknown"
    score = rounded(score)
    return "red" if score <= 3.33 else "yellow" if score <= 6.66 else "green"


def chemistry_measures(nationalities_a=None, nationalities_b=None, club_days=None,
                       languages_a=None, languages_b=None, languages_complete=False,
                       age_gap=None, shared_minutes=None, nationalities_complete=True):
    """Complete, verified absence is zero; unavailable/incomplete evidence is None."""
    nationality = None
    if nationalities_a is not None and nationalities_b is not None:
        if set(nationalities_a) & set(nationalities_b):
            nationality = 10.0
        elif nationalities_complete:
            nationality = 0.0
    language = None
    if languages_a is not None and languages_b is not None:
        if set(languages_a) & set(languages_b):
            language = 10.0
        elif languages_complete:
            language = 0.0
    return [nationality, min(max(club_days, 0) / 365, 1) * 10 if club_days is not None else None,
            language, max(0, 1 - abs(age_gap) / 10) * 10 if age_gap is not None else None,
            min(max(shared_minutes, 0) / 1800, 1) * 10 if shared_minutes is not None else None]


def shared_tenure_days(tenures_a, tenures_b):
    """Union of shared-club half-open date intervals, avoiding duplicate stints."""
    intervals = sorted((max(a[1], b[1]), min(a[2], b[2]))
                       for a in tenures_a for b in tenures_b
                       if a[0] == b[0] and max(a[1], b[1]) < min(a[2], b[2]))
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum((end - start).days for start, end in merged)


def concurrent_minutes(intervals_a, intervals_b):
    """Concurrent intervals in one match for players verified as teammates."""
    def merge(intervals):
        result = []
        for start, end in sorted(intervals):
            if start < 0 or end < start or end > 150:
                raise ValueError("Invalid match interval")
            if result and start <= result[-1][1]:
                result[-1] = (result[-1][0], max(end, result[-1][1]))
            else:
                result.append((start, end))
        return result
    return sum(max(0, min(a[1], b[1]) - max(a[0], b[0]))
               for a in merge(intervals_a) for b in merge(intervals_b))


def aggregate_chemistry(a, b, components):
    scores = [item.score for item in components if item.score is not None]
    score = rounded(sum(scores) / len(scores)) if len(scores) >= 3 else None
    return ChemistryResult(player_a=a, player_b=b, score=score, band=chemistry_band(score),
                           available=len(scores), components=components)


@lru_cache(maxsize=600)
def demo_chemistry(a, b):
    a, b = sorted((a, b))
    rng = seeded_rng(f"{CHEMISTRY_VERSION}:{a}:{b}")
    values = chemistry_measures(
        nationalities_a=["demo-A"], nationalities_b=["demo-A" if rng.random() > 0.55 else "demo-B"],
        club_days=int(rng.integers(0, 700)), languages_a=["demo-language-A"],
        languages_b=["demo-language-A" if rng.random() > 0.3 else "demo-language-B"],
        languages_complete=True, age_gap=int(rng.integers(0, 15)), shared_minutes=int(rng.integers(0, 3000)))
    labels = ["Shared nationality", "Overlapping club tenure", "Shared language", "Age proximity", "Shared competitive minutes"]
    keys = ["nationality", "club_tenure", "language", "age", "minutes"]
    components = [ChemistryComponent(key=key, label=label, score=rounded(value), evidence="synthetic",
        explanation="Seeded illustrative component. No claim about these players' actual nationality overlap, languages, ages, career history or shared minutes.")
        for key, label, value in zip(keys, labels, values, strict=True)]
    return aggregate_chemistry(a, b, components)


@lru_cache
def squad_snapshot():
    players = []
    for slug, name, short, number, country, category, roles, side in ROSTER:
        keeper = category == "Goalkeeper"
        _, peers = peer_population(keeper)
        rng = seeded_rng(f"{FEATURE_VERSION}:{slug}")
        emphasis = emphasized_keys(Role(roles[0]))
        skills = []
        for key, population in peers.items():
            q = float(rng.uniform(0.78, 0.99) if key in emphasis else rng.uniform(0.43, 0.88))
            raw = float(np.quantile(population, 1 - q if lower_is_better(key) else q))
            skills.append(SkillEvidence(key=key, label=METRIC_LABELS[key], raw_value=raw,
                unit="ratio" if key.endswith(("pct", "share")) else "per90",
                percentile=percentile(raw, population, lower_is_better(key)), peer_count=len(population),
                lower_is_better=lower_is_better(key)))
        players.append(SquadPlayer(id=f"lfc-{slug}", name=name, short_name=short, number=number,
            country_label=country, category=category, roles=roles, planning_side=side,
            source_url=PROFILE_BASE + slug, skills=skills))
    starting = {"GK": "alisson-becker", "LB": "milos-kerkez", "LCB": "virgil-van-dijk", "RCB": "ronald-araujo",
        "RB": "jeremie-frimpong", "DM": "ryan-gravenberch", "LCM": "alexis-mac-allister", "RCM": "dominik-szoboszlai",
        "LW": "bradley-barcola", "ST": "alexander-isak", "RW": "victor-munoz"}
    assignments = {slot: f"lfc-{slug}" for slot, slug in starting.items()}
    bench_slugs = ["giorgi-mamardashvili", "joe-gomez", "conor-bradley", "jeremy-jacquet", "wataru-endo",
                   "florian-wirtz", "cody-gakpo", "hugo-ekitike", "federico-chiesa"]
    return SquadSnapshot(id=SQUAD_ID, team="Liverpool", league="England", season="2026/27",
        snapshot_date=date(2026, 10, 6), snapshot_id=SNAPSHOT_ID, players=players,
        default_lineup=LineupState(snapshot_id=SNAPSHOT_ID, assignments=assignments,
            bench=[f"lfc-{slug}" for slug in bench_slugs]), sources=SOURCES,
        feature_version=FEATURE_VERSION, peer_version=PEER_VERSION, rating_version=RATING_VERSION,
        chemistry_version=CHEMISTRY_VERSION, peer_counts={"outfield": 2100, "goalkeepers": 500},
        observation_window="Illustrative fixtures only; no actual 2026/27 performance window",
        limitations=["Liverpool squad identities are sourced. Ratings and chemistry are demonstration data.",
            "Men's first-team snapshot; separate academy/U21 squad roster excluded. First-team-listed young players remain included.",
            "Snapshot checked 6 October 2026; not a live transfer, injury or eligibility feed.",
            "Specific role families and sides are manual planning metadata, not verified tactical suitability.",
            "Country tags follow official profile labels, not a complete citizenship record.",
            "Custom planning XI and nine bench places are not an official matchday selection.",
            "Ratings use magnitude z-scores and base 50. Striker peers are fictional role-specific cohorts; other positions remain provisional.",
            "Chemistry is a familiarity proxy; does not estimate performance or increase player ratings."])


def validate_lineup(lineup, snapshot_override=None):
    snapshot = snapshot_override or squad_snapshot()
    if lineup.snapshot_id != snapshot.snapshot_id:
        raise ValueError("Squad snapshot changed; import requires the current snapshot identifier")
    selected_formation = formation(lineup.formation_id)
    if set(lineup.assignments) != {slot.id for slot in selected_formation.slots}:
        raise ValueError("Assignments must contain exactly the selected formation's eleven slot identifiers")
    players = {player.id: player for player in snapshot.players}
    for pid in [*lineup.assignments.values(), *lineup.bench]:
        if pid is not None and pid not in players:
            raise ValueError("Lineup contains a player outside this squad snapshot")
    for slot in selected_formation.slots:
        pid = lineup.assignments[slot.id]
        if pid and (slot.role == Role.GK) != (Role.GK in players[pid].roles):
            raise ValueError("Goalkeepers and outfield players cannot exchange slot types")
    return snapshot, selected_formation, players


def evaluate_lineup(lineup, rating_function=None, snapshot_override=None, position_rating_function=None):
    snapshot, selected_formation, players = validate_lineup(lineup, snapshot_override)
    roles = {pid: slot.role for slot in selected_formation.slots if (pid := lineup.assignments[slot.id])}
    positions = {pid: slot.label for slot in selected_formation.slots if (pid := lineup.assignments[slot.id])}
    ratings = {pid: position_rating_function(player, roles.get(pid, player.roles[0]), positions.get(pid), lineup.role_multiplier)
               if position_rating_function else (rating_function or player_rating)(player, roles.get(pid, player.roles[0]), lineup.role_multiplier)
               for pid, player in players.items()}
    edges = []
    for slot_a, slot_b in selected_formation.edges:
        a, b = lineup.assignments[slot_a], lineup.assignments[slot_b]
        if a and b:
            edges.append(ChemistryEdge(slot_a=slot_a, slot_b=slot_b, chemistry=demo_chemistry(*sorted((a, b)))))
    scores = [ratings[pid].score for pid in roles]
    chemistry = [edge.chemistry.score for edge in edges if edge.chemistry.score is not None]
    occupied = set(roles) | set(lineup.bench)
    return DashboardEvaluation(lineup=lineup, ratings=ratings, edges=edges,
        team_rating=sum(scores) / 11 if len(scores) == 11 and all(score is not None for score in scores) else None,
        team_chemistry=rounded(sum(chemistry) / len(chemistry)) if chemistry else None,
        chemistry_scored_links=len(chemistry), chemistry_total_links=len(selected_formation.edges),
        completeness=len(roles), reserve_ids=[pid for pid in players if pid not in occupied],
        feature_version=snapshot.feature_version, peer_version=snapshot.peer_version,
        rating_version=snapshot.rating_version, chemistry_version=snapshot.chemistry_version,
        warnings=["Illustrative ratings and familiarity inputs; no claims of actual Liverpool skill or pair performance",
                  "All player roles/sides are manual planning assignments; squad remains browser-local"])


def change_formation(lineup, destination):
    _, _, players = validate_lineup(lineup)
    next_lineup = reassign(lineup, destination, players)
    validate_lineup(next_lineup)
    return next_lineup
