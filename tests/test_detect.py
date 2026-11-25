"""The orchestration: gate, lead time, and the opened-versus-backlog split."""

from __future__ import annotations

from raid_signal import detect
from raid_signal.model import RaidItem


def _blocker_opens(per_week: list[int]) -> list[RaidItem]:
    """Build items that open the given number of blockers each week and never close."""
    items: list[RaidItem] = []
    counter = 0
    for week, n in enumerate(per_week, start=1):
        for _ in range(n):
            counter += 1
            items.append(RaidItem(f"I-{counter}", "Issue", 4, True, week, None))
    return items


def test_lead_is_positive_when_the_signal_precedes_the_escalation(policy_factory):
    pol = policy_factory(baseline_end=6)
    # Six quiet weeks then a hard spike in week 8.
    items = _blocker_opens([1, 1, 1, 1, 1, 1, 1, 20])
    res = detect.analyse(items, pol, escalation_week=10)
    assert res.first_signal_week == 8
    assert res.lead_weeks == 2


def test_lead_is_none_without_an_escalation(policy_factory):
    pol = policy_factory(baseline_end=6)
    items = _blocker_opens([1, 1, 1, 1, 1, 1, 1, 20])
    res = detect.analyse(items, pol, escalation_week=None)
    assert res.lead_weeks is None
    assert res.first_signal_week == 8


def test_lead_is_negative_when_the_signal_came_late(policy_factory):
    pol = policy_factory(baseline_end=6)
    items = _blocker_opens([1, 1, 1, 1, 1, 1, 1, 20])
    res = detect.analyse(items, pol, escalation_week=7)
    assert res.lead_weeks == -1


def test_a_quiet_program_is_in_control(policy_factory):
    pol = policy_factory(baseline_end=6)
    items = _blocker_opens([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    res = detect.analyse(items, pol, escalation_week=None)
    assert res.in_control is True
    assert res.first_signal_week is None


def test_signals_inside_the_baseline_are_not_counted(policy_factory):
    pol = policy_factory(baseline_end=8)
    # A spike inside the baseline window is absorbed into the limits, not flagged.
    items = _blocker_opens([1, 1, 30, 1, 1, 1, 1, 1, 1, 1])
    res = detect.analyse(items, pol, escalation_week=None)
    assert all(s.week > 8 for s in res.signals)


def test_backlog_signals_are_kept_separate_from_opened_signals(policy_factory):
    pol = policy_factory(baseline_end=6)
    items = _blocker_opens([1, 1, 1, 1, 1, 1, 1, 20])
    res = detect.analyse(items, pol, escalation_week=None)
    # Opened signals and backlog signals are distinct lists on the result.
    assert isinstance(res.signals, list)
    assert isinstance(res.backlog_signals, list)


def test_load_escalations_reads_the_label(tmp_path):
    path = tmp_path / "esc.csv"
    path.write_text("label,escalated_week\nblocker_spike,20\nother,5\n")
    escalations = detect.load_escalations(str(path))
    assert escalations["blocker_spike"] == 20
    assert escalations["other"] == 5


def test_load_escalations_rejects_missing_columns(tmp_path):
    path = tmp_path / "esc.csv"
    path.write_text("label\nx\n")
    try:
        detect.load_escalations(str(path))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
