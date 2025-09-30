# analyst/edgar.py
"""
EDGAR (SEC) helper functions for fetching company filings.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional, TypedDict

import requests
from platform_core.config import SEC_USER_AGENT

# === Constants & config ===
SEC_BASE_URL = "https://data.sec.gov"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Per SEC fair-use policy, include a contact email.
SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL", "change-me@example.com")
SEC_USER_AGENT = f"FinOpsPlatform/0.1 (Contact: {SEC_CONTACT_EMAIL})"

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}


# === Types ===
class FilingMeta(TypedDict, total=False):
    ticker: str
    cik: str
    form: str
    filingDate: str
    reportDate: str
    accessionNumber: str
    primaryDocument: str
    filingDetailUrl: str


# === Helpers ===
def normalize_ticker_symbol(ticker: str) -> str:
    """Clean ticker string (remove symbols, uppercase)."""
    return re.sub(r"[^A-Za-z0-9]", "", ticker or "").upper()


def pad_cik_to_10_digits(cik: int | str) -> str:
    """Pad CIK to 10 digits (as SEC requires)."""
    return str(cik).zfill(10)


def build_company_submissions_url(padded_cik: str) -> str:
    """Return URL for the SEC company submissions JSON."""
    return f"{SEC_BASE_URL}/submissions/CIK{padded_cik}.json"


# === Main functions ===
def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """
    Look up the CIK for a ticker using SEC's official company_tickers.json.
    Returns 10-digit zero-padded CIK or None.
    """
    t = normalize_ticker_symbol(ticker)
    if not t:
        return None

    resp = requests.get(
        SEC_COMPANY_TICKERS_URL, headers=DEFAULT_REQUEST_HEADERS, timeout=30
    )
    resp.raise_for_status()
    data: Dict[str, Dict] = resp.json()
    for _, row in data.items():
        if row.get("ticker", "").upper() == t:
            return pad_cik_to_10_digits(row.get("cik_str"))
    return None


def latest_filing_meta(
    ticker: str, allowed_forms=("10-Q", "10-K")
) -> Optional[FilingMeta]:
    """
    Get metadata for the latest allowed filing (10-Q or 10-K) for a ticker.
    Returns FilingMeta dict or None.
    """
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return None

    resp = requests.get(
        build_company_submissions_url(cik), headers=DEFAULT_REQUEST_HEADERS, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    recent = data.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form in allowed_forms:
            acc_nodashes = accessions[i].replace("-", "")
            detail_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodashes}/index.html"
            return {
                "ticker": normalize_ticker_symbol(ticker),
                "cik": cik,
                "form": form,
                "filingDate": filing_dates[i] if i < len(filing_dates) else None,
                "reportDate": report_dates[i] if i < len(report_dates) else None,
                "accessionNumber": accessions[i],
                "primaryDocument": primary_docs[i] if i < len(primary_docs) else None,
                "filingDetailUrl": detail_url,
            }
    return None
