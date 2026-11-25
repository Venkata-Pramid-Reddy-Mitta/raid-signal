"""Experiment 3: which rule fires first, the single point or the run?

Question the README asks: run rules exist to catch a drift the single
out-of-limit point misses. On this spike, does any run rule actually fire before
the 3-sigma breach, and by how much? The honest answer matters more than the
flattering one: if the 3-sigma breach led here, say so, and let the per-rule
first-firing weeks show where a run rule would have led instead.

This experiment also prints the full rule-3 firing weeks on both charts, because
a trend rule that fires across a flat stretch is doing the wrong thing, and this
is where that was first noticed on this build.
"""

from __future__ import annotations

from _common import escalation_week, load, write

from raid_signal import detect


def _first_week_per_rule(signals) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in signals:
        if s.rule not in out or s.week < out[s.rule]:
            out[s.rule] = s.week
    return dict(sorted(out.items()))


def run() -> dict:
    policy, items = load(real=True)
    result = detect.analyse(items, policy, escalation_week=escalation_week())

    opened_first = _first_week_per_rule(result.signals)
    rule1_week = opened_first.get("rule1")
    run_rule_weeks = [w for r, w in opened_first.items() if r != "rule1"]
    earliest_run_rule = min(run_rule_weeks) if run_rule_weeks else None
    run_rule_lead = (
        rule1_week - earliest_run_rule
        if rule1_week is not None and earliest_run_rule is not None
        else None
    )

    rule3_weeks_opened = sorted(s.week for s in result.signals if s.rule == "rule3")
    rule3_weeks_backlog = sorted(s.week for s in result.backlog_signals if s.rule == "rule3")

    payload = {
        "opened_first_week_per_rule": opened_first,
        "rule1_week": rule1_week,
        "earliest_run_rule_week": earliest_run_rule,
        "run_rule_lead_over_3sigma": run_rule_lead,
        "rule3_firing_weeks_opened": rule3_weeks_opened,
        "rule3_firing_weeks_backlog": rule3_weeks_backlog,
    }
    write("exp03_run_rules_vs_3sigma.json", payload)
    return payload


def main() -> None:
    p = run()
    print("Experiment 3: run rules versus the 3-sigma breach")
    print(f"  first week per rule (opened) : {p['opened_first_week_per_rule']}")
    print(f"  3-sigma (rule1) first week   : {p['rule1_week']}")
    print(f"  earliest run-rule week       : {p['earliest_run_rule_week']}")
    print(f"  run-rule lead over 3-sigma   : {p['run_rule_lead_over_3sigma']}")
    print(f"  rule3 firings opened  weeks  : {p['rule3_firing_weeks_opened']}")
    print(f"  rule3 firings backlog weeks  : {p['rule3_firing_weeks_backlog']}")


if __name__ == "__main__":
    main()
