"""Shared loading for the experiments so each one reads the same fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from raid_signal import aggregate, detect
from raid_signal.config import load_policy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "experiments"


def load(real: bool = True):
    policy = load_policy()
    name = "raid_log.csv" if real else "raid_log_stable.csv"
    items = aggregate.load_raid_log(str(ROOT / "data" / name))
    return policy, items


def escalation_week() -> int:
    return detect.load_escalations(str(ROOT / "data" / "escalations.csv"))["blocker_spike"]


def write(name: str, payload: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
