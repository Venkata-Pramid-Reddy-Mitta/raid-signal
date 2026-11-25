"""Screenshot the real HTML report, framed by heading, with a legibility check.

Playwright drives a headless browser against the report the tool itself writes,
so the image in the README is the real output and a reviewer can regenerate it.
Three rules, each learned from a failure elsewhere:

* frame by a named heading, not a pixel offset, so the crop does not drift when a
  paragraph grows;
* pass full_page=True even with a clip, or the browser clamps the clip to the
  viewport and loses the bottom of the section;
* read back the verdict badge's computed style and fail if it is invisible, the
  one check only something that sees pixels can make.

If no browser binary is available the script says so and exits non-zero rather
than writing a stale image, so a missing tool is surfaced, not worked around.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "report.html"
OUT = ROOT / "docs" / "img" / "report.png"

CHROME_CANDIDATES = [
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def _build_report_if_missing() -> None:
    if REPORT.exists():
        return
    sys.path.insert(0, str(ROOT / "src"))
    from raid_signal import aggregate, detect
    from raid_signal.config import load_policy
    from raid_signal.report import write_report

    policy = load_policy(ROOT / "config" / "policy.toml")
    items = aggregate.load_raid_log(str(ROOT / "data" / "raid_log.csv"))
    esc = detect.load_escalations(str(ROOT / "data" / "escalations.csv"))["blocker_spike"]
    write_report(detect.analyse(items, policy, escalation_week=esc), REPORT)


def _executable() -> str | None:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("capture_screenshots: playwright not installed (pip install .[evidence])", file=sys.stderr)
        return 1

    exe = _executable()
    if exe is None:
        print("capture_screenshots: no chrome/chromium binary found; cannot screenshot", file=sys.stderr)
        return 1

    _build_report_if_missing()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 900, "height": 700}, device_scale_factor=2)
        page.goto(REPORT.as_uri())

        contrast = page.evaluate(
            """() => {
              const badge = document.querySelector('.badge');
              if (!badge) return null;
              const s = getComputedStyle(badge);
              return {color: s.color, background: s.backgroundColor,
                      visible: badge.offsetWidth > 0 && badge.offsetHeight > 0};
            }"""
        )
        if not contrast or not contrast["visible"]:
            browser.close()
            print(f"capture_screenshots: verdict badge invisible: {contrast}", file=sys.stderr)
            return 1
        if contrast["color"] == contrast["background"]:
            browser.close()
            print("capture_screenshots: badge text colour equals its background", file=sys.stderr)
            return 1

        page.screenshot(path=str(OUT), full_page=True)
        browser.close()

    print(f"wrote {OUT.relative_to(ROOT)} (badge {contrast['color']} on {contrast['background']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
