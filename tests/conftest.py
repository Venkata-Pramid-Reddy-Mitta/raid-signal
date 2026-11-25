"""Shared fixtures: a policy factory and small synthetic RAID logs.

The synthetic builders keep the unit tests independent of the committed data
fixtures, so a test for the moving-range maths does not quietly depend on the
generator. The committed fixtures get their own test module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from raid_signal.config import Policy
from raid_signal.model import RaidItem

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def policy_factory():
    def make(**overrides) -> Policy:
        base = dict(  # noqa: C408 keyword form reads better for a long override set
            baseline_start=1,
            baseline_end=12,
            sigma=3.0,
            clamp_lower_to_zero=True,
            rule1_point_beyond_3sigma=True,
            rule2_nine_one_side=True,
            rule3_six_trending=True,
            rule5_two_of_three_beyond_2sigma=True,
            blockers_only_for_opened_chart=True,
            late_grace_weeks=0,
        )
        base.update(overrides)
        return Policy(**base)

    return make


@pytest.fixture
def policy(policy_factory):
    return policy_factory()


def item(item_id, opened, closed=None, blocker=True, raid_type="Issue", severity=3):
    return RaidItem(
        item_id=item_id,
        raid_type=raid_type,
        severity=severity,
        is_blocker=blocker,
        opened_week=opened,
        closed_week=closed,
    )


@pytest.fixture
def make_item():
    return item


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
