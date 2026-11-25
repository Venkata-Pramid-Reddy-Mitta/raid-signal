"""Rebuilding the weekly series from the event log."""

from __future__ import annotations

import pytest

from raid_signal.aggregate import (
    load_raid_log,
    open_backlog_per_week,
    opened_per_week,
    program_weeks,
)


def test_program_weeks_runs_from_one_to_the_last_event(make_item):
    # The axis extends to the latest event of any kind, including a close in a
    # week later than any item opened.
    items = [make_item("A", 1, 3), make_item("B", 2, None)]
    assert program_weeks(items) == (1, 2, 3)


def test_program_weeks_includes_the_latest_close(make_item):
    items = [make_item("A", 1, 7)]
    assert program_weeks(items)[-1] == 7


def test_opened_per_week_counts_opens_in_each_week(make_item):
    items = [make_item("A", 1), make_item("B", 1), make_item("C", 3)]
    series = opened_per_week(items, blockers_only=False)
    assert series.values == (2.0, 0.0, 1.0)


def test_opened_per_week_blockers_only_filters_non_blockers(make_item):
    items = [make_item("A", 1, blocker=True), make_item("B", 1, blocker=False)]
    series = opened_per_week(items, blockers_only=True)
    assert series.values[0] == 1.0
    assert series.name == "blockers_opened"


def test_opened_per_week_all_items_names_itself(make_item):
    series = opened_per_week([make_item("A", 1, blocker=False)], blockers_only=False)
    assert series.name == "items_opened"


def test_backlog_is_cumulative_opens_minus_closes(make_item):
    # Open three in week 1, close one in week 2, one in week 3.
    items = [make_item("A", 1, 2), make_item("B", 1, 3), make_item("C", 1, None)]
    series = open_backlog_per_week(items)
    assert series.values == (3.0, 2.0, 1.0)


def test_backlog_is_correct_when_items_close_out_of_order(make_item):
    # The later-opened item closes first; the difference-of-cumulatives still holds.
    items = [make_item("A", 1, 4), make_item("B", 2, 3)]
    series = open_backlog_per_week(items)
    assert series.values == (1.0, 2.0, 1.0, 0.0)


def test_backlog_never_goes_negative(make_item):
    items = [make_item("A", 1, 1)]  # opened and closed same week
    series = open_backlog_per_week(items)
    assert all(v >= 0 for v in series.values)


REQUIRED_HEADER = "item_id,raid_type,severity,is_blocker,opened_week,closed_week\n"


def _csv(tmp_path, rows: str):
    path = tmp_path / "log.csv"
    path.write_text(REQUIRED_HEADER + rows)
    return str(path)


def test_load_accepts_a_blank_closed_week_as_open(tmp_path):
    items = load_raid_log(_csv(tmp_path, "A,Issue,3,True,1,\n"))
    assert items[0].closed_week is None


def test_load_rejects_missing_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("item_id,opened_week\nA,1\n")
    with pytest.raises(ValueError):
        load_raid_log(str(bad))


def test_load_rejects_unknown_raid_type(tmp_path):
    with pytest.raises(ValueError):
        load_raid_log(_csv(tmp_path, "A,Nonsense,3,True,1,3\n"))


def test_load_rejects_week_below_one(tmp_path):
    with pytest.raises(ValueError):
        load_raid_log(_csv(tmp_path, "A,Issue,3,True,0,3\n"))


def test_load_rejects_close_before_open(tmp_path):
    with pytest.raises(ValueError):
        load_raid_log(_csv(tmp_path, "A,Issue,3,True,5,3\n"))


def test_load_rejects_an_empty_log(tmp_path):
    with pytest.raises(ValueError):
        load_raid_log(_csv(tmp_path, ""))


@pytest.mark.parametrize("raid_type", ["Risk", "Assumption", "Issue", "Dependency"])
def test_load_accepts_every_canonical_raid_type(tmp_path, raid_type):
    items = load_raid_log(_csv(tmp_path, f"A,{raid_type},3,False,1,\n"))
    assert items[0].raid_type == raid_type
