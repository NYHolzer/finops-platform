import pandas as pd
from analyst import financials as fin


class FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            from requests import HTTPError

            raise HTTPError(self.status_code)

    def json(self):
        return self._payload


def test_pick_unit_prefers_usd():
    units = {"USD": [{"val": 1}], "USD/share": [{"val": 2}]}
    chosen = fin._pick_unit(units)
    assert chosen == [{"val": 1}]


def test_load_balance_sheet_with_mock(monkeypatch):
    # Minimal fake SEC payload: one annual Assets and Liabilities point
    payload = {
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2024-12-31",
                                "val": 123.0,
                            }
                        ]
                    }
                },
                "Liabilities": {
                    "units": {
                        "USD": [
                            {
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2024-12-31",
                                "val": 45.0,
                            }
                        ]
                    }
                },
            }
        }
    }

    # Monkeypatch requests.get used INSIDE analyst.financials to avoid the network
    import requests

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, headers=None, timeout=0: FakeResp(payload, 200),
    )

    df = fin.load_balance_sheet("0000320193", freq="annual")  # AAPL CIK as example
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Assets" in df.columns and "Liabilities" in df.columns
    assert pd.Timestamp("2024-12-31") in df.index
    assert df.loc[pd.Timestamp("2024-12-31"), "Assets"] == 123.0
    assert df.loc[pd.Timestamp("2024-12-31"), "Liabilities"] == 45.0
