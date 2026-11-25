"""Re-measure every published figure and write docs/metrics.json.

Nothing in the documents is typed by hand: this script runs the suite (or reads
its machine-readable reports), runs the four experiments, reads the corpus, and
computes the derived values. check_numbers.py then fails the build if any
document quotes a figure this script did not produce.

Run the test suite as its own CI step and call this with --skip-tests so a red
test surfaces as a failed test step, not as a traceback from here (trap 4 in the
CI notes). Without --skip-tests this script runs pytest itself for local use.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXP = DOCS / "experiments"
REPORTS = ROOT / "reports"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from raid_signal import aggregate  # noqa: E402

# Anchor phrases: the exact wording a document must use with the value
# substituted in. Alternatives are allowed; any one matching is enough. Short,
# two or three words, so they survive markdown line wrapping (receipts rules 1
# and 2). Every small number is anchored (rule 3).
ANCHORS: dict[str, list[str]] = {
    "tests_total": ["{} tests"],
    "coverage_line_pct": ["{}% line coverage", "{}% coverage"],
    "lead_weeks": ["{} weeks before", "lead of {} weeks", "{} weeks earlier"],
    "first_signal_week": ["week {}", "in week {}"],
    "escalation_week": ["week {}", "in week {}"],
    "three_sigma_lead_over_run_rules": [
        "{} weeks before the earliest run rule",
        "led the run rules by {} weeks",
    ],
    "opened_false_alarm_weeks": ["{} false-signal weeks", "{} weeks of the"],
    "backlog_false_alarm_weeks": ["{} backlog false-alarm weeks", "fires on {} of"],
    "post_baseline_weeks": ["{} post-baseline weeks", "over {} weeks"],
    "lcl_clamped_pct": ["{}% of weeks", "{}% of every"],
    "program_weeks": ["{} program weeks", "{}-week program"],
    "items_total": ["{} RAID items"],
    "blockers_total": ["{} of them blockers", "{} blockers"],
    "opened_center": ["centre line at {}", "centre of {}"],
    "opened_ucl": ["upper limit at {}", "UCL of {}"],
}

CHECKED_DOCUMENTS = [
    "README.md",
    "docs/defense-guide.md",
]


def _run_tests() -> None:
    REPORTS.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"--junitxml={REPORTS / 'junit.xml'}",
            "--cov=raid_signal",
            "--cov-report=json:coverage.json",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )


def _tests_total() -> int:
    root = ET.parse(REPORTS / "junit.xml").getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return int(suite.get("tests"))


def _coverage_pct() -> float:
    # Report line coverage specifically (covered statements over total), not the
    # combined line-plus-branch percentage, so the "% line coverage" anchor is
    # literally true. Branch coverage is enforced separately by the CI floor.
    totals = json.loads((ROOT / "coverage.json").read_text())["totals"]
    covered = totals["covered_lines"]
    statements = totals["num_statements"]
    return round(100.0 * covered / statements, 1)


def _run_experiments() -> None:
    for script in sorted((ROOT / "experiments").glob("exp*.py")):
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def _exp(name: str) -> dict:
    return json.loads((EXP / name).read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        _run_tests()
    _run_experiments()

    e1 = _exp("exp01_lead_time.json")
    e2 = _exp("exp02_false_alarms.json")
    e3 = _exp("exp03_run_rules_vs_3sigma.json")
    e4 = _exp("exp04_lcl_blindness.json")

    real = aggregate.load_raid_log(str(ROOT / "data" / "raid_log.csv"))
    weeks = aggregate.program_weeks(real)[-1]

    # The 3-sigma breach led the earliest run rule; publish that lead as a
    # positive magnitude for the prose, keeping the signed value in the JSON.
    signed = e3["run_rule_lead_over_3sigma"]
    three_sigma_lead = -signed if signed is not None and signed < 0 else 0

    metrics = {
        "tests_total": _tests_total(),
        "coverage_line_pct": _coverage_pct(),
        "lead_weeks": e1["lead_weeks"],
        "first_signal_week": e1["first_signal_week"],
        "escalation_week": e1["escalation_week"],
        "three_sigma_lead_over_run_rules": three_sigma_lead,
        "opened_false_alarm_weeks": e2["opened_false_alarm_weeks"],
        "backlog_false_alarm_weeks": e2["backlog_false_alarm_weeks"],
        "post_baseline_weeks": e2["post_baseline_weeks"],
        "lcl_clamped_pct": e4["clamped_pct"],
        "program_weeks": weeks,
        "items_total": len(real),
        "blockers_total": sum(i.is_blocker for i in real),
        "opened_center": round(e1["opened_center"], 2),
        "opened_ucl": round(e1["opened_ucl"], 2),
    }

    payload = {
        "metrics": metrics,
        "anchors": ANCHORS,
        "checked_documents": CHECKED_DOCUMENTS,
        "note": "every value here is produced by running the suite and the experiments",
    }
    out = DOCS / "metrics.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(metrics)} metrics")
    for key, value in metrics.items():
        print(f"  {key} = {value}")


if __name__ == "__main__":
    main()
