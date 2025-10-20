import pandas as pd
from analyst.metrics import return_on_equity


def test_roe_uses_profitloss_alias_when_netincome_missing():
    idx = pd.to_datetime(["2024-12-31"])
    df = pd.DataFrame(
        {
            # No 'NetIncomeLoss' provided on purpose:
            "ProfitLoss": [25.0],
            "StockholdersEquity": [100.0],
        },
        index=idx,
    )
    mx = return_on_equity(df)
    assert abs(mx.loc[idx[0], "ROE"] - 0.25) < 1e-12


def test_roe_uses_equity_including_nci_when_canonical_missing():
    idx = pd.to_datetime(["2024-12-31"])
    df = pd.DataFrame(
        {
            "NetIncomeLoss": [15.0],
            # No 'StockholdersEquity' on purpose:
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": [
                120.0
            ],
        },
        index=idx,
    )
    mx = return_on_equity(df)
    assert abs(mx.loc[idx[0], "ROE"] - (15.0 / 120.0)) < 1e-12
