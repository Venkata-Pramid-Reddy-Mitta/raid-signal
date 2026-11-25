"""Generate the committed RAID fixtures, deterministically.

Two programs are generated from one seeded generator so a reviewer reproduces
every published number with one command and no network:

* data/raid_log.csv       a real program: a stable first quarter, then a blocker
                          spike that a human escalates at a recorded week.
* data/raid_log_stable.csv a genuinely in-control program with no shift, used to
                          measure how often the charts fire when nothing is
                          wrong (the false-alarm cost).
* data/escalations.csv    the week a human manually escalated the spike.

The generator is seeded and writes integer events, so the fixtures are byte
stable across machines. Nothing here runs at analysis time; the CSVs are what
the package reads.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BASELINE_WEEKS = 12
TOTAL_WEEKS = 30
ESCALATION_WEEK = 20  # the week a human escalated the spike in the real program


def _dwell(rng: np.random.Generator) -> int:
    """How many weeks an item stays open: 1 + Geometric, floored small."""
    return 1 + int(rng.geometric(p=0.45))


def _emit_items(
    rng: np.random.Generator,
    opens_blocker: list[int],
    opens_other: list[int],
    prefix: str,
) -> list[dict]:
    items: list[dict] = []
    counter = 0
    for week in range(1, TOTAL_WEEKS + 1):
        n_block = opens_blocker[week - 1]
        n_other = opens_other[week - 1]
        for _ in range(n_block):
            counter += 1
            dwell = _dwell(rng)
            closed = week + dwell
            items.append(
                {
                    "item_id": f"{prefix}-{counter:04d}",
                    "raid_type": "Issue",
                    "severity": int(rng.integers(3, 6)),
                    "is_blocker": True,
                    "opened_week": week,
                    "closed_week": closed if closed <= TOTAL_WEEKS else "",
                }
            )
        for _ in range(n_other):
            counter += 1
            dwell = _dwell(rng)
            closed = week + dwell
            raid_type = rng.choice(["Risk", "Assumption", "Dependency", "Issue"])
            items.append(
                {
                    "item_id": f"{prefix}-{counter:04d}",
                    "raid_type": str(raid_type),
                    "severity": int(rng.integers(1, 5)),
                    "is_blocker": False,
                    "opened_week": week,
                    "closed_week": closed if closed <= TOTAL_WEEKS else "",
                }
            )
    return items


def _stable_opens(rng: np.random.Generator) -> tuple[list[int], list[int]]:
    """A flat, in-control opening process for every week."""
    blocker = [int(rng.poisson(1.0)) for _ in range(TOTAL_WEEKS)]
    other = [int(rng.poisson(2.2)) for _ in range(TOTAL_WEEKS)]
    return blocker, other


def _spiking_opens(rng: np.random.Generator) -> tuple[list[int], list[int]]:
    """Stable for the baseline, then a blocker rate that ramps into a spike."""
    blocker: list[int] = []
    other = [int(rng.poisson(2.2)) for _ in range(TOTAL_WEEKS)]
    for week in range(1, TOTAL_WEEKS + 1):
        if week <= BASELINE_WEEKS:
            lam = 1.0
        elif week <= 15:
            lam = 1.6  # the drift begins quietly, inside the 3-sigma limit
        elif week <= 19:
            lam = 3.6  # the spike proper
        else:
            lam = 4.8  # still elevated when the human finally escalates
        blocker.append(int(rng.poisson(lam)))
    return blocker, other


def _write_items(path: Path, items: list[dict]) -> None:
    fields = ["item_id", "raid_type", "severity", "is_blocker", "opened_week", "closed_week"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow(item)


def main() -> None:
    DATA.mkdir(exist_ok=True)

    rng = np.random.default_rng(20260411)
    stable_block, stable_other = _stable_opens(rng)
    stable_items = _emit_items(rng, stable_block, stable_other, prefix="S")
    _write_items(DATA / "raid_log_stable.csv", stable_items)

    # A fresh seed for the real program so the two fixtures are independent.
    rng2 = np.random.default_rng(76540123)
    spike_block, spike_other = _spiking_opens(rng2)
    spike_items = _emit_items(rng2, spike_block, spike_other, prefix="R")
    _write_items(DATA / "raid_log.csv", spike_items)

    with (DATA / "escalations.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["label", "escalated_week"])
        writer.writerow(["blocker_spike", ESCALATION_WEEK])

    print(f"stable items: {len(stable_items)}")
    print(f"real items:   {len(spike_items)}")
    print(f"escalation week: {ESCALATION_WEEK}")


if __name__ == "__main__":
    main()
