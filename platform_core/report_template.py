# platform_core/template.py
from pathlib import Path
from datetime import datetime
from typing import Iterable

def render_page(
    module_slug: str,
    page_title: str,
    body_html: str,
    nav_modules: Iterable[str] = ("analyst", "trader"),
) -> None:
    """
    Writes a complete HTML page to <module>/docs/index.html.
    Each module supplies only its unique `body_html`.
    """
    out_dir = Path(module_slug) / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    nav_links = " | ".join(
        f'<a href="../{m}/">{m.capitalize()}</a>' for m in nav_modules
    )
    nav = f'<nav style="margin-bottom:1rem;"><a href="../">Home</a> | {nav_links}</nav>'

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{page_title} · FinOps Platform</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{ --bg:#fff; --fg:#111; --muted:#666; --border:#eee; --link:#0b5bd3; }}
    * {{ box-sizing: border-box; }}
    body {{ background:var(--bg); color:var(--fg); font-family: system-ui, Arial, sans-serif; margin: 2rem; line-height:1.5; }}
    header, footer {{ color:var(--muted); }}
    a {{ color:var(--link); text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .card {{ border:1px solid var(--border); border-radius:12px; padding:1rem; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
    table {{ border-collapse: collapse; width:100%; }}
    td, th {{ border: 1px solid var(--border); padding: .6rem .8rem; text-align:left; }}
    .kpi {{ display:flex; gap:1rem; flex-wrap:wrap; }}
    .kpi > div {{ border:1px solid var(--border); border-radius:10px; padding:.6rem .8rem; min-width: 160px; }}
  </style>
</head>
<body>
  <header>
    <h1>FinOps Platform</h1>
    {nav}
  </header>

  <main class="card">
    {body_html}
  </main>

  <footer>
    <p style="margin-top:1rem;">Last updated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
  </footer>
</body>
</html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
