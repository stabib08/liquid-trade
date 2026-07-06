"""Append-only time-series store.

Source of truth  : data/snapshots/*.jsonl  (append-only, git-committed)
Derived cache    : data/store.duckdb        (rebuilt from the log, gitignored)

Design rules enforced here:
  1. No mutation. `append_*` only ever appends lines to the JSONL log.
  2. No lookahead. Every record must satisfy as_of_ts <= fetch_ts; violations
     raise LookaheadError at append time (guarded again in tests).
  3. No silent backfill. Re-observing a (ticker, date, source) with a DIFFERENT
     value than already logged raises ConflictError instead of overwriting.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots"
PRICE_LOG = SNAPSHOT_DIR / "prices.jsonl"
POSITIONING_LOG = SNAPSHOT_DIR / "positioning.jsonl"
RUNS_LOG = SNAPSHOT_DIR / "ingest_runs.jsonl"
DUCKDB_PATH = REPO_ROOT / "data" / "store.duckdb"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class LookaheadError(ValueError):
    """Raised when a record claims to have been observed before it existed."""


class ConflictError(ValueError):
    """Raised when a re-observation would silently overwrite differing history."""


def _to_dict(rec) -> dict:
    return asdict(rec) if is_dataclass(rec) else dict(rec)


def _parse_ts(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def assert_no_lookahead(rec: dict) -> None:
    """Core invariant: you cannot fetch data from the future."""
    as_of = _parse_ts(rec["as_of_ts"])
    fetch = _parse_ts(rec["fetch_ts"])
    if as_of > fetch:
        raise LookaheadError(
            f"Lookahead: as_of_ts {as_of.isoformat()} > fetch_ts {fetch.isoformat()} "
            f"for {rec.get('ticker') or rec.get('symbol')!r}"
        )


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _append_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a") as fh:
        for row in rows:
            fh.write(json.dumps(row, default=str, sort_keys=True) + "\n")
            n += 1
    return n


# --- append API -------------------------------------------------------------

# Columns that define whether a re-fetch "agrees" with already-logged history.
# Only the RAW close and volume are the immutability anchor: they are the
# point-in-time record and should never change for a past date. We deliberately
# do NOT include adj_close/open/high/low here — adj_close is *vendor-revisable*
# (a new dividend retroactively re-adjusts the whole back-history), so a differing
# adj_close on re-fetch is expected, not a conflict. On an agreeing (close,volume)
# re-fetch we keep the first-observed row unchanged. See docs/limitations.md.
_PRICE_VALUE_COLS = ("close", "volume")
_CONFLICT_REL_TOL = 1e-4


def append_prices(records) -> int:
    """Append price observations. Idempotent on agreeing re-fetches; refuses
    silent overwrites of disagreeing history. Returns rows actually appended."""
    existing = {
        (r["ticker"], r["as_of_date"], r["source"]): r for r in _read_jsonl(PRICE_LOG)
    }
    to_write: list[dict] = []
    for rec in records:
        rec = _to_dict(rec)
        rec["record_type"] = "price"
        assert_no_lookahead(rec)
        key = (rec["ticker"], rec["as_of_date"], rec["source"])
        if key in existing:
            prior = existing[key]
            disagree = any(
                _num_differs(prior.get(c), rec.get(c), rel=_CONFLICT_REL_TOL)
                for c in _PRICE_VALUE_COLS
            )
            if disagree:
                raise ConflictError(
                    f"Silent-backfill refused for {key}: logged close={prior.get('close')}, "
                    f"new close={rec.get('close')}. Investigate before overwriting."
                )
            continue  # agreeing re-fetch -> idempotent no-op
        to_write.append(rec)
        existing[key] = rec
    return _append_jsonl(PRICE_LOG, to_write)


def _num_differs(a, b, rel=1e-6) -> bool:
    if a is None or b is None:
        return a is not b
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a != b
    scale = max(1.0, abs(a), abs(b))
    return abs(a - b) > rel * scale


def append_positioning(records) -> int:
    """Append positioning observations. Positioning is a live snapshot, so every
    capture is a legitimately new row (no dedupe)."""
    to_write = []
    for rec in records:
        rec = _to_dict(rec)
        rec["record_type"] = "positioning"
        assert_no_lookahead(rec)
        to_write.append(rec)
    return _append_jsonl(POSITIONING_LOG, to_write)


def append_run(run: dict) -> int:
    run = dict(run)
    run["record_type"] = "ingest_run"
    return _append_jsonl(RUNS_LOG, [run])


# --- derived DuckDB cache ----------------------------------------------------

def rebuild_from_log(db_path: Path = DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """Rebuild the DuckDB cache from the append-only JSONL log. Deterministic:
    same log in -> same database out."""
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA_PATH.read_text())

    prices = _read_jsonl(PRICE_LOG)
    if prices:
        con.executemany(
            """INSERT INTO price_observations
               (ticker, as_of_date, open, high, low, close, adj_close, volume,
                market_cap, shares_outstanding, currency, source, as_of_ts,
                fetch_ts, ingest_run_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                [r.get(c) for c in (
                    "ticker", "as_of_date", "open", "high", "low", "close",
                    "adj_close", "volume", "market_cap", "shares_outstanding",
                    "currency", "source", "as_of_ts", "fetch_ts", "ingest_run_id")]
                for r in prices
            ],
        )

    pos = _read_jsonl(POSITIONING_LOG)
    if pos:
        con.executemany(
            """INSERT INTO positioning_observations
               (symbol, mapped_ticker, basket_id, metric, value, bucket, source,
                as_of_ts, fetch_ts, ingest_run_id, raw)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [
                [r.get("symbol"), r.get("mapped_ticker"), r.get("basket_id"),
                 r.get("metric"), r.get("value"), r.get("bucket"), r.get("source"),
                 r.get("as_of_ts"), r.get("fetch_ts"), r.get("ingest_run_id"),
                 json.dumps(r.get("raw")) if r.get("raw") is not None else None]
                for r in pos
            ],
        )

    runs = _read_jsonl(RUNS_LOG)
    if runs:
        con.executemany(
            """INSERT INTO ingest_runs
               (run_id, started_ts, finished_ts, price_source, positioning_source,
                n_price_rows, n_positioning_rows, tickers_requested, tickers_missing,
                degradation_log, code_version, python_version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                [r.get("run_id"), r.get("started_ts"), r.get("finished_ts"),
                 r.get("price_source"), r.get("positioning_source"),
                 r.get("n_price_rows"), r.get("n_positioning_rows"),
                 ",".join(r.get("tickers_requested", [])) if isinstance(r.get("tickers_requested"), list) else r.get("tickers_requested"),
                 ",".join(r.get("tickers_missing", [])) if isinstance(r.get("tickers_missing"), list) else r.get("tickers_missing"),
                 json.dumps(r.get("degradation_log")) if r.get("degradation_log") is not None else None,
                 r.get("code_version"), r.get("python_version")]
                for r in runs
            ],
        )
    return con
