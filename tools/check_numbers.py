"""Fail the build when a document quotes a figure the code no longer produces.

Loads docs/metrics.json, then for every checked document verifies that each
metric's anchor phrase appears with the current value substituted in. Anchors
are matched, not bare digits, so a stale sentence around a correct number is
caught and a coincidental digit elsewhere is not (receipts rules 1 to 3).

Also runs the reverse check: any number in the README that matches no metric is
reported, because that is a number nothing re-measures. Fenced code, inline code
and HTML attributes are excluded, because an example invocation may legitimately
contain a made-up count.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "docs" / "metrics.json"


def _fmt(value) -> str:
    if isinstance(value, float):
        # Match how the number is written in prose: trim a trailing .0 so an
        # integer-valued float anchors as "30", but keep real decimals.
        return f"{value:.0f}" if value.is_integer() else f"{value}"
    return str(value)


def _strip_uncheckable(text: str) -> str:
    """Remove fenced code, inline code, HTML attributes and reference labels.

    Besides code and attributes, this drops markdown link destinations and
    identifier tokens such as ADR-001 and exp03, because a reference label is not
    a quoted figure and flagging it trains the reader to ignore the reverse
    check.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r'=\s*"[^"]*"', " ", text)
    text = re.sub(r"=\s*'[^']*'", " ", text)
    text = re.sub(r"\]\([^)]*\)", "] ", text)  # markdown link destinations
    text = re.sub(r"[A-Za-z]+-?\d+", " ", text)  # ADR-001, exp03, rule3, week-ids
    return text


def check_document(path: Path, metrics: dict, anchors: dict) -> list[str]:
    failures: list[str] = []
    raw = path.read_text(encoding="utf-8")
    text = _strip_uncheckable(raw)
    for key, value in metrics.items():
        phrases = anchors.get(key)
        if not phrases:
            failures.append(f"{path.name}: metric {key} has no anchor phrase")
            continue
        rendered = [p.format(_fmt(value)) for p in phrases]
        if not any(phrase in text for phrase in rendered):
            # Only a failure if the document actually mentions this metric at
            # all; a document need not quote every metric. We treat "mentions"
            # as: at least one anchor's non-number words appear.
            skeleton_hit = any(
                re.sub(r"\{\}", "", p).strip() in text for p in phrases
            )
            if skeleton_hit:
                failures.append(
                    f"{path.name}: {key} expected one of {rendered!r} but none found "
                    f"(value {_fmt(value)})"
                )
    return failures


def reverse_check(path: Path, metrics: dict) -> list[str]:
    """Numbers in the doc that match no metric value (informational warnings)."""
    text = _strip_uncheckable(path.read_text(encoding="utf-8"))
    known = {_fmt(v) for v in metrics.values()}
    # Allow a small set of structural numbers that are not metrics.
    allowed = {"0", "1", "2", "3", "5", "9", "2026"}
    warnings: list[str] = []
    for match in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", text):
        if match not in known and match not in allowed:
            warnings.append(f"{path.name}: unverified number {match!r}")
    return warnings


def main() -> int:
    if not METRICS.exists():
        print("check_numbers: docs/metrics.json missing; run collect_metrics.py", file=sys.stderr)
        return 1
    payload = json.loads(METRICS.read_text())
    metrics = payload["metrics"]
    anchors = payload["anchors"]

    failures: list[str] = []
    for rel in payload["checked_documents"]:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"{rel}: checked document is missing")
            continue
        failures += check_document(path, metrics, anchors)

    warnings = reverse_check(ROOT / "README.md", metrics) if (ROOT / "README.md").exists() else []

    for w in warnings:
        print(f"warning: {w}")
    if failures:
        print("\ncheck_numbers: FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"check_numbers: OK ({len(metrics)} metrics across {len(payload['checked_documents'])} docs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
