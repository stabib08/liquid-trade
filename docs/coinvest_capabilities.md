# Co-Invest / Liquid connector — capabilities probe

**Probed:** 2026-07-05 (Phase 1). **Method:** live calls to the Co-Invest MCP
connector's discovery tools. This document records *what the connector actually
exposes*, so the pipeline uses it truthfully and never fabricates a value to fill
a gap. It is regenerated when the connector's surface changes.

## TL;DR

- **Liquid is not an equity price feed, and we do not use it as one.** Some
  equity *perpetual* markets exist and their marks track spot reasonably well,
  but coverage is partial, they are leveraged perps (not shares), and there is no
  clean historical OHLCV endpoint to backfill from. **Prices come from
  `yfinance`** (`PriceProvider`); Liquid is a *sentiment overlay* only.
- **The genuinely useful signal is `get_positioning_pulse`** (cohort long/short
  bias) plus `get_news` (headlines + unusual-activity). Both work and are wired
  into `PositioningProvider`.
- **Prediction markets are currently unavailable** ("not available in paper
  trading mode"), so the chip-export / AI-milestone / defense-budget outcome
  mapping the SPEC hoped for **cannot be captured right now**. Recorded as a
  limitation; the pipeline degrades gracefully.

## What was tested

### 1. Equity market coverage (`search_markets`)

| Query | Result | yfinance spot (2026-07-02) | Verdict |
|------|--------|-----------|---------|
| `TSM`  | ✅ `TSM` $444.30, max 10x | $434.16 | present, ~2% of spot |
| `PLTR` | ✅ `PLTR` $128.61, max 10x | $129.30 | present, ~in line |
| `VST`  | ❌ no match (suggested TST/LIT/MSTR…) | — | **absent** |
| `IONQ` | ❌ no match (suggested MON/INJ/IO…) | — | **absent** |

Also seen incidentally: `MSFT`, `MSTR`, `MU` (equity perps). So a *handful* of
large-cap names exist as perps and their marks are close to spot — but **most
basket constituents (VST, CEG, GEV, TLN, ASML, AMAT, KTOS, AVAV, IONQ, RGTI) are
not tradeable on Liquid at all.** Combined with the perps/no-OHLCV issues, Liquid
is unusable as the price source. yfinance stays authoritative.

### 2. Positioning pulse (`get_positioning_pulse`) — **USED**

Returns market-wide cohort bias, split into long-heavy / short-heavy buckets,
with notional and position count. Verbatim top rows from the probe:

```
BTC        50% long | $3.7B  | 53,102 positions
HYPE       50% long | $2.5B  | 32,522
ETH        50% long | $2.4B  | 26,472
SOL        50% long | $763.7M| 18,780
NASDAQ100  50% long | $692.1M| 10,512
SP500      50% long | $619.4M| 13,886
SPACEX     50% long | $563.5M| 17,878   <- a private-co proxy, directly on-thesis
CL (oil)   50% long | $385.9M|  6,272
SKHX       50% long | $376.9M|  4,196   <- SK Hynix, semis-adjacent
MU         50% long | $362.2M|  4,678   <- Micron, semis-adjacent
```

**Two honest caveats, both material:**

1. **It is market-wide top-N, not per-ticker.** It surfaces the *most crowded*
   assets, so a specific basket name (TSM, PLTR) only appears when it is at a
   positioning extreme. For per-ticker positioning we would need
   `analyze_market` (single-asset) — deferred to Phase 2. In Phase 1 we capture
   the pulse as-is; the deep-tech-adjacent names that show up (`SPACEX`, `MU`,
   `SKHX`) are captured and stored, and declared symbols that are absent are
   logged as degradations, **not fabricated**.
2. **Every row read "50% long" in this capture.** That is suspiciously uniform
   and likely a paper-trading / anonymized artifact rather than a real 50/50
   split. Until we see genuinely dispersed values, **treat the `cohort_long_pct`
   metric as low-confidence**; the notional and position-count columns are more
   informative. This caveat is repeated in `docs/limitations.md`.

### 3. News / unusual activity (`get_news`) — **USED (soft signal)**

Returns curated headlines with source links plus a Liquid "unusual activity"
list (symbols whose last-hour volume is anomalous vs. 24h average). The probe
returned relevant macro/semis headlines (SK Hynix $28B US listing, Samsung AI
memory, "semiconductor stocks slide amid AI spending concerns") alongside an
unusual-activity list that was crypto-skewed (`VINE`, `RUNE`, `SUI`, `AAVE`).
Useful as a qualitative overlay to eyeball against the price series; not a
quantitative factor.

### 4. Prediction markets (`search_prediction_markets`) — **UNAVAILABLE**

Both probes (`"semiconductor chip export controls AI"`,
`"defense budget military spending"`) returned:

> `Prediction market search failed: Prediction markets are not available in paper trading mode.`

The account is in paper-trading mode, which gates prediction markets. The SPEC's
intended mapping of prediction markets to deep-tech policy outcomes
(chip-export policy, AI milestones, defense budgets) is therefore **not capturable
right now**. If paper mode is disabled (or a live account is connected), re-run
this probe and revisit. Until then the `PositioningProvider` logs the gap and
continues.

## How this maps into the architecture

| Connector capability | Status | Where it lands |
|---|---|---|
| Equity perps (`search_markets`) | present but partial/perps | **not used for prices** |
| `get_positioning_pulse` | ✅ working (low-confidence long%) | `positioning_observations` |
| `get_news` | ✅ working | qualitative overlay (Phase 3) |
| `search_prediction_markets` | ❌ blocked in paper mode | logged degradation |

**Runtime reality:** the Co-Invest MCP lives in an interactive Claude session and
is **not reachable from the headless GitHub Actions cron**. Positioning is
therefore captured via a staged handoff (`stage_pulse` → `data/staging/…` →
`CoInvestPositioningProvider`), and the automated price cron runs without it. See
`src/providers/coinvest_provider.py` and `docs/limitations.md`.
