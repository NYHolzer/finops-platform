import pandas as pd
from analyst.metrics import explain_roe, return_on_equity


def test_roe_computation_simple():
    idx = pd.to_datetime(["2024-12-31", "2023-12-31"])
    df = pd.DataFrame(
        {
            "NetIncomeLoss": [20.0, 10.0],
            "StockholdersEquity": [100.0, 80.0],
        },
        index=idx,
    )
    mx = return_on_equity(df)
    assert list(mx.columns) == ["ROE"]
    # 2024: 20/100 = 0.20
    assert abs(mx.loc[idx[0], "ROE"] - 0.20) < 1e-12
    # 2023: 10/80 = 0.125
    assert abs(mx.loc[idx[1], "ROE"] - 0.125) < 1e-12


def test_roe_handles_missing_inputs():
    idx = pd.to_datetime(["2024-12-31"])
    df_missing = pd.DataFrame({"StockholdersEquity": [0.0]}, index=idx)
    mx = return_on_equity(df_missing)
    assert pd.isna(mx.loc[idx[0], "ROE"])  # no NetIncomeLoss/ProfitLoss


def test_explain_roe_bands():
    assert "Negative" in explain_roe(-0.01)
    assert "low" in explain_roe(0.02)
    mid = explain_roe(0.10)
    assert "mid-range" in mid or "acceptable" in mid
    assert "strong" in explain_roe(0.20)
    assert "unavailable" in explain_roe(float("nan"))
