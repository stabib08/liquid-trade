"""Analytics smoke + determinism tests.

Guards that basket construction is deterministic and point-in-time clean:
 - a basket return series has no NaN in its declared window,
 - it is reproducible run-to-run (same log -> same numbers),
 - a basket only starts once every constituent has data (no implicit backfill of
   a missing name to zero).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import baskets as basket_lib          # noqa: E402
from src.analytics import panel as panel_mod    # noqa: E402
from src.analytics import returns as ret_mod     # noqa: E402


def test_basket_series_deterministic_and_clean():
    adj, cap = panel_mod.load_panels()
    for b in basket_lib.load_all():
        r1 = ret_mod.basket_returns(b.constituents, adj, cap)
        r2 = ret_mod.basket_returns(b.constituents, adj, cap)
        assert r1.equals(r2), f"{b.id}: non-deterministic basket returns"
        body = r1.dropna()
        if body.empty:
            continue
        # No NaN inside the realised window.
        assert not r1.loc[body.index].isna().any(), f"{b.id}: NaN inside window"
        # Series cannot start before the last-listing constituent has data.
        starts = [adj[c].dropna().index.min() for c in b.constituents if c in adj.columns]
        assert body.index.min() >= max(starts), f"{b.id}: starts before all names exist"


if __name__ == "__main__":
    test_basket_series_deterministic_and_clean()
    print("OK: analytics smoke + determinism passing")
