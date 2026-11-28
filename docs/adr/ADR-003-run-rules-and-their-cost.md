# ADR-003: Add Nelson run rules, and price the false alarms each one buys

## Status

Accepted.

## Context

A single point beyond the 3-sigma limit is the slowest useful signal: a slow upward drift
can sit inside the limits for many weeks while every week is a little worse than the last.
The Nelson run rules read the sequence instead of the single point and fire on a sustained
shift before it breaches. But every rule added is another pattern that can occur by chance
on a stable process, so each one bought earlier warning at the cost of more false alarms.

## Decision

Implement rules 1 (one point beyond 3-sigma), 2 (nine points one side of center), 3 (six
points trending), and 5 (two of three beyond 2-sigma), each switchable in the policy file.
Do not treat the run rules as free: measure their cost directly.

## How the cost is priced

`experiments/exp02_false_alarms.py` runs every enabled rule on a matched stable fixture and
counts the weeks that fire when nothing is wrong. `experiments/exp03_run_rules_vs_3sigma.py`
reports, per rule, the first week it fires on the real spike, so the lead each rule actually
delivered is visible rather than assumed.

The uncomfortable result is kept: on this particular spike the run rules delivered no
earlier warning than the plain 3-sigma breach. They are retained because they lead on slower
drifts, and the experiment says plainly that this spike was not one of those.

## Consequences

The policy file is the honest place to turn a rule off for a noisier programme. A reader can
re-run the experiments after disabling a rule and see the false-alarm count drop.

## Alternatives rejected

Shipping only rule 1: rejected because it misses slow drifts, which is the failure mode the
whole tool is meant to catch. Shipping all eight Nelson rules: rejected because the extra
rules add false alarms out of proportion to the drift they catch on a series this short.
