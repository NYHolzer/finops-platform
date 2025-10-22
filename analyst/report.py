# analyst/report.py
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from analyst.edgar import (
    download_latest_primary_document_html,
    extract_section_texts,
    latest_filing_meta,
)
from analyst.financials import load_balance_sheet
from analyst.metrics import current_ratio
from analyst.summarize import top_sentences_tfidf
from platform_core.report_template import render_page

DEFAULT_TICKER = "AAPL"

import re


def _prep_for_summary(text: str) -> str:
    """Remove section headers/TOC noise so TF-IDF picks real sentences."""
    if not text:
        return ""
    t = text

    # Drop lines that are just 'ITEM 2.' / 'ITEM 7.' / 'ITEM 1A.' headings
    t = re.sub(r"(?im)^\s*ITEM\s+\d+[A]?\.\s*.*$", "", t)

    # Normalize whitespace and split to lines
    lines = [ln.strip() for ln in re.sub(r"[ \t\r\f\v]+", " ", t).splitlines()]

    keep: list[str] = []
    for ln in lines:
        if not ln:
            continue
        # Drop single numbers/page refs or bullets like "13", "(13)"
        if re.fullmatch(r"\(?\d+\)?", ln):
            continue
        # Drop very short “title-y” lines (likely TOC/headers)
        if len(ln.split()) < 6:
            continue
        # Drop obvious section titles
        if re.match(r"(?i)^(risk factors|management.*analysis)$", ln):
            continue
        # Drop lines that start with "Item" again (safety)
        if re.match(r"(?i)^item\s+\d", ln):
            continue
        keep.append(ln)

    return " ".join(keep)


def render_report(ticker: str = DEFAULT_TICKER) -> Path | None:
    print(f"[analyst] Fetching data for {ticker}…")
    meta = latest_filing_meta(
        ticker, allowed_forms=("10-K", "10-K/A", "20-F", "40-F")  # annual
    )
    if not meta:
        meta = latest_filing_meta(
            ticker, allowed_forms=("10-Q", "10-Q/A")  # quarterly filings
        )
    # --- If still nothing, render a friendly "no data" page ---
    if not meta:
        body = f"""
          <h2>Analyst Module</h2>
          <p>Could not find SEC filings for <strong>{ticker.upper()}</strong>.</p>
          <p>Please check if the ticker is correct or if the company files outside EDGAR.</p>
        """
        # RETURN the path we wrote
        return render_page("analyst", f"Analyst Report · {ticker.upper()}", body)

    # Download & cache the primary document HTML
    print(f"[analyst] Downloading primary document…")
    local_path, html = download_latest_primary_document_html(meta)
    parsed_file = local_path.name
    print(f"[analyst] Extracting sections…")
    sections = extract_section_texts(html)

    print(f"[analyst] Summarizing…")
    mdna = (sections.get("mdna", "") or "").strip()
    risk = (sections.get("risk", "") or "").strip()

    mdna_clean = _prep_for_summary(mdna)
    risk_clean = _prep_for_summary(risk)

    print(f"[debug] MDNA length: {len(mdna_clean.split())} words")
    print(f"[debug] Risk length: {len(risk_clean.split())} words")

    mdna_top = (
        top_sentences_tfidf(mdna_clean, k=3) if len(mdna_clean.split()) >= 30 else []
    )
    risk_top = (
        top_sentences_tfidf(risk_clean, k=3) if len(risk_clean.split()) >= 30 else []
    )

    def _fmt_list(items):
        if not items:
            return "<em>No highlights found.</em>"
        return "<ul>" + "".join(f"<li>{s}</li>" for s in items) + "</ul>"

    # --- Key metric: Current Ratio (alias-aware) ---
    metrics_html = "<em>No balance-sheet data available.</em>"
    try:
        df_bs = load_balance_sheet(meta["cik"], freq="annual")
        if not df_bs.empty:
            cr_df = current_ratio(df_bs)
            latest_period = cr_df.index.max()
            latest_cr = cr_df.loc[latest_period, "CurrentRatio"]

            if not pd.isna(latest_cr):
                note = (
                    "Liquidity: ~1.0–2.0 is common; <1.0 can signal short-term stress; "
                    ">2.0 may imply idle working capital."
                )
                metrics_html = f"""
                <table>
                  <thead><tr><th>Metric</th><th>Latest</th><th>As of</th><th>What it tells us</th></tr></thead>
                  <tbody>
                    <tr>
                      <td><strong>Current Ratio</strong></td>
                      <td>{float(latest_cr):.2f}</td>
                      <td>{pd.to_datetime(latest_period).date()}</td>
                      <td>{note}</td>
                    </tr>
                  </tbody>
                </table>
                """
    except Exception:
        metrics_html = (
            "<em>Metrics unavailable (failed to load balance-sheet data).</em>"
        )

    body = f"""
      <h2>Analyst · {meta['ticker']}</h2>
      <div class="kpi">
        <div><strong>Form:</strong> {meta.get('form','')}</div>
        <div><strong>Filing Date:</strong> {meta.get('filingDate','')}</div>
        <div><strong>Report Date:</strong> {meta.get('reportDate','')}</div>
        <div><strong>Accession:</strong> {meta.get('accessionNumber','')}</div>
      </div>
      <p style="margin-top:1rem;">
        <a href="{meta.get('filingDetailUrl','')}" target="_blank" rel="noopener">View filing on SEC</a>
      </p>

      <h3 style="margin-top:1.25rem;">MD&amp;A — Highlights</h3>
      {_fmt_list(mdna_top)}

      <h3 style="margin-top:1.25rem;">Risk Factors — Highlights</h3>
      {_fmt_list(risk_top)}

      <h3 style="margin-top:1.25rem;">Key Metrics</h3>
      {metrics_html}

      <details style="margin-top:1rem;">
        <summary>Local cache</summary>
        <p>Saved primary document: <code>{local_path.as_posix()}</code></p>
      </details>
      <p style="margin-top:0.5rem;color:#666;">
        Parsed: <code>{parsed_file}</code>
      </p>
    """

    # IMPORTANT: RETURN the path that render_page writes
    print(f"[analyst] Rendering HTML page…")
    return render_page("analyst", f"Analyst Report · {ticker.upper()}", body)
    print(f"[analyst] Report written successfully.")
