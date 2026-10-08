"""StatsBomb historical research adapter; never creates current candidate releases."""
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import httpx


def prepare_shots(matches: list, event_files: dict[int, list]):
    dates = {item["match_id"]: item["match_date"] for item in matches}
    shots, quarantine = [], []
    seen = set()
    for match_id, events in event_files.items():
        for event in events:
            if event.get("type", {}).get("name") != "Shot" or event.get("period", 0) == 5:
                continue  # Exclude penalty shootouts, retain in-match penalties.
            try:
                if match_id not in dates or not event.get("id") or event["id"] in seen:
                    raise ValueError("Missing date/ID or duplicate shot")
                seen.add(event["id"])
                x, y = event["location"][:2]
                if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= 120 and 0 <= y <= 80):
                    raise ValueError("Invalid normalized coordinates")
                shot = event["shot"]
                outcome, body_part = shot["outcome"]["name"], shot["body_part"]["name"]
                if outcome not in {"Goal", "Saved", "Off T", "Post", "Blocked", "Wayward", "Saved Off Target", "Saved to Post"}:
                    raise ValueError("Unknown shot outcome")
                if body_part not in {"Head", "Left Foot", "Right Foot", "Other"}:
                    raise ValueError("Unknown body part")
                pressure = event.get("under_pressure", False)  # Provider boolean presence convention.
                if not isinstance(pressure, bool):
                    raise ValueError("Invalid pressure flag")
                dx, dy = 120 - x, y - 40
                shots.append({"event_id": event["id"], "match_id": match_id, "match_date": dates[match_id],
                    "goal": int(outcome == "Goal"), "distance": math.hypot(dx, dy),
                    "angle": math.atan2(8 * dx, dx * dx + dy * dy - 16),
                    "header": int(body_part == "Head"), "under_pressure": int(pressure)})
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                quarantine.append({"match_id": match_id, "event_id": event.get("id"), "reason": str(error)})
    return shots, quarantine


def fetch_research(root: Path, competition: int = 9, season: int = 281):
    """Fetch pinned, checksummed male senior events; source is fixed, no arbitrary URL."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    root.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=False) as client:
        response = client.get("https://api.github.com/repos/hudl/open-data/commits/master")
        response.raise_for_status()
        revision = response.json()["sha"]
        records = []

        def fetch(path):
            url = f"https://raw.githubusercontent.com/hudl/open-data/{revision}/{path}"
            result = client.get(url)
            result.raise_for_status()
            if len(result.content) > 20_000_000:
                raise ValueError("Historical snapshot exceeds limit")
            checksum = hashlib.sha256(result.content).hexdigest()
            destination = root / revision / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(result.content)
            records.append({"url": url, "sha256": checksum, "bytes": len(result.content)})
            return result

        competitions = fetch("data/competitions.json").json()
        selected = next((item for item in competitions if item["competition_id"] == competition and item["season_id"] == season), None)
        if not selected or selected["competition_gender"] != "male" or selected["competition_youth"]:
            raise ValueError("Historical research requires a male senior competition")
        fetch("LICENSE.pdf")
        fetch("README.md")
        matches = fetch(f"data/matches/{competition}/{season}.json").json()
        events = {item["match_id"]: fetch(f"data/events/{item['match_id']}.json").json() for item in matches}
    shots, quarantine = prepare_shots(matches, events)
    if not shots:
        raise ValueError("No valid historical shots")
    pq.write_table(pa.Table.from_pylist(shots), root / "shots.parquet")
    manifest = {"scope": "historical-research-only", "source": "StatsBomb Open Data (Hudl)", "revision": revision,
        "competition": selected, "matches": len(matches), "shots": len(shots), "quarantine": quarantine,
        "retrieved_at": datetime.now(UTC).isoformat(), "snapshots": records,
        "limitations": ["Selected open matches may not cover an entire league; selection bias remains",
                        "Coordinates use a normalized 120x80 pitch; distance is not physical metres",
                        "Absent under_pressure flag is false under the provider presence convention",
                        "In-match penalties included; shootout shots excluded",
                        "Before public sharing, review archived license and provide required source/logo attribution",
                        "Does not certify any current candidate coverage or publication permission"]}
    (root / "source-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root / "shots.parquet"
