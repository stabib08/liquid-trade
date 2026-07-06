"""Factor regressions with Newey-West (HAC) standard errors.

Daily equity returns are autocorrelated and heteroskedastic, so plain OLS t-stats
overstate significance. We report HAC t-stats (maxlags=5) throughout. Alpha is the
regression intercept; alpha_annual annualizes it by 252. Every regression uses
basket EXCESS returns (over the FF daily RF) as the dependent variable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

TRADING_DAYS = 252
HAC_LAGS = 5

FF5_COLS = ["Mkt_RF", "SMB", "HML", "RMW", "CMA"]


def _ols_hac(y: pd.Series, X: pd.DataFrame) -> dict:
    """OLS with a constant and HAC covariance. Returns tidy coef/tstat dicts."""
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    if len(df) < max(30, X.shape[1] + 5):
        return {"n_obs": int(len(df)), "insufficient": True}
    yy = df["y"]
    XX = sm.add_constant(df[X.columns], has_constant="add")
    res = sm.OLS(yy, XX).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    betas = {k: float(v) for k, v in res.params.items()}
    tstats = {k: float(v) for k, v in res.tvalues.items()}
    return {
        "n_obs": int(len(df)),
        "start": str(df.index.min().date()),
        "end": str(df.index.max().date()),
        "alpha_daily": betas.get("const"),
        "alpha_annual": betas.get("const", 0.0) * TRADING_DAYS,
        "alpha_tstat": tstats.get("const"),
        "betas": {k: v for k, v in betas.items() if k != "const"},
        "tstats": {k: v for k, v in tstats.items() if k != "const"},
        "r2": float(res.rsquared),
        "r2_adj": float(res.rsquared_adj),
        "hac_lags": HAC_LAGS,
    }


def regress(basket_excess: pd.Series, factors: dict) -> dict:
    """General HAC regression of basket excess returns on a named factor dict
    {name: Series}. Used for bespoke kill-criterion tests (e.g. ARKK + TLT)."""
    X = pd.DataFrame({k: v for k, v in factors.items()})
    return _ols_hac(basket_excess, X)


def ff5_regression(basket_excess: pd.Series, ff5: pd.DataFrame) -> dict:
    return _ols_hac(basket_excess, ff5[FF5_COLS])


def thematic_regression(basket_excess: pd.Series, etf_excess: pd.DataFrame,
                        factors: list[str]) -> dict:
    cols = [c for c in factors if c in etf_excess.columns]
    return _ols_hac(basket_excess, etf_excess[cols])


def comparator_regression(basket_excess: pd.Series, comparator_excess: pd.Series,
                          market_excess: pd.Series) -> dict:
    """Two-factor: basket ~ market + comparator. Isolates the comparator beta and
    the alpha AFTER controlling for the broad market — the exact object the AI-power
    and quantum kill-criteria are stated against."""
    X = pd.DataFrame({"Mkt": market_excess, "Comparator": comparator_excess})
    return _ols_hac(basket_excess, X)


def rolling_beta(basket_ret: pd.Series, factor_ret: pd.Series,
                 window: int = 126) -> pd.DataFrame:
    """Rolling single-factor beta with a HAC-free analytic SE and 95% CI. Used for
    the 'is the 6-month beta distinguishable from 1?' kill-criterion test."""
    df = pd.concat([basket_ret.rename("y"), factor_ret.rename("x")], axis=1).dropna()
    out = []
    for i in range(window, len(df) + 1):
        w = df.iloc[i - window:i]
        x, y = w["x"].values, w["y"].values
        xc = x - x.mean()
        var = (xc ** 2).sum()
        if var <= 0:
            continue
        beta = (xc * (y - y.mean())).sum() / var
        alpha = y.mean() - beta * x.mean()
        resid = y - (alpha + beta * x)
        se = np.sqrt((resid ** 2).sum() / (window - 2) / var)
        out.append({"date": w.index[-1], "beta": float(beta),
                    "se": float(se), "ci_low": float(beta - 1.96 * se),
                    "ci_high": float(beta + 1.96 * se)})
    return pd.DataFrame(out).set_index("date") if out else pd.DataFrame()
