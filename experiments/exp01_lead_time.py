"""Experiment 1: how many weeks before the manual escalation did SPC fire?

Question the README asks: a committed escalation date is a fact about when a
human finally reacted. Did the control chart reach the same conclusion earlier,
and by how much? Lead is escalation week minus the first opened-count signal
week; a positive number is weeks of warning the chart would have bought.
"""

from __future__ import annotations

from _common import escalation_week, load, write

from raid_signal import detect


def run() -> dict:
    policy, items = load(real=True)
    esc = escalation_week()
    result = detect.analyse(items, policy, escalation_week=esc)
    first = result.first_signal_week
    first_rule = None
    if first is not None:
        first_rule = sorted(s.rule for s in result.signals if s.week == first)[0]
    payload = {
        "escalation_week": esc,
        "first_signal_week": first,
        "first_signal_rule": first_rule,
        "lead_weeks": result.lead_weeks,
        "opened_center": round(result.opened_limits.center, 4),
        "opened_ucl": round(result.opened_limits.upper, 4),
    }
    write("exp01_lead_time.json", payload)
    return payload


def main() -> None:
    p = run()
    print("Experiment 1: warning lead time")
    print(f"  manual escalation week : {p['escalation_week']}")
    print(f"  first signal week      : {p['first_signal_week']} ({p['first_signal_rule']})")
    print(f"  lead weeks             : {p['lead_weeks']}")


if __name__ == "__main__":
    main()
