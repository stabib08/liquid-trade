"""Load and validate versioned basket thesis configs from baskets/*.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BASKETS_DIR = REPO_ROOT / "baskets"

_REQUIRED = [
    "id", "name", "thesis", "falsifiable_prediction", "kill_criterion",
    "constituents", "weighting_scheme", "primary_benchmark", "natural_comparator",
]


@dataclass(frozen=True)
class Basket:
    id: str
    name: str
    thesis: str
    falsifiable_prediction: str
    kill_criterion: str
    constituents: list[str]
    weighting_scheme: str
    primary_benchmark: str
    natural_comparator: str
    factor_tickers: list[str]
    positioning_symbols: list[str]
    speculative: bool
    version: str
    raw: dict

    def all_price_tickers(self) -> list[str]:
        """Everything we must fetch prices for: constituents + benchmark +
        comparator + factor ETFs, de-duplicated, order-stable."""
        seen, out = set(), []
        for t in (self.constituents + [self.primary_benchmark,
                  self.natural_comparator] + list(self.factor_tickers)):
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out


def _validate(data: dict, path: Path) -> None:
    missing = [k for k in _REQUIRED if k not in data or data[k] in (None, "")]
    if missing:
        raise ValueError(f"{path.name}: missing required fields {missing}")


def load_basket(path: Path) -> Basket:
    data = yaml.safe_load(path.read_text())
    _validate(data, path)
    return Basket(
        id=data["id"],
        name=data["name"],
        thesis=data["thesis"].strip(),
        falsifiable_prediction=data["falsifiable_prediction"].strip(),
        kill_criterion=data["kill_criterion"].strip(),
        constituents=list(data["constituents"]),
        weighting_scheme=data["weighting_scheme"],
        primary_benchmark=data["primary_benchmark"],
        natural_comparator=data["natural_comparator"],
        factor_tickers=list(data.get("factor_tickers", [])),
        positioning_symbols=list(data.get("positioning_symbols", [])),
        speculative=bool(data.get("speculative", False)),
        version=str(data.get("version", "")),
        raw=data,
    )


def load_all() -> list[Basket]:
    return [load_basket(p) for p in sorted(BASKETS_DIR.glob("*.yaml"))]


def positioning_symbol_map() -> dict[str, tuple[str, str]]:
    """Liquid symbol -> (mapped_ticker, basket_id) for every symbol a basket
    declares coverage for. Used to attribute captured positioning to a thesis."""
    out: dict[str, tuple[str, str]] = {}
    for b in load_all():
        for sym in b.positioning_symbols:
            out[sym.upper()] = (sym.upper(), b.id)
    return out
