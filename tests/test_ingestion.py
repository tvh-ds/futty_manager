import httpx
import pytest

from scout.ingestion import ApiFootball, QuotaExhausted, canonicalize


def test_cached_pages_do_not_consume_quota(tmp_path):
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"response": [], "paging": {"total": 1}, "errors": {}})
    client = httpx.Client(base_url="https://v3.football.api-sports.io", transport=httpx.MockTransport(respond))
    provider = ApiFootball("test-key", tmp_path, daily_budget=1, client=client)
    provider.get("players", {"page": 1})
    provider.get("players", {"page": 1})
    assert len(calls) == 1
    with pytest.raises(QuotaExhausted):
        provider.get("players", {"page": 2})
    assert "test-key" not in "".join(path.read_text() for path in tmp_path.glob("*.json"))


def test_resume_checkpoint_after_quota(tmp_path):
    requests = []
    def respond(request):
        requests.append(dict(request.url.params))
        return httpx.Response(200, json={"response": [], "paging": {"total": 2}, "errors": {}})
    client = httpx.Client(base_url="https://v3.football.api-sports.io", transport=httpx.MockTransport(respond))
    first = ApiFootball("key", tmp_path, daily_budget=3, client=client)
    with pytest.raises(QuotaExhausted):
        first.ingest(2024)
    first._save({**first._state(), "used": 0})
    second = ApiFootball("key", tmp_path, daily_budget=90, client=client)
    second.ingest(2024)
    assert sum(item.get("page") == "1" and item.get("league") == "39" for item in requests) == 1


def test_broad_positions_are_quarantined_and_missing_counts_retained(tmp_path):
    import json
    document = {"endpoint": "players", "params": {"league": 39, "season": 2024}, "retrieved_at": "2025-07-01", "checksum": "fixture",
      "payload": {"response": [{"player": {"id": 1, "name": "Example"}, "statistics": [{"league": {"id": 39, "season": 2024}, "team": {"id": 2},
        "games": {"minutes": 900, "position": "Defender"}, "goals": {"total": 0, "assists": None}}]}]}}
    (tmp_path / "snapshot.json").write_text(json.dumps(document))
    players, _, quarantine = canonicalize(tmp_path, 2024, {})
    assert not players and quarantine
    players, _, _ = canonicalize(tmp_path, 2024, {"1": ["CB"]})
    assert players[0].metrics["goals_p90"].value == 0
    assert "assists_p90" not in players[0].metrics
    assert players[0].age is None
