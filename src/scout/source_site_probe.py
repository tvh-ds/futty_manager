"""Inspect discovered navigation and collection conditions without browser bypasses."""
import hashlib
import json
import re
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

HOSTS = {"www.whoscored.com", "soccerstats.statbunker.com"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.text, self.tables, self.options = [], [], [], []
        self.href, self.link_text = None, []
        self.table, self.row, self.cell = None, None, None
        self.row_links, self.table_links, self.tables_links = [], [], []
        self.option = None
        self.hidden = 0
        self.parents = []
        self.cell_title = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "a":
            self.href, self.link_text = a.get("href"), []
        if tag == "table":
            self.parents.append((self.table, self.row, self.cell, self.row_links, self.table_links))
            self.table = []
            self.table_links = []
            self.row, self.cell = None, None
        if tag == "tr" and self.table is not None:
            self.row = []
            self.row_links = []
        if tag in {"td", "th"} and self.row is not None:
            self.cell = []
            self.cell_title = a.get("title", "")
        if tag == "img" and self.cell is not None and a.get("alt"):
            self.cell.append(a["alt"])
        if tag == "option":
            self.option = {"value": a.get("value"), "text": []}

    def handle_data(self, data):
        if self.hidden:
            return
        if data.strip():
            self.text.append(data.strip())
        if self.href is not None:
            self.link_text.append(data)
        if self.cell is not None:
            self.cell.append(data)
        if self.option is not None:
            self.option["text"].append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "a" and self.href is not None:
            self.links.append({"href": self.href, "text": " ".join(self.link_text).strip()})
            if self.row is not None:
                self.row_links.append(self.links[-1])
            self.href = None
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join(self.cell).strip() or self.cell_title)
            self.cell = None
        if tag == "tr" and self.row is not None:
            if self.row:
                self.table.append(self.row)
                self.table_links.append(self.row_links)
            self.row = None
        if tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.tables_links.append(self.table_links)
            self.table, self.row, self.cell, self.row_links, self.table_links = self.parents.pop()
        if tag == "option" and self.option is not None:
            self.option["text"] = " ".join(self.option["text"]).strip()
            self.options.append(self.option)
            self.option = None


def inspect(html):
    page = Page()
    page.feed(html)
    return {"links": page.links, "tables": page.tables, "tables_links": page.tables_links, "options": page.options,
            "text": " ".join(page.text)}


def fetch(url, root, client, redirected=False):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.password:
        raise ValueError("Unapproved source navigation")
    root.mkdir(parents=True, exist_ok=True)
    request_id = hashlib.sha256(url.encode()).hexdigest()
    meta = root / f"{request_id}.json"
    if meta.exists():
        saved = json.loads(meta.read_text(encoding="utf-8"))
        body = root / saved.get("snapshot", "missing")
        if body.is_file() and hashlib.sha256(body.read_bytes()).hexdigest() == saved.get("sha256"):
            return {**saved, "cached": True}, body.read_text(encoding="utf-8", errors="replace")
    saved = {"url": url, "retrieved_at": datetime.now(UTC).isoformat()}
    try:
        with client.stream("GET", url) as response:
            saved.update(status=response.status_code, location=response.headers.get("location"))
            parts, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 5_000_000:
                    raise ValueError("Source page exceeds byte limit")
                parts.append(chunk)
            data = b"".join(parts)
        saved["sha256"] = hashlib.sha256(data).hexdigest()
        saved["snapshot"] = saved["sha256"] + ".html"
        path = root / saved["snapshot"]
        if not path.exists():
            path.write_bytes(data)
        html = data.decode("utf-8", errors="replace")
        if saved["status"] in {301, 302, 307, 308} and saved.get("location") and not redirected:
            destination = urljoin(url, saved["location"])
            if urlsplit(destination).hostname == urlsplit(url).hostname and urlsplit(destination).scheme == "https":
                child, html = fetch(destination, root, client, redirected=True)
                saved.update(child, redirected_from=url)
    except (httpx.HTTPError, ValueError) as error:
        saved["error"] = type(error).__name__
        html = ""
    meta.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    time.sleep(1)
    return saved, html


def probe(root=Path("data/source-audit/2025-26/navigation")):
    root.mkdir(parents=True, exist_ok=True)
    result = {}
    with httpx.Client(timeout=10, follow_redirects=False,
                      headers={"User-Agent": "Scout-Portfolio-Source-Audit/1.0"}) as client:
        for source, urls in {
            "whoscored": ["https://www.whoscored.com/termsofuse", "https://www.whoscored.com/robots.txt"],
            "statbunker": ["https://soccerstats.statbunker.com/robots.txt",
                           "https://soccerstats.statbunker.com/competitions/LeagueTable?comp_id=791"],
        }.items():
            result[source] = []
            for url in urls:
                meta, html = fetch(url, root / source, client)
                page = inspect(html)
                snippets = [page["text"][max(0, m.start() - 150):m.end() + 250] for m in
                    re.finditer(r"scrap|automated|robots|personal|non.commercial|extract|2025|2026", page["text"], re.I)]
                result[source].append({**meta, "snippets": snippets[:25],
                    "options": page["options"], "tables": page["tables"],
                    "links": [link for link in page["links"] if any(s in link["href"].lower() for s in
                        ["comp_id", "season", "terms", "conditions", "privacy", "statistics"])]})
    (root / "navigation-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def seasons(root=Path("data/source-audit/2025-26/navigation")):
    """Only URLs observed in cached provider navigation, never guessed seasons."""
    from scout.source_audit_fetch import URLS
    access = root.parent / "access-20261006"
    access_manifest = json.loads((access / "access-manifest.json").read_text(encoding="utf-8"))
    result = {}
    with httpx.Client(timeout=10, follow_redirects=False,
                      headers={"User-Agent": "Scout-Portfolio-Source-Audit/1.0"}) as client:
        for source in ("whoscored", "statbunker"):
            p = access_manifest[source].get("redirect_result", access_manifest[source])
            html = (access / source / p["snapshot"]).read_text(encoding="utf-8", errors="replace")
            if source == "whoscored":
                urls = [urljoin(URLS[source], href) for href, _ in re.findall(r"url:'([^']+)', name:'([^']+)'", html)
                    if any(href.endswith(s) for s in ("/england-premier-league", "/france-ligue-1", "/germany-bundesliga",
                                              "/italy-serie-a", "/spain-laliga"))]
            else:
                urls = [link["href"] for link in inspect(html)["links"] if link["text"] in
                    {"Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1", "French Ligue"}]
            result[source] = []
            for url in sorted(set(urls)):
                meta, html = fetch(url, root / source, client)
                page = inspect(html)
                result[source].append({**meta, "text": page["text"], "options": page["options"],
                    "links": page["links"], "tables": page["tables"]})
    (root / "season-navigation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {k: [{"url": p["url"], "status": p.get("status"), "error": p.get("error"),
        "options": [o for o in p["options"] if "2025" in o["text"] or "2026" in o["text"]],
        "text": p["text"][:700]} for p in v] for k, v in result.items()}


def collect(root=Path("data/source-audit/2025-26/navigation"), budget=300):
    """Collect discovered historical player tables, respecting same-host scope.

    Ranked tables never establish zero values for players absent from the table.
    Dynamic pages without a numeric table are incomplete, not fabricated feeds.
    """
    nav = json.loads((root / "season-navigation.json").read_text(encoding="utf-8"))
    result = {"whoscored": [], "statbunker": []}
    requests = 0
    with httpx.Client(timeout=10, follow_redirects=False,
                      headers={"User-Agent": "Scout-Portfolio-Source-Audit/1.0"}) as client:
        for source in result:
            for seed in nav[source]:
                if source == "whoscored" and not any(seed["url"].endswith(t) for t in
                    ["/england-premier-league", "/spain-laliga", "/germany-bundesliga", "/italy-serie-a", "/france-ligue-1"]):
                    continue
                if not seed.get("snapshot"):
                    meta, html = fetch(seed["url"], root / source, client)
                    requests += not meta.get("cached", False)
                else:
                    html = (root / source / seed["snapshot"]).read_text(encoding="utf-8", errors="replace")
                page = inspect(html)
                option = next((o for o in page["options"] if o["text"] == "2025/2026"), None) if source == "whoscored" else next(
                    (o for o in page["options"] if "25/26" in o["text"]), None)
                if not option:
                    result[source].append({"url": seed["url"], "status": "target season not discovered", "accepted": False})
                    continue
                url = urljoin(seed["url"], option["value"]) if source == "whoscored" else re.sub(
                    r"comp_id=\d+", "comp_id=" + option["value"], seed["url"])
                meta, html = fetch(url, root / source, client)
                requests += not meta.get("cached", False)
                season = inspect(html)
                label = option["text"]
                if meta.get("status") != 200:
                    result[source].append({**meta, "label": label, "accepted": False})
                    continue
                if source == "whoscored":
                    urls = [urljoin(url, link["href"]) for link in season["links"]
                            if link["text"].strip() == "Player Statistics"]
                else:
                    urls = [urljoin(url, link["href"]) for link in season["links"] if "/competitions/" in link["href"]
                            and any(word in link["text"].lower() for word in
                                ["player", "scorer", "assist", "appearances", "minutes", "booked", "sent off", "hat trick"])
                            and "teams" not in link["href"].lower() and "club_id" not in link["href"]]
                queue, seen = sorted(set(urls)), set()
                while queue and requests < budget:
                    target = queue.pop(0)
                    if target in seen:
                        continue
                    seen.add(target)
                    meta, html = fetch(target, root / source, client)
                    requests += not meta.get("cached", False)
                    table = inspect(html)
                    target_ok = (label.lower() in table["text"].lower() if source == "statbunker"
                                 else "2025/2026" in table["text"])
                    rows = {**meta, "label": label, "accepted": meta.get("status") == 200 and target_ok,
                            "tables": table["tables"], "tables_links": table["tables_links"],
                            "links": table["links"], "options": table["options"],
                            "pagination_seen": []}
                    if rows["accepted"]:
                        for link in table["links"]:
                            next_url = urljoin(target, link["href"])
                            if (urlsplit(next_url).hostname == urlsplit(target).hostname
                                    and urlsplit(next_url).path.lower() == urlsplit(target).path.lower()
                                    and parse_qs(urlsplit(next_url).query).get("comp_id") == parse_qs(urlsplit(target).query).get("comp_id")
                                    and any(s in next_url.lower() for s in ["page=", "offset=", "start="])
                                    and next_url not in seen):
                                queue.append(next_url)
                                rows["pagination_seen"].append(next_url)
                    result[source].append(rows)
                    (root / "collected-tables.json").write_text(json.dumps({"requests": requests, "sources": result}, indent=2), encoding="utf-8")
                if queue:
                    result[source].append({"label": label, "accepted": False, "status": "request budget exhausted", "remaining": len(queue)})
    result = {"requests": requests, "sources": result}
    (root / "collected-tables.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"requests": requests, "pages": {source: len(rows) for source, rows in result["sources"].items()}}
