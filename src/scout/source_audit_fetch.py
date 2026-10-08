"""Bounded public access checks. Never bypass access challenges or publish data."""
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

URLS = {
    "whoscored": "https://www.whoscored.com/Statistics",
    "fbref": "https://fbref.com/en/comps/Big5/2025-2026/2025-2026-Big-5-European-Leagues-Stats",
    "statbunker": "https://soccerstats.statbunker.com/",
    "statsbomb": "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json",
    "sofascore": "https://www.sofascore.com/sl/terms-and-conditions",
    "fotmob": "https://www.fotmob.com/en-GB/leagues/47/stats/season/27110/players/interception/team/9826/crystal-palace",
}
HOSTS = {urlsplit(url).hostname for url in URLS.values()}
MAX_BYTES = 20_000_000


def fetch(url, root, client, redirect=False):
    """Fixed HTTPS allowlist, streaming bound, no redirect following or secrets."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.password:
        raise ValueError("URL is outside the source audit host allowlist")
    if not redirect and url not in URLS.values():
        raise ValueError("URL is outside the source audit allowlist")
    root.mkdir(parents=True, exist_ok=True)
    entry = {"url": url, "retrieved_at": datetime.now(UTC).isoformat()}
    try:
        with client.stream("GET", url) as response:
            entry.update(status=response.status_code, content_type=response.headers.get("content-type"),
                         last_modified=response.headers.get("last-modified"), location=response.headers.get("location"))
            parts, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Response exceeds audit byte limit")
                parts.append(chunk)
            body = b"".join(parts)
        checksum = hashlib.sha256(body).hexdigest()
        path = root / f"{checksum}.body"
        if not path.exists():
            path.write_bytes(body)
        entry.update(sha256=checksum, bytes=len(body), snapshot=path.name)
        if entry["status"] in {301, 302, 307, 308} and not redirect and entry.get("location"):
            from urllib.parse import urljoin
            destination = urljoin(url, entry["location"])
            if urlsplit(destination).hostname == parsed.hostname and urlsplit(destination).scheme == "https":
                entry["redirect_result"] = fetch(destination, root, client, redirect=True)
        if url == URLS["statsbomb"] and entry["status"] == 200:
            competitions = json.loads(body)
            names = {"Premier League", "La Liga", "1. Bundesliga", "Serie A", "Ligue 1"}
            entry["qualifying_competitions"] = [c for c in competitions if c.get("season_name") in
                {"2025/2026", "2025/26"} and c.get("competition_name") in names
                and c.get("competition_gender") == "male" and not c.get("competition_youth")]
            entry["manifest_entries"] = len(competitions)
        if entry["status"] in {401, 403, 429}:
            entry["collection_status"] = "access_blocked_no_bypass"
        elif entry["status"] == 200:
            entry["collection_status"] = "page_retrieved_not_player_coverage"
        else:
            entry["collection_status"] = "unavailable_response"
    except (httpx.HTTPError, ValueError) as error:
        entry.update(collection_status="failed", error=type(error).__name__)
    return entry


def probe(root: Path):
    manifest = root / "access-manifest.json"
    previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    with httpx.Client(timeout=25, follow_redirects=False,
                      headers={"User-Agent": "Scout-Portfolio-Source-Audit/1.0"}) as client:
        for source, url in URLS.items():
            if source in previous:
                snapshot = root / source / previous[source].get("snapshot", "missing")
                if (snapshot.is_file() and hashlib.sha256(snapshot.read_bytes()).hexdigest() == previous[source].get("sha256")
                        and previous[source].get("status") not in {301, 302, 307, 308}):
                    continue
            previous[source] = fetch(url, root / source, client)
            manifest.write_text(json.dumps(previous, indent=2, allow_nan=False), encoding="utf-8")
            time.sleep(1)
    return previous
