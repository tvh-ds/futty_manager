"""Reproducible raw-field coverage inventory, separate from serving and ratings."""
import hashlib
import itertools
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from scout.opta_analyst_probe import FIELDS as OPTA_FIELDS
from scout.pitchapi import ADVANCED, FRACTIONS, STAT_KEYS
from scout.striker_features import FEATURES
from scout.understat_probe import FIELDS as UNDERSTAT_FIELDS

VERSION = "raw-source-audit-v1"
LEAGUES = ("England", "Spain", "Germany", "Italy", "France")
ROOTS = {
    "opta": Path("data/opta-analyst/season-2025-with-gk-20261006"),
    "pitchapi": Path("data/pitchapi/live-probe-2025"),
    "understat": Path("data/striker-source-probes/understat-recheck-20261006"),
}
OPTA_SLUGS = dict(zip(LEAGUES, ("premier-league", "la-liga", "bundesliga", "serie-a", "ligue-1"), strict=True))
UNDERSTAT_SLUGS = dict(zip(LEAGUES, ("EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"), strict=True))
IDENTITY = {"age", "date_of_birth", "first_name", "last_name", "player", "player_id", "player_uuid",
            "shirt_number", "squad_position", "squad_position_detailed", "team_id", "team_uuid",
            "contestantClubName", "contestantCode", "contestantName", "contestantShortName"}
# Only zero-attempt ratios with known same-row denominators receive N/A.
OPTA_RATIOS = {"shot_conv": ("goals", "shots"), "xg_per_shot": ("xg", "shots"),
    "np_shot_conv": ("np_goals", "np_shots"), "np_xg_per_shot": ("np_xg", "np_shots"),
    "pass_perc": ("successful_passes", "passes"),
    "ft_pass_perc": ("successful_final_third_passes", "total_final_third_passes"),
    "cross_perc": ("successful_op_crosses", "op_crosses"),
    "through_ball_perc": ("successful_through_balls", "through_balls"),
    "aerial_duel_perc": ("aerial_duels_won", "aerial_duels"),
    "ground_duel_perc": ("ground_duels_won", "ground_duels"),
    "dist_per_carry": ("carry_distance", "carries"),
    "dist_per_progressive_carry": ("progressive_distance", "progressive_carries")}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify(value):
    if value is None or value == "":
        return "missing"
    if isinstance(value, bool):
        return "categorical"
    if isinstance(value, (int, float)):
        return "numeric" if math.isfinite(value) else "invalid"
    if isinstance(value, str):
        return "categorical"
    return "invalid"


def ratio_status(row, numerator, denominator):
    n, d = row.get(numerator), row.get(denominator)
    if classify(n) != "numeric" or classify(d) != "numeric":
        return None
    if d < 0 or (d == 0 and n != 0):
        return "invalid"
    return "na" if n == d == 0 else None


def flatten(value, prefix=""):
    """All scalar paths; list members retain structural wildcard paths."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from flatten(child, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten(child, f"{prefix}[{index}]" if len(value) <= 3 else f"{prefix}[]")
    else:
        yield prefix, value


@dataclass
class Field:
    key: str
    group: str
    scope: str
    imported: bool = False
    kind: str = "metric"
    unit: str = "source-native; see definition"
    observations: dict = field(default_factory=lambda: defaultdict(dict))


class Inventory:
    def __init__(self, provider):
        self.provider = provider
        self.players = set()
        self.keepers = set()
        self.expected = Counter()
        self.records = 0
        self.fields = {}
        self.inputs = []
        self.freshness = {}
        self.context = defaultdict(set)
        self.event_expected = Counter()
        self._people_cache = {}
        self.raw_records = 0

    def add(self, key, person, sample, value, *, group, scope="aggregate", imported=False,
            kind="metric", unit="source-native; see definition", status=None):
        f = self.fields.setdefault(key, Field(key, group, scope, imported, kind, unit))
        self._people_cache.clear()
        f.imported |= imported
        state = status or classify(value)
        previous = f.observations[person].get(sample)
        # Duplicate rows are idempotent; conflicting repetitions are invalid.
        observation = (state, value)
        if previous is not None and previous != observation:
            observation = ("invalid", None)
        f.observations[person][sample] = observation

    def people(self, f, status, complete=False):
        cache_key = (f.key, frozenset(status), complete)
        if cache_key in self._people_cache:
            return self._people_cache[cache_key]
        result = set()
        for person in self.players:
            rows = f.observations.get(person, {})
            if not rows:
                continue
            states = [s[0] for s in rows.values()]
            if complete:
                required = self.event_expected[person] if f.scope == "event" else self.expected[person]
                if f.scope == "identity":
                    required = 1
                if required and len(rows) >= required and all(s in status for s in states):
                    result.add(person)
            elif any(s in status for s in states):
                result.add(person)
        self._people_cache[cache_key] = result
        return result

    def apply_empty_cell_policy(self):
        """User rule: present empty numeric cells are zero; absent rows/keys stay absent.

        Calculations, explicit N/A, identities and null structural objects are
        separate from numeric source cells and are never fabricated here.
        """
        self.empty_zero_counts = {}
        for key, f in self.fields.items():
            if f.group == 'calculated' or f.kind not in {'metric', 'event'}:
                continue
            if not any(state == 'numeric' for rows in f.observations.values() for state, _ in rows.values()):
                continue
            people = set()
            for person, rows in f.observations.items():
                for sample, (state, value) in list(rows.items()):
                    if state == 'missing' and value in (None, ''):
                        rows[sample] = ('numeric', 0)
                        people.add(person[1])
            self.empty_zero_counts[key] = len(people)
        self._people_cache.clear()

    def counts(self, f, population):
        numeric = self.people(f, {"numeric"}) & population
        recorded = self.people(f, {"numeric", "categorical"}) & population
        complete_numeric = self.people(f, {"numeric"}, complete=True) & population
        supported = self.people(f, {"numeric", "categorical", "na"}, complete=True) & population
        na = self.people(f, {"na"}) & population
        invalid = self.people(f, {"invalid"}) & population
        zeros = {p for p, rows in f.observations.items() if p in population and
                 any(state == "numeric" and value == 0 for state, value in rows.values())}
        missing = {p for p in population if not f.observations.get(p) or
            any(state == "missing" for state, _ in f.observations[p].values()) or
            (f.scope != "identity" and len(f.observations[p]) <
             (self.event_expected[p] if f.scope == "event" else self.expected[p]))}
        def unique(people):
            return len({p[1] for p in people})
        # Global metrics use distinct provider IDs; any cross-league partial record
        # keeps that person's global completeness below the complete numerator.
        incomplete_ids = {p[1] for p in population - supported}
        complete_ids = {p[1] for p in supported} - incomplete_ids
        numeric_incomplete_ids = {p[1] for p in population - complete_numeric}
        complete_numeric_ids = {p[1] for p in complete_numeric} - numeric_incomplete_ids
        denominator = unique(population)
        return {"players": denominator, "numeric": unique(numeric), "recorded": unique(recorded),
            "zero": unique(zeros), "na": unique(na), "invalid": unique(invalid),
            "missing": unique(missing), "partial": unique((recorded | na) - supported),
            "complete_supported": len(complete_ids), "complete_numeric": len(complete_numeric_ids),
            "supported_pct": round(100 * len(complete_ids) / denominator, 2) if denominator else None,
            "numeric_pct": round(100 * len(complete_numeric_ids) / denominator, 2) if denominator else None}

    def report(self):
        result = {"provider": self.provider, "player_team_or_league_records": self.records,
            "raw_normalized_records": self.raw_records, "excluded_no_minutes_records": self.raw_records - self.records,
            "unique_players": len({p[1] for p in self.players}),
            "player_league_rows": len(self.players), "inputs": self.inputs, "freshness": self.freshness,
            "context_fields": {k: sorted(v) for k, v in self.context.items()}, "fields": {}}
        for key, f in sorted(self.fields.items()):
            applicable = self.keepers if f.group == "goalkeeping" else self.players
            result["fields"][key] = {"group": f.group, "scope": f.scope, "kind": f.kind,
                "unit": f.unit, "imported": f.imported, "all": self.counts(f, self.players),
                "leagues": {league: self.counts(f, {p for p in self.players if p[0] == league}) for league in LEAGUES},
                "applicable": self.counts(f, applicable)}
            result["fields"][key]["applicable_leagues"] = {league: self.counts(f, {p for p in applicable if p[0] == league}) for league in LEAGUES}
        return result


def normalized_inventory(provider, root):
    inv = Inventory(provider)
    paths = [root / "measurements.json"] if provider == "pitchapi" else list(root.glob("*/measurements.json"))
    rows = [r for path in paths for r in read(path)]
    inv.raw_records = len(rows)
    for r in rows:
        if r.get("competition") not in LEAGUES or r.get("season") not in {2025, "2025/2026", "2025/26"}:
            raise ValueError("Non-target league/season in normalized input")
        if (r["totals"].get("minutes") or 0) <= 0:
            continue
        p = (r["competition"], str(r["provider_player_id"]))
        inv.players.add(p)
        inv.expected[p] += r.get("appearance_count", 1)
        inv.records += 1
        if r.get("source_position") in {"Goalkeeper", "GK"} or r["totals"].get("saves_made") is not None:
            inv.keepers.add(p)
    inv.inputs = [{"path": str(path), "sha256": checksum(path)} for path in paths]
    # Existing calculations are reported separately, including missing and N/A slots.
    definitions = {f.key: f for f in FEATURES}
    for index, r in enumerate(rows):
        p = (r["competition"], str(r["provider_player_id"]))
        if p not in inv.players or (r["totals"].get("minutes") or 0) <= 0:
            continue
        sample = str(r.get("provider_team_id", index)) if provider == "opta" else "aggregate"
        for key, value in r["features"].items():
            f = definitions.get(key)
            status = ratio_status(r["totals"], f.numerator, f.denominator) if value is None and f else None
            # Calculated Pitch totals already represent all validated appearances.
            inv.add("calculated." + key, p, sample, value, group="calculated", scope="identity" if provider == "pitchapi" else "aggregate",
                    imported=f is not None, unit=f.unit if f else "legacy calculation; definition not in active registry", status=status)
    return inv, rows


def audit_opta(root):
    inv, normalized = normalized_inventory("opta", root)
    accepted = {(r["competition"], str(r["provider_player_id"]), str(r["provider_team_id"])) for r in normalized
                if (r["totals"].get("minutes") or 0) > 0}
    report = read(root / "coverage.json")
    if report["requested_season"] != "2025/2026":
        raise ValueError("Wrong Opta season")
    inv.freshness = report["leagues"]
    imported = {(a, b, key) for (a, b), mapping in OPTA_FIELDS.items() for key in mapping.values()}
    for league, slug in OPTA_SLUGS.items():
        path = root / slug / "bronze.json"
        if checksum(path) != report["leagues"][league]["snapshot_sha256"]:
            raise ValueError("Opta bronze checksum mismatch")
        inv.inputs.append({"path": str(path), "sha256": checksum(path)})
        doc = read(path)
        excluded = {(str(q.get("provider_player_id")), str(q.get("provider_team_id"))) for q in
                    read(root / slug / "quarantine.json")}
        for group, sections in doc.items():
            if not isinstance(sections, dict):
                inv.context["document"].add(group)
                continue
            for section, rows in sections.items():
                if not isinstance(rows, list):
                    inv.context[group].add(section)
                    continue
                for row in rows:
                    p = (league, str(row["player_uuid"]))
                    sample = str(row["team_uuid"])
                    if (league, p[1], sample) not in accepted or (row.get("mins_played") or 0) <= 0 or (p[1], sample) in excluded:
                        continue
                    if group == "goalkeeping":
                        inv.keepers.add(p)
                    for key, value in row.items():
                        identity = key in IDENTITY
                        exposure = key in {"apps", "mins_played", "team_mins", "team_mins_perc"}
                        namespace = "identity" if identity else "exposure" if exposure else f"{group}.{section}"
                        status = ratio_status(row, *OPTA_RATIOS[key]) if key in OPTA_RATIOS else None
                        inv.add(f"{namespace}.{key}", p, sample, value,
                            group="identity" if identity else "exposure" if exposure else group,
                            kind="identity" if identity else "context" if exposure else "metric",
                            scope="identity" if identity else "aggregate",
                            imported=identity or exposure or (group, section, key) in imported,
                            unit="%" if key.endswith(("_perc", "_conv")) else "source-native",
                            status=status)
    return inv


def audit_understat(root):
    inv, _ = normalized_inventory("understat", root)
    report = read(root / "coverage.json")
    inv.freshness = report["leagues"]
    for league, slug in UNDERSTAT_SLUGS.items():
        path = root / slug / "bronze.json"
        facts = report["leagues"][league]
        expected = facts.get("snapshot_sha256")
        if expected and checksum(path) != expected:
            raise ValueError("Understat bronze checksum mismatch")
        inv.inputs.append({"path": str(path), "sha256": checksum(path)})
        doc = read(path)
        dates = [r["datetime"] for r in doc.get("dates", []) if r.get("isResult")]
        inv.freshness[league] = {**facts, "first_match": min(dates) if dates else None,
                               "last_match": max(dates) if dates else None,
                               "completed_fixtures": len(dates)}
        for row in doc["players"]:
            p = (league, str(row["id"]))
            if p not in inv.players or float(row.get("time") or 0) <= 0:
                continue
            for key, value in row.items():
                identity = key in {"id", "player_name", "position", "team_title"}
                exposure = key in {"games", "time"}
                if not identity and isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                inv.add("players." + key, p, "aggregate", value,
                    group="identity" if identity else "exposure" if exposure else "performance",
                    kind="identity" if identity else "context" if exposure else "metric",
                    imported=key in UNDERSTAT_FIELDS.values() or identity,
                    unit="minutes" if key == "time" else "source-native")
        for section in ("teams", "dates"):
            for key, _ in flatten(doc.get(section, {})):
                inv.context[section].add(re.sub(r"\[\d+\]", "[]", key))
    return inv


def pitch_snapshot(path):
    saved = read(path)
    body = json.dumps(saved["document"], sort_keys=True, allow_nan=False).encode()
    if hashlib.sha256(body).hexdigest() != saved["sha256"]:
        raise ValueError("PitchAPI bronze checksum mismatch")
    if not saved["url"].startswith("https://api.pitchapi.dev/v1/"):
        raise ValueError("Unexpected cached PitchAPI host")
    return saved


def audit_pitch(root):
    inv, rows = normalized_inventory("pitchapi", root)
    accepted = {re.search(r"/matches/(m_[A-Za-z0-9]+)", url)[1]
                for row in rows for url in row["source_urls"] if "/matches/" in url}
    paths = sorted((root / "snapshots").glob("*.json"))
    matches, fresh, match_dates = {}, defaultdict(list), defaultdict(list)
    league_names = {"Premier League": "England", "LaLiga": "Spain", "Bundesliga": "Germany",
                    "Serie A": "Italy", "Ligue 1": "France"}
    for path in paths:
        # Small inventories can be found without loading the 577 MB collection twice.
        if path.stat().st_size > 400_000:
            continue
        saved = read(path)
        if "/leagues/" not in saved.get("url", "") or not saved["url"].endswith("/matches"):
            continue
        saved = pitch_snapshot(path)
        data = saved["document"]["data"]
        if data["league"]["season"] != "2025/2026":
            raise ValueError("Wrong PitchAPI season")
        league = league_names[data["league"]["name"]]
        for match in data["matches"]:
            matches[match["id"]] = league
            if match["status"] == "finished":
                match_dates[league].append(match["date"])
            for key, _ in flatten(match):
                inv.context["match"].add(key)
    if len(matches) != 1752:
        raise ValueError("Incomplete PitchAPI fixture inventories")
    for path in paths:
        saved = pitch_snapshot(path)
        inv.inputs.append({"path": str(path), "sha256": saved["sha256"]})
        found = re.search(r"/matches/(m_[A-Za-z0-9]+)", saved["url"])
        if not found:
            continue
        mid = found[1]
        if mid not in accepted:
            continue
        league = matches[mid]
        fresh[league].append(saved["retrieved_at"])
        if saved.get("unavailable") or saved["document"].get("data") is None:
            continue
        data = saved["document"]["data"]
        if saved["url"].endswith("/shots"):
            for period in data["periods"]:
                for shot in period["shots"]:
                    p = (league, shot["player"]["id"])
                    if p not in inv.players:
                        continue
                    sample = mid + ":" + shot["id"]
                    inv.event_expected[p] += 1
                    for key, value in flatten(shot):
                        inv.add("shot." + key, p, sample, value, group="shot event", scope="event",
                            kind="identity" if key.startswith(("player.", "keeper.")) or key in {"id", "team_id"} else "event",
                            unit="source-native")
        elif "/advanced/" in saved["url"]:
            for row in data["players"]:
                p = (league, row["player"]["id"])
                if p not in inv.players or (row.get("minutes_played") or 0) <= 0:
                    continue
                if row.get("goalkeeping"):
                    inv.keepers.add(p)
                for key, value in flatten(row):
                    group = key.split(".")[0]
                    is_identity = key.startswith("player.") or key == "team_id"
                    imported = any(key == f"{g}.{k}" for g, k in ADVANCED.values()) or key == "minutes_played"
                    inv.add("advanced." + key, p, mid, value,
                        group="identity" if is_identity else group,
                        kind="identity" if is_identity else "context" if key in {"minutes_played", "actions"} else "metric",
                        scope="identity" if is_identity else "appearance", imported=imported,
                        unit="source-native")
        elif saved["url"].endswith("/players"):
            for row in data:
                p = (league, row["player"]["id"])
                stats = [(entry.get("key") or "unnamed", entry.get("stat", {}))
                         for group in row["stats"] for entry in group["stats"].values()]
                minutes = next((s.get("value") for k, s in stats if k == "minutes_played"), None)
                if p not in inv.players or not minutes or minutes <= 0:
                    continue
                for key, value in flatten({"player": row["player"], "team_id": row["team_id"]}):
                    inv.add("metadata." + key, p, mid, value, group="identity", kind="identity", scope="identity", imported=True)
                for key, stat in stats:
                    for part, value in stat.items():
                        imported = key in STAT_KEYS.values() or key in FRACTIONS
                        status = None
                        if part == "value" and stat.get("type") == "fractionWithPercentage":
                            n, d = stat.get("value"), stat.get("total")
                            if classify(n) == classify(d) == "numeric" and (n < 0 or d < 0 or n > d):
                                status = "invalid"
                        inv.add(f"stats.{key}.{part}", p, mid, value,
                            group="goalkeeping" if any(s in key.lower() for s in ("save", "keeper", "conceded", "prevented")) else "match statistics",
                            kind="context" if part == "type" or key in {"unnamed", "minutes_played", "xg_and_xa"}
                            else "rating" if key in {"rating_title", "fantasy_points"} else "metric",
                            scope="appearance", imported=imported, status=status,
                            unit="successful count" if part == "value" and stat.get("type") == "fractionWithPercentage" else "source-native")
                    if stat.get("type") == "fractionWithPercentage":
                        n, d = stat.get("value"), stat.get("total")
                        percent = 100 * n / d if classify(n) == classify(d) == "numeric" and d > 0 and 0 <= n <= d else None
                        inv.add(f"stats.{key}.calculated_percentage", p, mid, percent,
                            group="match statistics", scope="appearance", imported=False, unit="% (same-source calculation)",
                            status=ratio_status(stat, "value", "total") if percent is None else None)
    inv.freshness = {league: {"retrieved_first": min(fresh[league]), "retrieved_last": max(fresh[league]),
        "first_match": min(match_dates[league]), "last_match": max(match_dates[league]),
        "inventory_matches": len(match_dates[league]), "validated_matches": sum(matches[m] == league for m in accepted),
        "provider_updated": None} for league in LEAGUES}
    return inv


def family(provider, key):
    """Grouping avoids counting representations as independent football abilities.

    Grouping does NOT authorize cross-provider fallback; only exact variant
    observations are unioned below, after explicit identity corroboration.
    """
    if key.startswith("calculated."):
        f = next((f for f in FEATURES if key == "calculated." + f.key), None)
        return f.numerator if f else key
    native = key.rsplit(".", 1)[-1]
    if provider == "pitchapi" and key.startswith("stats."):
        native = key[len("stats."):].rsplit(".", 1)[0]
    synonyms = {
        "np_goals": "non_penalty_goals", "npg": "non_penalty_goals", "np_xg": "npxg", "npxG": "npxg",
        "np_shots": "non_penalty_shots", "np_shots_on_target": "non_penalty_shots_on_target",
        "xG": "xg", "xA": "xa", "expected_goals": "xg", "expected_assists": "xa",
        "xGChain": "xg_chain", "xGBuildup": "xg_buildup", "xg_per_shot": "xg",
        "np_xg_per_shot": "npxg", "shot_conv": "goals", "np_shot_conv": "non_penalty_goals",
        "goals_vs_xg": "finishing_delta", "np_goals_vs_xg": "finishing_delta",
        "accurate_passes": "passes_completed", "successful_passes": "passes_completed",
        "passes": "passes_attempted", "pass_perc": "passes_completed", "pass_accuracy": "passes_completed",
        "total_final_third_passes": "passes_into_final_third", "ft_pass_perc": "successful_final_third_passes",
        "cross_perc": "successful_op_crosses", "through_ball_perc": "successful_through_balls",
        "aerial_duel_perc": "aerial_duels_won", "aerials_won": "aerial_duels_won",
        "aerials": "aerial_duels_attempted", "aerial_duels": "aerial_duels_attempted",
        "aerial_duels_lost": "aerial_duels_attempted", "duel_won": "duels_won",
        "duel_lost": "duels_attempted", "ground_duel_perc": "ground_duels_won",
        "was_fouled": "fouls_won", "fouls": "fouls_committed", "fouls_commited": "fouls_committed",
        "yellow_cards": "yellow_cards", "yellows": "yellow_cards", "red_cards": "red_cards", "reds": "red_cards",
        "passes_into_box": "passes_into_penalty_area", "carries_into_box": "carries_into_penalty_area",
        "take_ons": "take_ons_attempted", "take_ons_won": "take_ons_successful",
        "dribbles_succeeded": "take_ons_successful", "shot_blocks": "blocks",
        "touches_opp_box": "touches_opposition_box", "ShotsOnTarget": "shots_on_target", "Offsides": "offsides",
        "progressive_distance": "progressive_carry_distance", "dist_per_carry": "carry_distance",
        "dist_per_progressive_carry": "progressive_carry_distance", "save_perc": "saves_made",
        "long_balls_accurate": "accurate_long_balls", "goals_prevented_rate": "goals_prevented",
        "matchstats.headers.tackles": "tackles", "expected_goals_non_penalty": "npxg",
        "total_shots": "shots", "shot_accuracy": "shots_on_target",
    }
    return synonyms.get(native, native)


def canonical_maps(db, manifest):
    """Read-only serving DB and existing corroboration audit; never match names."""
    mappings = {}
    with sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True) as con:
        records = {r[0]: (r[1], r[2], json.loads(r[3])["provider_player_id"]) for r in con.execute(
            "SELECT id, provider, league, payload FROM source_records WHERE import_id=?", (manifest["import_id"],))}
    for provider, league, pid in records.values():
        mappings[(provider, league, pid)] = f"{provider}:{pid}"
    for link in manifest["mapping_audit"]:
        if link["status"] != "corroborated_not_human_reviewed":
            continue
        anchor, candidate = records[link["anchor"]], records[link["record"]]
        mappings[candidate] = f"{anchor[0]}:{anchor[2]}"
    return mappings


def combinations(inventories, mappings):
    anchor = inventories["opta"].players
    baseline = {(league, mappings.get(("opta", league, pid), f"opta:{pid}")) for league, pid in anchor}
    variants = {}
    for provider, inv in inventories.items():
        for key, f in inv.fields.items():
            if f.kind != "metric" or f.group in {"identity", "exposure"} or f.scope == "event":
                continue
            if not inv.people(f, {"numeric", "na"}):
                continue
            supported = {(league, mappings.get((provider, league, pid), f"{provider}:{pid}"))
                         for league, pid in inv.people(f, {"numeric", "na"}, complete=True)} & baseline
            keeper = {(league, mappings.get((provider, league, pid), f"{provider}:{pid}"))
                      for league, pid in inv.keepers} & baseline
            variants[(provider, key)] = {"family": family(provider, key), "people": supported,
                                       "keeper": keeper, "specialist": f.group == "goalkeeping"}
    results = []
    providers = sorted(inventories)
    for count in range(1, len(providers) + 1):
        for combo in itertools.combinations(providers, count):
            families = defaultdict(list)
            for (provider, key), variant in variants.items():
                if provider not in combo:
                    continue
                coverage = {league: round(100 * sum(p[0] == league for p in variant["people"]) /
                    max(1, sum(p[0] == league for p in baseline)), 2) for league in LEAGUES}
                incomplete_ids = {pid for _, pid in baseline - variant['people']}
                unique_supported = len({pid for _, pid in variant['people']} - incomplete_ids)
                families[variant["family"]].append({"provider": provider, "key": key,
                    "coverage": coverage, "all_five_pass": all(10 * sum(p[0] == league for p in variant["people"]) >=
                        9 * sum(p[0] == league for p in baseline) and any(p[0] == league for p in baseline) for league in LEAGUES),
                    "counts": {league: sum(p[0] == league for p in variant["people"]) for league in LEAGUES},
                    "unique_supported": unique_supported,
                    "pooled": round(100 * unique_supported / len({pid for _, pid in baseline}), 2),
                    "player_league_supported": len(variant['people']),
                    "specialist": variant["specialist"]})
            passed = {name for name, options in families.items() if any(v["all_five_pass"] for v in options)}
            results.append({"sources": list(combo), "reliable_general_families": len(passed),
                "observed_families": len(families), "passing_families": sorted(passed),
                "families": dict(families)})
    results.sort(key=lambda r: (-r["reliable_general_families"], -r["observed_families"], len(r["sources"]), r["sources"]))
    return {"benchmark": "Validated positive-minute Opta identities, including GK; not a proven universal roster",
        "identity_coverage": {provider: {league: {
            "source_players": sum(p[0] == league for p in inv.players),
            "matched_benchmark": len({(player_league, mappings.get((provider, player_league, pid), f"{provider}:{pid}")) for player_league, pid in inv.players if player_league == league} & baseline),
            "benchmark_players": sum(p[0] == league for p in baseline)} for league in LEAGUES} for provider, inv in inventories.items()},
        "baseline_player_league_rows": len(baseline), "baseline_unique_players": len({p[1] for p in baseline}),
        "equivalence_policy": "Source-native variants stay separate. Family grouping is not permission to mix definitions. A family passes only if a single variant reaches 90% in every league.",
        "ranked": results}


def escape(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def md_table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] +
        ["| " + " | ".join(escape(v) for v in row) + " |" for row in rows]) + "\n"


def persist_report(output, result):
    """Hash exact UTF-8 bytes; Windows text newline conversion must not alter them."""
    body = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode('utf-8')
    digest = hashlib.sha256(body).hexdigest()
    path = output / f'audit-{digest}.json'
    if path.exists() and path.read_bytes() != body:
        raise ValueError('Content-addressed audit collision or corrupt existing snapshot')
    if not path.exists():
        path.write_bytes(body)
    (output / 'latest.json').write_text(json.dumps({'report': path.name, 'sha256': digest}, indent=2), encoding='utf-8')
    return digest


def write_provider(path, report):
    provider = report["provider"]
    links = {"opta": "https://optaplayerstats.statsperform.com/", "pitchapi": "https://pitchapi.dev/",
             "understat": "https://understat.com/"}
    text = [f"# {provider.title()} — exhaustive cached-field audit", "",
        f"Source: [{provider}]({links[provider]}). Performance season **2025/26**. Audit version `{VERSION}`.", "",
        f"**{report['unique_players']:,} distinct provider IDs**; {report['player_league_rows']:,} player/league rows; "
        f"{report['player_team_or_league_records']:,} normalized records. Low-minute players and GK are included.", "",
        f"All normalized source records: {report['raw_normalized_records']:,}; zero/unknown-minute records excluded from the league-participant denominator: "
        f"{report['excluded_no_minutes_records']:,}. Registered non-participants are not silently treated as observed league players.", "",
        "Rights: " + ("user-confirmed collection/reuse consent; retain the consent evidence before deployment." if provider != "understat"
                       else "private local intake; public redistribution permission is unverified."), "",
        "## Coverage interpretation", "",
        "Cells show **numeric / recorded** distinct players. Recorded also includes valid categorical/boolean values. "
        "The total deduplicates IDs across leagues. C = complete supported observation coverage; CN = complete numeric coverage. "
        "N/A means a verified zero-attempt ratio, never a fabricated zero. Counts can overlap across categories when a player has multiple records.", "",
        "Complete means every validated stint/appearance has the field; it does not certify an independently complete league roster. "
        "PitchAPI remains fixture-incomplete (five quarantined matches); event rows cover shooters with observed events, not non-shooters. "
        "Numeric field presence is not proof of correct provider semantics or suitability for a player rating.", "",
        "## Freshness and scope", ""]
    rows = []
    for league in LEAGUES:
        f = report["freshness"].get(league, {})
        rows.append([league, f.get("retrieved_at") or f.get("retrieved_last") or "unknown",
            f.get("source_last_updated", "not supplied"), f.get("first_match", "not supplied"),
            f.get("last_match", "not supplied"), f.get("validated_matches", f.get("completed_fixtures", "aggregate feed"))])
    text.append(md_table(["League", "Retrieved (UTC)", "Provider updated (timezone unspecified)", "First match", "Last match", "Validated fixtures"], rows))
    groups = sorted({f["group"] for f in report["fields"].values()})
    for group in groups:
        text.extend([f"## {group}", ""])
        rows = []
        for key, f in report["fields"].items():
            if f["group"] != group:
                continue
            a = f["all"]
            applicable = f["applicable"]
            cells = [f"{f['leagues'][league]['numeric']}/{f['leagues'][league]['recorded']}" for league in LEAGUES]
            rows.append([f"`{key}`", f["unit"], *cells, f"{a['numeric']}/{a['recorded']}",
                f"{a['zero']} / {a['na']} / {a['missing']} / {a['invalid']}",
                f"{a['complete_supported']} ({a['supported_pct']}%) / {a['complete_numeric']} ({a['numeric_pct']}%)",
                f"{applicable['complete_supported']}/{applicable['players']}" if group == "goalkeeping" else "all players",
                "imported/used" if f["imported"] else "raw only", f["scope"]])
        text.append(md_table(["Native field / calculated key", "Unit", *LEAGUES, "Five-league numeric/recorded",
            "Zero / N/A / missing / invalid", "C / CN", "Applicable coverage", "Engine", "Scope"], rows))
    text.extend(["## Non-player schema inventory", "", "Player counts are **not applicable** to these team/match/document fields.", ""])
    for group, keys in report["context_fields"].items():
        text.extend([f"### {group}", "", ", ".join(f"`{escape(k)}`" for k in keys), ""])
    text.extend(["## Per-league availability details", "",
        "Full = every retained stint/appearance supported (numeric or verified N/A). Partial means some records have evidence "
        "but at least one retained record is missing or invalid. Match-derived full observation coverage does not certify full fixtures.", ""])
    for league in LEAGUES:
        text.extend([f"### {league}", ""])
        rows = []
        for key, f in report["fields"].items():
            a = f["leagues"][league]
            applicable = f["applicable_leagues"][league]
            rows.append([f"`{key}`", a["players"], a["numeric"], a["recorded"], a["zero"], a["na"], a["missing"],
                a["invalid"], a["partial"], a["complete_supported"], a["supported_pct"], a["numeric_pct"],
                f"{applicable['complete_supported']}/{applicable['players']} ({applicable['supported_pct']}%)" if f['group'] == 'goalkeeping' else 'all players'])
        text.append(md_table(["Field", "Players", "Numeric", "Recorded", "Zero", "N/A", "Missing", "Invalid", "Partial", "Full", "Supported %", "Numeric %", "Applicable GK"], rows))
    text.extend(["## Provenance and reproduction", "", "Checksums and all input paths are recorded in the machine-readable audit. "
        "Run `scout audit-data-sources` from the repository root. No serving release or rating is changed.", ""])
    path.write_text("\n".join(text), encoding="utf-8")


EXTERNAL = {
    "whoscored": {"url": "https://www.whoscored.com/Statistics", "status": "historical navigation verified; dynamic tables not obtained",
        "fields": ["goals", "assists", "shots", "key passes", "fouled", "offsides", "dispossessed", "bad control",
                   "dribbles", "tackles", "interceptions", "clearances", "blocks", "passing", "aerial duels", "provider rating"],
        "note": "These are historical research leads, not a verified current 2025/26 schema. Do not assume fouled closes fouls-won coverage.",
        "references": ["https://www.whoscored.com/Statistics",
            "https://www.ida.liu.se/research/sportsanalytics/projects/conferences/MLSA18-soccer/player-valuation-european-extended.pdf"]},
    "fbref": {"url": "https://fbref.com/en/comps/Big5/2025-2026/2025-2026-Big-5-European-Leagues-Stats",
        "status": "access blocked", "fields": ["identity", "appearances", "minutes", "goals", "assists", "cards", "basic shooting", "basic goalkeeping"],
        "note": "2025/26 pages are indexed but this audit cannot enumerate current columns. The 20 January 2026 provider-data removal means historic advanced-stat tutorials are not evidence of current xG/passing/possession availability.",
        "references": ["https://www.sports-reference.com/blog/category/advanced-stats/",
            "https://fbref.com/en/comps/9/2025-2026/stats/2025-2026-Premier-League-Stats"]},
    "sofascore": {"url": "https://www.sofascore.com/football/player/compare", "status": "permission required; access blocked",
        "fields": ["goals", "assists", "xG", "xA", "shots", "passing", "dribbles", "possession lost", "tackles", "provider rating"],
        "note": "The comparison tool documents these capability families, not full historical coverage. Terms 2.8–2.9 restrict database extraction and scraping without consent. No mass collection is enabled.",
        "references": ["https://www.sofascore.com/football/player/compare", "https://www.sofascore.com/sl/terms-and-conditions"]},
    "fotmob": {"url": "https://www.fotmob.com/en-GB/leagues/47/stats/season/27110/players/interception/team/9826/crystal-palace",
        "status": "permission required", "fields": ["interceptions", "interceptions per90", "save percentage", "goals + assists"],
        "note": "A 2025/26 Crystal Palace table is visible. Its 17 ranked rows are a filtered sample, not a complete player inventory or proof of coverage of zero-event players. The site explicitly prohibits automated/systematic collection; no mass crawl is performed.",
        "references": ["https://www.fotmob.com/en-GB/leagues/47/stats/season/27110/players/interception/team/9826/crystal-palace",
            "https://www.fotmob.com/leagues/47/stats/season/27110/players/_save_percentage/team/9826/crystal-palace-fcplayers-players"]},
    "statbunker": {"url": "https://soccerstats.statbunker.com/", "status": "historical HTML collection; incomplete identity inventory",
        "fields": [], "note": "See the captured historical columns below. Native records are retained without invented IDs. Some requests time out; reuse conditions and complete provider-ID inventories remain unverified. Unique-player coverage is unknown, not zero.",
        "references": ["https://soccerstats.statbunker.com/"]},
    "statsbomb": {"url": "https://github.com/statsbomb/open-data", "status": "target season absent",
        "fields": ["event type", "timestamp", "player", "position", "location", "pass", "carry", "shot", "shot xG",
                   "pressure", "duel", "interception", "goalkeeper event", "freeze frame (selected matches)"],
        "note": "The full live competition manifest has no qualifying senior men's 2025/26 top-five league season. Historical event data is useful for modelling but contributes zero target-season players. Event field variants are competition/match dependent.",
        "references": ["https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json",
            "https://github.com/statsbomb/open-data/blob/master/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf"]},
}


def write_external(folder, probes):
    for source, info in EXTERNAL.items():
        probe = probes.get(source, {})
        status = info["status"]
        absent = source == "statsbomb" and probe.get("status") == 200 and probe.get("qualifying_competitions") == []
        count = "0 (season absent)" if absent else "unknown / not collected"
        text = [f"# {source.title()} — additional-source investigation", "",
            f"Website: [{source}]({info['url']}). Target: **2025/26**, senior men's top-five leagues.", "",
            f"Status: **{status}**. Probe result: `{probe.get('status', probe.get('error', 'not run'))}`. "
            f"Retrieved: `{probe.get('retrieved_at', 'unknown')}`. Provider update time: unknown.", "", info["note"], "",
            "## Field leads and measured coverage", "",
            "These are documented/observed capability leads, not a complete crawled schema. Unverified counts are never estimated from a ranked sample.", "",
            md_table(["Field family", *LEAGUES, "Five-league players", "Evidence"],
                [[f, *([count] * 5), count, "historical schema only" if absent else "not fully collected"] for f in info["fields"]]),
            "## Collection completeness", "", "No qualifying full player collection was accepted. No rating or candidate release was activated.", "",
            f"Live StatsBomb manifest entries inspected: {probe.get('manifest_entries', 'not applicable')}. "
            f"Qualifying seasons: {len(probe.get('qualifying_competitions', [])) if absent else 'not established'}.", "",
            "## References", "", *[f"- [Source {i + 1}]({url})" for i, url in enumerate(info["references"])], ""]
        (folder / f"{source}.md").write_text("\n".join(text), encoding="utf-8")


def write_combined(folder, combo):
    ranked = combo["ranked"]
    general = ranked[0]
    public = next(r for r in ranked if "understat" not in r["sources"])
    smallest = min((r for r in ranked if r["reliable_general_families"] == general["reliable_general_families"]),
                   key=lambda r: (len(r["sources"]), -r["observed_families"], r["sources"]))
    rows = [[" + ".join(r["sources"]), r["reliable_general_families"], r["observed_families"],
             "private" if "understat" in r["sources"] else "user-confirmed reuse"] for r in ranked]
    text = ["# Source selection — measured 2025/26 combinations", "",
        f"Benchmark: **{combo['baseline_player_league_rows']:,} validated Opta player/league identities**, "
        f"{combo['baseline_unique_players']:,} unique IDs, including GK. This is not independently proven universal player coverage.", "",
        "## Recommendations", "",
        f"- Best measured local research combination: **{' + '.join(general['sources'])}**.",
        f"- Best measured public-demo candidate: **{' + '.join(public['sources'])}**. Consent does not bypass identity, definition or completeness gates.",
        f"- Smallest combination matching the best general 90% coverage: **{' + '.join(smallest['sources'])}**.", "",
        md_table(["Combination", "Families ≥90% in EACH league", "Observed families", "Reuse boundary"], rows),
        "Counts measure source-native observation availability, not validated ability models. "
        "The denominator includes every positive-minute player, so goalkeeper-specific families generally fail this general gate. "
        "Their applicable coverage appears separately in source reports. Family names group totals/ratios/per90; "
        "an available family does not mean every representation is usable.", "",
        "## Definition and identity constraints", "", combo["equivalence_policy"], "",
        "A source variant is evaluated only on existing corroborated identities. An unmatched source player cannot silently "
        "fill an Opta player's gap. Cross-source metric variants are not unioned merely because labels resemble each other. "
        "Consequently these rankings are a conservative measured capability comparison, not a harmonized production release.", "",
        "### Corroborated identity coverage", "",
        "Cells show source players / identities matched to the benchmark / benchmark players. A zero in the ranking for "
        "a non-Opta source reflects unresolved identity and completeness gaps on this shared benchmark; it does not mean "
        "that source has no useful metrics. Source-native coverage is reported separately.", "",
        md_table(["Source", *LEAGUES], [[provider, *[" / ".join(str(counts[league][k]) for k in
            ("source_players", "matched_benchmark", "benchmark_players")) for league in LEAGUES]]
            for provider, counts in combo["identity_coverage"].items()]), "",
        "PitchAPI's five quarantined matches prevent independently complete season coverage even where every retained appearance "
        "has a feature. Source-native standardization, exposure reconciliation and further source validation are needed before rating use.", "",
        "## Incremental contribution", ""]
    all_families = set(general["families"])
    for provider in general["sources"]:
        without = next((r for r in ranked if set(r["sources"]) == set(general["sources"]) - {provider}), None)
        missing = sorted(all_families - set(without["families"])) if without else sorted(all_families)
        text.extend([f"### {provider}", "", f"Unique observed families added: **{len(missing)}**. "
                     + ", ".join(f"`{name}`" for name in missing), ""])
    text.extend(["## Remaining gaps", "",
        "- Fouls won remains poorly covered. A visible WhoScored ‘fouled’ field is not verified five-league coverage.",
        "- Tracking-based acceleration, sprint speed, off-ball runs and true pressure reception are not established by these collections.",
        "- Physicality and OVR remain unavailable under the current strict ST model.",
        "- GK actions and possession-value estimates in PitchAPI are provider-defined; audit presence does not validate their model quality.",
        "- New sources cannot be recommended as coverage fillers while access, consent or the target season is unresolved.", ""])
    text.extend(["## Additional-source collection outcome", "",
        "Statbunker returned historical player tables, but player IDs are not consistently present and some pages fail. "
        "Its captured columns are inventoried separately; none is treated as a verified coverage filler. "
        "WhoScored's five historical player-statistics pages return HTML shells without numeric tables. "
        "FBref blocks direct retrieval; Sofascore/FotMob need collection permission; StatsBomb has no qualifying season. "
        "This recommendation is strongest among measured eligible inventories, not a claim of an exhaustive global optimum.", ""])
    (folder / "source-selection.md").write_text("\n".join(text), encoding="utf-8")
    matrix = ["# Cross-source feature families and preferred variants", "",
        "Preferred variant maximizes minimum per-league observation coverage, then pooled coverage. "
        "Ties prefer Opta, PitchAPI, Understat. Alternate variants are comparison leads, **not validated interchangeable fallbacks**. "
        "Identity, ratings and event schemas are excluded from performance-family totals.", ""]
    rows = []
    for name, options in sorted(general["families"].items()):
        options = sorted(options, key=lambda v: (-min(v["coverage"].values()), -v["pooled"],
            ["opta", "pitchapi", "understat"].index(v["provider"]), v["key"]))
        best = options[0]
        rows.append([name, f"{best['provider']} `{best['key']}`", *[f"{best['counts'][league]} ({best['coverage'][league]}%)" for league in LEAGUES],
            f"{best['unique_supported']} ({best['pooled']}%)", "yes" if best["all_five_pass"] else "no",
            "; ".join(f"{v['provider']}:{v['key']}" for v in options[1:]),
            "not enabled; requires definition reconciliation"])
    matrix.append(md_table(["Feature family", "Preferred available variant", *LEAGUES, "Five-league unique supported", "Each league ≥90%", "Alternate variants", "Cross-source fallback"], rows))
    (folder / "coverage-matrix.md").write_text("\n".join(matrix), encoding="utf-8")


def run(folder=Path("docs/data-sources"), output=Path("data/source-audit/2025-26"), fetch=False):
    from scout.source_audit_fetch import probe
    from scout.source_table_audit import audit as audit_tables
    from scout.source_table_audit import fotmob_sample
    output.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    access_root = output / "access-20261006"
    probes = probe(access_root) if fetch else read(access_root / "access-manifest.json") if (access_root / "access-manifest.json").exists() else {}
    inventories = {"opta": audit_opta(ROOTS["opta"]), "understat": audit_understat(ROOTS["understat"]),
                   "pitchapi": audit_pitch(ROOTS["pitchapi"])}
    for inventory in inventories.values():
        inventory.apply_empty_cell_policy()
    reports = {provider: inventory.report() for provider, inventory in inventories.items()}
    additional = audit_tables(output / "navigation")
    sample = fotmob_sample(access_root)
    from scout.source_counts import browser_inventory, render
    result = {"audit_version": VERSION, "season": "2025/26", "generated_at": datetime.now(UTC).isoformat(),
        "code_sha256": checksum(__file__), "policy": "source counts only; no coverage gate; existing empty numeric cells are zero",
        "providers": reports, "access_probes": probes, "additional_tables": additional, "fotmob_sample": sample,
        "browser_whoscored": browser_inventory(output),
        "empty_zero_counts": {p: inv.empty_zero_counts for p, inv in inventories.items()}}
    # Content-addressed report snapshots preserve prior audit runs.
    digest = persist_report(output, result)
    return render(folder, output, result, digest)
