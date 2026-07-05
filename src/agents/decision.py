"""Decision agent.

For each conference, asks the LLM two questions:
  1. Is this a real, standalone academic conference?
  2. Is it relevant to the candidate's research?

Returns a DecisionResult attached to the conference.
"""

from __future__ import annotations

import json
import re
import time

from langchain_ollama import ChatOllama

from schemas.conference import Conference, DecisionResult, UserPreferences


def _extract_json(text: str) -> str:
    """Strip <think>...</think> reasoning blocks (e.g. deepseek-r1, which
    emits these even under format="json") and markdown code fences before
    parsing — some models wrap JSON in these despite being told not to."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?\n?|\n?```", "", text)
    return text.strip()


_SYSTEM = """\
You are a strict academic advisor evaluating whether a researcher should attend a conference.
Given a conference and a researcher's profile, answer two questions:

  1. Is this a real, standalone academic conference? (not a workshop, seminar, journal, \
     summer school, or symposium embedded in another event)
  2. Is the conference topic DIRECTLY relevant to the researcher's specific field? \
     Only mark relevant=true if there is clear, specific topic overlap — not just a vague \
     or indirect connection. For example: a networking conference is NOT relevant to a \
     computer vision researcher. A general AI conference is only relevant if the researcher \
     works on AI topics specifically.

Return ONLY valid JSON — no explanation, no markdown fences.

Schema:
{
  "valid": true | false,
  "relevant": true | false,
  "reason": "one sentence explaining your decision"
}"""

# Four examples targeting the specific fabrication patterns documented in
# src/benchmark/claude_judgments.md: generic "both involve AI/data" hand-
# waving (examples 1, 4), treating the coarse topic-category label as
# evidence of relevance rather than checking actual content (example 2),
# and what a genuinely specific, grounded overlap looks like (example 3).
_FEWSHOT_EXAMPLES = """

Examples of correct vs incorrect reasoning:

Example 1 (reject — generic justification is not enough):
Conference: IEEE International Conference on Big Data (topics: Interdiscipline/Mixture/Emerging)
Researcher: "Neural Rendering and 3D Reconstruction" — neural radiance fields and differentiable rendering for photorealistic 3D scene reconstruction.
WRONG reasoning: "Relevant because both involve large-scale data processing."
CORRECT: {"valid": true, "relevant": false, "reason": "Big Data conferences address data storage/processing infrastructure generally; the researcher's work is specifically about rendering algorithms, with no shared methodology beyond both broadly 'processing data'."}

Example 2 (reject — a topic label is not evidence, check actual content):
Conference: IEEE International Conference on Acoustics, Speech, and Signal Processing (topics: Graphics)
Researcher: "Neural Rendering and 3D Reconstruction" — same profile as above.
WRONG reasoning: "The topic 'Graphics' listed for this conference aligns with the researcher's graphics-adjacent work."
CORRECT: {"valid": true, "relevant": false, "reason": "Despite being tagged 'Graphics' in this dataset, the conference's actual focus is acoustics and speech signal processing — a different modality from visual 3D rendering. A topic label is a coarse category, not proof of relevance."}

Example 3 (accept — this is what a genuine, specific overlap looks like):
Conference: ACM Knowledge Discovery and Data Mining (topics: Database/Data Mining/Information Retrieval)
Researcher: "Knowledge Graph Construction from Unstructured Text" — automates knowledge graph population using entity linking and relation extraction.
CORRECT: {"valid": true, "relevant": true, "reason": "The conference's core focus on data mining and information extraction directly covers entity linking and relation extraction, the specific techniques named in the researcher's own work — not just a generic 'both involve AI' connection."}

Example 4 (reject — being AI-adjacent in the broadest sense is not sufficient):
Conference: AAAI Conference on Artificial Intelligence (topics: Artificial Intelligence)
Researcher: "Energy-Efficient GPU Accelerator Design" — designs low-power accelerator architectures for deep learning inference.
WRONG reasoning: "Relevant because the researcher's work supports AI/deep learning."
CORRECT: {"valid": true, "relevant": false, "reason": "AAAI covers AI algorithms and models broadly; the researcher's work is specifically about hardware architecture for accelerating inference, a distinct systems/hardware subfield. The conference must share the researcher's specific technical focus, not just be AI-adjacent."}"""


def _system_prompt(few_shot: bool) -> str:
    return _SYSTEM + _FEWSHOT_EXAMPLES if few_shot else _SYSTEM


# Targets two specific failure modes observed in production and in the
# decision/scoring benchmark (src/benchmark/claude_judgments.md): (1) models
# treating "both are broadly AI/CS-adjacent" as sufficient grounds for
# relevance regardless of actual subfield mismatch (e.g. recommending a
# computer vision conference to a speech-processing researcher), and (2)
# reasoning that references details not actually present in the researcher's
# stated profile.
_VALIDATION_SYSTEM = """\
You are a skeptical reviewer double-checking another advisor's decision about whether a \
researcher should attend a conference.

You will see the conference, the researcher's profile, and the ORIGINAL decision with its \
stated reason. Check for two specific failure modes:

  1. Generic/superficial justification: the reason claims relevance based on both being \
     broadly "AI-related", "CS-related", or "involving data/computation" without a SPECIFIC, \
     substantive topic overlap. For example, "computer vision is closely related to speech \
     processing" is NOT a valid justification -- they are different modalities despite both \
     being AI subfields.
  2. Factual mismatch: the reason references details about the researcher's work that are not \
     actually present in their stated research title or context.

If the original reason exhibits either failure mode, correct the valid/relevant flags to reflect \
what a strict, specific-overlap standard would conclude, and explain what was wrong with the \
original reasoning. If the original reasoning holds up under scrutiny, confirm it unchanged.

Return ONLY valid JSON — no explanation, no markdown fences.

Schema:
{
  "valid": true | false,
  "relevant": true | false,
  "reason": "one sentence: either confirms the original reasoning, or explains what was wrong with it and states the corrected verdict"
}"""


def _llm(model: str, base_url: str) -> ChatOllama:
    # reasoning=False disables thinking mode on models that support it (e.g.
    # deepseek-r1). Without this, the default (None) leaves <think>...</think>
    # inline in response.content, and a reasoning model can spend its entire
    # response thinking without ever emitting the requested JSON -- observed
    # as a 98.8% parse-failure rate for deepseek-r1:7b in practice. No effect
    # on non-reasoning models.
    return ChatOllama(model=model, base_url=base_url, format="json", reasoning=False)


def _format_conference(conf: Conference) -> str:
    parts = [
        f"Name: {conf.name}",
        f"Acronym: {conf.acronym or 'N/A'}",
        f"Topics: {', '.join(conf.topics) if conf.topics else 'N/A'}",
        f"Description: {conf.description or 'N/A'}",
    ]
    if conf.location:
        parts.append(f"Location: {conf.location.city}, {conf.location.country}")
    return "\n".join(parts)


def _validate(
    conference: Conference,
    user_prefs: UserPreferences,
    original: DecisionResult,
    model: str,
    ollama_base_url: str,
) -> DecisionResult:
    llm = _llm(model, ollama_base_url)

    prompt = (
        f"{_VALIDATION_SYSTEM}\n\n"
        f"Conference:\n{_format_conference(conference)}\n\n"
        f"Researcher profile:\n"
        f"Research title: {user_prefs.research_title}\n"
        f"Research context: {user_prefs.research_context}\n\n"
        f"Original decision:\n"
        f"valid={original.valid}, relevant={original.relevant}\n"
        f"reason: {original.reason}"
    )

    try:
        response = llm.invoke(prompt)
        data = json.loads(_extract_json(response.content))
        return DecisionResult(
            valid=bool(data.get("valid", original.valid)),
            relevant=bool(data.get("relevant", original.relevant)),
            reason=data.get("reason", original.reason),
        )
    except Exception:
        # Validation call failed -- fall back to the original decision rather
        # than losing the whole result.
        return original


def decide(
    conference: Conference,
    user_prefs: UserPreferences,
    model: str,
    ollama_base_url: str,
    self_validate: bool = False,
    few_shot: bool = False,
) -> Conference:
    llm = _llm(model, ollama_base_url)

    prompt = (
        f"{_system_prompt(few_shot)}\n\n"
        f"Conference:\n{_format_conference(conference)}\n\n"
        f"Researcher profile:\n"
        f"Research title: {user_prefs.research_title}\n"
        f"Research context: {user_prefs.research_context}"
    )

    try:
        response = llm.invoke(prompt)
        data = json.loads(_extract_json(response.content))
        result = DecisionResult(
            valid=bool(data.get("valid", False)),
            relevant=bool(data.get("relevant", False)),
            reason=data.get("reason", ""),
        )
    except Exception as exc:
        result = DecisionResult(valid=False, relevant=False, reason=f"Decision failed: {exc}")

    if self_validate and not result.reason.startswith("Decision failed"):
        conference.decision_pre_validation = result
        result = _validate(conference, user_prefs, result, model, ollama_base_url)

    conference.decision = result
    return conference


def run_decision_agent(
    conferences: list[Conference],
    user_prefs: UserPreferences,
    model: str,
    ollama_base_url: str,
    self_validate: bool = False,
    few_shot: bool = False,
) -> tuple[list[Conference], list[Conference], dict]:
    """Return (accepted, rejected, timing) where timing has inference stats.

    self_validate=True adds a second LLM call per conference that scrutinizes
    the first decision's reasoning before finalizing it -- roughly doubles
    latency, see _VALIDATION_SYSTEM above for what it checks.

    few_shot=True adds 4 worked examples to the system prompt (see
    _FEWSHOT_EXAMPLES) targeting the specific fabrication patterns documented
    in src/benchmark/claude_judgments.md -- no added latency or LLM calls,
    pure prompt change."""
    accepted, rejected = [], []
    times = []
    for conf in conferences:
        t0 = time.perf_counter()
        conf = decide(
            conf, user_prefs, model, ollama_base_url,
            self_validate=self_validate, few_shot=few_shot,
        )
        times.append(round(time.perf_counter() - t0, 3))
        if conf.decision and conf.decision.valid and conf.decision.relevant:
            accepted.append(conf)
        else:
            rejected.append(conf)
    timing = {
        "calls": len(times),
        "total_s": round(sum(times), 2),
        "mean_s": round(sum(times) / len(times), 3) if times else 0,
        "min_s": round(min(times), 3) if times else 0,
        "max_s": round(max(times), 3) if times else 0,
    }
    return accepted, rejected, timing
