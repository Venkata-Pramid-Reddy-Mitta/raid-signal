"""Experiment 4: how blind is the chart to improvement?

Question the README asks: the Poisson lower limit for a low count is negative and
is clamped to zero, so a week can never fall below it, so an improvement can
never be a signal. This measures the cost of that structural fact two ways:
the share of weeks the lower limit was clamped, and a direct demonstration that
halving the blocker rate for the whole post-baseline period produces zero
signals, because the chart has no lower limit to breach.
"""

from __future__ import annotations

from _common import load, write

from raid_signal import control, detect, rules
from raid_signal.model import WeeklySeries


def run() -> dict:
    policy, items = load(real=True)
    result = detect.analyse(items, policy, escalation_week=None)

    weeks = result.opened_series.weeks
    total = len(weeks)
    clamped = result.opened_limits.lower_clamped
    # Every week shares the one frozen lower limit, so a clamped limit clamps all
    # of them; the share is reported as a fraction for honesty about what "blind"
    # means here.
    clamped_weeks = total if clamped else 0

    # Demonstration: build a counterfactual series where the post-baseline rate is
    # halved (a real improvement) and show the chart raises no signal below.
    halved_values = []
    for w, v in zip(result.opened_series.weeks, result.opened_series.values):
        halved_values.append(v / 2.0 if w > policy.baseline_end else v)
    halved = WeeklySeries(
        name="opened_halved", weeks=result.opened_series.weeks, values=tuple(halved_values)
    )
    halved_limits = control.c_chart_limits(halved, policy)
    halved_signals = [
        s for s in rules.evaluate(halved, halved_limits, policy) if s.week > policy.baseline_end
    ]
    low_signals = [s for s in halved_signals if "below" in s.detail or "low" in s.detail]

    payload = {
        "total_weeks": total,
        "lower_clamped": clamped,
        "clamped_weeks": clamped_weeks,
        "clamped_pct": round(100.0 * clamped_weeks / total, 1),
        "halved_post_baseline_low_signals": len(low_signals),
        "halved_lower_limit": halved_limits.lower,
    }
    write("exp04_lcl_blindness.json", payload)
    return payload


def main() -> None:
    p = run()
    print("Experiment 4: blindness to improvement")
    print(f"  weeks total              : {p['total_weeks']}")
    print(f"  lower limit clamped      : {p['lower_clamped']}")
    print(f"  clamped weeks (pct)      : {p['clamped_weeks']} ({p['clamped_pct']}%)")
    print(f"  signals when rate halved : {p['halved_post_baseline_low_signals']} (low-side)")


if __name__ == "__main__":
    main()
