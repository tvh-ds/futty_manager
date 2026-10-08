"""Audit discovered HTML tables without inventing player IDs or ranked-list zeros."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from scout.source_site_probe import inspect

LEAGUES = ("England", "Spain", "Germany", "Italy", "France")
CURRENT = {"791": "England", "792": "Spain", "798": "Germany", "797": "Italy", "796": "France"}


def numeric(value, *, empty_zero=False):
    value = value.strip().replace(",", "")
    if empty_zero and value in {"", "-", "—"}:
        return "numeric", 0.0
    if value in {"", "-", "—", "N/A", "NA"}:
        return "missing", None
    if re.fullmatch(r"[-+]?\d+(\.\d+)?%?", value):
        return "numeric", float(value.rstrip("%"))
    return "categorical", value


def audit(root=Path("data/source-audit/2025-26/navigation")):
    path = root / "collected-tables.json"
    if not path.exists():
        return {}
    nav = json.loads((root / "season-navigation.json").read_text(encoding="utf-8"))
    comps = {}
    for seed in nav.get("statbunker", []):
        current = parse_qs(urlsplit(seed["url"]).query).get("comp_id", [""])[0]
        for option in seed.get("options", []):
            if "25/26" in option["text"] and current in CURRENT:
                comps[option["value"]] = CURRENT[current]
    result = {}
    collected = json.loads(path.read_text(encoding="utf-8"))
    for source, pages in collected["sources"].items():
        fields, provenance, accepted_pages = {}, [], 0
        seen = set()
        for meta in pages:
            url = meta.get("url", "")
            comp = parse_qs(urlsplit(url).query).get("comp_id", [""])[0]
            league = comps.get(comp)
            if source == "whoscored":
                league = next((region for token, region in (("england", "England"), ("spain", "Spain"),
                    ("germany", "Germany"), ("italy", "Italy"), ("france", "France")) if token in url), None)
            provenance.append({**{k: meta.get(k) for k in ("url", "status", "error", "retrieved_at", "sha256", "snapshot")}, "league": league})
            if not meta.get("accepted") or not meta.get("snapshot") or not league:
                continue
            body = (root / source / meta["snapshot"]).read_bytes()
            if hashlib.sha256(body).hexdigest() != meta["sha256"]:
                raise ValueError("Additional-source snapshot checksum mismatch")
            page = inspect(body.decode("utf-8", errors="replace"))
            # Require the selected season, not a historical label anywhere in navigation.
            if source == "statbunker" and not any(o["value"] == comp and "25/26" in o["text"] for o in page["options"]):
                continue
            accepted_pages += 1
            for table_index, table in enumerate(page["tables"]):
                if not table or not any(h.lower() in {"player", "players"} for h in table[0]):
                    continue
                headers = table[0]
                rows = table[1:]
                for column, heading in enumerate(headers):
                    if heading.lower() == "more":
                        continue
                    key = urlsplit(url).path.rsplit("/", 1)[-1] + "." + (heading or f"unlabelled_column_{column}")
                    f = fields.setdefault(key, {"heading": heading, "kind": "identity" if heading.lower() in
                        {"player", "players", "club", "clubs", "position"} else "source-native metric/context",
                        "leagues": {region: {"records": 0, "numeric": 0, "zero": 0, "missing": 0, "categorical": 0,
                            "invalid": 0, "na": 0, "unique_players": None} for region in LEAGUES}, "urls": []})
                    f["urls"].append(url)
                    for row_index, row in enumerate(rows):
                        identity = (source, meta["sha256"], table_index, row_index, column)
                        if identity in seen:
                            continue
                        seen.add(identity)
                        c = f["leagues"][league]
                        c["records"] += 1
                        state, value = numeric(row[column], empty_zero=f['kind'] != 'identity') if len(row) == len(headers) else ("invalid", None)
                        c[state] += 1
                        c["zero"] += state == "numeric" and value == 0
        for f in fields.values():
            f["urls"] = sorted(set(f["urls"]))
        result[source] = {"pages": provenance, "accepted_pages": accepted_pages, "fields": fields,
            "identity_status": "No complete provider-ID inventory established; distinct-player and coverage denominators unknown",
            "collection_status": "Observed tables collected; inaccessible pages and dynamic data remain incomplete"}
    return result


def append_reports(folder, table):
    for source, data in table.items():
        path = folder / f"{source}.md"
        from scout.source_audit import md_table
        text = ["", "## Actual historical navigation and collection", "",
            f"Accepted historical pages: **{data['accepted_pages']}**. {data['collection_status']}.", "",
            data["identity_status"] + ". Names are not substituted for provider IDs. "
            "Ranked-list absence is never interpreted as zero. No records were imported into Scout.", "",
            md_table(["League", "URL", "HTTP", "Retrieved UTC", "Failure"], [[p["league"] or "unknown",
                p["url"], p["status"] or "unknown", p["retrieved_at"] or "unknown", p["error"] or ""] for p in data["pages"]]),
            "### Exhaustive captured player-table columns", "",
            "Cells are **raw numeric records / zero records / missing records / invalid records**. "
            "These are NOT distinct-player counts. Unique player counts, applicable populations, supported percentages "
            "and complete-season coverage are unknown for each field. Verified zero-attempt N/A: none established. "
            "Image labels and column tooltips are preserved. Empty headings remain explicitly unlabelled.", ""]
        rows = []
        for key, f in sorted(data["fields"].items()):
            cells = [" / ".join(str(f["leagues"][region][k]) for k in ("numeric", "zero", "missing", "invalid")) for region in LEAGUES]
            total = " / ".join(str(sum(f["leagues"][region][k] for region in LEAGUES)) for k in ("numeric", "zero", "missing", "invalid"))
            rows.append([f"`{key}`", f["kind"], *cells, total, "unknown", "raw only"])
        text.append(md_table(["Native endpoint.column", "Type", *LEAGUES, "Total records", "Unique players", "Engine"], rows))
        if not rows:
            text.append("No numeric player table was delivered in the retrieved HTML. Dynamic feeds were not obtained; counts remain unknown.")
        text.extend(["", "Snapshot checksums, season identifiers, page URLs and attempted-page failures are retained in "
            "`data/source-audit/2025-26/navigation/`. No challenge was bypassed or paid account started.", ""])
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\n".join(text))


def fotmob_sample(root=Path("data/source-audit/2025-26/access-20261006")):
    """Inventory the already fetched public sample; no further requests."""
    manifest = json.loads((root / "access-manifest.json").read_text(encoding="utf-8"))["fotmob"]
    body = (root / "fotmob" / manifest["snapshot"]).read_bytes()
    if hashlib.sha256(body).hexdigest() != manifest["sha256"]:
        raise ValueError("FotMob sample checksum mismatch")
    match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', body.decode("utf-8", errors="replace"))
    if not match:
        return {}
    data = json.loads(match[1])["props"]["pageProps"]["data"]
    if str(data["currentSeasonId"]) != "27110" or not any(str(s["id"]) == "27110" and s["name"] == "2025/2026" for s in data["seasons"]):
        raise ValueError("Non-target FotMob sample")
    from scout.source_audit import classify, flatten
    fields = {}
    for row in data["statsData"]:
        for key, value in flatten(row):
            fields.setdefault(key, {}).setdefault(str(row["id"]), []).append((classify(value), value))
    counts = {key: {"players": len(values), "numeric": sum(any(s == "numeric" for s, _ in v) for v in values.values()),
        "zero": sum(any(s == "numeric" and value == 0 for s, value in v) for v in values.values()),
        "missing": sum(any(s == "missing" for s, _ in v) for v in values.values())} for key, values in fields.items()}
    return {"provenance": manifest, "season_id": "27110", "team_id": data["teamId"], "team": data["teamName"],
        "sample_player_ids": len({r["id"] for r in data["statsData"]}), "fields": counts,
        "advertised_fields": data["statsList"], "denominator": "Filtered Crystal Palace ranked sample only; league coverage unknown"}


def append_fotmob(folder, sample):
    if not sample:
        return
    from scout.source_audit import md_table
    text = ["", "## Complete captured sample schema", "",
        f"Historical season ID `{sample['season_id']}`; team `{sample['team']}` (`{sample['team_id']}`). "
        f"**{sample['sample_player_ids']} distinct provider IDs**. {sample['denominator']}. All fields remain raw only.", "",
        "England values below are observed sample player counts, not full-league counts. Other leagues and five-league coverage are unknown. "
        "ID/rank/format fields describe records, not football abilities; statValue is interception per90 and substatValue is total interceptions.", "",
        md_table(["Native player field", "England sample numeric", "Zeros", "Missing", "Spain", "Germany", "Italy", "France", "Full five-league coverage"],
            [[f"`{key}`", c['numeric'], c['zero'], c['missing'], *['unknown'] * 5] for key, c in sorted(sample['fields'].items())]),
        "## All advertised player statistic selectors in captured season page", "",
        "This is the complete selector catalogue actually recorded, not proof each feature has observations in every league. "
        "Player counts and coverage are unknown for every selector except the limited interception sample above.", "",
        md_table(["Native selector", "Display name", "Category", "Five-league player coverage"],
            [[f"`{f['name']}`", f.get('title',''), f.get('category',''), 'unknown / permission-dependent'] for f in sample['advertised_fields']]), ""]
    with (folder / 'fotmob.md').open('a', encoding='utf-8') as stream:
        stream.write('\n'.join(text))
