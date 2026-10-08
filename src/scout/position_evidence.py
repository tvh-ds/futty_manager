"""Read-only provider-local feature bundles from the retained master snapshot."""

import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

from scout.position_config import CONFIG, DEFINITIONS, position_id, registry

PRIORITY = ("opta", "pitchapi", "understat", "whoscored")
MASTER = Path("data/master/2025-26-v2/master.sqlite")
ST_COMPATIBLE = {
    "npg": "npg90",
    "npxg": "npxg90",
    "finish": "finishing_delta90",
    "xgshot": "npxg_per_shot",
    "boxshots": "box_shots90",
    "boxtouch": "box_touches90",
    "opxg": "open_xg90",
    "sca": "sca90",
    "ppa": "ppa90",
    "dribble": "successful_take_ons90",
    "dribblepct": "take_on_pct",
    "carrybox": "box_carries90",
    "carrythird": "third_carries90",
    "passpct": "pass_pct",
    "mis": "miscontrols90",
    "dis": "dispossessed90",
    "intercept": "interceptions90",
    "recover": "recoveries90",
    "aerial": "aerials_won90",
    "aerialpct": "aerial_pct",
}


def measurement(key, bundle, provider, url, scope="aggregate"):
    d = DEFINITIONS[key]
    inputs = d.inputs
    if any(bundle.get(k) is None for k in inputs) or bundle.get("minutes") is None:
        return None
    a = bundle[inputs[0]]
    b = bundle[inputs[1]] if len(inputs) > 1 else bundle["minutes"]
    if key == "pos_savepct":
        b = (bundle.get("saves_made") or 0) + (bundle.get("goals_conceded") or 0)
        if b <= 0:
            return None
        value = a
    elif key == "pos_distpct":
        value = a
    else:
        value = a / b * (100 if d.unit == "%" else 90) if b > 0 else None
    status = (
        "observed"
        if value is not None
        else "not_applicable_zero_attempts"
        if d.unit == "%"
        else "zero_exposure"
    )
    if value is not None and (
        not math.isfinite(value)
        or d.unit == "%"
        and not 0 <= value <= 100
        or value < 0
        and key not in ("pos_finish", "pos_progdist", "pos_prevent")
    ):
        status, value = "invalid", None
    return dict(
        key=key,
        label=d.label,
        unit=d.unit,
        value=value,
        numerator=a,
        denominator=b,
        status=status,
        provider=provider,
        source_url=url,
        measurement_version=f"{provider}:{scope}:" + ",".join(inputs),
    )


class MasterFeatures:
    def __init__(self, path=MASTER):
        self.path = path.resolve(strict=True)
        self.bundles = defaultdict(lambda: defaultdict(dict))
        self.source_rows = {}
        self.positions = {}
        self.names = defaultdict(list)
        with sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True) as con:
            for row, league, names, sources in con.execute("SELECT * FROM players"):
                for source in json.loads(sources):
                    self.source_rows[(source, league)] = row
                for name in json.loads(names):
                    self.names[(name, league)].append(row)
            for provider, _pid, _league, row, field, sample, status, value in con.execute(
                "SELECT provider,player_id,league,master_row,field,sample,status,value_json FROM observations WHERE season=? AND scope IN ('aggregate','identity')",
                (CONFIG["season"],),
            ):
                if status not in ("numeric", "categorical"):
                    continue
                v = json.loads(value)
                if field == "identity.squad_position_detailed" and isinstance(v, str):
                    self.positions[row] = v
                if (
                    status == "numeric"
                    and isinstance(v, (int, float))
                    and not isinstance(v, bool)
                    and math.isfinite(v)
                ):
                    self.bundles[row][(provider, sample)][field.rsplit(".", 1)[-1]] = v
        for bundles in self.bundles.values():
            for (provider, _), bundle in bundles.items():
                bundle["minutes"] = bundle.get(
                    "mins_played" if provider == "opta" else "time" if provider == "understat" else "Mins"
                )
        self.raw = None

    def keeper_appearances(self):
        """Idempotent sample joins; unknown or conflicting samples are not zeros."""
        if self.raw is not None:
            return self.raw
        wanted = {
            f
            for key, d in DEFINITIONS.items()
            if key.startswith("pos_") and d.scope == "appearance"
            for f in d.inputs
        }
        wanted.add("stats.minutes_played.value")
        samples = defaultdict(dict)
        conflicts = set()
        placeholders = ",".join("?" for _ in wanted)
        with sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True) as con:
            for row, pid, sample, field, status, value in con.execute(
                f"SELECT master_row,player_id,sample,field,status,value_json FROM observations WHERE provider='pitchapi' AND season=? AND scope='appearance' AND field IN ({placeholders})",
                (CONFIG["season"], *sorted(wanted)),
            ):
                if self.positions.get(row) != "Goalkeeper":
                    continue
                token = (row, pid, sample)
                v = json.loads(value) if status == "numeric" else None
                if (
                    isinstance(v, bool)
                    or v is not None
                    and (not isinstance(v, (int, float)) or not math.isfinite(v))
                ):
                    v = None
                if field in samples[token] and samples[token][field] != v:
                    conflicts.add(token)
                samples[token][field] = v
        groups = defaultdict(list)
        for (row, pid, sample), values in samples.items():
            if (row, pid, sample) not in conflicts and 0 < (
                values.get("stats.minutes_played.value") or 0
            ) <= 130:
                groups[(row, pid)].append(values)
        self.raw = defaultdict(list)
        for (row, pid), appearances in groups.items():
            bundle = {"minutes": sum(a["stats.minutes_played.value"] for a in appearances)}
            for field in wanted - {"stats.minutes_played.value"}:
                if all(a.get(field) is not None for a in appearances):
                    bundle[field] = sum(a[field] for a in appearances)
            accuracy = "advanced.goalkeeping.distribution_accuracy"
            attempts = "advanced.goalkeeping.distributions"
            if bundle.get(attempts, 0) > 0 and all(
                a.get(accuracy) is not None and 0 <= a[accuracy] <= 100 and a.get(attempts) is not None
                for a in appearances
            ):
                bundle[accuracy] = sum(a[accuracy] * a[attempts] for a in appearances) / bundle[attempts]
            self.raw[row].append((pid, bundle))
        return self.raw

    def attach(self, player, assigned_position=None):
        matches = {
            self.source_rows[(s["provider"] + ":" + s["provider_player_id"], player["league"])]
            for s in player["sources"]
            if s.get("provider_player_id")
            and (s["provider"] + ":" + s["provider_player_id"], player["league"]) in self.source_rows
        }
        # A corroborated source identity is required, not a guessed name match.
        row = next(iter(matches)) if len(matches) == 1 else None
        player["master_row"] = row
        detailed = self.positions.get(row)
        if detailed in ("Left Midfielder", "Right Midfielder", "Wide Midfielder", "LM", "RM"):
            player["position"] = "LM/RM"
        role = assigned_position or position_id(player["position"])
        if not assigned_position and player["position"] == "LM/RM":
            role = "LM_RM"
        player["rating_position"] = role
        abilities, _, _ = registry(role)
        if not abilities:
            return
        keys = {k for weights in abilities.values() for k in weights}
        if role == "ST":
            player["defined_features"] = len(keys)
            player["numerical_features"] = sum(
                player["features"].get(k, {}).get("status") == "observed" for k in keys
            )
            player["supported_features"] = sum(
                player["features"].get(k, {}).get("status") in ("observed", "not_applicable_zero_attempts")
                for k in keys
            )
            return
        candidates = self.bundles.get(row, {})
        for key in sorted(keys):
            d = DEFINITIONS[key]
            choices = []
            if d.scope == "aggregate":
                for (provider, _sample), bundle in candidates.items():
                    source = next((s for s in player["sources"] if s["provider"] == provider), None)
                    if not source:
                        continue
                    feature = measurement(key, bundle, provider, source["source_urls"][0])
                    if feature:
                        choices.append(feature)
                compatible = ST_COMPATIBLE.get(key.removeprefix("pos_"))
                if compatible in player["features"]:
                    old = player["features"][compatible]
                    if old["status"] != "unrecorded_zero" and old["value"] is not None:
                        choices.append({**old, "key": key, "label": d.label, "unit": d.unit})
            elif role == "GK" and row:
                for pid, bundle in self.keeper_appearances().get(row, []):
                    source = next(
                        (
                            s
                            for s in player["sources"]
                            if s["provider"] == "pitchapi" and s.get("provider_player_id") == pid
                        ),
                        None,
                    )
                    if not source:
                        continue
                    feature = measurement(
                        key, bundle, "pitchapi", source["source_urls"][0], "verified-keeper-appearance-window"
                    )
                    if feature:
                        # Do not combine a partial numerator with full-season exposure.
                        if abs(bundle["minutes"] - player["minutes"]) > max(45, 0.02 * player["minutes"]):
                            feature["status"] = "partial_window"
                        choices.append(feature)
            choices.sort(
                key=lambda f: (
                    f["status"] not in ("observed", "not_applicable_zero_attempts"),
                    PRIORITY.index(f["provider"]),
                )
            )
            selected = (
                choices[0]
                if choices
                else dict(
                    key=key,
                    label=d.label,
                    unit=d.unit,
                    value=0.0,
                    numerator=None,
                    denominator=None,
                    status="unrecorded_zero",
                    provider="none",
                    source_url="https://optaplayerstats.statsperform.com/",
                    measurement_version="unrecorded",
                )
            )
            player["features"][key] = selected
        player["defined_features"] = len(keys)
        player["numerical_features"] = sum(player["features"][k]["status"] == "observed" for k in keys)
        player["supported_features"] = sum(
            player["features"][k]["status"] in ("observed", "not_applicable_zero_attempts") for k in keys
        )
