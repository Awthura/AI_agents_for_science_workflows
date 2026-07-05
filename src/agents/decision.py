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


def _llm(model: str, base_url: str) -> ChatOllama:
    return ChatOllama(model=model, base_url=base_url, format="json")


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


def decide(
    conference: Conference,
    user_prefs: UserPreferences,
    model: str,
    ollama_base_url: str,
) -> Conference:
    llm = _llm(model, ollama_base_url)

    prompt = (
        f"{_SYSTEM}\n\n"
        f"Conference:\n{_format_conference(conference)}\n\n"
        f"Researcher profile:\n"
        f"Research title: {user_prefs.research_title}\n"
        f"Research context: {user_prefs.research_context}"
    )

    try:
        response = llm.invoke(prompt)
        data = json.loads(_extract_json(response.content))
        conference.decision = DecisionResult(
            valid=bool(data.get("valid", False)),
            relevant=bool(data.get("relevant", False)),
            reason=data.get("reason", ""),
        )
    except Exception as exc:
        conference.decision = DecisionResult(
            valid=False, relevant=False, reason=f"Decision failed: {exc}"
        )

    return conference


def run_decision_agent(
    conferences: list[Conference],
    user_prefs: UserPreferences,
    model: str,
    ollama_base_url: str,
) -> tuple[list[Conference], list[Conference], dict]:
    """Return (accepted, rejected, timing) where timing has inference stats."""
    accepted, rejected = [], []
    times = []
    for conf in conferences:
        t0 = time.perf_counter()
        conf = decide(conf, user_prefs, model, ollama_base_url)
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
