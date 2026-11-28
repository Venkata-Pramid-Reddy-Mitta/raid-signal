# ADR-005: Freeze the limits on a declared baseline, do not re-learn them

## Status

Accepted.

## Context

Control limits need a baseline: a window of stable history whose mean and spread define
normal. Two ways to set it. Re-learn the limits every week from a trailing window, so they
adapt as the programme runs. Or declare a fixed baseline window once and freeze the limits
on it for the rest of the programme.

## Decision

Declare the baseline in the policy file (weeks 1 to 12 by default) and freeze the limits on
it. Later weeks are judged against those frozen limits and never fold back into them.

## Why

A trailing window that re-learns the limits every week absorbs a slow upward drift into its
own baseline: as the counts creep up, the center line and the upper limit creep up with
them, and the drift raises its own ceiling and hides. The one failure mode the tool exists to
catch is exactly the one an adaptive baseline is blind to. Freezing the baseline is what lets
a sustained shift read as a sustained shift.

## The cost, stated plainly

The baseline is assumed representative. If the declared window was itself abnormal (a quiet
fortnight, or a fortnight already in trouble), every later judgement is wrong, and the tool
cannot tell you that the baseline you handed it was the problem. That is why the window is a
policy value a human sets deliberately, not a default buried in code, and why a signal inside
the baseline window is reported but not counted as a warning.

## Consequences

`detect.py` only credits signals at or after `baseline_end + 1`. The baseline choice is the
single most consequential input, so it sits at the top of `policy.toml` with a comment
saying so.

## Alternatives rejected

A rolling recomputed baseline: rejected for the self-hiding-drift reason above. Learning the
baseline automatically from a changepoint detector: rejected as out of scope and as trading a
transparent human choice for an opaque one on the most important input.
