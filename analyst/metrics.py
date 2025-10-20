"""
Metrics computed from the wide balance-sheet Dataframe produced by load_balance_sheet().

We start small with a single, easy to audit metric:
- CurrentRatio = AssetsCurrent / LiabilitiesCurrent

Return shape: Dataframe indexed by period_end with a single column 'CurrentRatio'.
"""

from __future__ import annotations

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
