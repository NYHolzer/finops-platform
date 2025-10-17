# finops-platform/cli.py
from __future__ import annotations

import argparse
import os
import sys


def _default_ticker() -> str:
    # If not set, fall back to AAPL so the command always works in demos
    return os.getenv("ANALYST_DEFAULT_TICKER", "AAPL")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="finops", description="FinOps Platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # finops analyst [TICKER]
    p_analyst = sub.add_parser("analyst", help="Render SEC filing analysis as HTML")
    p_analyst.add_argument(
        "ticker",
        nargs="?",
        default=_default_ticker(),
        help="Public company ticker (e.g., AAPL). Defaults to env ANALYST_DEFAULT_TICKER or AAPL.",
    )

    args = parser.parse_args(argv)

    if args.command == "analyst":
        try:
            from analyst.report import render_report
        except Exception as e:
            print(f"[finops] Could not import analyst.report: {e}", file=sys.stderr)
            return 2

        try:
            print(f"[finops] Rendering Analyst report for {args.ticker} …")
            out_path = render_report(args.ticker)
            print(f"[finops] ✓ Wrote report: {out_path}")
            return 0
        except Exception as e:
            print(
                f"[finops] ✗ Failed to render report for {args.ticker}: {e}",
                file=sys.stderr,
            )
            return 1

    # Should never get here due to required=True, but just in case:
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
