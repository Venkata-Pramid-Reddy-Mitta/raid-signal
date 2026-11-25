"""Experiment 2: what does the warning cost on a program with no real shift?

Question the README asks: lead time is the thing the chart buys; false alarms
are what it spends. Run the same rules on a matched stable fixture that has no
planted spike and count the post-baseline weeks that still fire a signal. The
opened-count chart is the gate, so its false-alarm weeks are the real cost. The
backlog chart is reported separately because an individuals chart on an
autocorrelated level fires far more often, which is the evidence for not gating
on it (ADR-004).
"""

from __future__ import annotations

from _common import load, write

from raid_signal import detect


def _distinct_weeks(signals) -> list[int]:
    return sorted({s.week for s in signals})


def _rule_counts(signals) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in signals:
        counts[s.rule] = counts.get(s.rule, 0) + 1
    return dict(sorted(counts.items()))


def run() -> dict:
    policy, items = load(real=False)
    result = detect.analyse(items, policy, escalation_week=None)
    reporting_weeks = [w for w in result.opened_series.weeks if w > policy.baseline_end]

    opened_weeks = _distinct_weeks(result.signals)
    backlog_weeks = _distinct_weeks(result.backlog_signals)
    payload = {
        "post_baseline_weeks": len(reporting_weeks),
        "opened_false_alarm_weeks": len(opened_weeks),
        "opened_false_alarm_week_list": opened_weeks,
        "backlog_false_alarm_weeks": len(backlog_weeks),
        "opened_rule_counts": _rule_counts(result.signals),
        "backlog_rule_counts": _rule_counts(result.backlog_signals),
    }
    write("exp02_false_alarms.json", payload)
    return payload


def main() -> None:
    p = run()
    print("Experiment 2: false alarms on a stable program")
    print(f"  post-baseline weeks          : {p['post_baseline_weeks']}")
    print(f"  opened-count false-alarm wks : {p['opened_false_alarm_weeks']} {p['opened_false_alarm_week_list']}")
    print(f"  backlog false-alarm weeks    : {p['backlog_false_alarm_weeks']}")
    print(f"  opened rule counts           : {p['opened_rule_counts']}")
    print(f"  backlog rule counts          : {p['backlog_rule_counts']}")


if __name__ == "__main__":
    main()
