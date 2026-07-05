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
