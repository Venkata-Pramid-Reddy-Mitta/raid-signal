"""The CLI: exit codes that mean something, and the JSON summary."""

from __future__ import annotations

import json

from raid_signal import cli

HEADER = "item_id,raid_type,severity,is_blocker,opened_week,closed_week\n"


def _log(tmp_path, per_week):
    rows = []
    counter = 0
    for week, n in enumerate(per_week, start=1):
        for _ in range(n):
            counter += 1
            rows.append(f"I{counter},Issue,4,True,{week},\n")
    path = tmp_path / "log.csv"
    path.write_text(HEADER + "".join(rows))
    return str(path)


def _policy(tmp_path, baseline_end=6):
    text = f"""
[baseline]
start_week = 1
end_week = {baseline_end}
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
    path = tmp_path / "policy.toml"
    path.write_text(text)
    return str(path)


def test_in_control_program_exits_zero(tmp_path):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    code = cli.main([log, "--policy", _policy(tmp_path)])
    assert code == cli.EXIT_IN_CONTROL


def test_a_signal_exits_two(tmp_path):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 20])
    code = cli.main([log, "--policy", _policy(tmp_path)])
    assert code == cli.EXIT_SIGNAL


def test_a_missing_file_exits_one(tmp_path):
    code = cli.main([str(tmp_path / "nope.csv"), "--policy", _policy(tmp_path)])
    assert code == cli.EXIT_ERROR


def test_a_broken_policy_exits_one(tmp_path):
    log = _log(tmp_path, [1, 1, 1])
    bad = tmp_path / "bad.toml"
    bad.write_text("[baseline]\nstart_week = 0\nend_week = 1\n")
    code = cli.main([log, "--policy", str(bad)])
    assert code == cli.EXIT_ERROR


def test_json_output_is_valid_and_has_the_summary_keys(tmp_path, capsys):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 20])
    cli.main([log, "--policy", _policy(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["in_control"] is False
    assert payload["n_opened_signals"] >= 1
    assert "opened_ucl" in payload


def test_report_flag_writes_a_file(tmp_path):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 20])
    report = tmp_path / "r.html"
    cli.main([log, "--policy", _policy(tmp_path), "--report", str(report)])
    assert report.exists()


def test_escalations_feed_the_lead_time(tmp_path, capsys):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 20])
    esc = tmp_path / "esc.csv"
    esc.write_text("label,escalated_week\nblocker_spike,10\n")
    cli.main([log, "--policy", _policy(tmp_path), "--escalations", str(esc), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["lead_weeks"] == 2


def test_text_output_names_the_verdict(tmp_path, capsys):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 20])
    cli.main([log, "--policy", _policy(tmp_path)])
    out = capsys.readouterr().out
    assert "SIGNAL" in out


def test_text_output_prints_the_lead_when_an_escalation_is_given(tmp_path, capsys):
    log = _log(tmp_path, [1, 1, 1, 1, 1, 1, 1, 20])
    esc = tmp_path / "esc.csv"
    esc.write_text("label,escalated_week\nblocker_spike,10\n")
    cli.main([log, "--policy", _policy(tmp_path), "--escalations", str(esc)])
    out = capsys.readouterr().out
    assert "warning lead over manual escalation: 2 weeks" in out
