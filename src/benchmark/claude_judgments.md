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

(pending)

## phi4-mini

(pending)

## qwen3:4b

(pending)

## granite4:3b

(pending)
