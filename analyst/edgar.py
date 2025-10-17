"""
EDGAR (SEC) helper functions for fetching company filings.

Key improvements in this version:
- Resilient ticker→CIK resolution (accepts CIK directly, uses cache, live fetch, then a tiny builtin fallback).
- Correct request headers (no mismatched Host).
- Fixed data directory ('data/filings' not 'date/filings').
- Correct primary-document URL f-string.
- Fixed assignment typo when writing cache file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional, TypedDict

import requests
from bs4 import BeautifulSoup  # type: ignore

# === Constants & config ===
SEC_BASE_URL = "https://data.sec.gov"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Per SEC fair-use policy, include a contact email in the User-Agent.
SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL", "change-me@example.com")
SEC_USER_AGENT = f"FinOpsPlatform/0.2 (+{SEC_CONTACT_EMAIL})"

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept": "application/json, text/html",
    "Accept-Encoding": "gzip, deflate",
    # NOTE: Do NOT force a mismatched Host header; servers may reject.
}

# Directory for cached artifacts (filings, mappings, etc.)
DATA_DIR = Path("data") / "filings"
DATA_DIR.mkdir(parents=True, exist_ok=True)


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


# === Helpers: general ===
def normalize_ticker_symbol(ticker: str) -> str:
    """Clean ticker string (remove symbols, uppercase)."""
    return re.sub(r"[^A-Za-z0-9]", "", ticker or "").upper()


def pad_cik_to_10_digits(cik: int | str) -> str:
    """Pad CIK to 10 digits (as SEC requires)."""
    return str(cik).zfill(10)


def build_company_submissions_url(padded_cik: str) -> str:
    """Return URL for the SEC company submissions JSON."""
    return f"{SEC_BASE_URL}/submissions/CIK{padded_cik}.json"


# === Helpers: ticker→CIK (resilient) ===
_BUILTIN_CIK_FALLBACK: Dict[str, str] = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",  # Alphabet Inc. Class A
    "TSLA": "0001318605",
}
_CIK_RE = re.compile(r"^\d{1,10}$")


def _cache_path() -> Path:
    p = Path("data") / "company_tickers.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_cached_mapping() -> Optional[Dict[str, str]]:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        import json

        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        # normalize keys and zero-pad
        return {k.upper(): str(v).zfill(10) for k, v in data.items()}
    except Exception:
        return None


def _save_cached_mapping(mapping: Dict[str, str]) -> None:
    import json

    _cache_path().write_text(json.dumps(mapping), encoding="utf-8")


def _fetch_sec_ticker_mapping() -> Dict[str, str]:
    """
    Fetch {TICKER -> zero-padded CIK} from SEC helper file.
    Shape of payload: {"0": {"ticker": "...", "cik_str": 123, ...}, ...}
    """
    resp = requests.get(
        SEC_COMPANY_TICKERS_URL, headers=DEFAULT_REQUEST_HEADERS, timeout=30
    )
    resp.raise_for_status()
    payload = resp.json()
    out: Dict[str, str] = {}
    for _, rec in payload.items():
        t = str(rec["ticker"]).upper()
        cik = pad_cik_to_10_digits(rec["cik_str"])
        out[t] = cik
    return out


def ticker_to_cik(symbol_or_cik: str) -> str:
    """
    Accept either a stock ticker (e.g., 'AAPL') or a numeric CIK.
    Resolution order:
      1) If a CIK (digits) was provided, normalize & return.
      2) Local cache at data/company_tickers.json (if present).
      3) Live SEC helper fetch (and write cache).
      4) Built-in fallback for a few common tickers (AAPL, MSFT, etc.).
    Raises ValueError if resolution fails.
    """
    s = (symbol_or_cik or "").strip()
    if _CIK_RE.match(s):
        return pad_cik_to_10_digits(s)

    t = normalize_ticker_symbol(s)

    cached = _load_cached_mapping()
    if cached and t in cached:
        return cached[t]

    try:
        fresh = _fetch_sec_ticker_mapping()
        _save_cached_mapping(fresh)
        if t in fresh:
            return fresh[t]
    except Exception:
        # Network errors, 404/403, etc. -> fall through to builtin
        pass

    if t in _BUILTIN_CIK_FALLBACK:
        return _BUILTIN_CIK_FALLBACK[t]

    raise ValueError(
        f"Could not resolve '{symbol_or_cik}' to a CIK. "
        f"Try passing a CIK directly (digits only) or check access to {SEC_COMPANY_TICKERS_URL}."
    )


# === Main functions ===
def latest_filing_meta(
    ticker_or_cik: str, allowed_forms=("10-Q", "10-K")
) -> Optional[FilingMeta]:
    """
    Get metadata for the latest allowed filing (10-Q or 10-K).
    Accepts either a ticker (e.g., 'AAPL') or a CIK (digits).
    Returns FilingMeta dict or None if not found.
    """
    cik = ticker_to_cik(ticker_or_cik)

    resp = requests.get(
        build_company_submissions_url(cik), headers=DEFAULT_REQUEST_HEADERS, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    recent = data.get("filings", {}).get("recent", {})

    forms = recent.get("form", []) or []
    filing_dates = recent.get("filingDate", []) or []
    report_dates = recent.get("reportDate", []) or []
    accessions = recent.get("accessionNumber", []) or []
    primary_docs = recent.get("primaryDocument", []) or []

    for i, form in enumerate(forms):
        if form in allowed_forms:
            acc = accessions[i]
            acc_nodashes = acc.replace("-", "")
            detail_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodashes}/index.html"
            return {
                "ticker": normalize_ticker_symbol(ticker_or_cik),
                "cik": cik,
                "form": form,
                "filingDate": filing_dates[i] if i < len(filing_dates) else None,
                "reportDate": report_dates[i] if i < len(report_dates) else None,
                "accessionNumber": acc,
                "primaryDocument": primary_docs[i] if i < len(primary_docs) else None,
                "filingDetailUrl": detail_url,
            }
    return None


def build_primary_document_url(
    cik_padded: str, accession_number: str, primary_document: str
) -> str:
    """
    Primary document lives under:
    https://www.sec.gov/Archives/edgar/data/{CIK_no_leading_zeroes}/{acc_no_dashes}/{primary_doc}
    """
    acc_nodashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik_padded)}/{acc_nodashes}/{primary_document}"


def download_latest_primary_document_html(meta: FilingMeta) -> tuple[Path, str]:
    """
    Download and cache the latest filing's primary HTML document.
    Returns: (local_path, html_text)
    """
    cik = meta.get("cik")
    accession = meta.get("accessionNumber")
    primary = meta.get("primaryDocument")
    if not (cik and accession and primary):
        raise ValueError(
            "Missing keys to download primary document: need cik, accessionNumber, primaryDocument."
        )

    url = build_primary_document_url(cik, accession, primary)
    fname = f"{meta.get('ticker', 'unknown')}_{meta.get('form','')}_{accession.replace('-', '')}_{primary}".lower()
    local_path = DATA_DIR / fname

    if local_path.exists():
        html = local_path.read_text(encoding="utf-8", errors="ignore")
        return local_path, html

    resp = requests.get(url, headers=DEFAULT_REQUEST_HEADERS, timeout=60)
    resp.raise_for_status()
    html = resp.text
    local_path.write_text(html, encoding="utf-8", errors="ignore")
    return local_path, html


# --- Simple section extractors ---
def extract_section_texts(html: str) -> dict[str, str]:
    """
    Heuristics to isolate key sections by scanning headings that contain:
    - 'Item 7' (MD&A)
    - 'Item 1A' (Risk Factors)

    Returns a dict with 'mdna', 'risk' keys (empty strings if not found).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Collect all headings (h1..h6)
    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        candidates.append((tag, text.upper()))

    mdna_start = None
    risk_start = None
    for tag, up in candidates:
        if "ITEM 7" in up and "MANAGEMENT" in up:
            mdna_start = tag if mdna_start is None else mdna_start
        if "ITEM 1A" in up and "RISK" in up:
            risk_start = tag if risk_start is None else risk_start

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
        return " ".join(" ".join(parts).split())

    return {
        "mdna": _collect_until_next_heading(mdna_start),
        "risk": _collect_until_next_heading(risk_start),
    }
