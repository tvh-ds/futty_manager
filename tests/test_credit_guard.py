import importlib.util
from datetime import UTC, datetime
from pathlib import Path

spec = importlib.util.spec_from_file_location("credit_guard", Path(__file__).parents[1] / "scripts/credit_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_placeholders_cannot_enable_deployment():
    assert guard.check({})[0] is False


def test_attestation_requires_recent_balance_protection_and_expiry_buffer():
    now = datetime(2026, 10, 6, tzinfo=UTC)
    record = {"checked_at": "2026-10-05T00:00:00Z", "expires_at": "2026-12-01T00:00:00Z",
              "remaining_eur": 20, "spending_protection_confirmed": True}
    assert guard.check(record, now)[0]
    for update in ({"checked_at": "2026-09-01T00:00:00Z"}, {"remaining_eur": 0},
                   {"remaining_eur": float("nan")}, {"expires_at": "2026-10-07T00:00:00Z"},
                   {"spending_protection_confirmed": False}):
        assert not guard.check({**record, **update}, now)[0]
