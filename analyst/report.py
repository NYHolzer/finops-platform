# analyst/report.py
from __future__ import annotations

from pathlib import Path

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


def render_report(ticker: str = DEFAULT_TICKER) -> Path | None:
    print(f"[analyst] Fetching data for {ticker}…")
    meta = latest_filing_meta(ticker)
    if not meta:
        body = f"""
          <h2>Analyst Module</h2>
          <p>Could not find SEC filings for <strong>{ticker.upper()}</strong>.</p>
        """
        # RETURN the path we wrote
        return render_page("analyst", f"Analyst Report · {ticker.upper()}", body)

    # Download & cache the primary document HTML
    print(f"[analyst] Downloading primary document…")
    local_path, html = download_latest_primary_document_html(meta)
    print(f"[analyst] Extracting sections…")
    sections = extract_section_texts(html)

    print(f"[analyst] Summarizing…")
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

      <h3 style="margin-top:1.25rem;">Key Metrics</h3>
      {metrics_html}

      <details style="margin-top:1rem;">
        <summary>Local cache</summary>
        <p>Saved primary document: <code>{local_path.as_posix()}</code></p>
      </details>
    """
# --- Key metric: Current Ratio (alias-aware) ---
  metrics_html = "<em>No balance-sheet data available.</em>"
  try:
      df_bs = load_balance_sheet(meta["cik"], freq="annual")
      if not df_bs.empty:
          cr_df = current_ratio(df_bs)
          # pick the latest period
          latest_period = cr_df.index.max()
          latest_cr = cr_df.loc[latest_period, "CurrentRatio"]
          if not pd.isna(latest_cr):
              # simple interpretation
              note = (
                  "Liquidity: ~1.0–2.0 is common; <1.0 can signal short-term stress; >2.0 may imply idle working capital."
              )
              metrics_html = f"""
              <table>
                <thead><tr><th>Metric</th><th>Latest</th><th>As of</th><th>What it tells us</th></tr></thead>
                <tbody>
                  <tr>
                    <td><strong>Current Ratio</strong></td>
                    <td>{latest_cr:.2f}</td>
                    <td>{pd.to_datetime(latest_period).date()}</td>
                    <td>{note}</td>
                  </tr>
                </tbody>
              </table>
              """
    except Exception:
      metrics_html = "<em>Metrics unavailable (failed to load balance-sheet data).</em>"

    # IMPORTANT: RETURN the path that render_page writes
    print(f"[analyst] Rendering HTML page…")
    return render_page("analyst", f"Analyst Report · {ticker.upper()}", body)
    print(f"[analyst] Report written successfully.")
