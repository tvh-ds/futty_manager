from datetime import UTC, datetime

import numpy as np

from scout.contracts import DatasetRelease, Evidence, MetricObservation, PlayerStint, Role, Team
from scout.roles import ROLE_SPECS, TOP_FIVE


def demonstration():
    rng = np.random.default_rng(810)
    teams, players = [], []
    first_names = ["Adrian", "Luca", "Niko", "Mateo", "Elias", "Tomas", "Rafael", "Jonas"]
    surnames = ["Vale", "Marlow", "Costa", "Lind", "Morel", "Varga", "Rossi", "Santos"]
    clubs = ["Northbridge", "Puerto Azul", "Westhafen", "Porto Verde", "Montclair"]
    all_metrics = sorted(set().union(*(set(spec.style) | set(spec.quality) for spec in ROLE_SPECS.values())))
    for league_index, league in enumerate(TOP_FIVE):
        for club_index in range(2):
            team_id = f"demo-team-{league_index}-{club_index}"
            style = {"passes_p90": float(45 + league_index * 3), "progressive_passes_p90": float(3 + club_index),
                     "pressures_p90": float(15 + club_index * 5), "carries_p90": float(5 + league_index)}
            teams.append(Team(id=team_id, name=f"{clubs[league_index]} {'FC' if club_index == 0 else 'United'}",
                              league=league, style_targets=style, style_evidence=Evidence.SYNTHETIC))
            for role_index, role in enumerate(Role):
                for number in range(3):
                    player_id = f"demo-player-{league_index}-{club_index}-{role_index}-{number}"
                    minutes = int(rng.integers(350, 3000))
                    metrics = {}
                    keys = set(ROLE_SPECS[role].style) | set(ROLE_SPECS[role].quality)
                    for key in all_metrics:
                        if key not in keys or rng.random() < 0.09:
                            continue
                        if key.endswith("pct") or key.endswith("share"):
                            denominator = int(rng.integers(40, 250))
                            numerator = int(rng.binomial(denominator, rng.uniform(0.4, 0.85)))
                            metrics[key] = MetricObservation(value=numerator / denominator, unit="ratio",
                                numerator=numerator, denominator=denominator, evidence=Evidence.SYNTHETIC)
                        else:
                            mean = 45 if key == "passes_p90" else 17 if key == "pressures_p90" else 0.12 if key == "errors_p90" else 0.3 if key in ("goals_p90", "assists_p90") else 3.2
                            count = int(rng.poisson(mean * rng.uniform(0.4, 1.8) * minutes / 90))
                            metrics[key] = MetricObservation(value=count / (minutes / 90), numerator=count,
                                                            evidence=Evidence.SYNTHETIC)
                    players.append(PlayerStint(
                        id=player_id, player_id=player_id, name=f"{first_names[role_index]} {surnames[(league_index + number + club_index) % 8]} {league_index + 1}{club_index}{number}",
                        team_id=team_id, league=league, season="2024/25", age=int(rng.integers(19, 33)),
                        foot=None if number == 2 else "left" if number == 0 else "right", roles=[role],
                        role_evidence=Evidence.SYNTHETIC, minutes=minutes, metrics=metrics,
                    ))
    release = DatasetRelease(id="synthetic-2024-25-v1", kind="synthetic", season="2024/25",
                             created_at=datetime(2025, 7, 1, tzinfo=UTC),
                             leagues=list(TOP_FIVE), source="Deterministic fictional test fixtures",
                             limitations=["All clubs, players and statistics are fictional",
                                          "This release does not establish real league coverage or model validity",
                                          "No tracking, pressure-reception or athletic measurements are available"])
    return release, players, teams
