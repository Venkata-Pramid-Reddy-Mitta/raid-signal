# ADR-002: Build the control-limit maths rather than take a library

## Status

Accepted.

## Context

There are Python packages that draw control charts (pyspc and others), and statsmodels
covers some of the run-rule machinery. Using one would save perhaps thirty lines.

## Decision

Write the control-limit arithmetic by hand in `control.py` and the run rules in `rules.py`.
The formulas are closed form and short: a mean, a square root, an average of absolute
differences, the 2.66 individuals-chart constant. Nothing here needs a dependency.

## Why

Three reasons specific to this repository, not a general preference for reinvention:

1. Defensibility. This is a portfolio piece whose point is that the author understands the
   statistics. A library import moves the understanding into someone else's code and leaves
   nothing to explain in an interview. A reader can check every number in `control.py`
   against the definition of a c-chart.
2. Determinism and no network. The whole repository reproduces offline from a fresh clone.
   One fewer third-party package is one fewer version whose default could move a limit.
3. The surface actually used is tiny. Pulling a charting library for four formulas means
   carrying its plotting stack, its own data model and its release cadence for almost no
   code.

## Consequences

The author owns the correctness of the maths, so the test suite carries hand-computed
expectations for every limit (`tests/test_control.py`) rather than trusting a library's
tests. That is the cost, and it is paid.

## Alternatives rejected

pyspc: rejected for the reasons above. statsmodels for the run rules: rejected because it
would pull a large dependency for a few comparisons, and the rules are clearer written out
than configured.
