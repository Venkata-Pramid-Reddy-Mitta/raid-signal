"""The control-limit arithmetic, checked against hand computation."""

from __future__ import annotations

import math

import pytest

from raid_signal.control import c_chart_limits, moving_range_upper, xmr_limits
from raid_signal.model import WeeklySeries


def _series(values, start=1):
    weeks = tuple(range(start, start + len(values)))
    return WeeklySeries("s", weeks, tuple(float(v) for v in values))


def test_c_chart_center_is_the_baseline_mean(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4)
    limits = c_chart_limits(_series([2, 2, 2, 2, 9, 9]), pol)
    assert limits.center == pytest.approx(2.0)


def test_c_chart_upper_limit_is_center_plus_three_root_center(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4)
    limits = c_chart_limits(_series([4, 4, 4, 4]), pol)
    assert limits.upper == pytest.approx(4 + 3 * math.sqrt(4))


def test_c_chart_lower_limit_clamps_to_zero_and_records_it(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4, clamp_lower_to_zero=True)
    limits = c_chart_limits(_series([1, 1, 1, 1]), pol)
    assert limits.lower == 0.0
    assert limits.lower_clamped is True


def test_c_chart_lower_limit_can_stay_negative_when_clamp_is_off(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4, clamp_lower_to_zero=False)
    limits = c_chart_limits(_series([1, 1, 1, 1]), pol)
    assert limits.lower < 0.0
    assert limits.lower_clamped is False


def test_c_chart_two_sigma_band_is_center_plus_two_root_center(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4)
    limits = c_chart_limits(_series([9, 9, 9, 9]), pol)
    assert limits.two_sigma_upper == pytest.approx(9 + 2 * 3.0)


def test_c_chart_sigma_multiplier_widens_the_limit(policy_factory):
    narrow = c_chart_limits(_series([4, 4, 4, 4]), policy_factory(baseline_end=4, sigma=2.0))
    wide = c_chart_limits(_series([4, 4, 4, 4]), policy_factory(baseline_end=4, sigma=3.0))
    assert wide.upper > narrow.upper


def test_xmr_center_is_the_baseline_mean(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=5)
    limits = xmr_limits(_series([10, 12, 10, 12, 11]), pol)
    assert limits.center == pytest.approx(11.0)


def test_xmr_half_width_is_2_66_times_mean_moving_range(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=5)
    values = [10, 12, 10, 12, 11]
    limits = xmr_limits(_series(values), pol)
    mrs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mr_bar = sum(mrs) / len(mrs)
    assert limits.upper - limits.center == pytest.approx(2.66 * mr_bar)


def test_xmr_lower_limit_clamps_when_it_would_go_negative(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4, clamp_lower_to_zero=True)
    limits = xmr_limits(_series([1, 5, 1, 5]), pol)
    assert limits.lower == 0.0
    assert limits.lower_clamped is True


def test_moving_range_upper_is_d4_times_mr_bar(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=3)
    values = [4, 8, 4]
    mr_bar = (abs(8 - 4) + abs(4 - 8)) / 2
    assert moving_range_upper(_series(values), pol) == pytest.approx(3.267 * mr_bar)


def test_a_baseline_outside_the_data_is_an_error(policy_factory):
    pol = policy_factory(baseline_start=50, baseline_end=60)
    with pytest.raises(ValueError):
        c_chart_limits(_series([1, 2, 3]), pol)


def test_limits_depend_only_on_baseline_not_on_later_weeks(policy_factory):
    pol = policy_factory(baseline_start=1, baseline_end=4)
    quiet = c_chart_limits(_series([2, 2, 2, 2, 2, 2]), pol)
    spiky = c_chart_limits(_series([2, 2, 2, 2, 50, 99]), pol)
    assert quiet.upper == pytest.approx(spiky.upper)
