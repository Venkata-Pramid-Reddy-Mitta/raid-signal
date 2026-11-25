# ADR-001: A Poisson c-chart for opened counts, with a stated boundary

## Status

Accepted.

## Context

The gate needs limits for the number of blockers opened each week. Two families fit a
time series of small integers: a c-chart, which assumes the counts are Poisson (variance
equal to the mean, so the standard deviation is the square root of the mean), and an
individuals (XmR) chart, which estimates spread from the average moving range and assumes
nothing about the distribution.

## Decision

Use a c-chart for the opened-count series. The number of independent events in a fixed
interval, where each event is individually unlikely, is the textbook situation the Poisson
describes, and the closed-form limits `centre +/- 3*sqrt(centre)` need no distribution
fitting and no library.

## The boundary this buys

A c-chart assumes a constant area of opportunity: the same team, over the same length of
week, with the same exposure to things that can go wrong. When the team grows, the opening
rate rises for a reason that is not a process shift, and the chart reads it as a signal. The
fixtures hold team size fixed, so this never bites here, but a real programme changes size,
and the honest extension is a u-chart that divides by the area of opportunity. That is
recorded as future work, not smuggled in as if the c-chart already handled it.

## Consequences

The lower limit is frequently negative and must be handled (ADR-004). The backlog series,
which is a level rather than a count of independent events, does not fit the Poisson
assumption and gets the individuals chart instead, used only as a diagnostic.

## Alternatives rejected

An individuals chart on the opened counts too, for uniformity: rejected because it discards
the one thing actually known about the series (that it is a count), and estimates a spread
it does not need to estimate.
