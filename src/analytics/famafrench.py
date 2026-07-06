"""Fama-French 5-factor daily data from the Ken French Data Library.

Fetched once and cached to data/reference/ff5_daily.parquet with a provenance
sidecar (source URL + fetch timestamp). Factors are in DECIMAL daily units
(the library ships percent; we divide by 100). RF is the daily risk-free rate
used for excess returns throughout the project.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .. import store

REF_DIR = store.REPO_ROOT / "data" / "reference"
FF5_PARQUET = REF_DIR / "ff5_daily.parquet"
FF5_PROV = REF_DIR / "ff5_daily.provenance.json"
FF5_URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
           "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip")


def _download() -> pd.DataFrame:
    from curl_cffi import requests as cffi
    r = cffi.Session(impersonate="chrome").get(FF5_URL, timeout=60)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    name = zf.namelist()[0]
    raw = zf.read(name).decode("latin-1")

    # The CSV has header cruft, then a daily block of  YYYYMMDD, Mkt-RF, SMB, HML,
    # RMW, CMA, RF. Keep only lines whose first token is an 8-digit date.
    rows = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 7 and parts[0].isdigit() and len(parts[0]) == 8:
            rows.append(parts)
    df = pd.DataFrame(rows, columns=["date", "Mkt_RF", "SMB", "HML", "RMW", "CMA", "RF"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").astype(float) / 100.0   # percent -> decimal
    return df


def load(force_refresh: bool = False) -> pd.DataFrame:
    if FF5_PARQUET.exists() and not force_refresh:
        return pd.read_parquet(FF5_PARQUET)
    REF_DIR.mkdir(parents=True, exist_ok=True)
    df = _download()
    df.to_parquet(FF5_PARQUET)
    FF5_PROV.write_text(json.dumps({
        "source": "Ken French Data Library (F-F_Research_Data_5_Factors_2x3_daily)",
        "url": FF5_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "units": "decimal daily (library percent / 100)",
        "n_rows": int(len(df)),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
    }, indent=2))
    return df


if __name__ == "__main__":
    d = load(force_refresh=True)
    print(d.tail())
    print("rows:", len(d), "range:", d.index.min().date(), "->", d.index.max().date())
