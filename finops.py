#!/usr/bin/env python3
"""
FinOps Platform — Unified Entry-Point (v0.2.1)

Goal
----
Provide a single, friendly CLI to run FinOps modules, starting with the
Analyst module. This script favors sensible defaults and defers to your
existing module functions if present. If function names differ slightly in
your repo, the script will detect/call the closest match and print a clear
hint to adjust.

Usage (examples)
----------------
# Quickstart: run the full Analyst pipeline for a ticker
python finops.py analyst run --ticker AAPL --output docs/analyst/index.html

# Fetch only (store raw/normalized filings per your analyst.edgar)
python finops.py analyst fetch --ticker MSFT --forms 10-K 10-Q --from 2022-01-01

# Summarize existing fetched data
python finops.py analyst summarize --input .cache/edgar/MSFT

# Render a report from summaries into a single HTML page
python finops.py analyst report --input .cache/analyst/MSFT --output docs/analyst/index.html

# Show current config as seen by platform_core.config
python finops.py config show

Notes
-----
- Relies on platform_core/config.py to load .env (if available).
- Designed to be import-safe and resilient to minor API differences.
- Logs are concise by default; pass -v/--verbose multiple times to increase detail.
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

# ---------------------------
# Logging setup
# ---------------------------
_LOG = logging.getLogger("finops")


def setup_logging(verbosity: int) -> None:
    level = logging.WARNING  # 0
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
    )


# ---------------------------
# Config loader (platform_core/config.py)
# ---------------------------


def load_platform_config() -> Dict[str, Any]:
    """Attempt to import and run platform_core.config to load .env.

    Returns any exported CONFIG-like dict if present, else environment snapshot.
    """
    cfg: Dict[str, Any] = {}
    try:
        pc = importlib.import_module("platform_core.config")
        # Common patterns in repos: load(), load_env(), CONFIG, settings, etc.
        loader = getattr(pc, "load", None) or getattr(pc, "load_env", None)
        if callable(loader):
            _LOG.debug("Loading config via platform_core.config.%s", loader.__name__)
            loader()  # side-effect: os.environ is populated
        # Try to expose a dict-like object for introspection
        for name in ("CONFIG", "settings", "config"):
            maybe = getattr(pc, name, None)
            if isinstance(maybe, dict):
                cfg = maybe
                break
    except ModuleNotFoundError:
        _LOG.info(
            "platform_core.config not found; proceeding with OS environment only."
        )
    except Exception as e:  # pragma: no cover — defensive
        _LOG.warning("Config load warning: %s", e)
    return cfg or {k: v for k, v in os.environ.items() if k.startswith("FINOPS_")}


# ---------------------------
# Dynamic function helpers
# ---------------------------


def try_get_attr(mod: Any, names: Iterable[str]) -> Optional[Callable[..., Any]]:
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            _LOG.debug("Resolved %s.%s", mod.__name__, n)
            return fn
    return None


def import_module_or_fail(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        _LOG.error(
            "Missing module '%s'. Is your project structure correct?", module_name
        )
        raise


# ---------------------------
# Analyst pipeline steps
# ---------------------------


def analyst_fetch(
    ticker: Optional[str],
    cik: Optional[str],
    forms: Iterable[str],
    date_from: Optional[str],
    date_to: Optional[str],
    out_dir: Optional[str],
    **kwargs: Any,
) -> Any:
    """Call into analyst.edgar to fetch filings. Returns a dataset/path.

    Tries functions in this order: fetch_filings, fetch, run, main.
    """
    edgar = import_module_or_fail("analyst.edgar")
    fn = try_get_attr(edgar, ("fetch_filings", "fetch", "run", "main"))
    if not fn:
        raise AttributeError(
            "analyst.edgar must expose one of: fetch_filings, fetch, run, main"
        )
    _LOG.info(
        "Fetching filings (forms=%s, from=%s, to=%s)", list(forms), date_from, date_to
    )
    return fn(
        ticker=ticker,
        cik=cik,
        forms=list(forms) if forms else None,
        date_from=date_from,
        date_to=date_to,
        out_dir=out_dir,
        **kwargs,
    )


def analyst_summarize(input_path: str, **kwargs: Any) -> Any:
    """Call into analyst.summarize to build summaries from fetched data.

    Tries: summarize, run, main. Returns a dataset/path.
    """
    sm = import_module_or_fail("analyst.summarize")
    fn = try_get_attr(sm, ("summarize", "run", "main"))
    if not fn:
        raise AttributeError(
            "analyst.summarize must expose one of: summarize, run, main"
        )
    _LOG.info("Summarizing input: %s", input_path)
    return fn(input_path=input_path, **kwargs)


def analyst_report(
    input_path: str, output_html: str, template: Optional[str] = None, **kwargs: Any
) -> str:
    """Render the report HTML via analyst.report using platform_core.report_template.

    Tries functions in analyst.report: render_report, build, run, main.
    Returns the path to the written HTML file.
    """
    rpt = import_module_or_fail("analyst.report")
    fn = try_get_attr(rpt, ("render_report", "build", "run", "main"))
    if not fn:
        raise AttributeError(
            "analyst.report must expose one of: render_report, build, run, main"
        )
    _LOG.info("Rendering report → %s", output_html)
    # Provide common kwargs explicitly; pass-through for custom implementations
    res = fn(
        input_path=input_path, output_path=output_html, template=template, **kwargs
    )
    return str(res) if res is not None else output_html


def analyst_run_pipeline(
    ticker: Optional[str],
    cik: Optional[str],
    forms: Iterable[str],
    date_from: Optional[str],
    date_to: Optional[str],
    work_dir: str,
    output_html: str,
    template: Optional[str],
    **kwargs: Any,
) -> str:
    """End-to-end: fetch → summarize → report.

    Intermediates are stored under work_dir by ticker/CIK.
    This function is defensive about where "summarize" writes and what it returns.
    """
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    ident = ticker or cik or "dataset"
    base_dir = Path(work_dir) / ident
    raw_dir = base_dir / "raw"
    sum_dir = base_dir / "summary"

    _LOG.debug("Work directories: raw=%s, summary=%s", raw_dir, sum_dir)

    # 1) Fetch → raw_dir
    analyst_fetch(
        ticker=ticker,
        cik=cik,
        forms=forms,
        date_from=date_from,
        date_to=date_to,
        out_dir=str(raw_dir),
        **kwargs,
    )

    # 2) Summarize → try to capture return path; fall back to conventional sum_dir
    summary_ret = analyst_summarize(input_path=str(raw_dir), **kwargs)

    # Normalize report input path
    report_input: Path
    if isinstance(summary_ret, (str, Path)) and str(summary_ret):
        report_input = Path(str(summary_ret))
        _LOG.debug("Summarize returned path: %s", report_input)
    elif sum_dir.exists():
        report_input = sum_dir
        _LOG.debug("Using existing summary dir: %s", report_input)
    else:
        # Some implementations write summaries back under raw or elsewhere; be tolerant
        candidate = raw_dir / "summary"
        report_input = candidate if candidate.exists() else raw_dir
        _LOG.warning(
            "Summarize did not return a path and %s missing; using %s",
            sum_dir,
            report_input,
        )

    # 3) Report
    return analyst_report(
        input_path=str(report_input),
        output_html=output_html,
        template=template,
        **kwargs,
    )


# ---------------------------
# CLI definitions
# ---------------------------


def add_analyst_subparser(subparsers: argparse._SubParsersAction) -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-t", "--ticker", help="Ticker symbol (e.g., AAPL)")
    common.add_argument("--cik", help="SEC CIK as string (zero-padded fine)")
    common.add_argument(
        "--forms",
        nargs="+",
        default=["10-K", "10-Q"],
        help="SEC form types (space-separated)",
    )
    common.add_argument("--from", dest="date_from", help="Start date YYYY-MM-DD")
    common.add_argument("--to", dest="date_to", help="End date YYYY-MM-DD")
    common.add_argument(
        "-w",
        "--work-dir",
        default=".cache/analyst",
        help="Directory for intermediate artifacts",
    )
    common.add_argument(
        "-T", "--template", help="Optional path to custom HTML template"
    )

    sp = subparsers.add_parser("analyst", help="Run Analyst module")
    asp = sp.add_subparsers(dest="analyst_cmd", required=True)

    # fetch
    p_fetch = asp.add_parser("fetch", parents=[common], help="Fetch filings from EDGAR")
    p_fetch.add_argument(
        "-o", "--out", dest="out_dir", default=None, help="Output dir for raw data"
    )

    # summarize
    p_sum = asp.add_parser("summarize", help="Summarize fetched data")
    p_sum.add_argument("--input", required=True, help="Path to fetched/raw data root")

    # report
    p_rep = asp.add_parser("report", help="Render HTML report from summaries")
    p_rep.add_argument("--input", required=True, help="Path to summary data root")
    p_rep.add_argument("-o", "--output", required=True, help="Path to output HTML file")
    p_rep.add_argument("-T", "--template", help="Optional path to custom HTML template")

    # run (pipeline)
    p_run = asp.add_parser("run", parents=[common], help="Fetch → Summarize → Report")
    p_run.add_argument(
        "-o",
        "--output",
        default="docs/analyst/index.html",
        help="Destination HTML (default: docs/analyst/index.html)",
    )


def add_config_subparser(subparsers: argparse._SubParsersAction) -> None:
    sp = subparsers.add_parser("config", help="Inspect configuration")
    csp = sp.add_subparsers(dest="config_cmd", required=True)

    p_show = csp.add_parser(
        "show", help="Print detected FinOps config (.env and ENV vars)"
    )
    p_show.add_argument("--as-json", action="store_true", help="Output JSON")


# ---------------------------
# Main
# ---------------------------


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="finops", description="FinOps Platform CLI")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v, -vv)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    add_analyst_subparser(sub)
    add_config_subparser(sub)

    args = parser.parse_args(list(argv) if argv is not None else None)
    setup_logging(args.verbose)

    # Load config early (safe if module not present)
    cfg = load_platform_config()
    _LOG.debug("Loaded config keys: %s", list(cfg.keys())[:10])

    try:
        if args.cmd == "config":
            if args.config_cmd == "show":
                if args.as_json:
                    print(json.dumps(cfg, indent=2, default=str))
                else:
                    print("Detected FinOps configuration (subset):")
                    for k in sorted(cfg.keys()):
                        print(f"  {k}={cfg[k]}")
                return 0

        elif args.cmd == "analyst":
            if args.analyst_cmd == "fetch":
                analyst_fetch(
                    ticker=args.ticker,
                    cik=args.cik,
                    forms=args.forms,
                    date_from=args.date_from,
                    date_to=args.date_to,
                    out_dir=args.out_dir or args.work_dir,
                )
                _LOG.info("Fetch complete.")
                return 0

            elif args.analyst_cmd == "summarize":
                analyst_summarize(input_path=args.input)
                _LOG.info("Summarize complete.")
                return 0

            elif args.analyst_cmd == "report":
                out = analyst_report(
                    input_path=args.input,
                    output_html=args.output,
                    template=args.template,
                )
                _LOG.info("Report written: %s", out)
                print(out)
                return 0

            elif args.analyst_cmd == "run":
                out = analyst_run_pipeline(
                    ticker=args.ticker,
                    cik=args.cik,
                    forms=args.forms,
                    date_from=args.date_from,
                    date_to=args.date_to,
                    work_dir=args.work_dir,
                    output_html=args.output,
                    template=args.template,
                )
                _LOG.info("Pipeline complete → %s", out)
                print(out)
                return 0

    except Exception as e:  # Pragmatic top-level guard for a CLI entrypoint
        _LOG.error("%s", e)
        if args.verbose >= 2:
            raise
        return 1

    # Should not reach here
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
