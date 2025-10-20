import pandas as pd
from analyst.metrics import current_ratio


def test_current_ratio_uses_aliases_when_canonical_missing():
    idx = pd.to_datetime(["2024-12-31"])
    # Use alias names, not the canonical ones
    bs = pd.DataFrame(
        {
            "CurrentAssets": [450.0],
            "CurrentLiabilities": [225.0],
        },
        index=idx,
    )
    mx = current_ratio(bs)
    assert list(mx.columns) == ["CurrentRatio"]
    assert abs(mx.loc[idx[0], "CurrentRatio"] - 2.0) < 1e-12  # 450/225


def test_current_ratio_nan_when_inputs_missing():
    idx = pd.to_datetime(["2024-12-31"])
    bs = pd.DataFrame({"CurrentAssets": [100.0]}, index=idx)  # missing liabilities
    mx = current_ratio(bs)
    assert pd.isna(mx.loc[idx[0], "CurrentRatio"])
