"""The control-limit arithmetic. This is the part a RAID list does not have.

Two charts, because the two series have different statistics:

* The opened-count series is a count of events per week. Under a stable process
  those counts are approximately Poisson, whose variance equals its mean, so the
  standard deviation is the square root of the mean and the limits are
  center +/- sigma*sqrt(center). This is the c-chart.

* The backlog series is a running level, not a count of independent events, so
  its week-to-week variation is estimated from the average moving range rather
  than from a Poisson assumption. This is the individuals (XmR) chart, with the
  2.66 constant that converts an average moving range of two consecutive points
  into a three-sigma distance.

The limits are computed once, on a declared baseline window, and then frozen
(ADR-005). No SPC library is used: the formulas are closed form and author-built
so every number is defensible line by line and moves with nothing but the data.
"""

from __future__ import annotations

import numpy as np

from .config import Policy
from .model import ControlLimits, WeeklySeries

# d2 for a moving range of n=2 consecutive observations. 3/d2 = 3/1.128 = 2.66,
# the standard individuals-chart constant that turns the average moving range
# into a three-sigma half-width.
_XMR_CONSTANT = 2.66
# Upper control limit factor for the moving-range chart itself (D4 at n=2).
_MR_UPPER_FACTOR = 3.267


def _baseline_slice(series: WeeklySeries, policy: Policy) -> np.ndarray:
    """The baseline values, or an error if the window falls outside the data."""
    wanted = set(policy.baseline_weeks())
    picked = [v for w, v in zip(series.weeks, series.values) if w in wanted]
    if len(picked) < 2:
        raise ValueError(
            f"series {series.name!r} has {len(picked)} weeks inside the baseline "
            f"{policy.baseline_start}..{policy.baseline_end}; need at least 2"
        )
    return np.asarray(picked, dtype=float)


def c_chart_limits(series: WeeklySeries, policy: Policy) -> ControlLimits:
    """Poisson count-chart limits frozen on the baseline window.

    The lower limit is clamped to zero when it goes negative (the usual case for
    a low count), and the clamp is recorded, because a clamped lower limit means
    a drop in the count can never be a signal: the chart is blind to improvement.
    """
    baseline = _baseline_slice(series, policy)
    center = float(baseline.mean())
    spread = float(np.sqrt(center))
    upper = center + policy.sigma * spread
    raw_lower = center - policy.sigma * spread
    two_upper = center + 2.0 * spread
    two_lower = center - 2.0 * spread
    clamped = policy.clamp_lower_to_zero and raw_lower < 0.0
    lower = 0.0 if clamped else raw_lower
    return ControlLimits(
        chart="c",
        center=center,
        upper=upper,
        lower=lower,
        sigma=policy.sigma,
        lower_clamped=clamped,
        two_sigma_upper=two_upper,
        two_sigma_lower=max(0.0, two_lower) if policy.clamp_lower_to_zero else two_lower,
    )


def xmr_limits(series: WeeklySeries, policy: Policy) -> ControlLimits:
    """Individuals-chart limits from the baseline average moving range.

    The spread is 2.66 times the average of the absolute differences between
    consecutive baseline points, which is the three-sigma half-width for an
    individuals chart. sigma here is reported as that half-width so the report
    can draw a two-sigma band consistently with the c-chart.
    """
    baseline = _baseline_slice(series, policy)
    center = float(baseline.mean())
    moving_ranges = np.abs(np.diff(baseline))
    mr_bar = float(moving_ranges.mean()) if moving_ranges.size else 0.0
    half_width = _XMR_CONSTANT * mr_bar
    one_sigma = half_width / 3.0
    upper = center + half_width
    raw_lower = center - half_width
    clamped = policy.clamp_lower_to_zero and raw_lower < 0.0
    lower = 0.0 if clamped else raw_lower
    two_lower_raw = center - 2.0 * one_sigma
    return ControlLimits(
        chart="xmr",
        center=center,
        upper=upper,
        lower=lower,
        sigma=policy.sigma,
        lower_clamped=clamped,
        two_sigma_upper=center + 2.0 * one_sigma,
        two_sigma_lower=max(0.0, two_lower_raw) if policy.clamp_lower_to_zero else two_lower_raw,
        # mr_bar is folded into half_width above; it is not stored separately
        # because nothing downstream needs the moving-range chart's own limit.
    )


def moving_range_upper(series: WeeklySeries, policy: Policy) -> float:
    """Upper limit of the moving-range chart (D4 * MR_bar), for completeness."""
    baseline = _baseline_slice(series, policy)
    moving_ranges = np.abs(np.diff(baseline))
    mr_bar = float(moving_ranges.mean()) if moving_ranges.size else 0.0
    return _MR_UPPER_FACTOR * mr_bar
