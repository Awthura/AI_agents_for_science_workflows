"""LangGraph pipeline definition.

Graph nodes:
  scrape  →  decide  →  score  →  END

State carries all data between nodes. Model name and config
live in state so they can be swapped per run (supports RQ1/RQ2).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.decision import run_decision_agent
from agents.scorer import run_scorer
from agents.scraper import run_scraper
from schemas.conference import (
    Conference,
    ConferenceDates,
    ConferenceLocation,
    CoreRank,
    UserPreferences,
)

CCF_DEADLINES_PATH = Path(__file__).parent.parent / "future_conferences.json"


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


def _parse_iso_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _load_ccf_deadlines_fallback(path: Path = CCF_DEADLINES_PATH) -> list[Conference]:
    """Fallback data source for when live scraping is unavailable (e.g. no
    Firecrawl on the cluster): load conferences pre-fetched from CCF-Deadlines
    via scripts/fetcher/ccf-deadlines_fetcher.py + agents/ccfddl_conferences.py.
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    conferences = []
    for entry in data.get("conferences", []):
        start = _parse_iso_date(entry.get("start_date", ""))
        if start is None:
            continue  # dates.start is required; skip entries we can't parse

        name = entry.get("name") or entry.get("acronym") or "Unknown"
        core_rank_raw = (entry.get("core_rank") or "").strip().upper()
        try:
            core_rank = CoreRank(core_rank_raw) if core_rank_raw else None
        except ValueError:
            core_rank = None

        conferences.append(Conference(
            id=hashlib.md5(f"{name.lower().strip()}{start.year}".encode()).hexdigest()[:12],
            name=name,
            acronym=entry.get("acronym") or None,
            year=start.year,
            url=entry.get("url") or None,
            source_url="ccf-deadlines",
            scraped_at=datetime.now(timezone.utc),
            dates=ConferenceDates(
                start=start,
                submission_deadline=_parse_iso_date(entry.get("submission_deadline", "")),
            ),
            location=ConferenceLocation(
                city=entry.get("city") or "Unknown",
                country=entry.get("country") or "",
            ),
            topics=entry.get("topics", []),
            core_rank=core_rank,
        ))
    return conferences


def scrape_node(state: PipelineState) -> dict[str, Any]:
    conferences = run_scraper(
        queries=state["scrape_queries"],
        model=state["model_name"],
        ollama_base_url=state["ollama_base_url"],
        cache_path=Path(state["cache_path"]),
        ttl_days=state.get("cache_ttl_days", 7),
    )
    if not conferences:
        print(f"  [*] Live scraping returned nothing — falling back to {CCF_DEADLINES_PATH}...")
        conferences = _load_ccf_deadlines_fallback()
        print(f"  [*] Loaded {len(conferences)} conference(s) from CCF-Deadlines fallback.")
    return {"raw_conferences": _to_dicts(conferences)}


def decide_node(state: PipelineState) -> dict[str, Any]:
    conferences = _from_dicts(state["raw_conferences"])
    print(f"  [*] Decision agent evaluating {len(conferences)} conference(s)...")
    accepted, rejected, _timing = run_decision_agent(
        conferences=conferences,
        user_prefs=_prefs(state),
        model=state["model_name"],
        ollama_base_url=state["ollama_base_url"],
    )
    print(f"  [*] Decision agent: {len(accepted)} accepted, {len(rejected)} rejected.")
    for conf in rejected[:5]:
        reason = conf.decision.reason if conf.decision else "no reason recorded"
        print(f"      rejected: {conf.name!r} — {reason}")
    return {
        "accepted_conferences": _to_dicts(accepted),
        "rejected_conferences": _to_dicts(rejected),
    }


def score_node(state: PipelineState) -> dict[str, Any]:
    conferences = _from_dicts(state["accepted_conferences"])
    scored, _timing = run_scorer(
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
