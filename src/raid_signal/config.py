"""Load and validate the control policy.

Every tunable that changes whether a week is flagged lives in config/policy.toml
so a reviewer argues with the policy, not with a constant buried in control.py.
This module turns that file into a validated object and refuses a policy that
would silently misbehave (a baseline that runs backwards, a non-positive sigma),
because a bad policy should fail at load, not produce a confident wrong chart.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "policy.toml"


class ConfigError(ValueError):
    """Raised when the policy file is missing a key or holds an invalid value."""


@dataclass(frozen=True)
class Policy:
    baseline_start: int
    baseline_end: int
    sigma: float
    clamp_lower_to_zero: bool
    rule1_point_beyond_3sigma: bool
    rule2_nine_one_side: bool
    rule3_six_trending: bool
    rule5_two_of_three_beyond_2sigma: bool
    blockers_only_for_opened_chart: bool
    late_grace_weeks: int

    def baseline_weeks(self) -> range:
        """The inclusive baseline week range as a Python range."""
        return range(self.baseline_start, self.baseline_end + 1)


def _require(table: dict, section: str, key: str):
    try:
        return table[section][key]
    except KeyError as exc:
        raise ConfigError(f"policy is missing [{section}].{key}") from exc


def load_policy(path: str | Path | None = None) -> Policy:
    """Read policy.toml into a validated Policy, or raise ConfigError."""
    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    if not policy_path.exists():
        raise ConfigError(f"policy file not found: {policy_path}")

    with policy_path.open("rb") as handle:
        raw = tomllib.load(handle)

    policy = Policy(
        baseline_start=int(_require(raw, "baseline", "start_week")),
        baseline_end=int(_require(raw, "baseline", "end_week")),
        sigma=float(_require(raw, "limits", "sigma")),
        clamp_lower_to_zero=bool(_require(raw, "limits", "clamp_lower_to_zero")),
        rule1_point_beyond_3sigma=bool(_require(raw, "rules", "rule1_point_beyond_3sigma")),
        rule2_nine_one_side=bool(_require(raw, "rules", "rule2_nine_one_side")),
        rule3_six_trending=bool(_require(raw, "rules", "rule3_six_trending")),
        rule5_two_of_three_beyond_2sigma=bool(
            _require(raw, "rules", "rule5_two_of_three_beyond_2sigma")
        ),
        blockers_only_for_opened_chart=bool(
            _require(raw, "scope", "blockers_only_for_opened_chart")
        ),
        late_grace_weeks=int(_require(raw, "escalation", "late_grace_weeks")),
    )
    _validate(policy)
    return policy


def _validate(policy: Policy) -> None:
    if policy.baseline_start < 1:
        raise ConfigError("baseline.start_week must be >= 1")
    if policy.baseline_end < policy.baseline_start:
        raise ConfigError("baseline.end_week must be >= baseline.start_week")
    # A baseline of one week has no spread to estimate limits from.
    if policy.baseline_end - policy.baseline_start + 1 < 2:
        raise ConfigError("baseline must span at least 2 weeks to estimate limits")
    if policy.sigma <= 0:
        raise ConfigError("limits.sigma must be positive")
    if policy.late_grace_weeks < 0:
        raise ConfigError("escalation.late_grace_weeks must be >= 0")
