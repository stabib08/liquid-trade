"""Swappable provider interfaces.

PriceProvider       -> daily equity OHLCV + cap snapshot (yfinance MVP; a paid
                       source like Polygon/Tiingo implements the same ABC).
PositioningProvider -> point-in-time sentiment overlay (Co-Invest / Liquid MCP),
                       which MUST degrade gracefully: an unavailable signal is
                       logged and skipped, never fabricated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PriceRecord:
    ticker: str
    as_of_date: str          # ISO date, the point-in-time key
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    adj_close: Optional[float]
    volume: Optional[int]
    market_cap: Optional[float]
    shares_outstanding: Optional[float]
    currency: Optional[str]
    source: str
    as_of_ts: str            # ISO ts, >= market close of as_of_date
    fetch_ts: str            # ISO ts, when we retrieved it
    ingest_run_id: str


@dataclass(frozen=True)
class PositioningRecord:
    symbol: str
    mapped_ticker: Optional[str]
    basket_id: Optional[str]
    metric: str              # cohort_long_pct | notional_usd | position_count | ...
    value: Optional[float]
    bucket: Optional[str]
    source: str
    as_of_ts: str
    fetch_ts: str
    ingest_run_id: str
    raw: Optional[dict] = None


class PriceProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def fetch_daily(self, tickers: list[str], ingest_run_id: str,
                    period: str = "5d") -> list[PriceRecord]:
        """Return daily observations for `tickers`. Missing tickers are omitted
        (the caller records them as a degradation), never faked."""


class PositioningProvider(ABC):
    """Graceful-degradation contract: implementations return whatever is genuinely
    available and append to `degradation_log` for anything that is not. They never
    invent a value to fill a gap."""

    name: str = "abstract"

    @abstractmethod
    def available(self) -> bool:
        """False when the underlying connector is not reachable (e.g. headless
        cron with no MCP session). Callers must handle False without erroring."""

    @abstractmethod
    def capture(self, ingest_run_id: str,
                degradation_log: list) -> list[PositioningRecord]:
        ...
