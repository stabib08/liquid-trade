-- liquid-trade time-series store schema (DuckDB)
-- =============================================================================
-- IMMUTABILITY MODEL
-- -----------------------------------------------------------------------------
-- The authoritative, immutable record is the append-only JSONL log under
-- data/snapshots/*.jsonl, which is COMMITTED TO GIT. Each ingestion run appends
-- lines and never rewrites existing ones; `git log` is therefore the tamper-
-- evident audit trail of the whole longitudinal dataset.
--
-- This DuckDB database is a DERIVED CACHE, rebuilt from the log by
-- src/store/store.py (rebuild_from_log). Do not treat it as the source of truth
-- and do not hand-edit it. It is .gitignored precisely so it can never diverge
-- silently from the log.
--
-- POINT-IN-TIME / NO-LOOKAHEAD
-- -----------------------------------------------------------------------------
-- Every observation carries THREE times:
--   as_of_date : the trading date the datum describes (the point-in-time key)
--   as_of_ts   : an instant guaranteed to be at/after that date's US market
--                close (date @ 21:00:00Z; covers both EST and EDT).
--   fetch_ts   : when WE actually retrieved it (provenance).
-- Invariant, enforced at append time (src/store/store.py) and by
-- tests/test_lookahead.py:  as_of_ts <= fetch_ts  for every row.
-- You cannot observe the future. Any analytic that asks "what was knowable on
-- date D" filters rows to fetch_ts <= D; because rows are never mutated, the
-- past is perfectly reconstructable.
-- =============================================================================

-- Raw daily equity observations (one row per ticker per trading date per source).
CREATE TABLE IF NOT EXISTS price_observations (
    ticker              VARCHAR   NOT NULL,
    as_of_date          DATE      NOT NULL,   -- point-in-time key
    open                DOUBLE,
    high                DOUBLE,
    low                 DOUBLE,
    close               DOUBLE,               -- raw close
    adj_close           DOUBLE,               -- split/div-adjusted close (return basis)
    volume              BIGINT,
    market_cap          DOUBLE,               -- snapshot cap, for market-cap weighting
    shares_outstanding  DOUBLE,               -- to reconstruct point-in-time caps
    currency            VARCHAR,
    source              VARCHAR   NOT NULL,    -- e.g. 'yfinance'
    as_of_ts            TIMESTAMPTZ NOT NULL,  -- >= market close of as_of_date
    fetch_ts            TIMESTAMPTZ NOT NULL,  -- when retrieved (>= as_of_ts)
    ingest_run_id       VARCHAR   NOT NULL,
    -- One canonical observation per (ticker, date, source). Re-fetches that agree
    -- are idempotent; a DISAGREEING re-fetch is a new run and is caught by the
    -- store layer rather than silently overwriting history (no silent backfills).
    PRIMARY KEY (ticker, as_of_date, source)
);

-- Positioning / sentiment overlay from the Co-Invest (Liquid) MCP connector.
-- Long/tidy format: one row per (symbol, metric) per capture. Sparse by design —
-- most equity tickers have NO Liquid coverage, and the pipeline logs-and-skips
-- rather than fabricating a value. See docs/coinvest_capabilities.md.
CREATE TABLE IF NOT EXISTS positioning_observations (
    symbol          VARCHAR   NOT NULL,        -- Liquid market symbol
    mapped_ticker   VARCHAR,                   -- our basket ticker, if it maps
    basket_id       VARCHAR,                   -- which thesis this informs, if any
    metric          VARCHAR   NOT NULL,        -- cohort_long_pct | notional_usd |
                                               -- position_count | unusual_activity_ratio
    value           DOUBLE,
    bucket          VARCHAR,                   -- long_heavy | short_heavy | NULL
    source          VARCHAR   NOT NULL,        -- e.g. 'coinvest:get_positioning_pulse'
    as_of_ts        TIMESTAMPTZ NOT NULL,      -- capture instant (positioning is
                                               -- inherently a live snapshot; as_of == fetch)
    fetch_ts        TIMESTAMPTZ NOT NULL,
    ingest_run_id   VARCHAR   NOT NULL,
    raw             JSON                       -- verbatim payload, for reproducibility
);

-- Provenance / audit row per ingestion run. Records what was asked for, what came
-- back, and every graceful-degradation event (a missing signal is DATA, not an error).
CREATE TABLE IF NOT EXISTS ingest_runs (
    run_id                 VARCHAR   NOT NULL PRIMARY KEY,
    started_ts             TIMESTAMPTZ NOT NULL,
    finished_ts            TIMESTAMPTZ,
    price_source           VARCHAR,
    positioning_source     VARCHAR,
    n_price_rows           INTEGER,
    n_positioning_rows     INTEGER,
    tickers_requested      VARCHAR,            -- comma-joined
    tickers_missing        VARCHAR,            -- comma-joined (degradation)
    degradation_log        JSON,               -- list of {stage, detail}
    code_version           VARCHAR,            -- git describe / sha at run time
    python_version         VARCHAR
);
