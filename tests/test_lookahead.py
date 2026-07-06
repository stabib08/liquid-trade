"""Lookahead-bias guard.

The SPEC requires a test that guards against lookahead. The core invariant of a
point-in-time store is: you cannot possess data you have not yet observed, i.e.
for every record  as_of_ts <= fetch_ts. These tests assert the store REFUSES to
append a violating record, and that the committed log contains no violations.

Run:  ./.venv/bin/python -m pytest -q   (or ./.venv/bin/python tests/test_lookahead.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import store  # noqa: E402


def _rec(as_of_ts: str, fetch_ts: str) -> dict:
    return {
        "ticker": "TEST", "as_of_date": as_of_ts[:10], "source": "unit",
        "close": 1.0, "adj_close": 1.0, "open": 1.0, "high": 1.0, "low": 1.0,
        "volume": 1, "as_of_ts": as_of_ts, "fetch_ts": fetch_ts,
        "ingest_run_id": "test",
    }


def test_future_observation_is_rejected():
    """as_of_ts AFTER fetch_ts = observing the future -> must raise."""
    bad = _rec(as_of_ts="2026-07-10T21:00:00+00:00",
               fetch_ts="2026-07-05T12:00:00+00:00")
    try:
        store.assert_no_lookahead(bad)
    except store.LookaheadError:
        return
    raise AssertionError("store accepted a future-dated observation (lookahead!)")


def test_past_observation_is_allowed():
    ok = _rec(as_of_ts="2026-07-02T21:00:00+00:00",
              fetch_ts="2026-07-05T12:00:00+00:00")
    store.assert_no_lookahead(ok)  # must not raise


def test_committed_log_has_no_lookahead():
    """Every price row ever committed must satisfy the invariant."""
    rows = store._read_jsonl(store.PRICE_LOG)
    violations = []
    for r in rows:
        if store._parse_ts(r["as_of_ts"]) > store._parse_ts(r["fetch_ts"]):
            violations.append((r.get("ticker"), r.get("as_of_date")))
    assert not violations, f"lookahead in committed log: {violations[:10]}"


if __name__ == "__main__":
    test_future_observation_is_rejected()
    test_past_observation_is_allowed()
    test_committed_log_has_no_lookahead()
    print("OK: lookahead guard passing")
