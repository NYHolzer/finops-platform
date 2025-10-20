"""
Metrics computed from the wide balance-sheet Dataframe produced by load_balance_sheet().

We start small with a single, easy to audit metric:
- CurrentRatio = AssetsCurrent / LiabilitiesCurrent

Return shape: Dataframe indexed by period_end with a single column 'CurrentRatio'.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

# --- Catalog scaffold (so we can group & explain later) ---
METRIC_CATEGORIES = {
    "profitability": "How efficiently the business generates profits.",
    "liquidity": "Ability to meet short-term obligations.",
    "leverage": "How much debt/financial risk the firm takes on.",
    "efficiency": "How well resources are used (turnover, cycles).",
    "cashflow_quality": "Earnings vs. cash conversion and sustainability.",
}

METRICS_CATALOG: Dict[str, Dict[str, str]] = {
    "ROE": {
        "category": "profitability",
        "label": "Return on Equity (ROE)",
        "formula": "NetIncome / Stockholders' Equity",
        "what_it_tells_us": "How effectively equity capital is turned into profit.",
    }
}

NET_INCOME_ALIASES = [
    "NetIncomeLoss",  # US-GAAP, very common
    "ProfitLoss",  # IFRS/common alternative
    "NetIncomeLossAvailableToCommonStockholdersBasic",  # sometimes used
]

# Equity (with/without noncontrolling interest; US-GAAP & variants):
EQUITY_ALIASES = [
    "StockholdersEquity",  # US-GAAP canonical
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "PartnersCapital",  # partnerships/LLC
    "MemberEquity",  # alt naming
    "Equity",  # some IFRS filers
]
# Current assets / liabilities aliases (US-GAAP + common variants)
ASSETS_CURRENT_ALIASES = [
    "AssetsCurrent",
    "CurrentAssets",
]

LIABILITIES_CURRENT_ALIASES = [
    "LiabilitiesCurrent",
    "CurrentLiabilities",
]


def current_ratio(bs: pd.DataFrame) -> pd.DataFrame:
    """
    Current Ratio = Current Assets / Current Liabilities
    Alias-aware to handle XBRL naming differences.
    """
    a_cur = _first_available(bs, ASSETS_CURRENT_ALIASES)
    l_cur = _first_available(bs, LIABILITIES_CURRENT_ALIASES)
    cr = a_cur / l_cur
    return pd.DataFrame({"CurrentRatio": cr}, index=bs.index).sort_index()


def _first_available(df: pd.DataFrame, names: list[str]) -> pd.Series:
    """
    Return the first Series present in df matching any of `names`.
    If none exist, return a NaN Series aligned to df.index.
    """
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series(index=df.index, dtype="float64")


def return_on_equity(df: pd.DataFrame) -> pd.DataFrame:
    """
    ROE = NetIncome / Equity (gracefully handles naming differences via aliases).
    """
    ni = _first_available(df, NET_INCOME_ALIASES)
    eq = _first_available(df, EQUITY_ALIASES)
    roe = ni / eq
    return pd.DataFrame({"ROE": roe}, index=df.index).sort_index()


def explain_roe(latest_value: float) -> str:
    """
    Return a short, investor-friendly interpretation string for a single ROE value.
    Bands are rough, industry-dependent (good enough for defaults; we can refine later).
    """
    if pd.isna(latest_value):
        return (
            "ROE is unavailable for the latest period (missing Net Income or Equity)."
        )
    if latest_value < 0:
        return (
            "Negative ROE: losses relative to equity — profitability is currently weak."
        )
    pct = latest_value * 100.0
    if pct < 5:
        return f"ROE ≈ {pct:.1f}%: low capital efficiency; below typical hurdle rates."
    if pct < 15:
        return f"ROE ≈ {pct:.1f}%: mid-range; generally acceptable, compare vs. peers."
    return f"ROE ≈ {pct:.1f}%: strong capital efficiency; a positive quality signal (industry-dependent)."
