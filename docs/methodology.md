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

## Phase 3 analytics decisions

| Choice | Value | Defense |
|---|---|---|
| Return basis | daily simple returns from `adj_close` | standard; split/div adjusted |
| Risk-free | FF daily `RF` | consistent between Sharpe and factor regressions |
| Basket construction | market-cap weight, monthly rebalance (first trading day), buy-and-hold between rebalances (fixed shares within month) | unambiguous, no daily-rebalance lookahead |
| Sample start per basket | first date all constituents have prices | weights always well-defined; each basket's window is reported (AI-power effectively starts at GEV's 2024 spin-off) |
| Factor set (a) | Fama-French 5 (Mkt-RF, SMB, HML, RMW, CMA) | canonical academic factors |
| Factor set (b) | thematic ETF excess returns: SPY, TLT, SOXX, XLU, MTUM | maps to each thesis's natural drivers |
| Standard errors | **Newey-West HAC, maxlags=5** | daily returns are autocorrelated/heteroskedastic; plain OLS t-stats overstate significance |
| Kill-criterion beta test | **rolling 126-day (6-month) beta** to the natural comparator, 95% CI | matches the "rolling 6-month window" wording in the basket kill-criteria |
| Significance threshold | \|t\| > 2 | conventional |

**Verdict discipline.** A thesis is only marked `FAILED` when its kill-criterion is
*actively met* (e.g. comparator-beta CI contains 1.0 **and** alpha is both small and
insignificant). A large-but-insignificant alpha on a short, high-vol sample is
`INDETERMINATE` (underpowered), never `FAILED` — failing to reject zero is not the
same as zero. This is why AI-Power reads INDETERMINATE despite a +37%/yr alpha point
estimate: the test simply lacks power over ~2 years at ~48% vol.

**Event studies are NOT yet implemented.** The two event-driven theses (Onshoring
Semis, Autonomy/Defense) name catalysts (capex/policy announcements, defense-budget
events) whose test requires a hand-curated, dated event catalog. Until that exists,
those kill-criteria are adjudicated only on their non-event component (comparator
beta, alpha, R²) and explicitly marked INDETERMINATE with the missing test named.

## Open items deferred to later phases

- Event-study catalogs for the two event-driven theses (dated catalyst lists +
  abnormal-return windows).
- Prediction-market mapping, contingent on the connector leaving paper mode.
