from platform_core.report_template import render_page

def render_report():
    body = """
      <h2>Trader Module</h2>
      <p>Status: OK — placeholder report</p>
      <ul>
        <li>Next: pull prices (yfinance)</li>
        <li>Plot 6M chart</li>
        <li>Add basic strategy stats</li>
      </ul>
    """
    render_page(module_slug="trader", page_title="Trader Report", body_html=body)

if __name__ == "__main__":
    render_report()