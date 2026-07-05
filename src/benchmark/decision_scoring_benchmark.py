"""Decision agent + scorer benchmark runner.

Runs each of the 6 selected models against all 20 synthetic profiles in
decision_scoring_profiles.py, using the same CCF-Deadlines conference data
the live pipeline uses. Produces one combined JSON file with raw decision +
scoring output for all 6 x 20 = 120 runs.

This captures raw data only -- no groundtruth, no scoring rubric attached.
Designing the rubric to evaluate this data is a separate, later task.

Usage (from repo root):
    python src/benchmark/decision_scoring_benchmark.py

Requires all 6 models pulled and Ollama running (bash scripts/start_ollama.sh
on the cluster) -- see MODELS below; 4 of these are not part of the
project's default pull list yet.

This is a long run (likely hours, not minutes): decision.py calls the LLM
once per conference, sequentially, per profile, per model. Run it in a
screen session. It saves incrementally after every (model, profile)
combination and skips already-completed ones on restart, so it's safe to
interrupt and resume.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

_SRC = Path(__file__).parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agents.decision import run_decision_agent  # noqa: E402
from agents.scorer import run_scorer  # noqa: E402
from schemas.conference import UserPreferences  # noqa: E402
from tools.geocoding import geocode  # noqa: E402
from test_pipeline import load_conferences, _passes_topic_filter  # noqa: E402
from benchmark.decision_scoring_profiles import PROFILES  # noqa: E402

OLLAMA_URL = "http://localhost:11434"
DATA_FILE = Path(__file__).parent.parent.parent / "future_conferences.json"

# Which hallucination-mitigation experiment to run, if any. Each writes to
# its own results file so runs stay independently comparable against the
# plain baseline (mode="baseline", decision_scoring_results.json) -- see
# src/benchmark/claude_judgments.md for the write-up of each experiment.
#   "baseline"      -- no mitigation, the original run
#                      (decision_scoring_results.json)
#   "selfvalidated" -- second LLM call scrutinizes the first decision before
#                      finalizing (agents/decision.py's _VALIDATION_SYSTEM).
#                      Roughly doubles decision-agent latency. Found to help
#                      over-accepting models but hurt already-strict ones
#                      (see claude_judgments.md's "Self-Validation Experiment").
#   "fewshot"       -- 4 worked examples added to the system prompt
#                      (agents/decision.py's _FEWSHOT_EXAMPLES). Pure prompt
#                      change, no added latency or calls.
MODE = "fewshot"
RESULTS_FILE = (
    Path(__file__).parent / "decision_scoring_results.json"
    if MODE == "baseline"
    else Path(__file__).parent / f"decision_scoring_results_{MODE}.json"
)

MODELS = [
    "gemma4:e4b",
    "llama3.2",
    "phi4-mini",
    "qwen3:4b",
    "granite4:3b",
    "deepseek-r1:7b",
]


def _check_ollama() -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(f"{OLLAMA_URL}/api/tags"), timeout=3)
    except Exception:
        print(f"[ERROR] Ollama is not running at {OLLAMA_URL}. Run: bash scripts/start_ollama.sh")
        sys.exit(1)


def _load_existing_results() -> list[dict]:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))["results"]
    return []


def _save_results(results: list[dict]) -> None:
    RESULTS_FILE.write_text(
        json.dumps(
            {
                "run_at": datetime.now().isoformat(),
                "models": MODELS,
                "profile_count": len(PROFILES),
                "mode": MODE,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    _check_ollama()

    all_conferences = load_conferences(DATA_FILE)
    print(f"[*] Loaded {len(all_conferences)} conferences from {DATA_FILE.name}")

    profiles = [UserPreferences(**p) for p in PROFILES]
    print(f"[*] {len(profiles)} profiles x {len(MODELS)} models = {len(profiles) * len(MODELS)} runs")

    # Pre-geocode every profile once, up front -- avoids re-geocoding the
    # same address once per model (6x redundant Nominatim calls otherwise).
    print("[*] Geocoding profile addresses...")
    for profile in profiles:
        if profile.coordinates is None:
            profile.coordinates = geocode(profile.address)

    results = _load_existing_results()
    done = {(r["model"], r["profile_idx"]) for r in results}
    if done:
        print(f"[*] Resuming: {len(done)} run(s) already completed, skipping those.")

    total_runs = len(MODELS) * len(profiles)
    run_num = 0

    for model in MODELS:
        for idx, profile in enumerate(profiles):
            run_num += 1
            if (model, idx) in done:
                continue

            print(f"\n[{run_num}/{total_runs}] model={model}  profile={idx}: {profile.research_title}")

            pre_filtered = [c for c in all_conferences if _passes_topic_filter(c, profile)]

            t0 = time.perf_counter()
            error = None
            try:
                accepted, rejected, decision_timing = run_decision_agent(
                    pre_filtered, profile, model, OLLAMA_URL,
                    self_validate=(MODE == "selfvalidated"),
                    few_shot=(MODE == "fewshot"),
                )
                if accepted:
                    scored, scorer_timing = run_scorer(accepted, profile, model, OLLAMA_URL)
                else:
                    scored = []
                    scorer_timing = {"calls": 0, "total_s": 0, "mean_s": 0, "min_s": 0, "max_s": 0}
            except Exception as exc:
                accepted, rejected, scored = [], [], []
                decision_timing = {}
                scorer_timing = {}
                error = str(exc)
                print(f"  [!] ERROR: {error}")

            elapsed = round(time.perf_counter() - t0, 2)

            result = {
                "model": model,
                "profile_idx": idx,
                "profile": {
                    "address": profile.address,
                    "research_title": profile.research_title,
                    "research_context": profile.research_context,
                },
                "pre_filtered_count": len(pre_filtered),
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "elapsed_s": elapsed,
                "decision_timing": decision_timing,
                "scorer_timing": scorer_timing,
                "error": error,
                "decisions": [
                    {
                        "name": c.name,
                        "acronym": c.acronym,
                        "topics": c.topics,
                        "core_rank": c.core_rank.value if c.core_rank else None,
                        "valid": c.decision.valid if c.decision else None,
                        "relevant": c.decision.relevant if c.decision else None,
                        "reason": c.decision.reason if c.decision else None,
                        # Only populated when SELF_VALIDATE=True and the
                        # validation pass actually ran -- lets us measure how
                        # often self-validation changed the outcome.
                        "pre_validation_valid": c.decision_pre_validation.valid
                        if c.decision_pre_validation else None,
                        "pre_validation_relevant": c.decision_pre_validation.relevant
                        if c.decision_pre_validation else None,
                        "pre_validation_reason": c.decision_pre_validation.reason
                        if c.decision_pre_validation else None,
                    }
                    for c in (accepted + rejected)
                ],
                "scored": [
                    {
                        "name": c.name,
                        "acronym": c.acronym,
                        "relevancy": c.scores.relevancy if c.scores else None,
                        "distance": c.scores.distance if c.scores else None,
                        "prestige": c.scores.prestige if c.scores else None,
                        "total": c.scores.total if c.scores else None,
                    }
                    for c in scored
                ],
            }
            results.append(result)
            _save_results(results)  # incremental save -- safe to interrupt/resume
            print(
                f"  [OK] accepted={len(accepted)} rejected={len(rejected)} "
                f"scored={len(scored)}  ({elapsed}s)"
            )

    print(f"\n[DONE] {len(results)} results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
