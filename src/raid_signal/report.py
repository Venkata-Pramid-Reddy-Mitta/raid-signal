"""Render a DetectionResult to a self-contained HTML report with an SVG chart.

The chart is drawn by hand as SVG rather than with a plotting library so the
report is deterministic to the pixel (a reviewer gets the same bytes on any
machine) and carries no runtime dependency beyond the standard library. The SVG
draws the control chart a PM would recognise: the centre line, the upper limit,
the two-sigma band, the weekly points, and a marker where the human escalated.

The verdict badge gets an explicit colour and a matching text colour so the
screenshot tool can read its computed style back and fail if it ever renders
invisibly (see tools/capture_screenshots.py and ADR notes on evidence).
"""

from __future__ import annotations

import html
from pathlib import Path

from .model import ControlLimits, DetectionResult, WeeklySeries

_W = 820
_H = 320
_PAD_L = 48
_PAD_R = 24
_PAD_T = 24
_PAD_B = 40


def _scale(series: WeeklySeries, limits: ControlLimits, escalation_week: int | None):
    weeks = series.weeks
    top = max(max(series.values, default=1.0), limits.upper) * 1.12 + 1.0
    plot_w = _W - _PAD_L - _PAD_R
    plot_h = _H - _PAD_T - _PAD_B
    wmin, wmax = weeks[0], weeks[-1]
    span = max(1, wmax - wmin)

    def x(week: int) -> float:
        return _PAD_L + (week - wmin) / span * plot_w

    def y(value: float) -> float:
        return _PAD_T + (1 - value / top) * plot_h

    return x, y, top


def control_chart_svg(result: DetectionResult) -> str:
    """Draw the opened-count c-chart as a standalone SVG string."""
    series = result.opened_series
    limits = result.opened_limits
    x, y, _ = _scale(series, limits, result.escalation_week)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="Verdana,Arial,sans-serif">',
        f'<rect x="0" y="0" width="{_W}" height="{_H}" fill="#ffffff"/>',
    ]

    # Limit lines.
    def hline(value: float, colour: str, dash: str, label: str) -> None:
        yy = y(value)
        parts.append(
            f'<line x1="{_PAD_L}" y1="{yy:.1f}" x2="{_W - _PAD_R}" y2="{yy:.1f}" '
            f'stroke="{colour}" stroke-width="1.2" stroke-dasharray="{dash}"/>'
        )
        parts.append(
            f'<text x="{_W - _PAD_R:.0f}" y="{yy - 3:.1f}" font-size="10" '
            f'fill="{colour}" text-anchor="end">{html.escape(label)}</text>'
        )

    hline(limits.upper, "#c0392b", "4 3", f"UCL {limits.upper:.2f}")
    hline(limits.two_sigma_upper, "#e67e22", "2 3", f"2s {limits.two_sigma_upper:.2f}")
    hline(limits.center, "#2c3e50", "0", f"CL {limits.center:.2f}")
    # The clamped lower limit is drawn so the blindness to improvement is visible.
    low_label = "LCL 0 (clamped)" if limits.lower_clamped else f"LCL {limits.lower:.2f}"
    hline(limits.lower, "#7f8c8d", "4 3", low_label)

    # Escalation marker.
    if result.escalation_week is not None:
        ex = x(result.escalation_week)
        parts.append(
            f'<line x1="{ex:.1f}" y1="{_PAD_T}" x2="{ex:.1f}" y2="{_H - _PAD_B}" '
            f'stroke="#8e44ad" stroke-width="1.5" stroke-dasharray="1 3"/>'
        )
        parts.append(
            f'<text x="{ex + 3:.1f}" y="{_PAD_T + 10:.0f}" font-size="10" '
            f'fill="#8e44ad">escalated w{result.escalation_week}</text>'
        )

    # First-signal marker.
    if result.first_signal_week is not None:
        sx = x(result.first_signal_week)
        parts.append(
            f'<line x1="{sx:.1f}" y1="{_PAD_T}" x2="{sx:.1f}" y2="{_H - _PAD_B}" '
            f'stroke="#16a085" stroke-width="1.5" stroke-dasharray="1 3"/>'
        )
        parts.append(
            f'<text x="{sx + 3:.1f}" y="{_PAD_T + 22:.0f}" font-size="10" '
            f'fill="#16a085">signal w{result.first_signal_week}</text>'
        )

    # The series polyline and points.
    pts = " ".join(f"{x(w):.1f},{y(v):.1f}" for w, v in zip(series.weeks, series.values))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="#2980b9" stroke-width="1.6"/>')
    signal_weeks = {s.week for s in result.signals}
    for w, v in zip(series.weeks, series.values):
        colour = "#c0392b" if w in signal_weeks else "#2980b9"
        parts.append(f'<circle cx="{x(w):.1f}" cy="{y(v):.1f}" r="3" fill="{colour}"/>')

    # Axes labels.
    parts.append(
        f'<text x="{_PAD_L}" y="{_H - 10}" font-size="10" fill="#333">'
        f'week {series.weeks[0]}</text>'
    )
    parts.append(
        f'<text x="{_W - _PAD_R}" y="{_H - 10}" font-size="10" fill="#333" '
        f'text-anchor="end">week {series.weeks[-1]}</text>'
    )
    parts.append(
        f'<text x="12" y="{_PAD_T + 6}" font-size="10" fill="#333" '
        f'transform="rotate(-90 12 {_PAD_T + 6})">blockers opened / week</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _verdict(result: DetectionResult) -> tuple[str, str, str]:
    if result.in_control:
        return "IN CONTROL", "#1e8449", "#ffffff"
    return "SIGNAL", "#c0392b", "#ffffff"


def render_html(result: DetectionResult) -> str:
    """Build the full HTML report around the SVG chart."""
    label, bg, fg = _verdict(result)
    svg = control_chart_svg(result)

    rows = []
    for s in result.signals:
        rows.append(
            f"<tr><td>{s.week}</td><td>{html.escape(s.rule)}</td>"
            f"<td>{html.escape(s.detail)}</td></tr>"
        )
    signal_table = "".join(rows) or '<tr><td colspan="3">no opened-count signal</td></tr>'

    lead = "n/a" if result.lead_weeks is None else f"{result.lead_weeks}"
    first = "n/a" if result.first_signal_week is None else f"w{result.first_signal_week}"
    esc = "n/a" if result.escalation_week is None else f"w{result.escalation_week}"
    clamp = "yes" if result.opened_limits.lower_clamped else "no"

    style = (
        "body{font-family:Verdana,Arial,sans-serif;color:#222;margin:24px;}"
        "table{border-collapse:collapse;margin:8px 0;}"
        "td,th{border:1px solid #ccc;padding:4px 8px;font-size:13px;text-align:left;}"
        ".badge{display:inline-block;padding:6px 14px;border-radius:4px;"
        "font-weight:bold;font-size:15px;}"
        ".kpi{font-size:13px;margin:2px 0;}"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>raid-signal report</title><style>{style}</style></head><body>"
        "<h1>raid-signal control report</h1>"
        f'<div class="badge" style="background:{bg};color:{fg};">{label}</div>'
        f'<p class="kpi">first opened-count signal: {first}</p>'
        f'<p class="kpi">manual escalation: {esc}</p>'
        f'<p class="kpi">warning lead: {lead} weeks</p>'
        f'<p class="kpi">lower limit clamped to zero (blind to improvement): {clamp}</p>'
        "<h2>Opened-count control chart</h2>"
        f"{svg}"
        "<h2>Signals (opened-count chart)</h2>"
        "<table><tr><th>week</th><th>rule</th><th>detail</th></tr>"
        f"{signal_table}</table>"
        "</body></html>"
    )


def write_report(result: DetectionResult, path: str | Path) -> Path:
    """Write the HTML report to disk and return the path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(result), encoding="utf-8")
    return out
