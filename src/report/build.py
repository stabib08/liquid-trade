"""Build the versioned analytics report the dashboard consumes.

Recomputes everything from the immutable log (rebuild -> panels -> returns ->
performance/factors/correlation -> kill-criterion verdicts) and writes:
  src/report/out/report.json          (the dashboard payload)
  src/report/out/*.parquet            (return + equity-curve series)
  dashboard/public/data/report.json   (copy for the Next.js app)

Deterministic given the log; safe to run in CI after each snapshot.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .. import baskets as basket_lib
from .. import store
from ..analytics import correlation, factors, famafrench, killcriteria, performance
from ..analytics import panel as panel_mod
from ..analytics import returns as ret_mod

OUT_DIR = store.REPO_ROOT / "src" / "report" / "out"
DASH_DATA = store.REPO_ROOT / "dashboard" / "public" / "data"
THEMATIC = ["SPY", "TLT", "SOXX", "XLU", "MTUM"]


def _r(x, nd=6):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    if isinstance(x, (np.floating, np.integer)):
        x = float(x)
    return round(x, nd) if isinstance(x, float) else x


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return _r(o)
    if isinstance(o, (np.floating, np.integer)):
        return _r(float(o))
    return o


def _code_version():
    try:
        return subprocess.check_output(["git", "describe", "--always", "--dirty"],
                                       cwd=store.REPO_ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _thin(block, cap=800):
    """Stride every parallel list in a chart block down to <= cap points so the
    dashboard payload stays small. Full fidelity is preserved in the Parquet
    artifacts; this only thins what gets plotted."""
    if not block:
        return block
    lists = {k: v for k, v in block.items() if isinstance(v, list)}
    n = max((len(v) for v in lists.values()), default=0)
    if n <= cap:
        return block
    stride = -(-n // cap)  # ceil
    out = dict(block)
    for k, v in lists.items():
        out[k] = v[::stride]
    return out


def _equity_curves(basket_ret, series_map):
    """Growth-of-$1 curves aligned to the basket's common window, rounded."""
    idx = basket_ret.dropna().index
    out = {"dates": [str(d.date()) for d in idx]}
    for name, r in series_map.items():
        curve = (1 + r.reindex(idx).fillna(0)).cumprod()
        out[name] = [_r(v, 4) for v in curve.values]
    return out


def _positioning_overlay(con):
    """Latest positioning per source, structured for the overlay panel."""
    overlay = {"analyze_market": {}, "pulse": []}
    am = con.execute("""
        SELECT mapped_ticker, metric, value, max(as_of_ts) AS ts
        FROM positioning_observations WHERE source='coinvest:analyze_market'
        GROUP BY mapped_ticker, metric, value""").fetch_df()
    for tkr, grp in am.groupby("mapped_ticker"):
        m = dict(zip(grp["metric"], grp["value"]))
        retail, whale = m.get("retail_long_frac"), m.get("whale_long_frac")
        overlay["analyze_market"][tkr] = {
            "retail_long_frac": _r(retail, 3), "whale_long_frac": _r(whale, 3),
            "smart_money_divergence": _r((retail - whale), 3) if (retail is not None and whale is not None) else None,
            "mark_px": _r(m.get("mark_px"), 2),
            "open_interest_usd": _r(m.get("open_interest_usd"), 0),
            "position_count": _r(m.get("position_count"), 0),
            "as_of": str(grp["ts"].max()),
        }
    pulse = con.execute("""
        SELECT symbol, value FROM positioning_observations
        WHERE source='coinvest:get_positioning_pulse' AND metric='notional_usd'
        ORDER BY value DESC""").fetch_df()
    for _, row in pulse.iterrows():
        overlay["pulse"].append({"symbol": row["symbol"],
                                 "notional_usd": _r(row["value"], 0)})
    return overlay


def build() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DASH_DATA.mkdir(parents=True, exist_ok=True)

    adj, cap = panel_mod.load_panels()
    ff5 = famafrench.load()
    rf = ff5["RF"]
    rets = adj.pct_change()

    def excess(t):
        return (rets[t] - rf).dropna() if t in rets.columns else pd.Series(dtype=float)

    spy_x = excess("SPY")
    all_baskets = basket_lib.load_all()

    basket_ret_map = {}
    report_baskets = []
    parquet_curves = {}

    for b in all_baskets:
        b_ret = ret_mod.basket_returns(b.constituents, adj, cap).dropna()
        if b_ret.empty:
            continue
        basket_ret_map[b.id] = b_ret
        bench_ret = ret_mod.ticker_returns(b.primary_benchmark, adj)
        comp_ret = ret_mod.ticker_returns(b.natural_comparator, adj)
        b_excess = (b_ret - rf).dropna()

        # performance
        stats_basket = performance.summary_stats(b_ret, rf)
        stats_bench = performance.summary_stats(bench_ret, rf)
        stats_comp = performance.summary_stats(comp_ret, rf)
        roll = performance.rolling_stats(b_ret, rf, 63)

        # factor regressions
        ff5_reg = factors.ff5_regression(b_excess, ff5)
        etf_x = pd.DataFrame({t: excess(t) for t in THEMATIC})
        thematic_reg = factors.thematic_regression(b_excess, etf_x, THEMATIC)
        comp_reg = factors.comparator_regression(b_excess, excess(b.natural_comparator), spy_x)
        rb = factors.rolling_beta(b_ret, comp_ret, 126)
        rb_latest = (rb.iloc[-1][["beta", "ci_low", "ci_high"]].to_dict()
                     if not rb.empty else None)
        vol_ratio = (stats_basket.get("annualized_vol", np.nan)
                     / stats_comp.get("annualized_vol", np.nan)
                     if stats_comp.get("annualized_vol") else None)

        ev = {"comparator_reg": comp_reg, "ff5": ff5_reg, "thematic": thematic_reg,
              "rolling_comp_beta_latest": rb_latest, "vol_ratio": vol_ratio}
        if b.id == "quantum":
            ev["extra_reg"] = factors.regress(b_excess, {
                "Mkt": spy_x, "Comparator": excess(b.natural_comparator), "TLT": excess("TLT")})
        verdict = killcriteria.evaluate(b.id, ev)

        # correlations vs broad market
        corr_spy = correlation.rolling_correlation(b_ret, rets.get("SPY", pd.Series(dtype=float)), 63)
        corr_qqq = correlation.rolling_correlation(b_ret, rets.get("QQQ", pd.Series(dtype=float)), 63)

        # charts
        curves = _equity_curves(b_ret, {"basket": b_ret, "benchmark": bench_ret,
                                        "comparator": comp_ret})
        parquet_curves[b.id] = b_ret.rename("basket_return")

        report_baskets.append(_clean({
            "id": b.id, "name": b.name, "speculative": b.speculative,
            "thesis": b.thesis, "falsifiable_prediction": b.falsifiable_prediction,
            "kill_criterion": b.kill_criterion,
            "constituents": b.constituents, "primary_benchmark": b.primary_benchmark,
            "natural_comparator": b.natural_comparator,
            "weighting_scheme": b.weighting_scheme,
            "effective_n": ret_mod.effective_n(b.constituents, adj, cap),
            "verdict": verdict,
            "performance": {"basket": stats_basket, "benchmark": stats_bench,
                            "comparator": stats_comp, "vol_ratio_vs_comparator": vol_ratio},
            "factors": {"ff5": ff5_reg, "thematic": thematic_reg,
                        "comparator": comp_reg,
                        "rolling_comparator_beta_latest": rb_latest},
            "equity_curves": _thin(curves),
            "rolling_sharpe": _thin({"dates": [str(d.date()) for d in roll.index],
                               "values": [_r(v, 3) for v in roll["sharpe"].values]}),
            "rolling_beta_series": _thin({
                "dates": [str(d.date()) for d in rb.index],
                "beta": [_r(v, 3) for v in rb["beta"].values],
                "ci_low": [_r(v, 3) for v in rb["ci_low"].values],
                "ci_high": [_r(v, 3) for v in rb["ci_high"].values]}) if not rb.empty else None,
            "rolling_corr": _thin({
                "dates": [str(d.date()) for d in corr_spy.index],
                "vs_SPY": [_r(v, 3) for v in corr_spy.values],
                "vs_QQQ": [_r(v, 3) for v in corr_qqq.reindex(corr_spy.index).values]}),
        }))

    # cross-basket correlation matrix (common dates)
    xmat = correlation.cross_basket_matrix(basket_ret_map)

    con = store.rebuild_from_log()
    try:
        overlay = _positioning_overlay(con)
        run_meta = con.execute(
            "SELECT max(finished_ts), count(*) FROM ingest_runs").fetchone()
    finally:
        con.close()

    report = _clean({
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "code_version": _code_version(),
            "python_version": platform.python_version(),
            "price_source": "yfinance",
            "factor_source": "Ken French Data Library (FF5 daily)",
            "risk_free": "FF daily RF",
            "return_frequency": "daily",
            "weighting": "market-cap (point-in-time snapshots, monthly rebalance)",
            "regression_se": f"Newey-West HAC (maxlags={factors.HAC_LAGS})",
            "rolling_beta_window_days": 126,
            "price_dates": [str(adj.index.min().date()), str(adj.index.max().date())],
            "factor_dates": [str(ff5.index.min().date()), str(ff5.index.max().date())],
            "n_ingest_runs": run_meta[1] if run_meta else None,
            "last_ingest": str(run_meta[0]) if run_meta else None,
            "assumptions_note": "Market-cap weighting; Newey-West t-stats; rolling "
            "6-month (126d) beta for kill-criteria. See docs/methodology.md. "
            "Event studies for the two event-driven theses are not yet implemented.",
        },
        "baskets": report_baskets,
        "cross_basket_correlation": {
            "labels": list(xmat.columns),
            "matrix": [[_r(v, 3) for v in row] for row in xmat.values],
            "window": [str(pd.DataFrame(basket_ret_map).dropna().index.min().date()),
                       str(pd.DataFrame(basket_ret_map).dropna().index.max().date())]
            if basket_ret_map else None,
        },
        "positioning_overlay": overlay,
    })

    (OUT_DIR / "report.json").write_text(json.dumps(report, indent=2))
    shutil.copy(OUT_DIR / "report.json", DASH_DATA / "report.json")
    # Parquet series artifacts
    if parquet_curves:
        pd.DataFrame(parquet_curves).to_parquet(OUT_DIR / "basket_returns.parquet")
    xmat.to_parquet(OUT_DIR / "cross_basket_correlation.parquet")

    print(f"report written: {len(report_baskets)} baskets -> {OUT_DIR/'report.json'}")
    for rb in report_baskets:
        print(f"  {rb['id']:18s} {rb['verdict']['verdict']:14s} {rb['verdict']['headline']}")
    return report


if __name__ == "__main__":
    build()
