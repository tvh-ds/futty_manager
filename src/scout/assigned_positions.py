"""Evaluate planning assignments against fixed natural-position reference players."""

from copy import deepcopy

import numpy as np

from scout.calibration import calibrate_ability, calibrate_composite, display, percentile
from scout.position_config import CONFIG, DEFINITIONS, registry
from scout.striker_features import effective_weights


def score_assignment(subject, references, position):
    abilities, overall_weights, abbreviations = registry(position)
    subject["abilities"], subject["ability_detail"], subject["overall"] = [], {}, None
    for key in ('overall_z','overall_raw','overall_percentile','overall_rank','overall_peer_ids'):
        subject.pop(key, None)
    canonical = {}
    for peer in sorted(references, key=lambda p: (not p["id"].startswith("player-opta-"), p["id"])):
        if peer["rating_position"] == position and peer["minutes"] >= CONFIG["minimum_minutes"]:
            canonical.setdefault(peer.get("master_row") or peer["id"], peer)
    peers = list(canonical.values())
    for name, weights in abilities.items():
        features = subject["features"]
        active = effective_weights(weights, {k: features.get(k, {}).get("status") for k in weights})
        used = [k for k in weights if active[k] > 0 and DEFINITIONS[k].direction]

        def valid(p, k):
            f = p["features"].get(k, {})
            return (
                f.get("status") == "observed"
                and f.get("value") is not None
                and np.isfinite(f["value"])
                and (f.get("denominator") or 0) > 0
            )

        reason, detail = None, None
        if subject["minutes"] < CONFIG["minimum_minutes"]:
            reason = "Below 900 minutes"
        elif not used or not all(valid(subject, k) for k in used):
            reason = "Missing, N/A, invalid or partial-window active features"
        else:
            # Every reference is recalculated using the subject's effective mask;
            # excluded features need not be absent in the reference observations.
            group = [
                p
                for p in peers
                if all(
                    valid(p, k)
                    and (p["features"][k]["provider"], p["features"][k]["measurement_version"])
                    == (features[k]["provider"], features[k]["measurement_version"])
                    for k in used
                )
            ]
            if len(group) < CONFIG["minimum_peers"]:
                reason = f"Only {len(group)} compatible {position} peers; requires 30"
            else:
                values = {k: np.array([p["features"][k]["value"] for p in group]) for k in used}
                calibrated = calibrate_ability(
                    weights,
                    values,
                    {k: np.array([p["features"][k]["denominator"] for p in group]) for k in used},
                    {k: features.get(k, {}).get("status") for k in weights},
                    {k: features[k]["value"] for k in used},
                    {k: features[k]["denominator"] for k in used},
                    definitions=DEFINITIONS,
                )
                composite = calibrated.composite
                if composite.z is None or np.std(composite.peer_raw) <= 1e-12:
                    reason = "Reference ability has insufficient variation"
                else:
                    detail = {
                        "raw": composite.raw,
                        "z": composite.z,
                        "rating": display(composite.z),
                        "percentile": percentile(composite.z, composite.peer_z),
                        "peer_ids": [p["id"] for p in group],
                        "peer_z": composite.peer_z.tolist(),
                        "effective_weights": active,
                        "excluded_zero_filled": [
                            k for k in weights if features.get(k, {}).get("status") == "unrecorded_zero"
                        ],
                        "feature_stats": {
                            k: {
                                "stable": stat.stable,
                                "reliability": stat.reliability,
                                "z": stat.z,
                                "mean": stat.mean,
                                "percentile": percentile(features[k]["value"], values[k])
                                if DEFINITIONS[k].direction > 0
                                else 100 - percentile(features[k]["value"], values[k]),
                            }
                            for k, stat in calibrated.features.items()
                        },
                    }
                    subject["ability_detail"][name] = detail
        subject["abilities"].append(
            {
                "name": name,
                "abbreviation": abbreviations[name],
                "rating": detail["rating"] if detail else None,
                "available": sum(valid(subject, k) for k in weights),
                "defined": len(weights),
                "peer_count": len(detail["peer_ids"]) if detail else 0,
                "reason": reason,
            }
        )
    details = subject["ability_detail"]
    if len(details) == 6:
        maps = {name: dict(zip(d["peer_ids"], d["peer_z"], strict=True)) for name, d in details.items()}
        common = sorted(set.intersection(*(set(m) for m in maps.values())))
        if len(common) >= CONFIG["minimum_peers"]:
            result = calibrate_composite(
                overall_weights,
                {name: d["z"] for name, d in details.items()},
                {name: np.array([m[i] for i in common]) for name, m in maps.items()},
            )
            if result.z is not None and np.std(result.peer_raw) > 1e-12:
                subject.update(
                    overall=display(result.z),
                    overall_z=result.z,
                    overall_raw=result.raw,
                    overall_percentile=percentile(result.z, result.peer_z),
                    overall_rank=1 + int(np.sum(result.peer_z > result.z)),
                    overall_peer_ids=common,
                )
    return subject


def build_assignments(players, squad_map, master):
    for p in players:
        if p["id"] not in set(squad_map.values()):
            continue
        keeper = p["rating_position"] == "GK"
        evaluations = {}
        for position in CONFIG["positions"]:
            if (position == "GK") != keeper:
                continue
            subject = deepcopy({k: v for k, v in p.items() if k != "position_evaluations"})
            for key in ("overall_z", "overall_raw", "overall_percentile", "overall_rank", "overall_peer_ids"):
                subject.pop(key, None)
            master.attach(subject, assigned_position=position)
            score_assignment(subject, players, position)
            evaluations[position] = {
                k: v
                for k, v in subject.items()
                if k
                in (
                    "rating_position",
                    "features",
                    "abilities",
                    "ability_detail",
                    "overall",
                    "overall_z",
                    "overall_raw",
                    "overall_percentile",
                    "overall_rank",
                    "overall_peer_ids",
                    "defined_features",
                    "numerical_features",
                    "supported_features",
                )
            }
        p["position_evaluations"] = evaluations
