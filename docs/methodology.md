# Methodology

Living document. Records every data-provenance and modeling decision so the
project is reproducible from a clean clone and defensible under scrutiny. Phase 1
covers the data layer; factor/return methodology is expanded in Phase 3.

## Data provenance

| Field on every record | Meaning |
|---|---|
| `source` | who produced the datum (`yfinance`, `coinvest:get_positioning_pulse`, …) |
| `as_of_date` / `as_of_ts` | the point-in-time the datum describes (trading date; ts ≥ that day's US close) |
| `fetch_ts` | when we actually retrieved it |
| `ingest_run_id` | the run that wrote it; joins to `ingest_runs` for full context |

- **Prices:** `yfinance` (Yahoo Finance), daily bars, `auto_adjust=False` so we
  store both raw `close` and `adj_close`. Returns are computed from `adj_close`
  (split/dividend adjusted). yfinance 1.5.x is pinned because it uses
  `curl_cffi` browser impersonation; older 0.2.x reliably hits Yahoo `HTTP 429`
  from datacenter/shared IPs.
- **Positioning:** Co-Invest / Liquid MCP (`get_positioning_pulse`, `get_news`).
  See `coinvest_capabilities.md` for exactly what is and isn't available and the
  low-confidence caveat on `cohort_long_pct`.

## The store: append-only, point-in-time

- **Source of truth is an append-only JSONL log** (`data/snapshots/*.jsonl`)
  that is **committed to git**. History accumulates in version control; `git log`
  is the tamper-evident audit trail. Each ingestion run appends and never
  rewrites.
- **DuckDB (`data/store.duckdb`) is a derived cache**, rebuilt deterministically
  from the log (`store.rebuild_from_log`) and git-ignored so it can never diverge
  silently.
- **No-lookahead invariant:** every record satisfies `as_of_ts ≤ fetch_ts`,
  enforced at append time and by `tests/test_lookahead.py`. To reconstruct "what
  was knowable on date D", filter `fetch_ts ≤ D`; because rows are immutable, the
  past is exactly reproducible.
- **No silent backfills:** re-observing a `(ticker, date, source)` with a
  *different* value raises `ConflictError` instead of overwriting.

## Modeling decisions (confirmed with the project owner)

| Decision | Choice | Rationale / defense |
|---|---|---|
| Basket weighting | **Market-cap**, derived from point-in-time cap snapshots | Owner's call. See lookahead note below. |
| Return frequency | **Daily** (from `adj_close`) | SPEC assumes daily throughout; standard for factor work. |
| Weight storage | **Not hardcoded** in YAML; the `weighting_scheme` *rule* is stored and weights are derived at analysis time from stored caps | Avoids stale hardcoded weights and avoids historical-cap lookahead. |

### Market-cap weighting — the point-in-time subtlety (important)

Market-cap weighting needs each name's cap *as of each rebalance date*. Doing that
without lookahead requires **historical** shares-outstanding, which yfinance does
not cleanly provide. Our rule, to stay honest:

- We snapshot `market_cap` **and** `shares_outstanding` at fetch time on every run.
- A point-in-time cap on date *t* is reconstructed as `adj_close(t) × shares`,
  using the shares figure **as known on/at *t***, never a future shares figure.
- Weights are recomputed at each monthly rebalance from those point-in-time caps.
- **Limitation:** for the historical backfill window (before this project started
  snapshotting), we only have *current* shares outstanding, so pre-start caps are
  approximate (price moves captured, share-count changes not). This is disclosed
  in `docs/limitations.md`. Going forward, each run captures the then-current
  shares, so the series becomes properly point-in-time from inception onward.

## Open items deferred to later phases

- Factor set, regression windows, and t-stat conventions → **Phase 3** (will be
  chosen and documented here before any regression is run; the owner is consulted
  on window length).
- Per-ticker positioning via `analyze_market` and prediction-market mapping →
  **Phase 2+**, contingent on connector availability.
