import shutil
import tempfile
from pathlib import Path

from platform_core.report_template import render_page


def test_render_page_creates_file_and_content():
    tmpdir = Path(tempfile.mkdtemp())
    module_name = "testmodule"
    try:
        render_page(
            module_slug=module_name,
            page_title="Test Report",
            body_html="<p>Hello World</p>",
            nav_modules=["analyst", "trader"],
            base_path=tmpdir,  # <-- direct output into temp dir
        )
        out_file = tmpdir / module_name / "docs" / "index.html"
        assert out_file.exists(), "Expected index.html to be created"
        html = out_file.read_text(encoding="utf-8")
        assert "Hello World" in html
        assert "Test Report" in html
        assert "Analyst" in html or "Trader" in html
    finally:
        shutil.rmtree(tmpdir)
