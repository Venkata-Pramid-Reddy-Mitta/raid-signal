"""Regression test pinning the flat-week trend bug.

The bug: rule 3 (six points all increasing or all decreasing) was written with
`>=` and `<=`, so a week whose count equalled the week before was counted as
both an increase and a decrease. On the real fixture this fired three false
trends, each spanning a plateau: the opened chart in week 22 (counts
1,2,3,4,6,6) and the backlog chart in weeks 16 and 30, each with a repeated
value inside the six-point window.

The number that revealed it: experiment 3 reported rule3 firing weeks
[22] on the opened chart and [16, 30] on the backlog chart. A trend rule has no
business firing across a flat stretch, so every one of those was wrong. After
the strict fix all three disappear, while the week-16 breach and the 4-week
lead, which never depended on rule 3, are untouched.
"""

from __future__ import annotations

from raid_signal.config import Policy
from raid_signal.model import ControlLimits, WeeklySeries
from raid_signal.rules import _rule3


def _policy() -> Policy:
    return Policy(
        baseline_start=1,
        baseline_end=6,
        sigma=3.0,
        clamp_lower_to_zero=True,
        rule1_point_beyond_3sigma=True,
        rule2_nine_one_side=True,
        rule3_six_trending=True,
        rule5_two_of_three_beyond_2sigma=True,
        blockers_only_for_opened_chart=True,
        late_grace_weeks=0,
    )


def _limits() -> ControlLimits:
    return ControlLimits(
        chart="c", center=3.0, upper=10.0, lower=0.0, sigma=3.0,
        lower_clamped=True, two_sigma_upper=8.0, two_sigma_lower=0.0,
    )


def test_rule3_does_not_count_a_flat_week_as_part_of_an_upward_trend():
    # Five strict increases then a flat week: not six increasing points.
    series = WeeklySeries("s", tuple(range(1, 7)), (1.0, 2.0, 3.0, 4.0, 6.0, 6.0))
    assert _rule3(series, _limits()) == []


def test_rule3_does_not_count_a_flat_week_as_part_of_a_downward_trend():
    series = WeeklySeries("s", tuple(range(1, 7)), (29.0, 24.0, 23.0, 23.0, 19.0, 13.0))
    assert _rule3(series, _limits()) == []


def test_rule3_still_fires_on_six_strictly_increasing_points():
    series = WeeklySeries("s", tuple(range(1, 7)), (1.0, 2.0, 3.0, 4.0, 5.0, 6.0))
    fired = _rule3(series, _limits())
    assert len(fired) == 1
    assert fired[0].week == 6
    assert "up" in fired[0].detail


def test_rule3_still_fires_on_six_strictly_decreasing_points():
    series = WeeklySeries("s", tuple(range(1, 7)), (6.0, 5.0, 4.0, 3.0, 2.0, 1.0))
    fired = _rule3(series, _limits())
    assert len(fired) == 1
    assert "down" in fired[0].detail


def test_rule3_needs_a_full_run_of_six_not_five():
    # Only five strictly increasing points: must not fire.
    series = WeeklySeries("s", tuple(range(1, 6)), (1.0, 2.0, 3.0, 4.0, 5.0))
    assert _rule3(series, _limits()) == []
