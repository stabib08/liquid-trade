"""Performance statistics. All Sharpe/Sortino use excess returns over the
Fama-French daily risk-free rate for internal consistency with the factor work.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _align_rf(returns: pd.Series, rf_daily: pd.Series) -> pd.Series:
    return rf_daily.reindex(returns.index).fillna(0.0)


def max_drawdown(returns: pd.Series) -> float:
    curve = (1 + returns.fillna(0)).cumprod()
    peak = curve.cummax()
    return float((curve / peak - 1).min())


def summary_stats(returns: pd.Series, rf_daily: pd.Series) -> dict:
    r = returns.dropna()
    if len(r) < 2:
        return {"n_obs": int(len(r))}
    rf = _align_rf(r, rf_daily)
    excess = r - rf
    n = len(r)
    ann_ret = float((1 + r).prod() ** (TRADING_DAYS / n) - 1)
    ann_vol = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))
    ann_excess = float(excess.mean() * TRADING_DAYS)
    sharpe = float(ann_excess / ann_vol) if ann_vol > 0 else float("nan")
    downside = excess[excess < 0].std(ddof=1) * np.sqrt(TRADING_DAYS)
    sortino = float(ann_excess / downside) if downside and downside > 0 else float("nan")
    cum_ret = float((1 + r).prod() - 1)
    return {
        "n_obs": int(n),
        "start": str(r.index.min().date()),
        "end": str(r.index.max().date()),
        "cumulative_return": cum_ret,
        "annualized_return": ann_ret,
        "annualized_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown(r),
    }


def rolling_stats(returns: pd.Series, rf_daily: pd.Series,
                  window: int = 63) -> pd.DataFrame:
    r = returns.dropna()
    rf = _align_rf(r, rf_daily)
    excess = r - rf
    ann_ret = (1 + r).rolling(window).apply(
        lambda x: np.prod(1 + x) ** (TRADING_DAYS / len(x)) - 1, raw=True)
    ann_vol = r.rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS)
    sharpe = (excess.rolling(window).mean() * TRADING_DAYS) / ann_vol
    return pd.DataFrame({"ann_return": ann_ret, "ann_vol": ann_vol,
                         "sharpe": sharpe}).dropna(how="all")


def equity_curve(returns: pd.Series) -> pd.Series:
    return (1 + returns.fillna(0)).cumprod()
