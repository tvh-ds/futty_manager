"""Fail-closed deployment gate on a recent portal attestation. Never changes billing."""
import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def check(record, now=None):
    now = now or datetime.now(UTC)
    try:
        checked = datetime.fromisoformat(record["checked_at"].replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
        remaining = float(record["remaining_eur"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return False, "Credit protection/balance/expiry must be verified in the subscription portal"
    if checked.tzinfo is None or expiry.tzinfo is None or checked > now:
        return False, "Invalid attestation timestamp"
    if record.get("spending_protection_confirmed") is not True:
        return False, "Subscription spending protection is unconfirmed"
    if now - checked > timedelta(days=7):
        return False, "Credit attestation is older than seven days"
    if expiry <= now + timedelta(days=3) or not 5 <= remaining < float("inf"):
        return False, "Credit reserve or expiry buffer is insufficient"
    return True, "Recent manual credit attestation accepted; budget alerts do not cap spending"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    allowed, message = check(json.loads(args.record.read_text()))
    print(message)
    raise SystemExit(0 if allowed else 1)
