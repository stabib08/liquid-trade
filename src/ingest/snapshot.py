"""Ingestion orchestrator: take one point-in-time snapshot.

Phase 1 scope: snapshot prices for one or more baskets, ingest any staged
Co-Invest positioning, append everything to the immutable log, rebuild the
DuckDB cache, and write a provenance row. Graceful degradation throughout —
a missing signal is recorded as data, never faked, never fatal.

Usage:
    python -m src.ingest.snapshot                 # all baskets
    python -m src.ingest.snapshot --basket ai_power
    python -m src.ingest.snapshot --period 1mo    # deeper backfill window
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone

from .. import baskets as basket_lib
from .. import store
from ..providers.coinvest_provider import CoInvestPositioningProvider
from ..providers.yfinance_provider import YFinanceProvider

# Thematic-factor ETFs pulled on every run regardless of which baskets are
# selected, so the Phase-3 factor regressions always have their factor universe
# (market/SPY, growth/QQQ, rates/TLT, semis/SOXX, utilities/XLU, momentum/MTUM).
FACTOR_UNIVERSE = ["SPY", "QQQ", "TLT", "SOXX", "XLU", "MTUM"]


def _code_version() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "describe", "--always", "--dirty"],
            cwd=store.REPO_ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def run(basket_ids: list[str] | None = None, period: str = "5d") -> dict:
    run_id = uuid.uuid4().hex[:12]
    started = datetime.now(timezone.utc).isoformat()
    degradation: list[dict] = []

    all_baskets = basket_lib.load_all()
    if basket_ids:
        wanted = set(basket_ids)
        all_baskets = [b for b in all_baskets if b.id in wanted]
        missing_baskets = wanted - {b.id for b in all_baskets}
        for mb in sorted(missing_baskets):
            degradation.append({"stage": "config", "detail": f"unknown basket id {mb!r}"})

    # Union of every ticker any selected basket needs (constituents + benchmarks
    # + comparator + factor ETFs) plus the always-on thematic factor universe.
    tickers: list[str] = list(FACTOR_UNIVERSE)
    for b in all_baskets:
        for t in b.all_price_tickers():
            if t not in tickers:
                tickers.append(t)

    # --- prices ---
    price_provider = YFinanceProvider()
    print(f"[{run_id}] fetching {len(tickers)} tickers from {price_provider.name} "
          f"(period={period})...", file=sys.stderr)
    price_records = price_provider.fetch_daily(tickers, run_id, period=period)
    got = {r.ticker for r in price_records}
    for t in tickers:
        if t not in got:
            degradation.append({"stage": "price", "detail": f"no data returned for {t}"})
    n_price = store.append_prices(price_records)

    # --- positioning (graceful) ---
    pos_provider = CoInvestPositioningProvider()
    pos_records = pos_provider.capture(run_id, degradation)
    n_pos = store.append_positioning(pos_records)

    finished = datetime.now(timezone.utc).isoformat()
    run_row = {
        "run_id": run_id,
        "started_ts": started,
        "finished_ts": finished,
        "price_source": price_provider.name,
        "positioning_source": pos_provider.name if pos_records else None,
        "n_price_rows": n_price,
        "n_positioning_rows": n_pos,
        "tickers_requested": tickers,
        "tickers_missing": [t for t in tickers if t not in got],
        "degradation_log": degradation,
        "code_version": _code_version(),
        "python_version": platform.python_version(),
    }
    store.append_run(run_row)

    # Rebuild the derived cache so it always matches the log.
    con = store.rebuild_from_log()
    counts = con.execute(
        "SELECT (SELECT count(*) FROM price_observations), "
        "(SELECT count(*) FROM positioning_observations), "
        "(SELECT count(*) FROM ingest_runs)").fetchone()
    con.close()

    print(f"[{run_id}] appended {n_price} price rows, {n_pos} positioning rows. "
          f"Store now holds {counts[0]} price / {counts[1]} positioning / "
          f"{counts[2]} run rows. Degradations: {len(degradation)}.", file=sys.stderr)
    return run_row


def main() -> None:
    ap = argparse.ArgumentParser(description="Take one point-in-time snapshot.")
    ap.add_argument("--basket", action="append", dest="baskets",
                    help="basket id (repeatable); default = all")
    ap.add_argument("--period", default="5d",
                    help="yfinance history window, e.g. 5d, 1mo, 1y, max")
    args = ap.parse_args()
    run(args.baskets, period=args.period)


if __name__ == "__main__":
    main()
