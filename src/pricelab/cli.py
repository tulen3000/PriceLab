from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pricelab.adjuster import apply_back_adjustment, build_adjustment_events
from pricelab.detector import run_check
from pricelab.io import default_adjust_output_path, default_check_output_path, load_params, load_quotes, load_roll_datetimes_only, save_check_results, save_quotes
from pricelab.report import build_adjust_summary, build_check_summary


def cmd_check(args: argparse.Namespace) -> int:
    quotes_path = Path(args.quotes)
    params_path = Path(args.params)
    output_path = Path(args.output) if args.output else default_check_output_path(quotes_path)
    df = load_quotes(quotes_path)
    config = load_params(params_path)
    results, summary = run_check(df=df, config=config)
    save_check_results(results, output_path)
    print(build_check_summary(summary, str(output_path)))
    return 0


def cmd_adjust(args: argparse.Namespace) -> int:
    quotes_path = Path(args.quotes)
    rolls_path = Path(args.rolls)
    output_path = Path(args.output) if args.output else default_adjust_output_path(quotes_path)
    df = load_quotes(quotes_path)
    roll_datetimes = load_roll_datetimes_only(rolls_path)
    print(f"roll_datetime_found={len(roll_datetimes)}")
    events = build_adjustment_events(df=df, roll_datetimes=roll_datetimes)
    adjusted = apply_back_adjustment(df=df, events=events)
    save_quotes(adjusted, output_path)
    print(build_adjust_summary(events, str(output_path)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pricelab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Detect roll candidates")
    check_parser.add_argument("--quotes", required=True, help="Path to MT5 TSV/CSV quotes file")
    check_parser.add_argument("--params", required=True, help="Path to YAML/ENV params file")
    check_parser.add_argument("--output", help="Optional output CSV path")
    check_parser.set_defaults(func=cmd_check)

    adjust_parser = subparsers.add_parser("adjust", help="Back-adjust quotes by roll_datetime")
    adjust_parser.add_argument("--quotes", required=True, help="Path to MT5 TSV/CSV quotes file")
    adjust_parser.add_argument("--rolls", required=True, help="Path to file with roll_datetime values")
    adjust_parser.add_argument("--output", help="Optional output file path")
    adjust_parser.set_defaults(func=cmd_adjust)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
