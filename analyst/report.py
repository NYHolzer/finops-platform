# analyst/report.py
from analyst.edgar import latest_filing_meta
from platform_core.report_template import render_page

DEFAULT_TICKER = "AAPL"  # you can change later or make configurable


def render_report(ticker: str = DEFAULT_TICKER):
    meta = latest_filing_meta(ticker) or {}
    if not meta:
        body = f"""
          <h2>Analyst Module</h2>
          <p>Could not find SEC filings for <strong>{ticker}</strong>.</p>
          <p>Try another ticker or check network/User-Agent settings.</p>
        """
    else:
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
          <hr>
          <p>Next steps (coming soon):</p>
          <ul>
            <li>Pull and cache the full filing text</li>
            <li>Extract MD&A / Risk Factors sections</li>
            <li>Summarize with AI and compute basic valuation stubs</li>
          </ul>
        """
    render_page(
        module_slug="analyst",
        page_title=f"Analyst Report · {ticker.upper()}",
        body_html=body,
        nav_modules=("analyst", "trader"),
    )


if __name__ == "__main__":
    render_report()
