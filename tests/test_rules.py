"""The Nelson run rules, each tested as the property it claims."""

from __future__ import annotations

from raid_signal.model import ControlLimits, WeeklySeries
from raid_signal.rules import (
    _rule1,
    _rule2,
    _rule5,
    evaluate,
    first_signal_week,
)


def _series(values, start=1):
    weeks = tuple(range(start, start + len(values)))
    return WeeklySeries("s", weeks, tuple(float(v) for v in values))


def _limits(center=3.0, upper=10.0, lower=0.0, two_up=8.0, two_low=0.0):
    return ControlLimits("c", center, upper, lower, 3.0, True, two_up, two_low)


def test_rule1_fires_above_the_upper_limit():
    fired = _rule1(_series([1, 11, 2]), _limits())
    assert [s.week for s in fired] == [2]
    assert "above" in fired[0].detail


def test_rule1_fires_below_the_lower_limit_when_unclamped():
    fired = _rule1(_series([5, 5, 5]), _limits(lower=4.0))
    assert len(fired) == 0  # all equal to center region, none below 4
    fired2 = _rule1(_series([3, 2, 3]), _limits(lower=2.5))
    assert [s.week for s in fired2] == [2]
    assert "below" in fired2[0].detail


def test_rule1_does_not_fire_inside_the_limits():
    assert _rule1(_series([3, 4, 2, 5]), _limits()) == []


def test_rule2_fires_on_nine_points_above_centre():
    fired = _rule2(_series([4] * 9), _limits())
    assert len(fired) == 1
    assert fired[0].week == 9
    assert "above" in fired[0].detail


def test_rule2_fires_on_nine_points_below_centre():
    fired = _rule2(_series([1] * 9), _limits())
    assert "below" in fired[0].detail


def test_rule2_run_is_broken_by_a_point_on_the_centre_line():
    # Eight above, then exactly on centre, then one above: no run of nine.
    values = [4] * 8 + [3] + [4]
    assert _rule2(_series(values), _limits()) == []


def test_rule2_run_is_broken_by_crossing_the_centre():
    values = [4] * 5 + [1] + [4] * 4
    assert _rule2(_series(values), _limits()) == []


def test_rule5_fires_on_two_of_three_beyond_two_sigma_high():
    # Points 9 and 9 beyond 8, with a middle point inside: 2 of 3.
    fired = _rule5(_series([9, 3, 9]), _limits(two_up=8.0))
    assert any(s.rule == "rule5" for s in fired)


def test_rule5_does_not_fire_on_only_one_point_beyond_two_sigma():
    assert _rule5(_series([9, 3, 3]), _limits(two_up=8.0)) == []


def test_rule5_fires_low_side_when_unclamped():
    fired = _rule5(_series([1, 5, 1]), _limits(two_low=2.0))
    assert any("low" in s.detail for s in fired)


def test_evaluate_sorts_signals_by_week_then_rule(policy):
    # A series engineered to fire rule1 and rule2 in overlapping weeks.
    series = _series([11] * 9)
    signals = evaluate(series, _limits(), policy)
    weeks = [s.week for s in signals]
    assert weeks == sorted(weeks)


def test_evaluate_runs_only_enabled_rules(policy_factory):
    pol = policy_factory(
        rule1_point_beyond_3sigma=False,
        rule2_nine_one_side=False,
        rule3_six_trending=False,
        rule5_two_of_three_beyond_2sigma=False,
    )
    assert evaluate(_series([99] * 9), _limits(), pol) == []


def test_only_rule1_enabled_gives_only_rule1(policy_factory):
    pol = policy_factory(
        rule2_nine_one_side=False,
        rule3_six_trending=False,
        rule5_two_of_three_beyond_2sigma=False,
    )
    signals = evaluate(_series([11, 1, 1]), _limits(), pol)
    assert {s.rule for s in signals} == {"rule1"}


def test_first_signal_week_returns_the_earliest():
    from raid_signal.model import Signal

    signals = [Signal("rule1", 20, ""), Signal("rule5", 16, ""), Signal("rule2", 25, "")]
    assert first_signal_week(signals) == 16


def test_first_signal_week_respects_the_on_or_after_floor():
    from raid_signal.model import Signal

    signals = [Signal("rule1", 5, ""), Signal("rule5", 16, "")]
    assert first_signal_week(signals, on_or_after=13) == 16


def test_first_signal_week_is_none_when_empty():
    assert first_signal_week([]) is None
