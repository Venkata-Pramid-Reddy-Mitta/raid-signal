"""Render the defense guide to a PDF: a figures cover, then the guide body.

Markdown is rendered with cmark-gfm (the library GitHub uses) and laid out with
Chromium through page.pdf(), so tables and headings look the way they do on
GitHub. House rules: plain black text, roughly 10pt body, no decorative colour.
The cover carries the project's measured figures so the printed copy stands on
its own in an interview.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cmarkgfm
from cmarkgfm.cmark import Options

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "defense-guide.pdf"

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { font-family: 'DejaVu Sans', Arial, sans-serif; color: #000; }
body { font-size: 10.5pt; line-height: 1.42; }
h1 { font-size: 17pt; margin: 0 0 4pt; }
h2 { font-size: 12.5pt; margin: 14pt 0 4pt; border-bottom: 1px solid #000; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 10pt 0 2pt; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9.5pt; }
pre { background: #f2f2f2; padding: 7pt; font-size: 9pt; white-space: pre-wrap; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 9.5pt; }
td, th { border: 1px solid #000; padding: 3pt 6pt; text-align: left; }
.cover { page-break-after: always; }
.cover h1 { font-size: 24pt; margin-bottom: 2pt; }
.cover .sub { font-size: 11pt; margin-bottom: 18pt; }
.fig { font-size: 11pt; margin: 3pt 0; }
.fig b { display: inline-block; min-width: 62mm; }
.foot { margin-top: 20pt; font-size: 9pt; }
"""


def _cover(metrics: dict) -> str:
    rows = [
        ("Warning lead over manual escalation", f"{metrics['lead_weeks']} weeks"),
        ("First opened-count signal", f"week {metrics['first_signal_week']}"),
        ("Manual escalation", f"week {metrics['escalation_week']}"),
        ("3-sigma lead over run rules", f"{metrics['three_sigma_lead_over_run_rules']} weeks"),
        ("Opened-count false-alarm weeks", f"{metrics['opened_false_alarm_weeks']} of 18"),
        ("Lower limit clamped", f"{metrics['lcl_clamped_pct']}% of weeks"),
        ("Tests / line coverage", f"{metrics['tests_total']} / {metrics['coverage_line_pct']}%"),
        ("Corpus", f"{metrics['items_total']} RAID items, {metrics['blockers_total']} blockers"),
    ]
    figs = "".join(f'<p class="fig"><b>{k}</b> {v}</p>' for k, v in rows)
    return (
        '<div class="cover">'
        "<h1>raid-signal</h1>"
        '<p class="sub">Defense guide: statistical process control over a RAID log.</p>'
        f"{figs}"
        '<p class="foot">Every figure above is produced by running the suite and the '
        "experiments, and guarded against the prose by tools/check_numbers.py.</p>"
        "</div>"
    )


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("render_pdf: playwright not installed (pip install .[evidence])", file=sys.stderr)
        return 1

    exe = None
    for cand in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if Path(cand).exists():
            exe = cand
            break
    if exe is None:
        print("render_pdf: no chrome/chromium binary found", file=sys.stderr)
        return 1

    metrics = json.loads((ROOT / "docs" / "metrics.json").read_text())["metrics"]
    body_md = (ROOT / "docs" / "defense-guide.md").read_text()
    body_html = cmarkgfm.markdown_to_html_with_extensions(
        body_md,
        options=Options.CMARK_OPT_UNSAFE,
        extensions=["table", "autolink", "strikethrough"],
    )
    page_html = (
        f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
        f"<body>{_cover(metrics)}{body_html}</body></html>"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_content(page_html, wait_until="load")
        page.pdf(path=str(OUT), format="A4", print_background=True)
        browser.close()

    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
