"""Nelson run rules: the signals a single out-of-limit point misses.

A point beyond three sigma (rule 1) is the slowest useful signal, because a slow
upward drift can sit inside the limits for many weeks while every week is a
little worse than the last. The run rules read the sequence, not the single
point, so they fire on a sustained shift before it breaches. Each rule enabled
buys earlier warning at the cost of more false alarms; experiments/exp02 and
exp03 price that trade.

Every rule returns the weeks at which its pattern completes. A rule fires at the
week that closes the run, which is the first week a human could have acted on it.
"""

from __future__ import annotations

import numpy as np

from .config import Policy
from .model import ControlLimits, Signal, WeeklySeries

RULE2_RUN = 9  # points in a row on one side of the centre
RULE3_RUN = 6  # points in a row all increasing or all decreasing
RULE5_WINDOW = 3  # two of any three consecutive points beyond two sigma


def _rule1(series: WeeklySeries, limits: ControlLimits) -> list[Signal]:
    out: list[Signal] = []
    for week, value in zip(series.weeks, series.values):
        if value > limits.upper or value < limits.lower:
            side = "above" if value > limits.upper else "below"
            out.append(
                Signal("rule1", week, f"point {value:g} is {side} the 3-sigma limit")
            )
    return out


def _rule2(series: WeeklySeries, limits: ControlLimits) -> list[Signal]:
    """Nine points in a row on the same side of the centre line.

    A point exactly on the centre line belongs to neither side and breaks the
    run, so a flat series sitting on the mean does not fire this rule.
    """
    out: list[Signal] = []
    run_side = 0
    run_len = 0
    for week, value in zip(series.weeks, series.values):
        side = 1 if value > limits.center else (-1 if value < limits.center else 0)
        if side == 0:
            run_side, run_len = 0, 0
            continue
        if side == run_side:
            run_len += 1
        else:
            run_side, run_len = side, 1
        if run_len == RULE2_RUN:
            where = "above" if side == 1 else "below"
            out.append(Signal("rule2", week, f"9 points in a row {where} centre"))
    return out


def _rule3(series: WeeklySeries, limits: ControlLimits) -> list[Signal]:
    """Six points in a row all increasing or all decreasing.

    The comparison is strict: a week equal to the one before it is not movement,
    so it breaks both the increasing and the decreasing run. A non-strict
    comparison (treating a flat week as both an increase and a decrease) reports
    a trend across a plateau, which is the opposite of what this rule is for; see
    the war story in the README and test_rule3_regression.py.
    """
    out: list[Signal] = []
    values = series.values
    inc = 0
    dec = 0
    for i in range(1, len(values)):
        inc = inc + 1 if values[i] > values[i - 1] else 0
        dec = dec + 1 if values[i] < values[i - 1] else 0
        if inc + 1 == RULE3_RUN:
            out.append(Signal("rule3", series.weeks[i], "6 points trending up"))
        if dec + 1 == RULE3_RUN:
            out.append(Signal("rule3", series.weeks[i], "6 points trending down"))
    return out


def _rule5(series: WeeklySeries, limits: ControlLimits) -> list[Signal]:
    """Two of three consecutive points beyond two sigma on the same side."""
    out: list[Signal] = []
    weeks, values = series.weeks, series.values
    for i in range(RULE5_WINDOW - 1, len(values)):
        window = values[i - RULE5_WINDOW + 1 : i + 1]
        above = sum(1 for v in window if v > limits.two_sigma_upper)
        below = sum(1 for v in window if v < limits.two_sigma_lower)
        if above >= 2:
            out.append(Signal("rule5", weeks[i], "2 of 3 points beyond 2-sigma, high"))
        elif below >= 2:
            out.append(Signal("rule5", weeks[i], "2 of 3 points beyond 2-sigma, low"))
    return out


def evaluate(series: WeeklySeries, limits: ControlLimits, policy: Policy) -> list[Signal]:
    """Run every enabled rule and return the signals sorted by week then rule."""
    signals: list[Signal] = []
    if policy.rule1_point_beyond_3sigma:
        signals += _rule1(series, limits)
    if policy.rule2_nine_one_side:
        signals += _rule2(series, limits)
    if policy.rule3_six_trending:
        signals += _rule3(series, limits)
    if policy.rule5_two_of_three_beyond_2sigma:
        signals += _rule5(series, limits)
    signals.sort(key=lambda s: (s.week, s.rule))
    return signals


def first_signal_week(signals: list[Signal], on_or_after: int = 1) -> int | None:
    """The earliest week any signal fired at or after a given week, or None."""
    weeks = [s.week for s in signals if s.week >= on_or_after]
    return min(weeks) if weeks else None


def _dedupe_consecutive(values: tuple[float, ...]) -> np.ndarray:
    """Helper kept for experiments that need the distinct-level sequence."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    keep = np.concatenate(([True], np.diff(arr) != 0))
    return arr[keep]
