"""Scoring agent.

Scores each accepted conference on three dimensions:
  - Distance   (deterministic, Haversine)
  - Relevancy  (LLM-based, 0–100)
  - Prestige   (deterministic, CORE rank mapping)

Weighted total = 0.50 * relevancy + 0.30 * distance + 0.20 * prestige
"""

from __future__ import annotations

import json

from langchain_ollama import ChatOllama

from ..schemas.conference import Conference, ConferenceScores, CoreRank, UserPreferences
from ..tools.geocoding import distance_to_score, geocode, haversine_km


WEIGHTS = {"relevancy": 0.50, "distance": 0.30, "prestige": 0.20}

_CORE_SCORE: dict[CoreRank, float] = {
    CoreRank.A_STAR: 100.0,
    CoreRank.A: 80.0,
    CoreRank.B: 55.0,
    CoreRank.C: 30.0,
    CoreRank.UNRANKED: 10.0,
}

_RELEVANCY_SYSTEM = """\
You are an academic advisor. Score how relevant the given conference is to a \
researcher's work, on a scale from 0 (completely unrelated) to 100 (perfect fit).

Consider: topic overlap, community fit, typical attendee profile.

Return ONLY valid JSON — no explanation, no markdown fences.

Schema:
{
  "score": <integer 0-100>,
  "explanation": "one sentence"
}"""


def _llm(model: str, base_url: str) -> ChatOllama:
    return ChatOllama(model=model, base_url=base_url, format="json")


def _prestige_score(rank: CoreRank | None) -> float:
    return _CORE_SCORE.get(rank, 10.0)


def _distance_score(conference: Conference, user_prefs: UserPreferences) -> float:
    if not conference.location:
        return 50.0  # neutral when location is unknown

    conf_addr = f"{conference.location.city}, {conference.location.country}"
    conf_coords = geocode(conf_addr)
    if not conf_coords:
        return 50.0

    user_coords = user_prefs.coordinates or geocode(user_prefs.address)
    if not user_coords:
        return 50.0

    km = haversine_km(user_coords, conf_coords)
    return distance_to_score(km)


def _relevancy_score(
    conference: Conference, user_prefs: UserPreferences, model: str, base_url: str
) -> tuple[float, str]:
    llm = _llm(model, base_url)
    prompt = (
        f"{_RELEVANCY_SYSTEM}\n\n"
        f"Conference: {conference.name}\n"
        f"Topics: {', '.join(conference.topics) if conference.topics else 'N/A'}\n"
        f"Description: {conference.description or 'N/A'}\n\n"
        f"Researcher:\n"
        f"Title: {user_prefs.research_title}\n"
        f"Context: {user_prefs.research_context}"
    )
    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        score = float(max(0, min(100, data.get("score", 0))))
        explanation = data.get("explanation", "")
        return score, explanation
    except Exception:
        return 0.0, "Relevancy scoring failed."


def score_conference(
    conference: Conference,
    user_prefs: UserPreferences,
    model: str,
    ollama_base_url: str,
) -> Conference:
    dist = _distance_score(conference, user_prefs)
    rel, explanation = _relevancy_score(conference, user_prefs, model, ollama_base_url)
    pres = _prestige_score(conference.core_rank)

    total = round(
        WEIGHTS["relevancy"] * rel
        + WEIGHTS["distance"] * dist
        + WEIGHTS["prestige"] * pres,
        1,
    )

    conference.scores = ConferenceScores(
        distance=dist, relevancy=rel, prestige=pres, total=total
    )
    if conference.decision and not conference.description:
        conference.description = explanation

    return conference


def run_scorer(
    conferences: list[Conference],
    user_prefs: UserPreferences,
    model: str,
    ollama_base_url: str,
) -> list[Conference]:
    scored = [
        score_conference(conf, user_prefs, model, ollama_base_url)
        for conf in conferences
    ]
    return sorted(scored, key=lambda c: c.scores.total if c.scores else 0, reverse=True)
