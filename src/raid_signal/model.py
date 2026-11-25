"""The small set of records the rest of the package passes around.

These exist so that a weekly series, a set of control limits and a fired signal
are named things with fixed fields rather than bare tuples or dict keys spelled
differently in two modules. The arithmetic lives elsewhere (control.py,
rules.py); this file only says what the arithmetic produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# RAID item types, kept as the four canonical letters so a typo in a CSV is
# rejected at load time rather than silently creating a fifth category.
RAID_TYPES = ("Risk", "Assumption", "Issue", "Dependency")


@dataclass(frozen=True)
class RaidItem:
    """One row of a RAID log.

    opened_week and closed_week are 1-indexed program weeks. closed_week is None
    while the item is still open. is_blocker marks the items the escalation
    process actually reacts to; the opened-count chart can be filtered to these.
    """

    item_id: str
    raid_type: str
    severity: int
    is_blocker: bool
    opened_week: int
    closed_week: int | None

    def is_open_at(self, week: int) -> bool:
        """True if the item was open at the end of the given week.

        Open means opened on or before this week and not yet closed, or closed
        in a strictly later week. An item opened and closed in the same week is
        counted as resolved by week end, so it does not inflate the backlog.
        """
        if self.opened_week > week:
            return False
        if self.closed_week is None:
            return True
        return self.closed_week > week


@dataclass(frozen=True)
class WeeklySeries:
    """A single metric observed once per week, with the weeks it belongs to.

    values[i] is the measurement for weeks[i]. Keeping the week labels next to
    the values means a signal can report the real program week it fired in, not
    an array index a reader has to translate.
    """

    name: str
    weeks: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.weeks) != len(self.values):
            raise ValueError(
                f"series {self.name!r}: {len(self.weeks)} weeks but "
                f"{len(self.values)} values"
            )


@dataclass(frozen=True)
class ControlLimits:
    """The frozen centre line and limits for one chart.

    center is the baseline mean. upper and lower are the control limits. For a
    Poisson count chart the lower limit is often negative and clamped to zero;
    lower_clamped records whether that clamp was applied, because a clamped
    lower limit makes the chart blind to improvement (ADR-004).
    """

    chart: str
    center: float
    upper: float
    lower: float
    sigma: float
    lower_clamped: bool
    two_sigma_upper: float
    two_sigma_lower: float


@dataclass(frozen=True)
class Signal:
    """One rule firing in one week.

    rule is the Nelson rule identifier. week is the program week it fired in.
    detail is a short human-readable reason, carried so the report and the CLI
    can explain the signal without re-deriving it.
    """

    rule: str
    week: int
    detail: str


@dataclass
class DetectionResult:
    """Everything a caller needs after an analysis run.

    Grouped into one object so the CLI, the report and the experiments all read
    the same fields rather than three functions returning three shapes.
    """

    opened_series: WeeklySeries
    backlog_series: WeeklySeries
    opened_limits: ControlLimits
    backlog_limits: ControlLimits
    signals: list[Signal] = field(default_factory=list)
    backlog_signals: list[Signal] = field(default_factory=list)
    escalation_week: int | None = None
    first_signal_week: int | None = None
    lead_weeks: int | None = None

    @property
    def in_control(self) -> bool:
        """True when no opened-count signal fired in the reporting window.

        The gate rests on the opened-count chart only; backlog signals are a
        secondary diagnostic and deliberately do not trip the gate (ADR-003).
        """
        return len(self.signals) == 0
