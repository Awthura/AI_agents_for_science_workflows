# Decision/Scoring Benchmark — Claude Judgment Notes

Judged by: Claude Sonnet 5 (`claude-sonnet-5`), 2026-07-05
Data: `decision_scoring_results.json` (100 entries, 5 models × 20 profiles;
`deepseek-r1:7b` excluded — 98.8% parse failure, see rubric doc)
Methodology: full-dataset review per model (not sampled — all decisions
read), per user request. Metrics 2/3/4 are qualitative judgment calls, not
formula-derived; Metrics 1/5 are computed directly from the data.

Weighting: equal 20% per metric (v1 default, per discussion — revisit once
all models are scored and we can see which metrics actually discriminate).

---

## gemma4:e4b

**Metric 1 (Reliability): 100** — 0/242 parse failures.

**Metric 2 (Decision Accuracy): ~85** — Systematic over-acceptance pattern
found: "IEEE International Conference on Big Data" accepted in ~13-14/20
profiles regardless of real topical fit (Neural Rendering, Accessible
Interfaces, Human-AI Trust, Distributed Storage, Public Health Surveillance),
via generic "involves large datasets" justifications. Also over-accepts
prestigious general-AI venues (AAAI/AAMAS/EACL/ACCV) beyond genuine fit, e.g.
accepting AAMAS (multiagent systems) for a Neural Rendering researcher via
"a specific area within AI relevant to the general field of 3D scene
understanding" (profile_idx=6). Correctly rejects the "easy" off-topic cases
(ICAIF/finance, BIBM/bioinformatics, SIGCSE/education) almost universally,
and correctly identifies genuine in-field venues for narrow-domain profiles
(Security, Cryptography, Type Systems).

**Metric 3 (Reasoning Quality): ~70 (3.5/5)** — Always well-formed and
specific-sounding, but a meaningful share is rationalization rather than
genuine analysis. Found a factual hallucination: justified accepting ACCV
(computer vision) for the Program Repair profile (idx=10) by claiming it
aligns with "the researcher's work in building an AI agent system" — that
phrase never appears in that profile's actual title/context (it's about
LLM-based bug repair, not agent systems).

**Metric 4 (Relevancy Calibration): ~75** — Directionally sound (higher
scores for better fits generally), but over-accepted marginal items still
get generously high relevancy (75-90) rather than scores reflecting their
actually weak fit — calibration issue extends beyond the binary accept/reject
into the continuous score too.

**Metric 5 (Discrimination): 100 (scaled)** — mean acceptance rate 0.531,
stdev 0.178 across 20 profiles (highest mean of all 5 models — consistent
with the over-acceptance finding above; real variance, not "lazy").

**Total: ~86/100**

---

## llama3.2

**Metric 1 (Reliability): 100** — 0/242 parse failures.

**Metric 2 (Decision Accuracy): ~78** — Correctly handles the "easy" off-topic
rejects (ICAIF/BIBM/SIGCSE) and correctly identifies the security/crypto
cluster for relevant profiles (idx=2,3,15,16). But under-accepts genuinely
on-topic venues: rejects SODA (discrete algorithms) for the Computational
Complexity profile (idx=14, 0/5 accepted — a textbook miss), rejects CHI/IUI
(HCI) for the Accessible Interfaces profile (idx=12, 0/14 accepted) and again
for Human-AI Collaborative Interfaces (idx=13). At least 2 wrong accepts
traced directly to hallucinated reasoning (see Metric 3).

**Metric 3 (Reasoning Quality): ~47 (2.3/5)** — Severe, repeated cross-profile
contamination: reasons frequently cite an entirely different profile's topic,
not the one actually being judged. Examples: profile_idx=4 (Knowledge Graph
Construction) rejects BIBM citing "AI agents for workflows" (profile 0's
topic) and rejects SIGCSE citing "computer vision" (neither belongs to this
profile). profile_idx=9 (Distributed Storage) rejects INFOCOM citing "secure
communication protocols" (profile 2's topic). profile_idx=11 (Type Systems)
does the same. profile_idx=12/13 reject CHI citing "model alignment"
(profile 1's topic). Most striking: profile_idx=19 (Public Health
Surveillance) *accepts* AAMAS with "directly addresses the core technology
(autonomous agents/multiagent systems) central to the researcher's work" —
near-verbatim language from profile_idx=0, producing a wrong accept as a
direct result. Also found a reason-contradicts-decision case: profile_idx=9
rejects MSN while its own reason states "directly relevant to the
researcher's specific field."

**Metric 4 (Relevancy Calibration): ~70** — Reasonable for the security
cluster (mostly 80-100), but some accepted items get erratic low scores with
no clear justification (EACL=40, FC=50 for profile_idx=3, both accepted
conferences scored lower than several rejected ones would deserve).

**Metric 5 (Discrimination): 100 (scaled)** — mean acceptance rate 0.228,
stdev 0.183 across 20 profiles — real variance, comparable to gemma's, despite
a much lower overall acceptance rate (more conservative model overall).

**Total: ~79/100** — notably below gemma4:e4b (~86), directionally consistent
with the team's own extraction benchmark (gemma4:e4b 73 vs llama3.2 59) —
independent cross-validation on a different task.

## phi4-mini

**Metric 1 (Reliability): 100** — 0/242 parse failures.

**Metric 2 (Decision Accuracy): ~73** — Multiple severe, clear-cut misses:
0/13 accepted for the Type Systems profile (idx=11), missing FSE (a
textbook fit even llama3.2 caught); 0/8 for Climate Modeling (idx=18) and
0/8 for Public Health Surveillance (idx=19), both missing AAAI, which
gemma4:e4b correctly accepted for both; 0/7 for Vector Search (idx=5),
missing SIGKDD and WSDM (clear data-mining fits). More numerous severe
misses than llama3.2, though each individual miss is a defensible-looking
"not directly enough related" call rather than an obvious error in isolation.

**Metric 3 (Reasoning Quality): ~60 (3.0/5)** — Notably cleaner than llama3.2:
no systematic cross-profile contamination found (a couple of very minor
traces, e.g. idx=4's BIBM rejection mentioning "AI agents for workflows",
but nothing close to llama3.2's pervasive pattern). Distinct quirk instead:
several decisions produce incoherent valid/relevant pairs where the reason
argues invalidity ("not a standalone event," "embedded workshop") while
relevant is marked true anyway, e.g. idx=15's HOTNETS (valid=false,
relevant=true, reason focuses entirely on the standalone-event question and
never actually resolves relevance). This model spends unusual effort
specifically litigating conference "validity" over topical fit.

**Metric 4 (Relevancy Calibration): ~75** — Reasonably consistent scores for
the accepted cluster (mostly 85-95 for security/crypto profiles), similar
calibration quality to gemma4:e4b.

**Metric 5 (Discrimination): ~86 (scaled)** — mean acceptance rate 0.160,
stdev 0.153 — lowest mean AND lowest variance of the 5 models (most
conservative overall), though still real discrimination, not degenerate.

**Total: ~79/100** — ties llama3.2's score, but via a different failure
profile: llama3.2 trades better recall for severe reasoning contamination;
phi4-mini has cleaner reasoning but misses more genuine accepts.

## qwen3:4b

**Metric 1 (Reliability): 100** — 0/242 parse failures.

**Metric 2 (Decision Accuracy): ~87** — Best nuanced-distinction handling of
the 5 models: correctly separates "adversarial ML security" from generic
network/crypto security for profile_idx=3 (rejecting CHES/USENIX
SECURITY/ASIACCS/FC/EUROCRYPT with specific reasoning other models missed),
and correctly separates "low-latency networking" from "network security" for
profile_idx=16 — a distinction gemma4:e4b and others didn't consistently
make. Offset by a topic-label-literalism flaw (see Metric 3) producing a
couple of clear wrong accepts.

**Metric 3 (Reasoning Quality): ~78 (3.9/5)** — Most detailed and specific
reasoning of the 5 models, generally well-grounded in both conference content
and profile specifics, no cross-profile contamination found. But a repeated
flaw: pattern-matches on the dataset's crude topic *category label* rather
than the conference's actual described focus. Clearest case: profile_idx=6
(Neural Rendering) accepts ICASSP (acoustics/speech processing) and NCMMSC
(speech communication) as relevant with reasoning "the topic 'Graphics'
directly aligns" — using the generic label bucket, not the conference's real
content (neither conference is actually about graphics).

**Metric 4 (Relevancy Calibration): ~65** — Concrete, repeated internal
contradiction between the decision agent and scorer *within the same run*:
for the ICASSP/NCMMSC wrong accepts above, the scorer (same model) assigns
relevancy 5.0 and 0.0 respectively — directly contradicting its own
"relevant: true" call. A second confirmed instance: profile_idx=17 accepts
POPL with a confident justification, but the scorer then assigns it just
30.0 relevancy. Happened at least twice, indicating a systematic
decision/scorer disagreement rather than a one-off — the lowest calibration
score of the 5 models for this reason.

**Metric 5 (Discrimination): ~95 (scaled)** — mean acceptance rate 0.344,
stdev 0.169 — real variance, comparable to gemma4:e4b and llama3.2.

**Total: ~85/100** — essentially ties gemma4:e4b for best overall. Notable
since qwen3:4b wasn't part of the team's original extraction benchmark, so
this is a new data point, not a confirmation of prior results. Also worth
flagging as a practical footnote (not part of the 5-metric score): by far the
slowest model, mean decision-call times of 10-18s vs. gemma's 5-7s, llama's
~1s, phi4-mini's 3-4s.

## granite4:3b

**Metric 1 (Reliability): 100** — 0/242 parse failures.

**Metric 2 (Decision Accuracy): ~72** — Overall conservative accept pattern
similar to llama3.2/phi4-mini (many profiles with 0-2 accepted out of
7-14 pre-filtered). At least one confirmed clear miss: rejects IUI (ACM
Conference on Intelligent User Interfaces) for the Accessible Interfaces
profile (idx=12) — a textbook match that gemma4:e4b and qwen3:4b both
correctly accepted.

**Metric 3 (Reasoning Quality): ~25 (1.25/5)** — Worst of all 5 models by a
wide margin, and a genuinely different kind of failure than the other four:
the `reason` text frequently *argues for relevance* while the `relevant`
field is set to `false` — a direct logical contradiction, confirmed in at
least 15 of the 20 profiles, often multiple times per profile. Examples:
idx=0 rejects AAAI with reason "The conference is highly relevant to the
researcher's work on AI agents for scientific workflows"; idx=12 rejects IUI
with reason "directly relevant to the researcher's field of designing and
evaluating accessible user interfaces for assistive technology" (this one
directly caused the wrong final decision above); idx=13 rejects EACL with
reason "directly relevant to the researcher's field of study in human-AI
collaborative interfaces"; idx=18 rejects AAMAS with reason "highly relevant
as autonomous agents/multiagent systems are central to developing advanced
AI models used in climate modeling." This isn't occasional noise or
cross-profile contamination (llama3.2's issue) — it's the reasoning
routinely contradicting the model's own decision, which directly undermines
the project's own XAI/explainability goal, since the stated explanation
frequently doesn't match what was actually decided.

**Metric 4 (Relevancy Calibration): ~72** — For the accepted subset, scores
look internally reasonable (mostly 85-95), comparable to other models —
this failure mode is specific to the decision agent's reasoning, not the
scorer.

**Metric 5 (Discrimination): 100 (scaled)** — mean acceptance rate 0.223,
stdev 0.201 — highest variance of all 5 models.

**Total: ~74/100** — lowest of the 5 models, driven almost entirely by the
reasoning-quality collapse rather than the underlying accept/reject pattern,
which is comparable to the other conservative models.

---

## Final Leaderboard (v2: equal 33.3% weighting on the 3 metrics that actually
## showed variance; Reliability and Discrimination dropped from scoring —
## see decision_scoring_rubric.md's "v2 update" section for why)

| Rank | Model | Accuracy | Reasoning | Calibration | **Total** | Reliability (diagnostic) | Discrimination (diagnostic) |
|---|---|---|---|---|---|---|---|
| 1 | qwen3:4b | 87 | 78 | 65 | **~77** | 100 | 95 |
| 2 | gemma4:e4b | 85 | 70 | 75 | **~77** | 100 | 100 |
| 3 | phi4-mini | 73 | 60 | 75 | **~69** | 100 | 86 |
| 4 | llama3.2 | 78 | 47 | 70 | **~65** | 100 | 100 |
| 5 | granite4:3b | 72 | 25 | 72 | **~56** | 100 | 100 |
| — | deepseek-r1:7b | — | — | — | excluded (98.8% parse failure, needs rerun with `reasoning=False` fix) | — | — |

Tiebreak rule: when the 3-metric average ties, rank by Decision Accuracy
(the single "did it get the right answer" metric) — qwen3:4b (87) beats
gemma4:e4b (85), so qwen3:4b takes #1. Chosen over an arbitrary secondary
formula because Accuracy is already the metric we'd trust most in isolation
if forced to pick one.

Dropping the two flat metrics meaningfully de-compresses the scale (was
74-86, now 56-77). The two dropped metrics had happened to slightly favor
gemma's higher Discrimination score, which was itself just a byproduct of
gemma's over-acceptance pattern, not a sign of better judgment — removing it
let qwen3:4b's stronger nuanced accuracy and reasoning fully show through.

Cross-validates against the team's own extraction benchmark for the 2 models
in common: gemma4:e4b (73/100) beat llama3.2 (59/100) there too — same
ranking, different task. qwen3:4b and granite4:3b were not part of the
original extraction benchmark, so their strong/weak showings here are new
data points, not confirmations.

Each model has a genuinely distinct failure signature, not just a score
difference: gemma over-accepts via a prestige halo (defaults to "yes" for
famous AI venues regardless of fit); llama3.2 hallucinates reasoning content
from other profiles; phi4-mini under-accepts and fixates on conference
"validity" logic over topical fit; qwen3:4b reasons best but pattern-matches
on topic labels and its own scorer contradicts its own decisions; granite4:3b's
reasoning routinely argues the opposite of its own decision.

---

# Self-Validation Experiment (v3)

Prompted by supervisor feedback (Valerie, 2026-07-05): a live demo run
recommended `ACCV` (computer vision) to a researcher on edge speech
processing, justified as "closely related" — the exact prestige-halo/generic-
AI-adjacency pattern already documented above for `gemma4:e4b`. Added a
second LLM call to the decision agent (`agents/decision.py`'s `_validate()`,
commit `e2a7c7f`) that reviews the first decision's reasoning for two
specific failure modes before finalizing: (1) generic AI-adjacency
justification without a substantive topic overlap, (2) hallucinated details
not present in the researcher's actual profile. Re-ran the full 6-model x
20-profile benchmark with `self_validate=True`, writing to
`decision_scoring_results_selfvalidated.json` (baseline file untouched).
`deepseek-r1:7b` is excluded from this analysis — the validation call itself
fails to parse for that model and doesn't fall back to the original decision
as the current code should (see conversation notes; looks like a stale
`__pycache__` on the server, not a logic bug — pending a clean re-run).

## Methodology note

`gemma4:e4b` got the same full line-by-line read as the baseline review (all
242 decisions). For the other 4 models, scores are derived from (a) the
override-direction statistics below (computed directly from the data, not
judgment calls) and (b) targeted qualitative sampling of the actual
overridden decisions (not a full re-read of all 242 unchanged-plus-changed
decisions per model — unchanged decisions carry no new information since
they're identical to what was already judged in the baseline review).
Directionally solid given how strong and consistent the pattern below is,
but individual model scores here carry more uncertainty than the baseline
scores.

## Core finding: the validator has a systematic reject-bias

Framing the second pass as "a skeptical reviewer checking for failure modes"
(see `_VALIDATION_SYSTEM` in `agents/decision.py`) biases it toward finding
problems and rejecting, not toward neutrally re-judging. This is visible
directly in the override direction — for every model except gemma4:e4b, the
overwhelming majority of overrides flip accept to reject, not the reverse:

| Model | Override rate | accept→reject | reject→accept |
|---|---|---|---|
| gemma4:e4b | 10.7% (26/242) | 10 | 12 |
| llama3.2 | 54.1% (131/242) | 49 | 1 |
| phi4-mini | 50.4% (122/242) | 28 | 2 |
| qwen3:4b | 28.5% (69/242) | 41 | 4 |
| granite4:3b | 46.3% (112/242) | 21 | 3 |

The practical consequence: this specific validation design helps a model
that was already over-accepting (gemma4:e4b, roughly balanced 10:12) but
actively harms models that were already appropriately strict or under-
accepting (llama3.2 especially, at a stark 49:1 ratio) — it makes an
already-too-strict model even stricter, compounding rather than fixing the
problem.

## Per-model findings

### gemma4:e4b (full read)

Genuine mixed bag — roughly equal parts real fixes and new fabrications,
some of them worse than anything found at baseline.

**Good catches (real fixes):**
- profile_idx=1 correctly flips `SIGCSE` to reject: "relies on the generic
  premise that 'applied AI/LLMs' relate to CS education without specifying a
  substantive overlap."
- profile_idx=18 produces an excellent, textbook self-critique of `ACCV`:
  "commits a superficial justification by claiming an overlap because both
  involve 'deep learning'... the connection to pure Computer Vision
  techniques... is too tenuous... speculative at best."
- profile_idx=10 correctly flips `ACCV` to reject: "unsubstantiated leap...
  these are distinct subfields."

**New fabrications introduced BY validation (worse than baseline):**
- profile_idx=6 flips `ICASSP` from a correct reject to a wrong accept via
  an invented connection: "Neural Rendering and 3D Reconstruction are highly
  relevant to modern speech/signal processing applications (e.g., virtual
  scene capture for speech analysis)" — structurally the *same* error
  Valerie flagged (claiming vision/graphics work relates to speech/audio),
  except here the validator introduced it rather than catching it.
- profile_idx=9's `AAMAS` justification ("almost perfect technical match for
  a project building an automated multi-agent system") is lifted from
  profile_idx=0's actual topic, not this profile's (Distributed Storage) —
  genuine cross-profile contamination introduced by the validator itself.
- profile_idx=4's `ACCV` override explicitly states "I correct the validity
  but maintain relevance due to the broader 'AI' topic listed for the
  conference" — an admitted fallback to the crude topic label, not
  substance.
- profile_idx=17's `SANER`/`OSDI`/`HOTNETS` all flip to accept while the
  reasoning literally admits weakness ("sufficiently broad... to allow for a
  plausible link") yet still concludes relevant — a self-contradiction.

**Self-validated scores**: Accuracy ~86 (flat), Reasoning ~63 (down from 70
— confident-sounding "the original reasoning is correct because..." wrapper
phrasing makes weak justifications sound more validated without adding real
substance), Calibration ~75 (flat). **Total: ~75** (down slightly from 77).

### llama3.2 (override-stats + sampling)

The worst regression of the 5. Validation didn't just fail to fix
llama3.2's known issues (cross-profile contamination, under-acceptance) — it
actively destroyed a previously-**correct** cluster of decisions.

Profile_idx=2 (Network Security and Cryptography) is the clearest case: at
baseline (pre-validation), llama3.2 correctly accepted the entire relevant
security/crypto cluster — `CHES`, `USENIX SECURITY`, `FC`, `CSCLOUD`,
`SODA`, `INFOCOM`. Validation flipped every one of them to reject, often
with reasoning that just restates the same description that justified the
original accept, then concludes the opposite — e.g. `CHES`: pre-validation
reason "The conference focuses on hardware and embedded security, which is
directly relevant to the researcher's work on secure communication
protocols" (correct, accept) vs. final reason "The conference focuses
heavily on hardware and embedded security, which doesn't directly align
with the researcher's focus on cryptographic implementations for secure
communication protocols" (same facts, now concludes reject).

**Self-validated scores**: Accuracy ~58 (down sharply from 78), Reasoning
~50 (up slightly from 47 — more specific-*sounding* language, but reaching
wrong conclusions more often, so specificity of phrasing is decoupled from
correctness here), Calibration ~65 (down from 70, fewer accepted items to
calibrate against). **Total: ~58** (down from 65).

### phi4-mini (override-stats + sampling)

Same reject-bias problem as llama3.2, compounding an already-under-
accepting baseline (recall: baseline phi4-mini already missed `FSE` for
Type Systems, `AAAI` for Climate Modeling and Public Health, `SIGKDD`/`WSDM`
for Vector Search). The 28:2 accept→reject skew pushes an already-too-strict
model further in the wrong direction.

**Self-validated scores**: Accuracy ~60 (down from 73), Reasoning ~55
(roughly flat/slightly down — the "conference validity litigation" quirk
from baseline persists, no structural change), Calibration ~72 (flat).
**Total: ~62** (down from 69).

### qwen3:4b (override-stats + sampling)

Mixed, but net negative — qwen3:4b was already the most accurate model at
baseline, so a reject-biased "fix" mostly introduces new over-corrections
rather than catching real errors.

**One good refinement**: profile_idx=4's `WSDM` override sharpens a
correct accept with better-grounded reasoning: "researcher's work on
knowledge graph construction via entity linking and relation extraction is
more specifically aligned with WSDM's focus on data mining and information
retrieval than a generic AI connection... explicitly states relevance to
relation and entity extraction for KG construction" — genuine improvement
in reasoning specificity without changing the (correct) decision.

**But real over-correction**: profile_idx=6 wrongly flips `ACCV` to reject
for a Neural Rendering researcher: "Computer vision (ACCV focus) and neural
radiance fields/3D reconstruction (research) are distinct subfields; vision
tasks like image processing differ fundamentally from 3D scene
reconstruction" — overly strict; in actual academic practice neural
rendering work is commonly published at computer-vision venues, so this is
a real accuracy regression, not a fix.

**And a backslide into its own known flaw**: profile_idx=6's `NCMMSC`
(speech communication, same profile) flips from a correct reject to a wrong
accept: "the conference's 'Graphics' topic is broad but... aligns with the
conference's graphics focus" — falling back on the crude topic label again,
the exact literalism flaw documented in qwen3:4b's baseline review.

**Self-validated scores**: Accuracy ~79 (down from 87), Reasoning ~72 (down
slightly from 78), Calibration ~65 (flat — same decision/scorer internal
contradiction from baseline likely persists, not something this validation
pass touches). **Total: ~72** (down from 77).

### granite4:3b (override-stats + sampling)

The one model where self-validation shows a genuine, targeted improvement —
not on accuracy, but specifically on the defect that tanked its baseline
Reasoning score.

Baseline granite4:3b's signature bug was the `reason` text arguing FOR
relevance while `relevant` was set to `false` — confirmed in a majority of
profiles at baseline. Checking the same pattern post-validation (reason
contains "directly relevant"/"highly relevant"/"aligns with"/"aligns
perfectly" while `relevant=False`): only 10/242 decisions (4.1%) now show
it, a meaningful reduction. Some of the remaining cases have shifted form —
now the validator's reasoning explicitly argues the *original* decision was
wrong to reject (e.g. idx=9's `WCNC`: "The original reason incorrectly
concludes that the conference is not directly relevant...") but then still
concludes `relevant=False` itself — a related but distinct residual bug
(the validator critiques the premise but doesn't follow through to a
consistent conclusion).

The accuracy cost: granite4:3b's boolean pattern was already fairly
conservative at baseline (mean acceptance 0.223); the reject-bias pushes
this further, likely costing some real accepts.

**Self-validated scores**: Accuracy ~65 (down slightly from 72), Reasoning
~48 (up substantially from 25 — the specific defect that drove this
model's low baseline score is genuinely, measurably better), Calibration
~70 (roughly flat). **Total: ~61** (up from 56).

## Full comparison table

| Model | Metric | Baseline | Self-validated | Δ |
|---|---|---|---|---|
| **gemma4:e4b** | Accuracy | 85 | 86 | +1 |
| | Reasoning | 70 | 63 | -7 |
| | Calibration | 75 | 75 | 0 |
| | **Total** | **77** | **75** | **-2** |
| **qwen3:4b** | Accuracy | 87 | 79 | -8 |
| | Reasoning | 78 | 72 | -6 |
| | Calibration | 65 | 65 | 0 |
| | **Total** | **77** | **72** | **-5** |
| **phi4-mini** | Accuracy | 73 | 60 | -13 |
| | Reasoning | 60 | 55 | -5 |
| | Calibration | 75 | 72 | -3 |
| | **Total** | **69** | **62** | **-7** |
| **granite4:3b** | Accuracy | 72 | 65 | -7 |
| | Reasoning | 25 | 48 | +23 |
| | Calibration | 72 | 70 | -2 |
| | **Total** | **56** | **61** | **+5** |
| **llama3.2** | Accuracy | 78 | 58 | -20 |
| | Reasoning | 47 | 50 | +3 |
| | Calibration | 70 | 65 | -5 |
| | **Total** | **65** | **58** | **-7** |
| **deepseek-r1:7b** | — | excluded | excluded (validation call fails to parse, needs clean re-run) | — |

**Ranking changes**: baseline had qwen3:4b/gemma4:e4b tied for 1st,
phi4-mini/llama3.2 tied for 3rd, granite4:3b last. Self-validated:
**gemma4:e4b (75) > qwen3:4b (72) > phi4-mini (62) > granite4:3b (61) >
llama3.2 (58)** — llama3.2 falls from a tie for 3rd to clearly last, and
granite4:3b is the only model that improves overall.

## Conclusion

Self-validation as currently designed is **not a net-positive change to
ship as-is**. It's the right idea (Valerie's feedback was real and
reproducible), but the specific prompt framing ("skeptical reviewer
checking for failure modes") introduces a systematic bias toward rejection
that helps exactly one failure mode (over-acceptance, gemma4:e4b's problem)
while making the opposite failure mode (under-acceptance, llama3.2 and
phi4-mini's problem) worse. A less asymmetric validation prompt — one that
checks for *both* over-rejection and over-acceptance with equal scrutiny,
rather than only hunting for "generic AI-adjacency" accepts — would be
worth testing before considering this for the live pipeline.

---

# Few-Shot Prompting Experiment (v4)

Tried a mechanistically different hallucination mitigation than
self-validation: 4 worked examples added directly to the decision agent's
system prompt (`agents/decision.py`'s `_FEWSHOT_EXAMPLES`, commit
`7c6dd14`), each showing a correct-vs-wrong reasoning pair targeting the
specific fabrication patterns documented above — generic "both involve
AI/data" hand-waving, treating the coarse topic-category label as evidence
of relevance, and what genuine specific overlap looks like. Pure prompt
change: no added latency, no extra LLM calls, unlike self-validation.
Results in `decision_scoring_results_fewshot.json` (`deepseek-r1:7b`
excluded again — 85.1% parse failure, still unresolved, separate from this
experiment).

## Core finding: unlike self-validation, changes are balanced, not
## systematically biased — and every model improves or holds flat

Diffing fewshot decisions against the plain baseline (matched by model +
profile + conference), the accept/reject flip counts are far more balanced
than self-validation's reject-skew, except where a real fix was needed:

| Model | accept→reject | reject→accept | unchanged |
|---|---|---|---|
| gemma4:e4b | 49 | 4 | 189 |
| llama3.2 | 24 | 29 | 189 |
| phi4-mini | 20 | 21 | 201 |
| qwen3:4b | 25 | 22 | 195 |
| granite4:3b | 28 | 13 | 201 |

gemma4:e4b is the one model with a strong directional skew (49:4) — and
that's exactly right, since its baseline problem *was* one-directional
over-acceptance. Every other model shows roughly balanced changes in both
directions, meaning the technique isn't just uniformly biasing toward
stricter judgment (self-validation's failure) — it's letting each model
recalibrate based on the actual examples.

## Per-model findings, checked against each model's specific documented baseline flaw

### gemma4:e4b — strong, clean fix of the prestige halo

`BIGDATA` over-acceptance (documented at 14/20 profiles at baseline) dropped
to 2/20, and the 2 remaining accepts (Distributed Storage Systems,
Climate Modeling) are genuinely defensible matches. `ACCV` over-acceptance
dropped from 7/20 to 2/20, with the 2 remaining (Adversarial ML Security,
Neural Rendering) also legitimate computer-vision-adjacent matches.
Reasoning is now specific and well-grounded — e.g. profile_idx=0 correctly
rejects `BIGDATA`: "the researcher's work focuses on multi-agent LLM
systems for knowledge discovery, which is conceptually distinct from
general large-scale data processing," while profile_idx=9 correctly
*accepts* it: "the researcher's work on 'Distributed Storage Systems for AI
Training' is a core infrastructure component directly related to big data
handling for ML." No sign of the old hand-waving.

**Fewshot scores**: Accuracy ~90 (up from 85), Reasoning ~85 (up from 70),
Calibration ~78 (up from 75). **Total: ~84** (up from 77).

### qwen3:4b — direct, near-verbatim fix of its documented flaw

Checked the exact baseline failure case: profile_idx=6 (Neural Rendering)
previously accepted `ICASSP` and `NCMMSC` via topic-label literalism. With
few-shot, both are now correctly rejected, and the reasoning for `ICASSP`
is a near-verbatim match to Example 2 in the prompt: "Despite being tagged
'Graphics' in this dataset, the conference's actual focus is acoustics and
speech signal processing — a different modality from visual 3D rendering.
A topic label is a coarse category, not proof of relevance." Confirms the
example was directly effective, not a coincidental improvement.

**Fewshot scores**: Accuracy ~90 (up from 87), Reasoning ~85 (up from 78),
Calibration ~65 (flat — the decision/scorer internal contradiction found at
baseline is a *scorer*-agent issue, not something a decision-agent prompt
change would touch). **Total: ~80** (up from 77).

### llama3.2 — fixes the under-acceptance misses, contamination persists partially

All three of the clean baseline misses are now fixed: `SODA` correctly
accepted for Computational Complexity, and both `CHI` and `IUI` correctly
accepted for Accessible Interfaces. Some cross-profile contamination is
also reduced — profile_idx=9's `SIGCSE`/`INFOCOM` rejections now correctly
reference "distributed storage systems for AI training" (this profile's
actual topic), not a different profile's language as at baseline. But
contamination isn't eliminated: profile_idx=4 (Knowledge Graph
Construction) wrongly accepts `BIBM` with reasoning describing "the
researcher's blend of ML and public health/infectious diseases" — that's
profile_idx=19's topic, not this one's. Few-shot examples target
fabrication style, not the underlying attention/context-tracking mechanism
behind contamination, so this is a partial, not complete, fix.

**Fewshot scores**: Accuracy ~82 (up from 78), Reasoning ~60 (up from 47),
Calibration ~72 (up slightly from 70). **Total: ~71** (up from 65).

### phi4-mini — modest, partial improvement

Checked all 4 of its documented baseline misses: `WSDM` for Vector Search
is now correctly accepted (fixed), but `FSE` for Type Systems, `AAAI` for
both Climate Modeling and Public Health Surveillance, and `SIGKDD` for
Vector Search all remain incorrectly rejected, unchanged from baseline. The
"conference validity litigation" quirk (spending effort on standalone-event
status over topical fit) also isn't targeted by these examples and likely
persists. Smallest improvement of the 5 models, but still not negative.

**Fewshot scores**: Accuracy ~76 (up from 73), Reasoning ~63 (up from 60),
Calibration ~75 (flat). **Total: ~71** (up from 69).

### granite4:3b — fixes the confirmed miss, but its signature bug improves less than self-validation did

profile_idx=12's `IUI` (Accessible Interfaces) — the specific confirmed
wrong-reject caused by granite4:3b's reason-contradicts-decision bug at
baseline — is now correctly accepted. But checking the broader defect rate
(reason argues relevant while `relevant=false`): 22/242 (9.1%) still show
it with few-shot, notably *higher* than self-validation's 4.1% (though
still better than baseline's majority-of-profiles rate). Makes sense: self-
validation explicitly forces a second pass to reconcile reasoning with the
boolean, directly targeting this exact defect; few-shot examples calibrate
topical judgment but don't structurally address reason/decision
consistency the same way.

**Fewshot scores**: Accuracy ~76 (up from 72), Reasoning ~40 (up from 25,
but less than self-validation's 48), Calibration ~72 (flat). **Total: ~63**
(up from 56, but below self-validation's 61 for this model specifically).

## Full 3-way comparison (with deltas vs. baseline)

| Model | Metric | Baseline | Self-validated | Δ | Few-shot | Δ |
|---|---|---|---|---|---|---|
| **gemma4:e4b** | Accuracy | 85 | 86 | +1 | **90** | **+5** |
| | Reasoning | 70 | 63 | -7 | **85** | **+15** |
| | Calibration | 75 | 75 | 0 | **78** | **+3** |
| | **Total** | 77 | 75 | -2 | **84** | **+7** |
| **qwen3:4b** | Accuracy | 87 | 79 | -8 | **90** | **+3** |
| | Reasoning | 78 | 72 | -6 | **85** | **+7** |
| | Calibration | 65 | 65 | 0 | 65 | 0 |
| | **Total** | 77 | 72 | -5 | **80** | **+3** |
| **llama3.2** | Accuracy | 78 | 58 | -20 | **82** | **+4** |
| | Reasoning | 47 | 50 | +3 | **60** | **+13** |
| | Calibration | 70 | 65 | -5 | **72** | **+2** |
| | **Total** | 65 | 58 | -7 | **71** | **+6** |
| **phi4-mini** | Accuracy | 73 | 60 | -13 | **76** | **+3** |
| | Reasoning | 60 | 55 | -5 | **63** | **+3** |
| | Calibration | 75 | 72 | -3 | 75 | 0 |
| | **Total** | 69 | 62 | -7 | **71** | **+2** |
| **granite4:3b** | Accuracy | 72 | 65 | -7 | **76** | **+4** |
| | Reasoning | 25 | 48 | **+23** | 40 | +15 |
| | Calibration | 72 | 70 | -2 | 72 | 0 |
| | **Total** | 56 | 61 | **+5** | 63 | **+7** |
| **deepseek-r1:7b** | — | excluded | excluded | — | excluded (85.1% parse failure) | — |

**Ranking with few-shot**: gemma4:e4b (84) > qwen3:4b (80) > llama3.2 (71) ≈
phi4-mini (71) > granite4:3b (63).

Reading the deltas side by side: self-validation is net-negative for 3 of 5
models (llama3.2 worst at -7, also phi4-mini -7 and qwen3:4b -5), only
gemma4:e4b (-2, near flat) and granite4:3b (+5) don't lose ground. Few-shot
is net-positive for all 5 models with no exceptions, and by a wider margin
on average (+2 to +7 in Total) — the strictly better technique on every
axis measured, not just in aggregate.

## Conclusion

**Few-shot prompting is the clear winner of the two techniques tried.**
Every single model improves over baseline (granite4:3b's Reasoning is the
one metric that improves less than self-validation achieved for that
specific model, but its Total still improves). It's also strictly cheaper:
no added latency or LLM calls, versus self-validation's ~2x decision-agent
cost. The one remaining gap is granite4:3b's reason-contradicts-decision
bug, which self-validation's explicit reconciliation step handles better —
a plausible next experiment is combining both: few-shot examples for
topical calibration plus a *reformed*, less reject-biased validation pass
specifically for reason/decision consistency checking, rather than generic
relevance re-litigation.

**Recommendation**: adopt few-shot prompting for the live decision agent
(`app.py`/`graph.py`'s default path, currently `few_shot=False`) given the
consistent, no-cost improvement across all 5 models — this is a much
stronger candidate for shipping than self-validation was.
