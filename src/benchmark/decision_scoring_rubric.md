# Decision Agent + Scorer Benchmark: Rubric (Draft v1)

## Why this is different from the extraction benchmark

`json_comparer.py` (extraction benchmark) works because there's an objective
groundtruth: a conference either has the right name, date, and city, or it
doesn't. Decision-agent and scorer quality has no equivalent groundtruth —
whether "IEEE BigData" is relevant to a "Machine Learning for Public Health"
researcher is a judgment call, not a fact lookup. That's why this rubric
uses **Claude as an LLM judge** for the subjective axes, combined with a
few genuinely objective/deterministic checks pulled directly from the data.

**Important structural note about the pipeline**, relevant to what's actually
judgeable: only `relevancy` is LLM-scored per conference. `distance` is a
deterministic Haversine calculation and `prestige` is a deterministic CORE-rank
lookup (see `src/agents/scorer.py`) — neither varies by model except insofar
as different models *accept different conferences* in the first place, which
changes which conferences are around to be scored at all, but the numbers
scorer.py computes for `distance`/`prestige` themselves.  So this rubric
focuses judgment on: (1) the accept/reject decision itself, (2) the reasoning
behind it, and (3) the relevancy score's calibration — the three places
where model quality actually shows up in the data.

## Input data

`src/benchmark/decision_scoring_results.json` — 120 entries (6 models × 20
profiles from `decision_scoring_profiles.py`), each containing:
- `decisions`: every pre-filtered conference with `valid`/`relevant`/`reason`
- `scored`: the accepted subset with `relevancy`/`distance`/`prestige`/`total`
- `error`, `elapsed_s`, timing stats

## Sampling strategy (judging all ~2,000-5,000 individual decisions isn't tractable)

For the Claude-judged metrics (2, 3, 4 below), sample **10 conferences per
model** (60 per profile-topic-model combination isn't needed — 10 gives a
reasonable per-model read without an enormous judging pass), stratified to
include:
- A mix of accepted and rejected conferences
- At least one "obvious" case per profile category (e.g. a Security
  conference for an AI profile, expected reject; an AI conference for an AI
  profile, expected accept) — these anchor whether the model gets the easy
  cases right before worrying about the hard ones
- Sampling is done *after* the full run completes, from the actual results
  file, not designed in advance — so it reflects what each model actually
  produced, not a fixed pre-selected set

## v2 update: dropped Reliability and Discrimination from scoring

After running all 5 metrics against real data, two of them turned out not to
discriminate between models at all:
- **Reliability**: every working model scored 100 (0 parse failures across
  242 decisions each). Zero variance — it contributed 20% of every score
  without doing any ranking work, which mechanically inflated and compressed
  the whole scale (this is exactly the risk flagged in the "open items"
  section below, now confirmed).
- **Discrimination**: after scaling, 4 of 5 models landed at or near 95-100.
  Real variance existed in the raw acceptance-rate stdev, but the scaling
  approach compressed it into another near-constant.

Both are still useful as **gates/diagnostics** (a model that failed
Reliability or showed zero Discrimination would be flagged separately, not
silently folded into the score), but they're no longer part of the weighted
total. The final leaderboard score is now Decision Accuracy + Reasoning
Quality + Relevancy Calibration at equal 33.3% each — the only 3 metrics
that showed real, meaningful variance across the 5 models actually judged.

## The 5 Metrics (Metrics 1 and 5 kept as diagnostics only — see v2 update above)

### 1. Instruction-Following Reliability (diagnostic only, not scored) — deterministic, no judge needed

What fraction of decisions were successfully parsed vs. fell back to the
`except` branch in `decision.py`/`scorer.py` (visible as `reason` containing
"Decision failed" or a non-null `error` field on the whole run)?

```
reliability = 1 - (failed_decisions / total_decisions)
score_1 = reliability * 100
```

This is the foundation metric: a model that can't reliably produce parseable
output shouldn't score well regardless of how good its reasoning is when it
*does* work. Directly computable from the JSON, no LLM judge involved.

### 2. Decision Accuracy (weight: 33.3%) — Claude-judged

For each sampled (profile, conference, decision) triple, Claude independently
answers: "Given this conference's name/topics and this researcher's
title/context, should this conference be accepted (valid AND relevant)?"
without seeing the model's actual answer first (avoid anchoring bias — judge
the case, then compare).

```
accuracy = agreements / sample_size
score_2 = accuracy * 100
```

This is the single most important "did it get the right answer" metric,
analogous to recall/precision in the extraction benchmark.

### 3. Reasoning Quality (weight: 33.3%) — Claude-judged

For the same sample, Claude rates each `reason` string on a 1-5 scale:

| Score | Meaning |
|---|---|
| 1 | Generic/boilerplate, doesn't reference actual conference or profile content |
| 2 | Vague reference to topic but no specific reasoning |
| 3 | Correct topic reference but reasoning is thin or partially wrong |
| 4 | Specific, correct reasoning with minor gaps |
| 5 | Specific, correct, and clearly grounded in both the conference's actual topics and the researcher's actual stated focus |

```
score_3 = (average_rating / 5) * 100
```

Distinct from accuracy: a model can reach the *right* accept/reject
conclusion with a lazy or generic reason, which this metric penalizes even
when metric 2 doesn't.

### 4. Relevancy Score Calibration (weight: 33.3%) — Claude-judged, accepted conferences only

For each sampled *accepted* conference, Claude independently assigns its own
0-100 relevancy estimate (same rubric text the scorer agent itself uses, in
`src/agents/scorer.py`'s `_RELEVANCY_SYSTEM`), then compares to the model's
actual assigned score.

```
deviation = mean(|model_score - claude_score|) across the sample
score_4 = max(0, 100 - deviation)
```

A model that's directionally right (accepts the right things) but assigns
wildly miscalibrated numbers (e.g. 95 for a marginal fit, 20 for a strong
one) should score worse here even if metric 2 gives it credit for the
accept/reject call itself.

### 5. Discrimination / Consistency (diagnostic only, not scored) — deterministic, computed across all 20 profiles per model

Does the model's acceptance rate actually vary by topic, or does it behave
close to identically regardless of the researcher's field (a "lazy" model
that accepts/rejects almost everything)?

```
acceptance_rate(profile) = accepted_count / pre_filtered_count, per profile
score_5 = min(100, stdev(acceptance_rate across the 20 profiles) * scaling_factor)
```

(Scaling factor to be calibrated once we see the actual distribution across
models — the point is: near-zero variance across wildly different research
topics is a red flag, not a sign of consistency.) This is the one metric
that needs a first look at real data before the exact formula is finalized;
flagging that explicitly rather than guessing a constant now.

## Penalties (subtracted from the weighted total, floor at 0)

| Issue | Penalty |
|---|---|
| Model accepts or rejects 100% of conferences for any single profile (degenerate, no real judgment happening) | −10 per affected profile |
| Reason text contradicts the actual decision (e.g. reason argues relevance but `relevant: false`) | −5 per confirmed case in the sample |
| Relevancy score assigned outside 0-100 or clearly nonsensical (e.g. 0 for an accepted "5/5 reasoning quality" match) | −5 per confirmed case in the sample |

## Final Leaderboard Score

```
total = 0.333*score_2 + 0.333*score_3 + 0.333*score_4 - penalties
total = max(0, min(100, total))
```

(score_1 and score_5 reported separately as pass/fail diagnostics, not part
of the weighted total — see v2 update above.)

**Tiebreak rule**: if two models land on the same total, rank by Decision
Accuracy (score_2) alone — the single metric we'd trust most in isolation if
forced to pick one, rather than introducing a separate secondary formula.

## Open items for v2 (not blocking a first pass)

- Metric 5's scaling factor needs calibration once real acceptance-rate data exists.
- Consider adding the presentation's "decoy" concept (RQ2: conferences with
  perfect topical fit but impossible distance) as a dedicated 6th metric in
  a future run — current 20 profiles don't include deliberate decoys, so
  distance-blind-trust isn't directly measurable from this dataset yet.
- Sample size (10/model) is a starting point; revisit if judging cost is
  low enough to sample more, or results are too noisy at this size.
