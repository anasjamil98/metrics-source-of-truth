"""Command line: python -m metrics {build,docs,compare,alert}"""

import argparse
import sys

from . import alert, build, compare, docs


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m metrics")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="rebuild the gold tables")
    sub.add_parser("docs", help="regenerate docs/metric_contracts.md from the registry")
    p_compare = sub.add_parser("compare", help="show how MAU changes under different definitions")
    p_compare.add_argument("--month", required=True, help="e.g. 2025-09")
    p_alert = sub.add_parser("alert", help="write the daily performance alert for one date")
    p_alert.add_argument("--date", required=True, help="local date, e.g. 2025-09-17")
    args = parser.parse_args(argv)

    if args.command == "docs":
        print(f"Wrote {docs.write().relative_to(docs.ROOT)}")
        return 0

    if not build.DEFAULT_SOURCE.exists():
        print("No source database. Run: python data/generate.py", file=sys.stderr)
        return 2

    if args.command == "build":
        daily, monthly = build.build()
        print(f"gold_daily_metrics: {daily} rows; gold_monthly_metrics: {monthly} rows")
        return 0

    if not build.DEFAULT_GOLD.exists():
        print("No gold tables yet. Run: python -m metrics build", file=sys.stderr)
        return 2

    if args.command == "compare":
        print(compare.render(args.month, compare.compare(args.month)))
        return 0

    message, _, path = alert.run(args.date)
    print(message)
    print(f"\nWrote {path.relative_to(build.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
