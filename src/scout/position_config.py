"""Validated, content-versioned position weights shared by every scoring adapter."""

import hashlib
import math
import os
from pathlib import Path
from types import SimpleNamespace

import yaml

CONFIG_PATH = Path(
    os.getenv(
        "SCOUT_POSITION_WEIGHTS_CONFIG",
        Path(__file__).resolve().parents[2] / "Rating System/position_rating_weights_config.yaml",
    )
)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    pairs = loader.construct_pairs(node, deep=deep)
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = value
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate_config(config):
    def weights(values):
        if not values or any(
            isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or not 0 <= w <= 1
            for w in values
        ):
            raise ValueError("Weights must be finite fractions between zero and one")
        if not math.isclose(sum(values), 1, abs_tol=1e-8):
            raise ValueError("Each ability and each position weight total must equal one")

    if config["season"] != "2025/26" or config["minimum_minutes"] < 900 or config["minimum_peers"] < 30:
        raise ValueError("Invalid season or calibration thresholds")
    expected = {"ST", "LW_RW", "LM_RM", "CM", "CAM", "CDM", "CB", "RB_LB", "GK"}
    if set(config["positions"]) != expected:
        raise ValueError("All nine grouped position registries are required")
    for feature in config["features"].values():
        if feature["direction"] not in (-1, 0, 1) or feature["unit"] not in (
            "per90",
            "%",
            "ratio",
            "xG/shot",
            "metres/90",
        ):
            raise ValueError("Invalid feature definition")
    for position in config["positions"].values():
        abilities = position["abilities"]
        if len(abilities) != 6 or len({a["name"] for a in abilities}) != 6:
            raise ValueError("A position must define six unique abilities")
        weights([a["overall_weight"] for a in abilities])
        for ability in abilities:
            weights(list(ability["features"].values()))
            if set(ability["features"]) - config["features"].keys():
                raise ValueError("Unknown feature in position weights")
    return config


def load_config(path=CONFIG_PATH):
    if not path.exists() and path == CONFIG_PATH:
        path = Path(__file__).with_name("position_rating_weights_config.yaml")
    raw = path.read_bytes()
    if len(raw) > 200_000 or b"&" in raw or b"*" in raw:
        raise ValueError("Oversized configuration or YAML aliases are not supported")
    config = validate_config(yaml.load(raw, Loader=UniqueLoader))
    config["checksum"] = hashlib.sha256(raw).hexdigest()
    return config


CONFIG = load_config()
WEIGHTING_VERSION = CONFIG["version"] + ":" + CONFIG["checksum"][:16]
FEATURE_VERSION = "position-features-v1"
DEFINITIONS = {key: SimpleNamespace(key=key, **value) for key, value in CONFIG["features"].items()}


def registry(position, config=CONFIG):
    role = config["positions"].get(position)
    if role is None:
        return {}, {}, {}
    return (
        {a["name"]: a["features"] for a in role["abilities"]},
        {a["name"]: a["overall_weight"] for a in role["abilities"]},
        {a["name"]: a["abbreviation"] for a in role["abilities"]},
    )


POSITION_IDS = {
    "W": "LW_RW",
    "LW": "LW_RW",
    "RW": "LW_RW",
    "LM": "LM_RM",
    "RM": "LM_RM",
    "AM": "CAM",
    "DM": "CDM",
    "FB/WB": "RB_LB",
    "LB": "RB_LB",
    "RB": "RB_LB",
    "LM/RM": "LM_RM",
    "LCM": "CM",
    "RCM": "CM",
    "LCB": "CB",
    "RCB": "CB",
    "LWB": "RB_LB",
    "RWB": "RB_LB",
    "LST": "ST",
    "RST": "ST",
    "LDM": "CDM",
    "RDM": "CDM",
}


def position_id(position):
    return POSITION_IDS.get(position, position)
