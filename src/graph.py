"""LangGraph pipeline definition.

Graph nodes:
  scrape  →  decide  →  score  →  END

State carries all data between nodes. Model name and config
live in state so they can be swapped per run (supports RQ1/RQ2).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.decision import run_decision_agent
from agents.scorer import run_scorer
from agents.scraper import run_scraper
from schemas.conference import Conference, UserPreferences


class PipelineState(TypedDict):
    user_preferences: dict
    scrape_queries: list[str]
    model_name: str
    ollama_base_url: str
    cache_path: str
    cache_ttl_days: int
    raw_conferences: list[dict]
    accepted_conferences: list[dict]
    rejected_conferences: list[dict]
    scored_conferences: list[dict]


def _prefs(state: PipelineState) -> UserPreferences:
    return UserPreferences.model_validate(state["user_preferences"])


def _to_dicts(conferences: list[Conference]) -> list[dict]:
    return [c.model_dump(mode="json") for c in conferences]


def _from_dicts(raw: list[dict]) -> list[Conference]:
    return [Conference.model_validate(r) for r in raw]


def scrape_node(state: PipelineState) -> dict[str, Any]:
    conferences = run_scraper(
        queries=state["scrape_queries"],
        model=state["model_name"],
        ollama_base_url=state["ollama_base_url"],
        cache_path=Path(state["cache_path"]),
        ttl_days=state.get("cache_ttl_days", 7),
    )
    return {"raw_conferences": _to_dicts(conferences)}


def decide_node(state: PipelineState) -> dict[str, Any]:
    conferences = _from_dicts(state["raw_conferences"])
    accepted, rejected = run_decision_agent(
        conferences=conferences,
        user_prefs=_prefs(state),
        model=state["model_name"],
        ollama_base_url=state["ollama_base_url"],
    )
    return {
        "accepted_conferences": _to_dicts(accepted),
        "rejected_conferences": _to_dicts(rejected),
    }


def score_node(state: PipelineState) -> dict[str, Any]:
    conferences = _from_dicts(state["accepted_conferences"])
    scored = run_scorer(
        conferences=conferences,
        user_prefs=_prefs(state),
        model=state["model_name"],
        ollama_base_url=state["ollama_base_url"],
    )
    return {"scored_conferences": _to_dicts(scored)}


def build_graph() -> Any:
    graph = StateGraph(PipelineState)
    graph.add_node("scrape", scrape_node)
    graph.add_node("decide", decide_node)
    graph.add_node("score", score_node)
    graph.add_edge("scrape", "decide")
    graph.add_edge("decide", "score")
    graph.add_edge("score", END)
    graph.set_entry_point("scrape")
    return graph.compile()


def make_initial_state(
    user_preferences: UserPreferences,
    scrape_queries: list[str],
    model_name: str | None = None,
    ollama_base_url: str | None = None,
    cache_path: str | None = None,
    cache_ttl_days: int | None = None,
) -> PipelineState:
    return PipelineState(
        user_preferences=user_preferences.model_dump(mode="json"),
        scrape_queries=scrape_queries,
        model_name=model_name or os.environ.get("OLLAMA_MODEL", "llama3.2"),
        ollama_base_url=ollama_base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        cache_path=cache_path or os.path.join(os.environ.get("CACHE_DIR", "./temp"), "conferences.json"),
        cache_ttl_days=cache_ttl_days or int(os.environ.get("CACHE_TTL_DAYS", "7")),
        raw_conferences=[],
        accepted_conferences=[],
        rejected_conferences=[],
        scored_conferences=[],
    )
