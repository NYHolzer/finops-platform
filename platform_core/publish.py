# platform_core/publish.py
import importlib
import sys
from pathlib import Path


def build_module(module: str):
    """Import <module>.report.render_report() and run it.
    Expects each module to have report.py with render_report().
    """
    print(f"[publish] Building {module} module…", flush=True)

    try:
        print(f"[publish] Importing {module}.report …", flush=True)
        rep = importlib.import_module(f"{module}.report")
    except Exception as e:
        print(f"[publish] ERROR importing {module}.report: {e!r}", flush=True)
        raise

    # --- Step 1: Run the report generator ---
    try:
        print(f"[{module}] Running render_report() …", flush=True)
        rep.render_report()
    except Exception as e:
        print(f"[{module}] ERROR in render_report(): {e!r}", flush=True)
        raise

    # --- Step 2: Copy generated docs ---
    src = Path(module) / "docs"
    dst = Path("docs") / module
    print(f"[publish] Preparing to copy from {src} → {dst}", flush=True)
    dst.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(
            f"[publish] WARNING: source {src} does not exist; nothing to copy.",
            flush=True,
        )
    else:
        for p in src.glob("*"):
            target = dst / p.name
            target.write_bytes(p.read_bytes())
            print(f"[copy] {p.name}", flush=True)

    print(f"[publish] ✅ Done. Published {module} → {dst}", flush=True)


if __name__ == "__main__":
    print(f"[publish] argv: {sys.argv}", flush=True)
    if len(sys.argv) < 2:
        print("Usage: python -m platform_core.publish <module>", flush=True)
        sys.exit(1)
    build_module(sys.argv[1])
    print("[publish] EXIT OK", flush=True)
