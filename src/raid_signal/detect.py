"""Orchestrate a full analysis: series, limits, signals, and the lead time.

This is the module the CLI, the report and the experiments all call. It pulls
the two weekly series out of the event log, freezes the limits on the baseline,
runs the rules, and then answers the one question the whole repository exists to
answer: did a signal fire before the human escalated, and by how many weeks.

Two charts are built, but they are not treated the same. The blocker-opened
count is a count of events per week, for which the Poisson c-chart is the right
model, so the gate and the lead time rest on it. The backlog level is a running
total, which is autocorrelated (a level carries last week's value forward), so an
individuals chart over-reports on it; it is built and shown as a secondary
diagnostic but does not drive the gate (ADR-003 and ADR-004). The lead time is
measured against a recorded manual escalation, never against a feature the tool
defines for itself, so the number cannot be circular.
"""

from __future__ import annotations

import pandas as pd

from . import aggregate, control, rules
from .config import Policy
from .model import DetectionResult, RaidItem


def load_escalations(path: str) -> dict[str, int]:
    """Read the escalation log: a label mapped to the week a human escalated."""
    frame = pd.read_csv(path)
    required = {"label", "escalated_week"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"escalation log missing columns: {sorted(missing)}")
    out: dict[str, int] = {}
    for row in frame.itertuples(index=False):
        out[str(row.label)] = int(row.escalated_week)
    return out


def analyse(
    items: list[RaidItem],
    policy: Policy,
    escalation_week: int | None = None,
) -> DetectionResult:
    """Build both charts, evaluate the rules, and compute the warning lead time.

    The gate (in_control) and the lead time are derived from the opened-count
    chart only. Backlog signals are carried on the result for the report but kept
    out of the gate, because an individuals chart on an autocorrelated level
    over-fires and would make the gate cry wolf.
    """
    opened = aggregate.opened_per_week(items, policy.blockers_only_for_opened_chart)
    backlog = aggregate.open_backlog_per_week(items)

    opened_limits = control.c_chart_limits(opened, policy)
    backlog_limits = control.xmr_limits(backlog, policy)

    opened_signals_all = rules.evaluate(opened, opened_limits, policy)
    backlog_signals_all = rules.evaluate(backlog, backlog_limits, policy)

    # A signal inside the baseline window is not a warning: the baseline is
    # assumed representative by construction (ADR-005), so limits are frozen on
    # it and only later weeks are judged against them.
    reporting_start = policy.baseline_end + 1
    opened_signals = [s for s in opened_signals_all if s.week >= reporting_start]
    backlog_signals = [s for s in backlog_signals_all if s.week >= reporting_start]

    first_week = rules.first_signal_week(opened_signals, on_or_after=reporting_start)
    lead = None
    if escalation_week is not None and first_week is not None:
        lead = escalation_week - first_week  # positive means the signal led

    return DetectionResult(
        opened_series=opened,
        backlog_series=backlog,
        opened_limits=opened_limits,
        backlog_limits=backlog_limits,
        signals=opened_signals,
        backlog_signals=backlog_signals,
        escalation_week=escalation_week,
        first_signal_week=first_week,
        lead_weeks=lead,
    )
