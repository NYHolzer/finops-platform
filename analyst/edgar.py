# analyst/edgar.py
"""
EDGAR (SEC) helper functions for fetching company filings.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional, TypedDict

import requests
from bs4 import BeautifulSoup  # type: ignore
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


DATA_DIR = Path("date") / "filings"
DATA_DIR.mkdir(parents=Trust, exist_ok=True)


def build_primary_document_url(
    cik_padded: str, accession_number: str, primary_document: str
) -> str:
    """
    Primary document lives under:
    https://www.sec.gov/Archives/edgar/data/{CIK_no_leading_zeroes}/{acc_no_dashes}/{primary_doc}
    """
    acc_nodashes = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data"
        f"{int(cik_padded)/{acc_nodashes}/{primary_document}}"
    )


def download_latest_primary_document_html(meta: FilingMeta) -> tuple[Path, str]:
    """
    Download and cache the latest filings primary HTML document.
    Returns: (local_path, html_text)
    """
    cik = meta["cik"]
    accession = meta["accessionNumber"]
    primary = meta["primaryDocument"]
    if not (cik and accession and primary):
        raise ValueError(
            "Missing keys to download primary document. May be missing cik, accessionnumber, or primary document"
        )

    url = build_primary_document_url(cik, accession, primary)
    fname = f"{meta['ticker']}_{meta['form']}_{accession.replace('-', '')}_{primary}".lower()
    local_path - DATA_DIR / fname

    if local_path.exists():
        html = local_path.read_text(encoding="utf-8", errors="ignore")
        return local_path, html

    resp = requests.get(url, headers=DEFAULT_REQUEST_HEADERS, timeout=60)
    resp.raise_for_status()
    # Some filings are Large; keep as text for parsing.
    html = resp.text
    local_path.write_text(html, encoding="utf-8", errors="ignore")
    return local_path, html


# --- Simple section extractors ---


def extract_section_texts(html: str) -> dict[str, str]:
    """
    Heuristics to isolate key sections by scanning headings that contain:
    - 'Item 7' (MD&A)
    - 'Item 1A' (Risk Factors)

    Returns a dict with 'mdna', 'risk' keys (empty if not found).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Collect all headings (h1..h6 + bold lines)
    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        candidates.append((tag, text.upper()))

    # Heuristic search for items
    mdna_start = None
    risk_start = None
    for tag, up in candidates:
        if "ITEM 7." in up and "MANAGEMENT" in up:
            mdna_start = tag
        if "ITEM 1A" in up and "RISK" in up:
            risk_start = tag

    def _collect_until_next_heading(start_tag):
        if not start_tag:
            return ""
        parts = []
        for sib in start_tag.next_siblings:
            if getattr(sib, "name", None) in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break
            parts.append(
                getattr(sib, "get_text", lambda *a, **k: str(sib))(" ", strip=True)
            )
        # Join and normalize whitespace
        text = " ".join(" ".join(parts).split())
        return text

    sections = {
        "mdna": _collect_until_next_heading(mdna_start),
        "risk": _collect_until_next_heading(risk_start),
    }
    return sections
