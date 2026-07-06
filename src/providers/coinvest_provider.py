"""Co-Invest (Liquid) PositioningProvider.

HONEST ARCHITECTURE NOTE
------------------------
Co-Invest is a claude.ai MCP connector. It is reachable only inside an
interactive Claude session that has the connector authenticated. A standalone
Python process — in particular the GitHub Actions cron — CANNOT call it.

So the data flow is a deliberate handoff, not a direct call:

  1. During a Claude-driven run, the assistant calls the MCP tools
     (get_positioning_pulse / get_news) and writes the raw payload to
     data/staging/coinvest_pulse.json via `stage_pulse(...)`.
  2. This provider reads that staged file, parses it into PositioningRecords,
     attributes each symbol to a basket where we declared coverage, and marks
     the file consumed.
  3. If no staged capture exists (e.g. headless cron), available() is False and
     capture() logs a graceful-degradation entry and returns []. NEVER fabricated.

See docs/coinvest_capabilities.md for what the connector actually exposes and
its current limitations (prediction markets blocked in paper mode, etc.).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..baskets import positioning_symbol_map
from .base import PositioningProvider, PositioningRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
STAGING_DIR = REPO_ROOT / "data" / "staging"
PULSE_FILE = STAGING_DIR / "coinvest_pulse.json"


def stage_pulse(payload: dict) -> Path:
    """Called by the Claude/MCP capture step. Persists a raw pulse payload for
    the pipeline to ingest. Payload shape (documented, verbatim from MCP):
        {
          "source": "coinvest:get_positioning_pulse",
          "fetched_at": "<ISO ts>",
          "long_heavy":  [{"symbol": "...", "long_pct": 0.5,
                           "notional_usd": ..., "position_count": ...}, ...],
          "short_heavy": [ ... same shape ... ]
        }
    """
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    PULSE_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return PULSE_FILE


class CoInvestPositioningProvider(PositioningProvider):
    name = "coinvest"

    def available(self) -> bool:
        return PULSE_FILE.exists()

    def capture(self, ingest_run_id: str,
                degradation_log: list) -> list[PositioningRecord]:
        if not self.available():
            degradation_log.append({
                "stage": "positioning",
                "detail": "Co-Invest MCP not staged (no data/staging/coinvest_pulse.json); "
                          "positioning overlay skipped for this run.",
            })
            return []

        payload = json.loads(PULSE_FILE.read_text())
        fetch_ts = payload.get("fetched_at") or datetime.now(timezone.utc).isoformat()
        source = payload.get("source", "coinvest:get_positioning_pulse")
        sym_map = positioning_symbol_map()

        records: list[PositioningRecord] = []
        for bucket in ("long_heavy", "short_heavy"):
            for row in payload.get(bucket, []):
                sym = str(row.get("symbol", "")).upper()
                mapped, basket_id = sym_map.get(sym, (None, None))
                # positioning is a live snapshot: as_of == fetch (no lookahead risk)
                common = dict(symbol=sym, mapped_ticker=mapped, basket_id=basket_id,
                              bucket=bucket, source=source, as_of_ts=fetch_ts,
                              fetch_ts=fetch_ts, ingest_run_id=ingest_run_id,
                              raw=row)
                for metric, key in (("cohort_long_pct", "long_pct"),
                                    ("notional_usd", "notional_usd"),
                                    ("position_count", "position_count")):
                    if row.get(key) is not None:
                        records.append(PositioningRecord(
                            metric=metric, value=_num(row.get(key)), **common))

        # Attribution transparency: note basket symbols that had NO coverage.
        covered = {r.symbol for r in records}
        for sym, (_, basket_id) in sym_map.items():
            if sym not in covered:
                degradation_log.append({
                    "stage": "positioning",
                    "detail": f"declared symbol {sym} (basket {basket_id}) absent from "
                              f"this pulse capture; skipped, not fabricated.",
                })

        # Consume the staged file so it is not double-ingested next run.
        PULSE_FILE.rename(PULSE_FILE.with_suffix(
            f".consumed.{ingest_run_id}.json"))
        return records


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
