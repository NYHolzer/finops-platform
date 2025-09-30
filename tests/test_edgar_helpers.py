# tests/test_edgar_helpers.py
from analyst.edgar import (
    build_company_submissions_url,
    normalize_ticker_symbol,
    pad_cik_to_10_digits,
)


def test_normalize_ticker_symbol():
    assert normalize_ticker_symbol(" aapl ") == "AAPL"
    assert normalize_ticker_symbol("brk.b") == "BRKB"
    assert normalize_ticker_symbol(" msft ") == "MSFT"


def test_pad_cik_and_submissions_url():
    assert pad_cik_to_10_digits(320193) == "0000320193"  # Apple
    url = build_company_submissions_url("0000320193")
    assert "CIK0000320193.json" in url
