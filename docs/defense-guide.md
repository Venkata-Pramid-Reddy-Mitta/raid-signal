# raid-signal: defense guide

How to present this repository, and how to answer the questions it invites. Every number
here is the one the code produces and the number checker guards.

## The 30-second version

"A RAID log is a list, and a raw blocker count has no baseline, so you cannot tell normal
churn from the start of trouble by reading it. raid-signal puts statistical process control
over the log: it freezes control limits on the team's stable history and runs Nelson run
rules over the weekly counts. On a seeded 30-week programme it signalled in week 16, a lead
of 4 weeks over the human escalation in week 20. The part I am most careful about is that
the chart is one-sided: the lower limit clamps to zero, so it is slow to see an
improvement." Then stop.

The question that usually comes next: "so is the early warning reliable, or did you get
lucky on one spike?" Answer with the false-alarm experiment.

## The claims, and how each is proved

### Claim 1: it warned 4 weeks before the manual escalation

- Proof: `raid-signal data/raid_log.csv --escalations data/escalations.csv`, or
  `experiments/exp01_lead_time.py`.
- Numbers: first opened-count signal in week 16, manual escalation in week 20, so a lead of
  4 weeks.
- If pushed ("the escalation week is something you chose"): yes, it is a recorded input in
  `data/escalations.csv`, and the lead is measured against it precisely so the tool is not
  grading its own homework. The signal week is computed; the escalation week is given.

### Claim 2: the warning has a measured cost

- Proof: `experiments/exp02_false_alarms.py`.
- Numbers: on a matched stable programme the opened-count gate raised 3 false-signal weeks,
  and the backlog chart fired on 6 of the 18 post-baseline weeks.
- If pushed ("3 false alarms out of 18 is a lot"): agreed, and that is why the gate uses the
  opened-count chart, where the statistics hold, and not the backlog chart, which fires on 6
  of the 18 weeks because a level is autocorrelated.

### Claim 3: the chart is blind to improvement, and I can prove it

- Proof: `experiments/exp04_lcl_blindness.py`.
- Numbers: the lower limit is clamped in 100% of weeks, and halving the blocker rate for the
  back half of the programme produces zero signals.
- If pushed ("then your tool is half-blind"): yes, on purpose, and it is in the README's
  first screen. A c-chart on a low count has a negative lower limit; clamping it to zero is
  the honest handling, and detecting improvement needs a different chart, which is the Pivot.

### Claim 4: the run rules did not help here, and I say so

- Proof: `experiments/exp03_run_rules_vs_3sigma.py`.
- Numbers: the single 3-sigma breach fired 5 weeks before the earliest run rule on this
  spike.
- If pushed ("then why ship run rules"): because they lead on a slower drift, which this
  spike was not. Shipping them and then publishing that they lost on this case is the point:
  the repository reports what happened, not what flatters the feature.

## Questions that are meant to be hard

**"Isn't this just a wrapper around a formula?"** The formulas are short on purpose, and I
wrote them rather than import them (ADR-002) so I could defend every number. The engineering
is not the square root; it is the decisions around it: gating on the sound chart and not the
autocorrelated one, freezing the baseline so a drift cannot hide in it, and pricing the run
rules instead of assuming they help.

**"The corpus is synthetic. Does any of this transfer?"** The maths is identical on real
data; what the fixture cannot prove is the false-alarm rate a real team would see, because
that depends on the team's real variation. The fixture is honest about being hard: the
stable programme is not quiet, which is why the backlog chart over-fires on it. The adapter
to a real Jira or Azure DevOps export sits behind the same `RaidItem` boundary and is listed
as future work.

**"What is the weakest part?"** The backlog chart. An individuals chart assumes independent
points, and a backlog level is a running total that carries last week forward, so its limits
are not trustworthy. I kept it because a rising backlog under flat opens is a real pattern a
reader should see, but I do not let it trip the gate, and I would not claim its false-alarm
rate means anything.

**"Why a declared baseline and not an adaptive one?"** Because an adaptive baseline absorbs
the very drift the tool is meant to catch (ADR-005). The cost is that a wrong baseline
poisons everything, which is why it is a deliberate human input at the top of the policy
file.

**"What would you do differently with more time?"** A u-chart that divides by team size, so
a change in the area of opportunity stops reading as a signal, and a second one-sided chart
tuned for improvement to cover the blindness. Both are in the README's future work with the
first metric to watch.

**"How do I know the numbers in your README are real?"** Break one and watch the build fail:
change a figure in the README, run `make verify`, and `tools/check_numbers.py` fails because
the anchor phrase no longer matches the measured value.

## Things to say, and things not to say

Say:
- "The lower limit is clamped, so it is one-sided and slow to see improvement."
- "The run rules did not lead on this spike, and the experiment shows it."
- "The gate ignores the backlog chart on purpose."

Do not say:
- "It catches problems early." Say: it signalled in week 16, a lead of 4 weeks over the
  escalation in week 20, on this fixture.
- "Low false alarms." Say: 3 false-signal weeks on the opened chart over 18 post-baseline
  weeks of a stable fixture, and the backlog chart is worse.
- "It works on any RAID log." Say: the maths transfers; the false-alarm rate has to be
  re-measured on real data.

## The live demo script

```bash
# 1. The headline: signal week and the lead over the manual escalation.
raid-signal data/raid_log.csv --escalations data/escalations.csv

# 2. The cost: false alarms on a programme with no real shift.
python experiments/exp02_false_alarms.py

# 3. The uncomfortable truth: blind to improvement.
python experiments/exp04_lcl_blindness.py

# 4. The honest finding: the run rules did not lead here.
python experiments/exp03_run_rules_vs_3sigma.py

# 5. The receipts: break a README number and watch the build fail.
make verify
```
