# platform_core/publish.py
from pathlib import Path
import importlib
import sys

def build_module(module: str):
    """
    Import <module>.report.render_report() and run it.
    Expects each module to have report.py with render_report().
    """
    try:
        rep = importlib.import_module(f"{module}.report")
    except ModuleNotFoundError as e:
        sys.stderr.write(f"[publish] Could not import {module}.report: {e}\n")
        raise

    # Each module's report is responsible for writing <module>/docs/index.html
    rep.render_report()

    # Copy generated docs to root /docs/<module> for GitHub Pages
    src = Path(module) / "docs"
    dst = Path("docs") / module
    dst.mkdir(parents=True, exist_ok=True)
    if src.exists():
        for p in src.glob("*"):
            target = dst / p.name
            target.write_bytes(p.read_bytes())
    print(f"[publish] Published {module} → {dst}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python -m platform_core.publish <module>\n")
        sys.exit(1)
    build_module(sys.argv[1])