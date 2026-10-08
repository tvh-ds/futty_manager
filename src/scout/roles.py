from dataclasses import dataclass

from scout.contracts import Role


@dataclass(frozen=True)
class RoleSpec:
    label: str
    style: tuple[str, ...]
    quality: dict[str, int]


ROLE_SPECS = {
    Role.GK: RoleSpec("Goalkeeper", ("save_pct", "claims_p90", "sweeps_p90", "passes_p90", "long_pass_share"),
                      {"save_pct": 1, "claims_p90": 1, "errors_p90": -1}),
    Role.CB: RoleSpec("Centre-back", ("tackles_p90", "interceptions_p90", "aerial_win_pct", "progressive_passes_p90", "passes_p90"),
                      {"aerial_win_pct": 1, "interceptions_p90": 1, "progressive_passes_p90": 1, "errors_p90": -1}),
    Role.FB: RoleSpec("Full-back / wing-back", ("carries_p90", "crosses_p90", "tackles_p90", "progressive_passes_p90", "pressures_p90"),
                      {"chances_p90": 1, "progressive_passes_p90": 1, "turnovers_p90": -1}),
    Role.DM: RoleSpec("Defensive midfielder", ("interceptions_p90", "tackles_p90", "progressive_passes_p90", "passes_p90", "turnovers_p90"),
                      {"progressive_passes_p90": 1, "interceptions_p90": 1, "turnovers_p90": -1}),
    Role.CM: RoleSpec("Central midfielder", ("progressive_passes_p90", "assists_p90", "carries_p90", "passes_p90", "turnovers_p90"),
                      {"progressive_passes_p90": 1, "chances_p90": 1, "turnovers_p90": -1}),
    Role.AM: RoleSpec("Attacking midfielder", ("chances_p90", "assists_p90", "dribbles_p90", "shots_p90", "progressive_passes_p90"),
                      {"chances_p90": 1, "assists_p90": 1, "turnovers_p90": -1}),
    Role.W: RoleSpec("Winger", ("dribbles_p90", "carries_p90", "shots_p90", "chances_p90", "goals_p90"),
                     {"goals_p90": 1, "chances_p90": 1, "turnovers_p90": -1}),
    Role.ST: RoleSpec("Striker", ("shots_p90", "goals_p90", "assists_p90", "aerial_win_pct", "pressures_p90"),
                      {"goals_p90": 1, "assists_p90": 1, "turnovers_p90": -1}),
}

METRIC_LABELS = {
    "save_pct": "Save share", "claims_p90": "Claims / 90", "sweeps_p90": "Sweeps / 90",
    "passes_p90": "Passes / 90", "long_pass_share": "Long-pass share", "errors_p90": "Errors / 90",
    "tackles_p90": "Tackles / 90", "interceptions_p90": "Interceptions / 90",
    "aerial_win_pct": "Aerial win share", "progressive_passes_p90": "Progressive passes / 90",
    "carries_p90": "Carries / 90", "crosses_p90": "Crosses / 90", "pressures_p90": "Pressures / 90",
    "turnovers_p90": "Turnovers / 90", "chances_p90": "Chances created / 90",
    "assists_p90": "Assists / 90", "dribbles_p90": "Completed dribbles / 90",
    "shots_p90": "Shots / 90", "goals_p90": "Goals / 90",
}

TOP_FIVE = ("England", "Spain", "Germany", "Italy", "France")
API_LEAGUES = {"England": 39, "Spain": 140, "Germany": 78, "Italy": 135, "France": 61}
