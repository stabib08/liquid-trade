"""Correlation analytics: rolling correlation vs broad-market proxies and the
cross-basket matrix (are the four theses distinct, or one big beta trade?)."""

from __future__ import annotations

import pandas as pd


def rolling_correlation(a: pd.Series, b: pd.Series, window: int = 63) -> pd.Series:
    df = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    return df["a"].rolling(window).corr(df["b"]).dropna()


def cross_basket_matrix(basket_returns: dict[str, pd.Series]) -> pd.DataFrame:
    """Full-sample pairwise correlation on the dates common to all baskets."""
    df = pd.DataFrame(basket_returns).dropna()
    return df.corr()
