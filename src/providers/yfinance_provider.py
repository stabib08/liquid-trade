"""yfinance PriceProvider (MVP).

Swap target: implement the same PriceProvider ABC against Polygon/Tiingo and
change one line in the ingest orchestrator. Nothing else in the pipeline knows
where prices came from beyond the `source` field stamped on every record.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from .base import PriceProvider, PriceRecord

# US equities close 16:00 ET. 21:00Z is at/after that close in BOTH EST (UTC-5)
# and EDT (UTC-4), so as_of_ts is guaranteed >= the real close instant. This is
# the conservative choice that keeps the no-lookahead invariant safe.
_CLOSE_HOUR_UTC = 21


def _as_of_ts(as_of_date: str) -> str:
    d = datetime.fromisoformat(as_of_date)
    return d.replace(hour=_CLOSE_HOUR_UTC, minute=0, second=0,
                     tzinfo=timezone.utc).isoformat()


class YFinanceProvider(PriceProvider):
    name = "yfinance"

    def fetch_daily(self, tickers: list[str], ingest_run_id: str,
                    period: str = "5d") -> list[PriceRecord]:
        fetch_ts = datetime.now(timezone.utc).isoformat()
        records: list[PriceRecord] = []

        for ticker in tickers:
            tk = yf.Ticker(ticker)
            hist = tk.history(period=period, auto_adjust=False)
            if hist is None or hist.empty:
                continue  # missing -> caller logs a degradation; never fabricated

            # Point-in-time cap inputs. shares_outstanding is a *current* figure
            # from yfinance; we store it so Phase 2+ can reconstruct a
            # point-in-time cap as (adj_close_at_date * shares). We do NOT
            # backfill historical caps we cannot actually observe.
            info = {}
            try:
                info = tk.get_info() or {}
            except Exception:
                info = {}
            shares = info.get("sharesOutstanding")
            currency = info.get("currency")

            for ts, row in hist.iterrows():
                as_of_date = pd.Timestamp(ts).date().isoformat()
                close = _f(row.get("Close"))
                mcap = close * shares if (close is not None and shares) else None
                records.append(PriceRecord(
                    ticker=ticker,
                    as_of_date=as_of_date,
                    open=_f(row.get("Open")),
                    high=_f(row.get("High")),
                    low=_f(row.get("Low")),
                    close=close,
                    adj_close=_f(row.get("Adj Close")),
                    volume=_i(row.get("Volume")),
                    market_cap=mcap,
                    shares_outstanding=_f(shares),
                    currency=currency,
                    source=self.name,
                    as_of_ts=_as_of_ts(as_of_date),
                    fetch_ts=fetch_ts,
                    ingest_run_id=ingest_run_id,
                ))
        return records


def _f(v):
    try:
        if v is None or pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return int(f) if f is not None else None
