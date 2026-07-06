# Limitations & honest failure modes

A reviewer should read this next to the README. Negative results and known gaps
are features of this project, not omissions.

## Data

- **Short live history.** The point-in-time series begins the day the snapshotter
  first ran (2026-07-05). Everything before that is *backfilled* daily bars from
  yfinance — real prices, but not captured point-in-time by us, so any analytic
  that depends on *when we knew something* is only trustworthy from inception
  forward. Statistical power is low until the series lengthens; treat early
  Sharpe/alpha/t-stats as indicative, not conclusive.
- **yfinance is a free, best-effort source.** Occasional gaps, late adjustments,
  and rate-limiting (`HTTP 429`) happen. The `PriceProvider` interface exists so a
  paid source (Polygon/Tiingo) can be swapped in via one adapter. Adjusted closes
  can be revised retroactively by the vendor — a form of quiet lookahead we cannot
  fully eliminate with a free feed.
- **Market-cap weighting uses current shares outstanding for the pre-start
  backfill.** Historical share-count changes (buybacks, issuance) are not captured
  before inception, so pre-start weights are approximate. Point-in-time from
  inception onward. (See `methodology.md`.)

## Co-Invest / Liquid positioning

- **Not an equity feed.** Most basket names are not on Liquid; we never use it for
  prices. (`coinvest_capabilities.md`.)
- **`cohort_long_pct` is low-confidence.** Every row read exactly "50% long" in
  the first capture — likely a paper-trading/anonymization artifact. Do not build
  a signal on the long% column until dispersed values are observed; notional and
  position counts are more informative.
- **Positioning is market-wide top-N, not per-ticker.** We capture the crowded
  names that appear (which happen to include `SPACEX`, `MU`, `SKHX`); specific
  basket tickers only show when at a positioning extreme. Per-ticker capture via
  `analyze_market` is a Phase 2 item.
- **Prediction markets are unavailable** (blocked in paper mode), so the intended
  chip-export / AI-milestone / defense-budget outcome overlay is not captured yet.
- **Positioning cannot be captured by the cron.** The MCP connector only exists in
  an interactive Claude session, not in headless GitHub Actions. Price history
  accumulates automatically; positioning is captured opportunistically via a
  staged handoff. Expect a sparse, irregular positioning series.

## Method (applies once Phase 3 analytics land)

- Betas/alphas from short samples have wide error bars; we report t-stats and CIs
  and will say "cannot reject" rather than implying precision we don't have.
- Event studies require a hand-curated, dated catalog of catalysts — itself a
  source of selection bias, disclosed where used.
- The quantum sleeve is explicitly speculative and tiny (2 names); its stats are
  illustrative.

## What this project is NOT

- Not investment advice and not a trading system. It cannot buy the private
  companies the theses are about; the baskets are *public-equity proxies*, and how
  well they proxy the underlying private thesis is itself unverifiable.
- Not a claim of alpha. It is a falsification harness: several theses are expected
  to fail their kill-criteria, and reporting those failures is the point.
