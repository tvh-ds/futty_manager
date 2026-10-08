import numpy as np
from scipy.stats import beta, gamma, percentileofscore

from scout.contracts import (
    DatasetRelease,
    PlayerStint,
    Recommendation,
    RecruitmentBrief,
    Role,
    RoleProfile,
    ScenarioRequest,
    ScenarioResult,
    Team,
)
from scout.roles import METRIC_LABELS, ROLE_SPECS


def posterior(player: PlayerStint, key: str, prior_mean: float):
    metric = player.metrics[key]
    if metric.unit == "ratio":
        if metric.numerator is None or metric.denominator is None:
            return metric.value, (0.0, 1.0)
        strength = 20
        alpha = metric.numerator + max(prior_mean, 0.01) * strength
        beta_value = metric.denominator - metric.numerator + max(1 - prior_mean, 0.01) * strength
        return alpha / (alpha + beta_value), tuple(float(value) for value in beta.ppf([0.05, 0.95], alpha, beta_value))
    if metric.unit == "per90" and metric.numerator is not None and player.minutes > 0:
        exposure = player.minutes / 90
        strength = 5.0
        shape = metric.numerator + max(prior_mean, 0.001) * strength
        rate = exposure + strength
        return shape / rate, tuple(float(value) for value in gamma.ppf([0.05, 0.95], shape, scale=1 / rate))
    return metric.value, (metric.value, metric.value)


class RecruitmentEngine:
    def __init__(self, release: DatasetRelease, players: list[PlayerStint], teams: list[Team]):
        self.release = release
        self.players = {player.id: player for player in players}
        self.teams = {team.id: team for team in teams}
        self.profiles: dict[tuple[str, Role], RoleProfile] = {}
        for role, spec in ROLE_SPECS.items():
            peers = [player for player in players if role in player.roles]
            keys = set(spec.style) | set(spec.quality)
            for player in peers:
                cohort = [peer for peer in peers if peer.league == player.league]
                values, intervals, percentiles = {}, {}, {}
                for key in sorted(keys):
                    if key not in player.metrics or (player.minutes == 0 and player.metrics[key].unit == "per90"):
                        continue
                    observed = [peer.metrics[key].value for peer in cohort if key in peer.metrics and peer.minutes > 0]
                    if not observed:
                        continue
                    prior = float(np.mean(observed))
                    value, interval = posterior(player, key, prior)
                    shrunk = [posterior(peer, key, prior)[0] for peer in cohort if key in peer.metrics and peer.minutes > 0]
                    values[key] = value
                    intervals[key] = interval
                    percentiles[key] = float(percentileofscore(shrunk, value, kind="mean"))
                self.profiles[player.id, role] = RoleProfile(
                    player_stint_id=player.id, role=role, values=values, intervals=intervals,
                    percentiles=percentiles, coverage=100 * len(values) / len(keys),
                )

    def profile(self, player_id: str, role: Role | None = None):
        player = self.players[player_id]
        return self.profiles[player_id, role or player.roles[0]]

    def distance_score(self, profile: RoleProfile, target: dict[str, float], preferences: dict[str, float]):
        keys = sorted(set(profile.values) & set(target) & set(ROLE_SPECS[profile.role].style))
        if not keys:
            return None
        distances, weights = [], []
        for key in keys:
            observed = [item.values[key] for (_, role), item in self.profiles.items()
                        if role == profile.role and key in item.values]
            quartiles = np.quantile(observed, [0.25, 0.75])
            scale = max(float(quartiles[1] - quartiles[0]), abs(float(np.median(observed))) * 0.1, 0.01)
            distances.append(((profile.values[key] - target[key]) / scale) ** 2)
            weights.append(preferences.get(key, 1.0))
        if sum(weights) == 0:
            return None
        return float(100 * np.exp(-np.sqrt(np.average(distances, weights=weights)) / 2))

    def recommend(self, brief: RecruitmentBrief):
        spec = ROLE_SPECS[brief.role]
        invalid_preferences = set(brief.preferences) - set(spec.style) - set(spec.quality)
        if invalid_preferences:
            raise ValueError("Preferences must name supported metrics for this role")
        if set(brief.intended_style) - set(spec.style):
            raise ValueError("Intended style must name supported style metrics for this role")
        if any(value > 1 for key, value in brief.intended_style.items() if key.endswith(("pct", "share"))):
            raise ValueError("Intended ratio targets must be between zero and one")
        if brief.team_id and brief.team_id not in self.teams:
            raise KeyError(brief.team_id)
        replacement = self.players.get(brief.replacement_id) if brief.replacement_id else None
        if brief.replacement_id and replacement is None:
            raise KeyError(brief.replacement_id)
        if replacement and brief.role not in replacement.roles:
            raise ValueError("Replacement player does not have the requested role")
        role_profiles = [profile for (_, role), profile in self.profiles.items() if role == brief.role]
        target = self.profile(replacement.id, brief.role).values if replacement else {
            key: float(np.quantile([profile.values[key] for profile in role_profiles if key in profile.values], 0.65))
            for key in spec.style if any(key in profile.values for profile in role_profiles)
        }
        team = self.teams.get(brief.team_id)
        results = []
        for player in self.players.values():
            if brief.role not in player.roles or player.id == brief.replacement_id:
                continue
            constraints = brief.constraints
            if player.minutes < constraints.min_minutes:
                continue
            unknowns = []
            if player.age is None:
                unknowns.append("Age must be verified")
            elif not constraints.min_age <= player.age <= constraints.max_age:
                continue
            if constraints.foot:
                if player.foot is None:
                    unknowns.append("Preferred foot must be verified")
                elif player.foot != constraints.foot and player.foot != "both":
                    continue
            rejected = False
            for attribute in constraints.attributes:
                value = player.attributes.get(attribute)
                if value is False:
                    rejected = True
                elif value is None:
                    unknowns.append(f"{attribute.replace('_', ' ').capitalize()} must be verified by scouting")
            if rejected or (unknowns and not brief.include_verification_required):
                continue
            profile = self.profile(player.id, brief.role)
            available_quality = {key: direction for key, direction in spec.quality.items() if key in profile.percentiles}
            quality = float(np.mean([profile.percentiles[key] if direction > 0 else 100 - profile.percentiles[key]
                                     for key, direction in available_quality.items()])) if available_quality else None
            similarity = self.distance_score(profile, target, brief.preferences)
            tactical_target = brief.intended_style or (team.style_targets if team else {})
            tactical = self.distance_score(profile, tactical_target, brief.preferences)
            changes = {key: profile.values[key] - value for key, value in target.items()
                       if replacement and key in profile.values}
            functions = {key: ("preserved" if abs(delta) <= max(abs(target[key]) * 0.1, 0.02)
                               else ("improved" if delta * spec.quality[key] > 0 else "compromised")
                               if key in spec.quality else "redistributed") for key, delta in changes.items()}
            components = {"similarity": similarity, "quality": quality, "tactical_fit": tactical,
                          "replacement_fit": similarity if replacement else None, "coverage": profile.coverage}
            applicable = {key: weight for key, weight in brief.weights.items()
                          if weight > 0 and components.get(key) is not None}
            score = sum(components[key] * weight for key, weight in applicable.items()) / sum(applicable.values()) if applicable else 0
            score *= 0.5 + 0.5 * profile.coverage / 100
            reasons = [f"{profile.coverage:.0f}% of role metrics available",
                       f"Quality uses {player.league} / {brief.role.value} peers; league talent is not calibrated"]
            if quality is not None:
                reasons.append("Quality is an exposure-adjusted statistical proxy, with team and opponent confounding")
            if brief.intended_style:
                reasons.append("Team fit uses your manually entered intended targets, not observed team measurements")
            if functions:
                reasons.append("Replacement function labels use metric direction and a 10% tolerance; they are not causal improvements")
            if player.role_evidence.value == "inferred":
                unknowns.append("Inferred role must be verified")
            if profile.coverage < 25:
                status = "insufficient_evidence"
                reasons.append("Too little evidence for a confident ranking")
            else:
                status = "verification_required" if unknowns else "eligible"
            results.append(Recommendation(player=player, score=score, components=components, status=status,
                                          reasons=reasons, unknowns=unknowns, profile=profile,
                                          replacement_changes=changes, replacement_functions=functions))
        return sorted(results, key=lambda item: (-item.score, item.player.id))[:brief.limit]

    def simulate(self, request: ScenarioRequest):
        player = self.players[request.player_id]
        team = self.teams[request.team_id]
        rng = np.random.default_rng(request.seed)
        if request.availability_mean in (0, 1):
            availability = np.full(request.samples, request.availability_mean)
        else:
            availability = rng.beta(request.availability_mean * 20, (1 - request.availability_mean) * 20, request.samples)
        minutes = request.season_minutes * availability
        adaptation = np.clip(rng.normal(request.adaptation_mean, request.adaptation_sd, request.samples), 0, 2)
        profile = self.profile(player.id)
        outcomes = {}
        for key, value in profile.values.items():
            if player.metrics[key].unit == "per90":
                draws = rng.poisson(np.maximum(value * minutes / 90 * adaptation, 0))
                outcomes[METRIC_LABELS.get(key, key)] = tuple(float(item) for item in np.quantile(draws, [0.1, 0.5, 0.9]))
        assignments = dict(request.assignments)
        if not assignments:
            assignments = {item.id: item.roles[0] for item in self.players.values()
                           if item.team_id == team.id and item.player_id != player.player_id}
            assignments[player.id] = player.roles[0]
        identities = []
        coverage = {role.value: 0 for role in Role}
        for stint_id, role in assignments.items():
            selected = self.players[stint_id]
            if role not in selected.roles:
                raise ValueError("A squad assignment must use a player's supported role")
            if selected.team_id != team.id and selected.id != player.id:
                raise ValueError("Assignments may include only the destination squad and the selected recruit")
            identities.append(selected.player_id)
            coverage[role.value] += 1
        if len(set(identities)) != len(identities):
            raise ValueError("A player cannot fill multiple simultaneous roles through different stints")
        if set(request.fees) - set(assignments):
            raise ValueError("Fees must refer to assigned players")
        fee_known = bool(assignments) and all(stint_id in request.fees for stint_id in assignments)
        total = sum(request.fees.values()) if fee_known else None
        return ScenarioResult(
            release=self.release, request=request.model_copy(deep=True), seed=request.seed,
            assumptions=request.model_dump(include={"season_minutes", "adaptation_mean", "adaptation_sd", "availability_mean", "samples"}),
            minutes_interval=tuple(float(item) for item in np.quantile(minutes, [0.1, 0.5, 0.9])),
            outcomes=outcomes, squad_coverage=coverage,
            squad_gaps=[role for role, count in coverage.items() if count < request.role_requirements.get(Role(role), 1)], total_fee=total,
            budget_satisfied=(total <= request.budget) if total is not None and request.budget is not None else None,
            limitations=["Assumption-driven scenarios; not a learned transfer forecast or causal team impact",
                         "Intervals are scenario percentiles, not calibrated forecast confidence intervals",
                         "Player rates, minutes and adaptation assumptions omit opponent and tactical interactions",
                         "Squad coverage is by role family; it is not a validated formation or registration check"],
        )
