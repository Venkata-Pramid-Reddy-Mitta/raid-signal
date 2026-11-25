"""Record a replay of the real CLI session as an animated GIF.

This is a replay, not a screen recording, and the README says so. Each command
is run for real; its stdout, exit code and wall time are captured and written to
docs/video/manifest.json. The GIF then types each command and reveals its
captured output paced by the measured duration, so a slow command looks slow and
every line of terminal text is real output rather than hand written.

Segments are ordered as the argument the demo makes, not as a feature list: the
headline first, then the cost, then the number no RAID list reports, then the
honest finding, then the receipts.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "docs" / "video"
GIF = VIDEO / "demo.gif"

SEGMENTS = [
    ["raid-signal", "data/raid_log.csv", "--escalations", "data/escalations.csv"],
    [sys.executable, "experiments/exp02_false_alarms.py"],
    [sys.executable, "experiments/exp04_lcl_blindness.py"],
    [sys.executable, "experiments/exp03_run_rules_vs_3sigma.py"],
    [sys.executable, "tools/check_numbers.py"],
]

WIDTH, HEIGHT = 820, 460
BG = (24, 26, 27)
FG = (220, 223, 224)
PROMPT = (120, 200, 140)
MAXLINES = 22


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _pretty(cmd: list[str]) -> str:
    out = []
    for token in cmd:
        out.append("python" if token == sys.executable else token)
    return " ".join(out)


def _capture() -> list[dict]:
    results = []
    for cmd in SEGMENTS:
        start = time.perf_counter()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        duration = time.perf_counter() - start
        text = (proc.stdout + proc.stderr).rstrip("\n")
        results.append(
            {
                "command": _pretty(cmd),
                "exit_code": proc.returncode,
                "duration_s": round(duration, 3),
                "output_lines": text.split("\n") if text else [],
            }
        )
    return results


def _frame(lines: list[str]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    mono = _font(14)
    y = 10
    for colour, text in lines[-MAXLINES:]:
        draw.text((12, y), text, font=mono, fill=colour)
        y += 19
    return img


def main() -> int:
    VIDEO.mkdir(parents=True, exist_ok=True)
    segments = _capture()
    (VIDEO / "manifest.json").write_text(
        json.dumps(segments, indent=2), encoding="utf-8"
    )

    frames: list[Image.Image] = []
    durations: list[int] = []
    shown: list[tuple[tuple[int, int, int], str]] = []

    for seg in segments:
        shown.append((PROMPT, f"$ {seg['command']}"))
        frames.append(_frame(shown))
        durations.append(700)
        # Reveal output lines paced by the measured wall time.
        per_line = max(60, int(seg["duration_s"] * 1000 / max(1, len(seg["output_lines"]))))
        per_line = min(per_line, 320)
        for line in seg["output_lines"]:
            shown.append((FG, line[:100]))
            frames.append(_frame(shown))
            durations.append(per_line)
        shown.append((FG, f"  (exit {seg['exit_code']})"))
        frames.append(_frame(shown))
        durations.append(500)
        shown.append((FG, ""))

    frames[0].save(
        GIF,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    size_kb = GIF.stat().st_size / 1024
    print(f"wrote {GIF.relative_to(ROOT)} ({len(frames)} frames, {size_kb:.0f} KB)")
    if size_kb > 5120:
        print("warning: GIF over 5 MB; consider fewer frames", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
