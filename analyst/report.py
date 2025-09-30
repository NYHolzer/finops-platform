from platform_core.report_template import render_page

def render_report():
    body = """
      <h2>Analyst Module</h2>
      <p>Status: OK — placeholder report</p>
      <div class="kpi">
        <div><strong>Ticker:</strong> AAPL</div>
        <div><strong>Next:</strong> Fetch 10-K/10-Q</div>
        <div><strong>Then:</strong> Summarize risks/opportunities</div>
      </div>
      <p>We will replace this with real SEC filing content soon.</p>
    """
    render_page(module_slug="analyst", page_title="Analyst Report", body_html=body)

if __name__ == "__main__":
    render_report()