# analyst/report.py
from __future__ import annotations

from pathlib import Path

from analyst.edgar import (
    download_latest_primary_document_html,
    extract_section_texts,
    latest_filing_meta,
)
from analyst.summarize import top_sentences_tfidf
from platform_core.report_template import render_page

DEFAULT_TICKER = "AAPL"


def render_report(ticker: str = DEFAULT_TICKER) -> Path | None:
    meta = latest_filing_meta(ticker)
    if not meta:
        body = f"""
          <h2>Analyst Module</h2>
          <p>Could not find SEC filings for <strong>{ticker.upper()}</strong>.</p>
        """
        # RETURN the path we wrote
        return render_page("analyst", f"Analyst Report · {ticker.upper()}", body)

    # Download & cache the primary document HTML
    local_path, html = download_latest_primary_document_html(meta)
    sections = extract_section_texts(html)

    mdna = sections.get("mdna", "")
    risk = sections.get("risk", "")

    mdna_top = top_sentences_tfidf(mdna, k=3)
    risk_top = top_sentences_tfidf(risk, k=3)

    def _fmt_list(items):
        if not items:
            return "<em>No highlights found.</em>"
        return "<ul>" + "".join(f"<li>{s}</li>" for s in items) + "</ul>"

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

      <details style="margin-top:1rem;">
        <summary>Local cache</summary>
        <p>Saved primary document: <code>{local_path.as_posix()}</code></p>
      </details>
    """
    # IMPORTANT: RETURN the path that render_page writes
    return render_page("analyst", f"Analyst Report · {ticker.upper()}", body)
