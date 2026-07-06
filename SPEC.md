# SPEC — liquid-trade

> This is the project contract. It is reproduced from the original brief. Where
> reality forced a deviation (e.g. Co-Invest prediction markets being blocked in
> paper mode), the deviation is documented in `docs/` and flagged in the phase
> checklist at the bottom — the SPEC itself is left intact.

## Premise

A portfolio-grade quant research project targeting deep-tech / venture and
crossover investing roles. The owner has theses on private deep-tech companies
(SpaceX, Anduril, …) that cannot be bought directly, so each thesis is expressed
as a **public-equity proxy basket** with a written, falsifiable thesis and an
explicit **kill-criterion**, then tracked for performance, factor exposure, and
correlation against natural benchmarks over time.

Quality bar: point-in-time correctness, reproducibility, real statistics, and
intellectual honesty. No lookahead bias, no fabricated data, negative results
expected and reported.

## Core engineering problem

The interesting part is not calling a price API — it's that useful signals
(especially positioning/sentiment) are **point-in-time snapshots**. The
differentiator is a **persistence-first architecture**: a scheduled job snapshots
prices and positioning into an append-only, immutable time-series store, and all
analytics are *derived* on top of the accumulated history. The longitudinal
dataset is the artifact; the API call is trivial.

## Data sources (honest)

- **Equity prices/returns:** a reliable public source (yfinance MVP), behind a
  `PriceProvider` adapter so a paid source (Polygon/Tiingo) can be swapped in.
- **Co-Invest / Liquid MCP:** primarily crypto-perps and prediction markets, so
  equity tickers are mostly not tradeable. Do **not** treat it as an equity feed.
  Instead: probe capabilities on first run (`docs/coinvest_capabilities.md`); use
  `get_positioning_pulse` (cohort bias) and `get_news` (unusual activity) as a
  sentiment overlay, plus any prediction markets that map to deep-tech outcomes;
  put everything behind a `PositioningProvider` that **degrades gracefully** and
  never fabricates a value.
- **Reproducibility rule:** every stored record carries its `source`, `as_of`
  timestamp, and `fetch` timestamp. No silent backfills.

## Baskets

Each is a versioned `baskets/*.yaml` with: name, one-paragraph thesis, a
falsifiable prediction, a kill-criterion, constituents + weights, primary
benchmark, and a **natural comparator** (the ETF that makes the falsification test
real).

1. **AI Power Demand** — `VST, CEG, GEV, TLN` — comparator **XLU**. Kill: beta to
   XLU ≈ 1 and alpha ≈ 0 → just utilities.
2. **Onshoring Semis** — `TSM, ASML, AMAT` — comparator **SOXX**. Kill: returns
   fully explained by SOXX beta with no event alpha → no onshoring edge.
3. **Autonomy / Defense** — `PLTR, KTOS, AVAV` — comparator **ITA/XAR**. Kill:
   high market beta with no budget-event sensitivity → just high-beta tech.
4. **Quantum** — `IONQ, RGTI` — comparator **ARKK**. Explicitly speculative; kill:
   indistinguishable from ARKK → label it as such.

## Analytics (point-in-time, no lookahead)

- **Performance:** cumulative & annualized return, vol, Sharpe/Sortino, max
  drawdown, rolling metrics — basket vs primary benchmark vs natural comparator.
- **Factor exposure:** OLS of daily basket excess returns on (a) Fama-French 5
  factors (Ken French library) and (b) a curated thematic-ETF factor set
  (SPY, TLT, SOXX, XLU, MTUM). Report betas, t-stats, R². Write the interpretation
  and the kill-criterion verdict, not just numbers.
- **Correlation:** rolling correlation vs SPY/QQQ and a cross-basket correlation
  matrix (are the theses distinct or one big beta trade?).
- **Positioning overlay:** Co-Invest cohort bias / unusual activity where
  available, aligned to price history.

## Deliverable

Python pipeline (pandas + DuckDB) computes everything and writes versioned
JSON/Parquet; a frontend renders it (Next.js → Vercel, or Streamlit as a faster
MVP — pick one, note the tradeoff, don't build both). Daily ingestion via GitHub
Actions cron so history accumulates hands-off. The dashboard leads with the
theses and their pass/fail status against kill-criteria — not a wall of charts.

## Build phases (checkpoint between each)

1. **Scaffold + data layer** — repo, DuckDB schema, `PriceProvider` (yfinance),
   one basket end-to-end, first snapshot committed, Co-Invest probed. Stop at the
   schema.
2. **Ingestion + persistence** — all four baskets, `PositioningProvider` with
   graceful degradation, GitHub Actions cron, historical backfill. Stop.
3. **Analytics** — performance, factor regressions, correlations, positioning
   alignment, with written kill-criterion verdicts. Stop.
4. **Dashboard + docs** — frontend, methodology, limitations, README. Deploy.

## Definition of done

No lookahead (guarded by a test); deterministic & reproducible from a clean
clone; real stats with t-stats and honest interpretation (including "this thesis
failed its kill-criterion"); Co-Invest handled truthfully; a README a reviewer
can skim in 60 seconds.

---

### Deviations from the brief, so far

- **Co-Invest prediction markets are unavailable** ("not available in paper
  trading mode"), so the chip-export / AI-milestone / defense-budget outcome
  overlay is not yet capturable. Logged, degraded gracefully. (`docs/`.)
- **Positioning cannot run in the headless cron** (MCP is session-only); price
  history automates, positioning is captured via a staged handoff.
- **Weighting = market-cap** (owner's decision), stored as a *rule* and derived
  from point-in-time cap snapshots to avoid stale weights / historical-cap
  lookahead.
