"""Return series and market-cap-weighted basket construction.

Weighting: market-cap, monthly rebalance, buy-and-hold between rebalances (fixed
shares within a month, drifting with prices). Weights are derived at each
rebalance from the point-in-time cap stored in the log — never hardcoded.

Point-in-time honesty: a basket series starts only once EVERY constituent has a
price (so weights are always well defined), and each basket's true sample window
is reported. Caps for the pre-inception backfill use current shares outstanding
(documented approximation — see docs/methodology.md / limitations.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def simple_returns(px: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    return px.pct_change()


def basket_value(constituents: list[str], adj_close: pd.DataFrame,
                 market_cap: pd.DataFrame) -> pd.Series:
    """Buy-and-hold, monthly-rebalanced, market-cap-weighted index value (base 1.0).

    Shares are set at the first trading day of each month from that day's caps and
    held fixed through the month; the index value drifts with prices. This is the
    unambiguous, standard construction and avoids any daily-rebalance lookahead.
    """
    cols = [c for c in constituents if c in adj_close.columns]
    px = adj_close[cols].dropna(how="any")
    if px.empty or px.shape[1] == 0:
        return pd.Series(dtype=float)
    caps = market_cap.reindex(index=px.index, columns=cols).ffill()

    period = px.index.to_period("M")
    is_reb = ~pd.Series(period, index=px.index).duplicated().values

    value = pd.Series(index=px.index, dtype=float)
    shares = None
    v = 1.0
    for i, dt in enumerate(px.index):
        if shares is None or is_reb[i]:
            cap_row = caps.loc[dt]
            if cap_row.notna().all() and cap_row.sum() > 0:
                w = cap_row / cap_row.sum()
            else:  # fall back to equal weight only if a cap is genuinely missing
                w = pd.Series(1.0 / len(cols), index=cols)
            shares = (v * w) / px.loc[dt]
        v = float((shares * px.loc[dt]).sum())
        value.loc[dt] = v
    return value


def basket_returns(constituents: list[str], adj_close: pd.DataFrame,
                   market_cap: pd.DataFrame) -> pd.Series:
    return basket_value(constituents, adj_close, market_cap).pct_change()


def ticker_returns(ticker: str, adj_close: pd.DataFrame) -> pd.Series:
    if ticker not in adj_close.columns:
        return pd.Series(dtype=float)
    return adj_close[ticker].dropna().pct_change()


def effective_n(constituents: list[str], adj_close: pd.DataFrame,
                market_cap: pd.DataFrame) -> float:
    """Effective number of names = 1 / sum(w^2) at the latest rebalance. Tells the
    reader how concentrated a market-cap-weighted basket actually is."""
    cols = [c for c in constituents if c in market_cap.columns]
    caps = market_cap[cols].dropna(how="any")
    if caps.empty:
        return float("nan")
    w = caps.iloc[-1] / caps.iloc[-1].sum()
    return float(1.0 / (w ** 2).sum())
