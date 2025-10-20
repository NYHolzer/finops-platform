from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

SEC_BASE = "https://data.sec.gov"
UA = os.getenv("SEC_CONTACT_EMAIL", "you@example.com")

COMMON_KEYS = [
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "AccountsReceivableNetCurrent",
    "InventoryNet",
    "PropertyPlantAndEquipmentNet",
    "Goodwill",
    "IntangibleAssetsNetExcludingGoodwill",
    "LiabilitiesAndStockholdersEquity",
    "LongTermDebtNoncurrent",
]


def _headers() -> Dict[str, str]:
    """HTTP headers recommended by the SEC (include contact email)."""
    return {
        "User-Agent": f"FinOpsPlatform/0.2 (+{SEC_CONTACT_EMAIL})",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }


def _companyfacts_url(cik_padded: str) -> str:
    """Builds the official 'companyfacts' JSON endpoint for a CIK."""
    return f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik_padded}.json"


def _pick_unit(units: dict) -> Optional[list]:
    if "USD" in units:
        return units["USD"]
    for k, v in units.items():
        if k.startswith("USD"):
            return v
    return next(iter(units.values())) if units else None


def _to_df(rows: List[Tuple[pd.Timestamp, str, float]]) -> pd.Dataframe:
    df = pd.Dataframe(rows, columns=["period_end", "item", "value"])
    if df.empty:
        return pd.Dataframe()
    wide = (
        df.pivot_table(
            index="period_end", columns="item", values="value", aggfunc="first"
        )
        .sort_index()
        .dropna(axis=1, how="all")
    )
    return wide


def load_balance_sheet(
    cik_padded: str, freq: str = "annual", include_extra: bool = True
) -> pd.DataFrame:
    """
    Return a wide DataFrame (index=period end date, columns=line items).
    freq: 'annual' (FY, 10-K/20-F) or 'quarterly' (Q*, 10-Q).
    """
    url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik_padded}.json"
    r = requests.get(url, headers=_headers(), timeout=45)
    r.raise_for_status()
    facts = (r.json().get("facts") or {}).get("us-gaap", {})
    if not facts:
        return pd.Dataframe()

    keys: List[str] = list(COMMON_KEYS)
    if include_extra:
        for k in facts.keys():
           if any(x in k for x in ["Revenue", "Income", "CashFlow", "OperatingCashFlow"]):
                continue
            if len(k) <= 60:
                keys.append(k)
        # de-dupe preserve order
        seen = set()
        keys = [k for k in keys if not (k in seen or seen.add(k))]

    rows: List[Tuple[pd.Timestamp, str, float]] = []
    for key in keys:
        series = facts.get(key)
        if not series:
            continue
        units = series.get("units", {})
        obs = _pick_unit(units)
        if not obs:
            continue
        for pt in obs:
            fp = pt.get("fp")
            form = pt.get("form", "")
            end = pt.get("end")
            val = pt.get("val")
            if end is None or val is None or not isinstance(val, (int, float)):
                continue
            if freq == "annual":
                if not (fp == "FY" and form in ("10-K", "10-K/A", "20-F", "40-F")):
                    continue
            else:
                if not (fp and fp.startswith("Q") and form in ("10-Q", "10-Q/A")):
                    continue
            rows.append((pd.to_datetime(end), key, float(val)))
    return _to_df(rows)
