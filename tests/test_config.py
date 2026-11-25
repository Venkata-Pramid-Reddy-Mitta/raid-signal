"""Policy loading and validation."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from raid_signal.config import ConfigError, Policy, load_policy

VALID = """\
[baseline]
start_week = 1
end_week = 12
[limits]
sigma = 3.0
clamp_lower_to_zero = true
[rules]
rule1_point_beyond_3sigma = true
rule2_nine_one_side = true
rule3_six_trending = true
rule5_two_of_three_beyond_2sigma = true
[scope]
blockers_only_for_opened_chart = true
[escalation]
late_grace_weeks = 0
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "policy.toml"
    path.write_text(textwrap.dedent(text))
    return path


def test_the_committed_policy_loads(repo_root):
    policy = load_policy(repo_root / "config" / "policy.toml")
    assert isinstance(policy, Policy)
    assert policy.baseline_end >= policy.baseline_start


def test_load_reads_every_field(tmp_path):
    policy = load_policy(_write(tmp_path, VALID))
    assert policy.sigma == 3.0
    assert policy.clamp_lower_to_zero is True
    assert policy.blockers_only_for_opened_chart is True
    assert policy.late_grace_weeks == 0


def test_baseline_weeks_is_an_inclusive_range(tmp_path):
    policy = load_policy(_write(tmp_path, VALID))
    assert list(policy.baseline_weeks()) == list(range(1, 13))


def test_missing_file_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_policy(tmp_path / "nope.toml")


def test_missing_key_names_the_section_and_key(tmp_path):
    broken = VALID.replace("sigma = 3.0\n", "")
    with pytest.raises(ConfigError) as exc:
        load_policy(_write(tmp_path, broken))
    assert "limits" in str(exc.value) and "sigma" in str(exc.value)


@pytest.mark.parametrize(
    "edit",
    [
        ("start_week = 1", "start_week = 0"),
        ("end_week = 12", "end_week = 1"),  # one-week window
    ],
)
def test_invalid_baseline_rejected(tmp_path, edit):
    old, new = edit
    with pytest.raises(ConfigError):
        load_policy(_write(tmp_path, VALID.replace(old, new)))


def test_end_before_start_is_rejected(tmp_path):
    text = VALID.replace("start_week = 1", "start_week = 8")  # start 8, end 12 ok... flip it
    text = text.replace("end_week = 12", "end_week = 3")  # now start 8 > end 3
    with pytest.raises(ConfigError) as exc:
        load_policy(_write(tmp_path, text))
    assert "end_week must be >= baseline.start_week" in str(exc.value)


def test_single_week_baseline_rejected(tmp_path):
    text = VALID.replace("start_week = 1", "start_week = 5")
    text = text.replace("end_week = 12", "end_week = 5")
    with pytest.raises(ConfigError) as exc:
        load_policy(_write(tmp_path, text))
    assert "at least 2 weeks" in str(exc.value)


def test_non_positive_sigma_rejected(tmp_path):
    with pytest.raises(ConfigError):
        load_policy(_write(tmp_path, VALID.replace("sigma = 3.0", "sigma = 0")))


def test_negative_grace_rejected(tmp_path):
    broken = VALID.replace("late_grace_weeks = 0", "late_grace_weeks = -1")
    with pytest.raises(ConfigError):
        load_policy(_write(tmp_path, broken))
