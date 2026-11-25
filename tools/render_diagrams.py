"""Render the architecture diagram to a committed SVG, deterministically.

GitHub does not reliably render a Mermaid fence, and a mermaid-produced SVG has
to be post-processed anyway (htmlLabels off, intrinsic dimensions, a painted
background) before it loads as <img src> (see the CI-and-rendering traps). This
build has no network at render time, so rather than fetch the mermaid library it
draws the box-and-arrow diagram directly as valid SVG from a small node and edge
spec. The result has explicit width and height, a light background, and <text>
labels, so it renders identically on GitHub, in a PDF export and offline.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams" / "architecture.svg"

# (id, column, row, label). Columns and rows lay the flow out left to right.
NODES = [
    ("log", 0, 1, "RAID event log\n(raid_log.csv)"),
    ("policy", 0, 0, "policy.toml\n(baseline, sigma, rules)"),
    ("agg", 1, 1, "aggregate\nopens + backlog / week"),
    ("control", 2, 0, "control\nc-chart + XmR limits"),
    ("rules", 2, 2, "rules\nNelson run rules"),
    ("detect", 3, 1, "detect\nsignals + lead time"),
    ("report", 4, 0, "report\nHTML + SVG chart"),
    ("cli", 4, 2, "cli\nexit 0 / 2 / 1"),
]
EDGES = [
    ("log", "agg"),
    ("policy", "control"),
    ("policy", "rules"),
    ("agg", "control"),
    ("agg", "rules"),
    ("control", "detect"),
    ("rules", "detect"),
    ("detect", "report"),
    ("detect", "cli"),
]

COL_W = 190
ROW_H = 95
BOX_W = 160
BOX_H = 58
MARGIN = 24


def _centre(col: int, row: int) -> tuple[float, float]:
    cx = MARGIN + col * COL_W + BOX_W / 2
    cy = MARGIN + row * ROW_H + BOX_H / 2
    return cx, cy


def build_svg() -> str:
    width = MARGIN * 2 + (max(c for _, c, _, _ in NODES)) * COL_W + BOX_W
    height = MARGIN * 2 + (max(r for _, _, r, _ in NODES)) * ROW_H + BOX_H
    pos = {nid: (col, row) for nid, col, row, _ in NODES}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Verdana,Arial,sans-serif">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#f7f7f5"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" '
        'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#555"/></marker></defs>',
    ]

    for src, dst in EDGES:
        x1, y1 = _centre(*pos[src])
        x2, y2 = _centre(*pos[dst])
        parts.append(
            f'<line x1="{x1 + BOX_W / 2 - 2:.1f}" y1="{y1:.1f}" '
            f'x2="{x2 - BOX_W / 2 - 4:.1f}" y2="{y2:.1f}" '
            f'stroke="#555" stroke-width="1.3" marker-end="url(#arrow)"/>'
        )

    for _nid, col, row, label in NODES:
        x = MARGIN + col * COL_W
        y = MARGIN + row * ROW_H
        parts.append(
            f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="6" '
            f'fill="#ffffff" stroke="#2c3e50" stroke-width="1.4"/>'
        )
        lines = label.split("\n")
        start_y = y + BOX_H / 2 - (len(lines) - 1) * 7 + 4
        for i, line in enumerate(lines):
            weight = "bold" if i == 0 else "normal"
            size = 12 if i == 0 else 10
            fill = "#1a1a1a" if i == 0 else "#555"
            parts.append(
                f'<text x="{x + BOX_W / 2:.1f}" y="{start_y + i * 14:.1f}" '
                f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
                f'text-anchor="middle">{line}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
