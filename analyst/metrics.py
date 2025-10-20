"""
Metrics computed from the wide balance-sheet Dataframe produced by load_balance_sheet().

We start small with a single, easy to audit metric:
- CurrentRatio = AssetsCurrent / LiabilitiesCurrent

Return shape: Dataframe indexed by period_end with a single column 'CurrentRatio'.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd


def current_ratio(bs: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Current Ratio = AssetsCurrent / LiabilitiesCurrent.

    Parameters
    -----------
    bs : pd.Dataframe
        Wide balance-sheet table (index = period_end, columns include 'AssetsCurrent' and 'LiabilitiesCurrent' if the company reported them).

    Returns
    -----------
        pd.DataFrame
        Index: same as bs (period_end)
        Columns: ['CurrentRatio']
        Values: float (NaN where inputs are missing)
    """
    # Gracefully handle missing columns: .get returns a Series of Nan if column absent
    a_cur = (
        bs["AssetsCurrent"]
        if "AssetsCurrent" in bs.columns
        else pd.Series(index=bs.index, dtype="float64")
    )
    l_cur = (
        bs["LiabilitiesCurrent"]
        if "LiabilitiesCurrent" in bs.columns
        else pd.Series(index=bs.index, dtype="float64")
    )

    cr = a_cur / l_cur

    out = pd.DataFrame({"CurrentRatio": cr}, index=bs.index).sort_index()
    return out


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


def return_on_equity(df: pd.DataFrame) -> pd.DataFrame:
    """
    ROE = NetIncome / Stockholders' Equity
    Uses the wide DataFrame (index: period_end). Gracefully returns NaN if inputs missing.

    We look for common income keys:
      - 'NetIncomeLoss' (preferred, US-GAAP)
      - 'ProfitLoss' (fallback some filers use)
    Equity: 'StockholdersEquity'
    """
    ni = None
    for cand in ("NetIncomeLoss", "ProfitLoss"):
        if cand in df.columns:
            ni = df[cand]
            break
    if ni is None:
        ni = pd.Series(index=df.index, dtype="float64")

    equity = (
        df["StockholdersEquity"]
        if "StockholdersEquity" in df.columns
        else pd.Series(index=df.index, dtype="float64")
    )

    roe = ni / equity
    out = pd.DataFrame({"ROE": roe}, index=df.index).sort_index()
    return out


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
