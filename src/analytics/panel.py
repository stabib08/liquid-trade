"""Load wide price/cap panels from the DuckDB cache (rebuilt from the log)."""

from __future__ import annotations

import pandas as pd

from .. import store


def _load(con, field: str) -> pd.DataFrame:
    df = con.execute(
        f"SELECT as_of_date, ticker, {field} FROM price_observations "
        f"WHERE {field} IS NOT NULL ORDER BY as_of_date"
    ).fetch_df()
    if df.empty:
        return pd.DataFrame()
    wide = df.pivot_table(index="as_of_date", columns="ticker", values=field)
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def load_panels(db_rebuild: bool = True):
    """Return (adj_close, market_cap) wide panels indexed by date, cols=tickers.

    We rebuild the DuckDB cache from the immutable log first so analytics always
    reflect exactly what is committed — no stale cache, fully reproducible.
    """
    con = store.rebuild_from_log() if db_rebuild else store.duckdb.connect(str(store.DUCKDB_PATH))
    try:
        adj = _load(con, "adj_close")
        cap = _load(con, "market_cap")
    finally:
        con.close()
    return adj, cap
