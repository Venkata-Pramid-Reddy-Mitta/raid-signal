"""Properties of the data records."""

from __future__ import annotations

import pytest

from raid_signal.model import ControlLimits, DetectionResult, RaidItem, Signal, WeeklySeries


def _item(opened, closed):
    return RaidItem("X-1", "Issue", 3, True, opened, closed)


def test_an_open_ended_item_is_open_from_its_opened_week_onward():
    it = _item(3, None)
    assert not it.is_open_at(2)
    assert it.is_open_at(3)
    assert it.is_open_at(99)


def test_an_item_is_closed_in_weeks_from_its_close_week_on():
    it = _item(3, 5)
    assert it.is_open_at(4)
    assert not it.is_open_at(5)
    assert not it.is_open_at(6)


def test_an_item_opened_and_closed_in_the_same_week_is_never_counted_open():
    it = _item(4, 4)
    assert not it.is_open_at(4)
    assert not it.is_open_at(3)


def test_item_open_exactly_on_the_week_before_close():
    it = _item(2, 6)
    assert it.is_open_at(5)
    assert not it.is_open_at(6)


def test_weekly_series_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        WeeklySeries("s", (1, 2, 3), (1.0, 2.0))


def test_weekly_series_keeps_weeks_and_values_together():
    s = WeeklySeries("s", (4, 5), (1.0, 9.0))
    assert s.weeks == (4, 5)
    assert s.values == (1.0, 9.0)


def _limits():
    return ControlLimits("c", 1.0, 4.0, 0.0, 3.0, True, 3.0, 0.0)


def test_detection_result_is_in_control_with_no_opened_signals():
    r = DetectionResult(
        opened_series=WeeklySeries("o", (1,), (1.0,)),
        backlog_series=WeeklySeries("b", (1,), (1.0,)),
        opened_limits=_limits(),
        backlog_limits=_limits(),
        signals=[],
        backlog_signals=[Signal("rule1", 5, "x")],
    )
    assert r.in_control is True


def test_detection_result_out_of_control_when_an_opened_signal_fired():
    r = DetectionResult(
        opened_series=WeeklySeries("o", (1,), (1.0,)),
        backlog_series=WeeklySeries("b", (1,), (1.0,)),
        opened_limits=_limits(),
        backlog_limits=_limits(),
        signals=[Signal("rule1", 5, "x")],
    )
    assert r.in_control is False


def test_backlog_signals_do_not_affect_the_gate():
    r = DetectionResult(
        opened_series=WeeklySeries("o", (1,), (1.0,)),
        backlog_series=WeeklySeries("b", (1,), (1.0,)),
        opened_limits=_limits(),
        backlog_limits=_limits(),
        signals=[],
        backlog_signals=[Signal("rule5", 7, "y"), Signal("rule2", 9, "z")],
    )
    assert r.in_control is True
