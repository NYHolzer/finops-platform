def build_module(module: str):
    """
    Import <module>.report.render_report() and run it.
    Expects each module to have report.py with render_report().
    """
    print(f"[publish] Building {module} module…")

    try:
        rep = importlib.import_module(f"{module}.report")
    except ModuleNotFoundError as e:
        sys.stderr.write(f"[publish] Could not import {module}.report: {e}\n")
        raise

    # --- Step 1: Run the report generator ---
    try:
        print(f"[{module}] Running render_report()…")
        rep.render_report()
    except Exception as e:
        sys.stderr.write(f"[{module}] Error while rendering: {e}\n")
        raise

    # --- Step 2: Copy generated docs ---
    src = Path(module) / "docs"
    dst = Path("docs") / module
    dst.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(f"[publish] No docs found at {src}, skipping copy.")
        return

    print(f"[publish] Copying files from {src} → {dst}")
    for p in src.glob("*"):
        target = dst / p.name
        target.write_bytes(p.read_bytes())
        print(f"  [copy] {p.name}")

    print(f"[publish] ✅ Published {module} → {dst}")
