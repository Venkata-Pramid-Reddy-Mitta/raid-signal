"""raid-signal: statistical process control over a RAID log.

A RAID log (Risks, Assumptions, Issues, Dependencies) is a list. A raw count of
open items, or of blockers opened this week, cannot say whether this week is
normal churn or the start of trouble, because a bare count carries no baseline.
This package supplies the baseline the list structurally lacks: control limits
computed from the process's own history, plus run rules that catch a drift
before any single point breaches a limit.
"""

__version__ = "0.1.0"
