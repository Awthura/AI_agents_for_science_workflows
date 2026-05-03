"""Web-scraping agent.

Fetches conference listings from WikiCFP, parses them with an Ollama LLM,
looks up CORE ranks, and caches results to temp/conferences.json.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dateutil import parser as dateutil_parser
from langchain_ollama import ChatOllama

from ..schemas.conference import (
    Conference,
    ConferenceDates,
    ConferenceFormat,
    ConferenceLocation,
    CoreRank,
)
from ..tools.firecrawl_tool import fetch_core_page, fetch_wikicfp


_PARSE_SYSTEM = """\
You are a structured data extraction assistant. Extract ALL academic conference listings \
from the provided text. Return ONLY valid JSON — no explanation, no markdown fences.

Schema:
{
  "conferences": [
    {
      "name": "full conference name",
      "acronym": "short name, e.g. ICML",
      "start_date": "YYYY-MM-DD or empty string",
      "end_date": "YYYY-MM-DD or empty string",
      "city": "city name or empty string",
      "country": "country name or empty string",
      "submission_deadline": "YYYY-MM-DD or empty string",
      "notification_date": "YYYY-MM-DD or empty string",
      "url": "official website URL or empty string",
      "topics": ["keyword1", "keyword2"]
    }
  ]
}"""

_CORE_SYSTEM = """\
Extract the CORE ranking for the given conference acronym from the provided text.
Return ONLY valid JSON — no explanation, no markdown fences.

Schema:
{
  "rank": "A* | A | B | C | Unranked | null"
}

If no ranking is found or the acronym is not listed, return {"rank": null}."""


def _llm(model: str, base_url: str) -> ChatOllama:
    return ChatOllama(model=model, base_url=base_url, format="json")


def _safe_date(raw: str) -> Optional[date]:
    if not raw or not raw.strip():
        return None
    try:
        return dateutil_parser.parse(raw, fuzzy=True).date()
    except Exception:
        return None


def _make_id(name: str, year: int) -> str:
    return hashlib.md5(f"{name.lower().strip()}{year}".encode()).hexdigest()[:12]


def _parse_core_rank(rank_str: Optional[str]) -> Optional[CoreRank]:
    if not rank_str:
        return None
    mapping = {"A*": CoreRank.A_STAR, "A": CoreRank.A, "B": CoreRank.B, "C": CoreRank.C}
    return mapping.get(rank_str.strip().upper(), CoreRank.UNRANKED)


def _extract_conferences(markdown: str, model: str, base_url: str) -> list[dict]:
    llm = _llm(model, base_url)
    prompt = f"{_PARSE_SYSTEM}\n\n---\n{markdown[:8000]}"
    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        return data.get("conferences", [])
    except Exception:
        return []


def _lookup_core_rank(acronym: str, model: str, base_url: str) -> Optional[CoreRank]:
    if not acronym:
        return None
    markdown = fetch_core_page(acronym)
    llm = _llm(model, base_url)
    prompt = f"{_CORE_SYSTEM}\n\nAcronym to look up: {acronym}\n\n---\n{markdown[:4000]}"
    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        return _parse_core_rank(data.get("rank"))
    except Exception:
        return None


def _normalize(raw: dict, source_query: str) -> Optional[Conference]:
    try:
        start = _safe_date(raw.get("start_date", ""))
        if not start:
            return None
        year = start.year
        dates = ConferenceDates(
            start=start,
            end=_safe_date(raw.get("end_date", "")),
            submission_deadline=_safe_date(raw.get("submission_deadline", "")),
            notification_date=_safe_date(raw.get("notification_date", "")),
        )
        location = None
        city = raw.get("city", "").strip()
        country = raw.get("country", "").strip()
        if city or country:
            location = ConferenceLocation(city=city, country=country)

        return Conference(
            id=_make_id(raw.get("name", ""), year),
            name=raw.get("name", "").strip(),
            acronym=raw.get("acronym", "").strip() or None,
            year=year,
            url=raw.get("url") or None,
            source_url=f"wikicfp:{source_query}",
            scraped_at=datetime.now(),
            dates=dates,
            location=location,
            format=ConferenceFormat.IN_PERSON,
            topics=raw.get("topics", []),
            description=raw.get("description"),
        )
    except Exception:
        return None


def _is_cache_fresh(cache_path: Path, ttl_days: int) -> bool:
    if not cache_path.exists():
        return False
    try:
        data = json.loads(cache_path.read_text())
        scraped_at = datetime.fromisoformat(data.get("scraped_at", "2000-01-01"))
        age = (datetime.now() - scraped_at).days
        return age < ttl_days
    except Exception:
        return False


def _load_cache(cache_path: Path) -> list[Conference]:
    raw = json.loads(cache_path.read_text())
    conferences = []
    for item in raw.get("conferences", []):
        try:
            conferences.append(Conference.model_validate(item))
        except Exception:
            pass
    return conferences


def _save_cache(cache_path: Path, conferences: list[Conference]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scraped_at": datetime.now().isoformat(),
        "conferences": [c.model_dump(mode="json") for c in conferences],
    }
    cache_path.write_text(json.dumps(payload, indent=2, default=str))


def run_scraper(
    queries: list[str],
    model: str,
    ollama_base_url: str,
    cache_path: Path,
    ttl_days: int = 7,
    months_ahead: int = 12,
    lookup_core: bool = True,
) -> list[Conference]:
    if _is_cache_fresh(cache_path, ttl_days):
        return _load_cache(cache_path)

    cutoff = date.today().replace(year=date.today().year + (months_ahead // 12))
    seen_ids: set[str] = set()
    conferences: list[Conference] = []

    for query in queries:
        markdown = fetch_wikicfp(query)
        raw_list = _extract_conferences(markdown, model, ollama_base_url)

        for raw in raw_list:
            conf = _normalize(raw, query)
            if conf is None or conf.id in seen_ids:
                continue
            if conf.dates.start > cutoff:
                continue
            seen_ids.add(conf.id)

            if lookup_core and conf.acronym:
                conf.core_rank = _lookup_core_rank(conf.acronym, model, ollama_base_url)

            conferences.append(conf)

    _save_cache(cache_path, conferences)
    return conferences
