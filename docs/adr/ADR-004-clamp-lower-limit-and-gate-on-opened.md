# ADR-004: Clamp the lower limit, declare the blindness, gate on opened not backlog

## Status

Accepted.

## Context

Two facts collide. First, for a low Poisson count the lower control limit `center -
3*sqrt(center)` is negative, and a count cannot be negative. Second, the backlog level chart
fires far more often than the opened-count chart on a stable programme, because a level
carries last week's value forward and so violates the independence an individuals chart
assumes.

## Decision

1. Clamp the opened-count lower limit to zero, and record on every result that the clamp was
   active, so the blindness is reported rather than hidden.
2. Gate on the opened-count chart only. Build the backlog chart and show its signals in the
   report, but keep them out of the `in_control` verdict and the exit code.

## The cost, stated plainly

Clamping the lower limit to zero means a week can never fall below it, so an improvement can
never be a signal. The chart is one-sided by construction: good at catching deterioration,
structurally slow at catching recovery. `experiments/exp04_lcl_blindness.py` demonstrates it
by halving the blocker rate for the whole back half of the programme and showing that no
signal fires.

Gating on opened rather than backlog trades away the ability to catch a backlog that climbs
while opens stay flat. That is a real loss, and the mitigation is that the backlog chart is
still shown, just not trusted to trip the gate.

## Why this way round

A gate that cries wolf is turned off, and then nothing is watched. The opened-count chart is
the one where the statistics are sound, so it is the one allowed to escalate. Showing the
backlog chart anyway keeps the information in front of the reader without letting its
over-firing drive the decision.

## Alternatives rejected

Gating on both charts: rejected because the backlog chart's false-alarm rate would dominate
the gate. Dropping the backlog chart entirely: rejected because a rising backlog under flat
opens is a real pattern a reader should see, even if the tool will not escalate on it.
