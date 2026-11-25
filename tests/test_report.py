"""The HTML report and the hand-drawn SVG chart."""

from __future__ import annotations

import re
import xml.dom.minidom as minidom

from raid_signal import detect
from raid_signal.model import RaidItem
from raid_signal.report import control_chart_svg, render_html, write_report


def _result(policy_factory):
    pol = policy_factory(baseline_end=6)
    items = []
    counter = 0
    for week, n in enumerate([1, 1, 1, 1, 1, 1, 1, 20], start=1):
        for _ in range(n):
            counter += 1
            items.append(RaidItem(f"I-{counter}", "Issue", 4, True, week, None))
    return detect.analyse(items, pol, escalation_week=10)


def test_the_svg_is_well_formed_xml(policy_factory):
    svg = control_chart_svg(_result(policy_factory))
    minidom.parseString(svg)  # raises on malformed XML


def test_the_svg_has_intrinsic_width_and_height(policy_factory):
    svg = control_chart_svg(_result(policy_factory))
    assert 'width="820"' in svg and 'height="320"' in svg


def test_the_svg_paints_a_white_background(policy_factory):
    svg = control_chart_svg(_result(policy_factory))
    assert 'fill="#ffffff"' in svg


def test_the_svg_labels_a_clamped_lower_limit(policy_factory):
    svg = control_chart_svg(_result(policy_factory))
    assert "clamped" in svg


def test_the_report_badge_has_an_explicit_colour(policy_factory):
    html = render_html(_result(policy_factory))
    assert "badge" in html
    assert re.search(r"background:#[0-9a-fA-F]{6};color:#[0-9a-fA-F]{6};", html)


def test_the_report_states_the_verdict_word(policy_factory):
    html = render_html(_result(policy_factory))
    assert "SIGNAL" in html  # the engineered spike is out of control


def test_the_report_lists_every_signal_row(policy_factory):
    result = _result(policy_factory)
    html = render_html(result)
    for s in result.signals:
        assert str(s.week) in html


def test_an_in_control_report_says_in_control(policy_factory):
    pol = policy_factory(baseline_end=6)
    items = [RaidItem(f"I-{i}", "Issue", 3, True, w, None) for i, w in enumerate(range(1, 11))]
    res = detect.analyse(items, pol, escalation_week=None)
    html = render_html(res)
    assert "IN CONTROL" in html


def test_write_report_creates_the_file(tmp_path, policy_factory):
    out = write_report(_result(policy_factory), tmp_path / "sub" / "report.html")
    assert out.exists()
    assert out.read_text().startswith("<!doctype html>")


def test_every_css_class_used_in_markup_has_a_rule(policy_factory):
    # Mirrors the evidence check: a class used but unstyled is how a badge went
    # invisible on an earlier project.
    html = render_html(_result(policy_factory))
    style_block = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    used = set(re.findall(r'class=["\']([a-zA-Z0-9_ -]+)["\']', html))
    classes = set()
    for group in used:
        classes.update(group.split())
    for cls in classes:
        assert f".{cls}" in style_block, f"class {cls} has no CSS rule"
