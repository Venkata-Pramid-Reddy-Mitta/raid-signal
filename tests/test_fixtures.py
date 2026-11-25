"""The committed fixtures must reproduce the published headline numbers.

These tie the data to the prose. If the generator or the maths drifts, the
headline figures in the README move, and one of these tests fails before the
number checker even runs.
"""

from __future__ import annotations

import pytest

from raid_signal import aggregate, detect
from raid_signal.config import load_policy


@pytest.fixture
def real(repo_root):
    policy = load_policy(repo_root / "config" / "policy.toml")
    items = aggregate.load_raid_log(str(repo_root / "data" / "raid_log.csv"))
    esc = detect.load_escalations(str(repo_root / "data" / "escalations.csv"))["blocker_spike"]
    return detect.analyse(items, policy, escalation_week=esc)


@pytest.fixture
def stable(repo_root):
    policy = load_policy(repo_root / "config" / "policy.toml")
    items = aggregate.load_raid_log(str(repo_root / "data" / "raid_log_stable.csv"))
    return detect.analyse(items, policy, escalation_week=None)


def test_the_real_program_signals_in_week_16(real):
    assert real.first_signal_week == 16


def test_the_warning_lead_is_four_weeks(real):
    assert real.lead_weeks == 4


def test_the_lower_limit_is_clamped_to_zero(real):
    assert real.opened_limits.lower_clamped is True
    assert real.opened_limits.lower == 0.0


def test_rule3_no_longer_fires_on_the_real_program_after_the_strict_fix(real):
    assert [s.week for s in real.signals if s.rule == "rule3"] == []
    assert [s.week for s in real.backlog_signals if s.rule == "rule3"] == []


def test_the_stable_program_has_three_opened_false_alarm_weeks(stable):
    weeks = sorted({s.week for s in stable.signals})
    assert len(weeks) == 3


def test_the_backlog_chart_over_fires_relative_to_the_opened_chart(stable):
    opened_weeks = len({s.week for s in stable.signals})
    backlog_weeks = len({s.week for s in stable.backlog_signals})
    assert backlog_weeks > opened_weeks
