"""Turn a RAID event log into the two weekly series the charts need.

The log is one row per item (when it opened, when it closed, whether it was a
blocker). A control chart needs a regular time series, so this module rebuilds
two of them: how many items were opened in each week (a count of events, which a
Poisson c-chart fits), and how many items stood open at the end of each week (a
level, which an individuals chart fits). This is the pivot-table step a PM does
in Excel, written so the numbers are reproducible rather than clicked.

The reconstruction is done without a per-week Python loop over items: the open
backlog is a classic difference of two cumulative counts (opened-to-date minus
closed-to-date), which pandas computes directly and which stays correct when
items open and close out of order.
"""

from __future__ import annotations

import pandas as pd

from .model import RAID_TYPES, RaidItem, WeeklySeries


def load_raid_log(path: str) -> list[RaidItem]:
    """Read a RAID log CSV into validated RaidItem records.

    Validation is strict on load: an unknown RAID type, a negative week, or a
    close-before-open is rejected here so a malformed row never reaches the
    arithmetic and produces a confident wrong chart.
    """
    frame = pd.read_csv(path)
    required = {
        "item_id",
        "raid_type",
        "severity",
        "is_blocker",
        "opened_week",
        "closed_week",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"raid log missing columns: {sorted(missing)}")

    items: list[RaidItem] = []
    for row in frame.itertuples(index=False):
        raid_type = str(row.raid_type)
        if raid_type not in RAID_TYPES:
            raise ValueError(f"item {row.item_id}: unknown RAID type {raid_type!r}")
        opened = int(row.opened_week)
        if opened < 1:
            raise ValueError(f"item {row.item_id}: opened_week {opened} < 1")
        closed_raw = row.closed_week
        closed = None if pd.isna(closed_raw) else int(closed_raw)
        if closed is not None and closed < opened:
            raise ValueError(
                f"item {row.item_id}: closed_week {closed} before opened_week {opened}"
            )
        items.append(
            RaidItem(
                item_id=str(row.item_id),
                raid_type=raid_type,
                severity=int(row.severity),
                is_blocker=bool(row.is_blocker),
                opened_week=opened,
                closed_week=closed,
            )
        )
    if not items:
        raise ValueError("raid log is empty")
    return items


def program_weeks(items: list[RaidItem]) -> tuple[int, ...]:
    """The contiguous week axis, 1..max week seen in any open or close event."""
    last = max(
        max(i.opened_week for i in items),
        max((i.closed_week for i in items if i.closed_week is not None), default=0),
    )
    return tuple(range(1, last + 1))


def opened_per_week(items: list[RaidItem], blockers_only: bool) -> WeeklySeries:
    """Count of items opened in each week (the event series for the c-chart)."""
    weeks = program_weeks(items)
    pool = [i for i in items if i.is_blocker] if blockers_only else list(items)
    opened = pd.Series(0, index=list(weeks), dtype="int64")
    counts = pd.Series([i.opened_week for i in pool]).value_counts()
    for week, n in counts.items():
        opened.loc[int(week)] = int(n)
    name = "blockers_opened" if blockers_only else "items_opened"
    return WeeklySeries(name=name, weeks=weeks, values=tuple(float(v) for v in opened.to_numpy()))


def open_backlog_per_week(items: list[RaidItem]) -> WeeklySeries:
    """Number of items open at the end of each week (the level for the XmR chart).

    Computed as cumulative opens minus cumulative closes rather than by testing
    every item against every week, so the cost is linear in weeks and the result
    is identical whether or not items were closed in opened order.
    """
    weeks = program_weeks(items)
    index = list(weeks)
    opens = pd.Series(0, index=index, dtype="int64")
    closes = pd.Series(0, index=index, dtype="int64")
    for item in items:
        opens.loc[item.opened_week] += 1
        if item.closed_week is not None and item.closed_week in opens.index:
            closes.loc[item.closed_week] += 1
    backlog = (opens.cumsum() - closes.cumsum()).clip(lower=0)
    return WeeklySeries(
        name="open_backlog",
        weeks=weeks,
        values=tuple(float(v) for v in backlog.to_numpy()),
    )
