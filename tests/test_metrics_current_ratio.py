# tests/test_metrics_current_ratio.py
import pandas as pd
from analyst.metrics import current_ratio


def test_current_ratio_simple():
    idx = pd.to_datetime(["2024-12-31"])
    bs = pd.DataFrame(
        {
            "AssetsCurrent": [400.0],
            "LiabilitiesCurrent": [200.0],
        },
        index=idx,
    )
    mx = current_ratio(bs)
    assert list(mx.columns) == ["CurrentRatio"]
    assert mx.loc[idx[0], "CurrentRatio"] == 2.0  # 400 / 200


def test_current_ratio_handles_missing_columns():
    idx = pd.to_datetime(["2024-12-31"])
    # Missing LiabilitiesCurrent -> expect NaN
    bs = pd.DataFrame({"AssetsCurrent": [100.0]}, index=idx)
    mx = current_ratio(bs)
    assert pd.isna(mx.loc[idx[0], "CurrentRatio"])
