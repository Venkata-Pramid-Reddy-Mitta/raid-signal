"""Command line entry point with exit codes that mean something.

The exit code is the product, not a side effect, because a governance gate is
most useful when a pipeline can read it:

* 0  the tool ran and the opened-count chart is in control (no escalation needed)
* 2  the tool ran and a signal fired (the answer is: escalate)
* 1  the tool failed to answer (bad input, missing file, invalid policy)

The distinction between 2 and 1 is the important one: "the tool did its job and
the answer is yes, escalate" must never be confused with "the tool broke". Code
2 is chosen for the signal case so a shell `set -e` script stops on it, the same
way a failing test would.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import detect
from .aggregate import load_raid_log
from .config import ConfigError, load_policy
from .model import DetectionResult
from .report import write_report

EXIT_IN_CONTROL = 0
EXIT_ERROR = 1
EXIT_SIGNAL = 2


def _summary(result: DetectionResult) -> dict:
    return {
        "in_control": result.in_control,
        "escalation_week": result.escalation_week,
        "first_signal_week": result.first_signal_week,
        "lead_weeks": result.lead_weeks,
        "opened_center": round(result.opened_limits.center, 4),
        "opened_ucl": round(result.opened_limits.upper, 4),
        "opened_lcl": result.opened_limits.lower,
        "lower_clamped": result.opened_limits.lower_clamped,
        "n_opened_signals": len(result.signals),
        "n_backlog_signals": len(result.backlog_signals),
        "signals": [
            {"week": s.week, "rule": s.rule, "detail": s.detail} for s in result.signals
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raid-signal",
        description="Statistical process control over a RAID log.",
    )
    parser.add_argument("raid_log", help="path to the RAID log CSV")
    parser.add_argument(
        "--escalations", help="path to an escalation log CSV (optional)", default=None
    )
    parser.add_argument(
        "--escalation-label",
        default="blocker_spike",
        help="which escalation label to measure lead time against",
    )
    parser.add_argument("--policy", default=None, help="path to a policy TOML")
    parser.add_argument("--report", default=None, help="write an HTML report to this path")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        policy = load_policy(args.policy)
        items = load_raid_log(args.raid_log)
        escalation_week = None
        if args.escalations:
            escalations = detect.load_escalations(args.escalations)
            escalation_week = escalations.get(args.escalation_label)
        result = detect.analyse(items, policy, escalation_week=escalation_week)
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"raid-signal: error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.report:
        write_report(result, args.report)

    if args.json:
        print(json.dumps(_summary(result), indent=2))
    else:
        verdict = "IN CONTROL" if result.in_control else "SIGNAL"
        print(f"raid-signal: {verdict}")
        if result.first_signal_week is not None:
            print(f"  first opened-count signal: week {result.first_signal_week}")
        if result.lead_weeks is not None:
            print(f"  warning lead over manual escalation: {result.lead_weeks} weeks")
        print(
            f"  opened-count chart: center={result.opened_limits.center:.2f} "
            f"UCL={result.opened_limits.upper:.2f} "
            f"LCL={result.opened_limits.lower:.2f}"
            + (" (clamped, blind to improvement)" if result.opened_limits.lower_clamped else "")
        )

    return EXIT_IN_CONTROL if result.in_control else EXIT_SIGNAL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
