from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dateutil import parser as dateutil_parser
from langchain_ollama import ChatOllama

from schemas.conference import (
    Conference,
    ConferenceDates,
    ConferenceFormat,
    ConferenceLocation,
    CoreRank,
)

from tools.firecrawl_tool import fetch_core_page, fetch_wikicfp, fetch_cfplist

_PARSE_SYSTEM = """\
You are a structured data extraction assistant. Extract ALL academic conference listings \
from the provided text. If there is 'CANCELED' in the name: IGNORE this conference. Return ONLY valid JSON — no explanation, no markdown fences.

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
        # Bereinige mögliche Markdown-Fences, die das Modell trotz JSON-Mode generiert
        raw_content = response.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        if raw_content.startswith("```"):
            raw_content = raw_content[3:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]

        data = json.loads(raw_content.strip())
        return data.get("conferences", [])
    except Exception as e:
        print(f"\n[!!!] KRITISCHER FEHLER beim JSON-Parsing: {e}")
        print(f"\n[!!!] CRITICAL ERROR during JSON parsing: {e}")
        try:
            print(f"[!!!] LLM Output war (erste 300 Zeichen):\n{response.content[:300]}...")
            print(f"[!!!] LLM output (first 300 chars):\n{response.content[:300]}...")
        except:
            pass
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


def _normalize(raw: dict, source_name: str, source_query: str) -> Optional[Conference]:
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
            source_url=f"{source_name}:{source_query}",
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
    conferences: list[Conference] = []
    if cache_path.exists():
        print(f"Lade bestehende Konferenzen aus {cache_path}...")
        print(f"  [*] Loading existing conferences from {cache_path}...")
        conferences = _load_cache(cache_path)

    seen_ids: set[str] = {conf.id for conf in conferences}
    cutoff = date.today().replace(year=date.today().year + (months_ahead // 12))

    # Definition der verfügbaren Scraping-Quellen
    sources = [
        {"name": "wikicfp", "fetch_func": fetch_wikicfp},
        {"name": "cfplist", "fetch_func": fetch_cfplist}
    ]

    for query in queries:
        print(f"\nSuche nach neuen Einträgen für '{query}'...")
        print(f"  [*] Searching for new entries for '{query}'...")

        for source in sources:
            source_name = source["name"]
            fetch_func = source["fetch_func"]

            print(f"\n  [>>>] Starte Quelle: {source_name.upper()} für '{query}'")
            print(f"  [>>>] Starting source: {source_name.upper()} for '{query}'")

            for page in range(1, 4):
                print(f"  [>] Hole {source_name} Seite {page} für '{query}'...")
                print(f"  [>] Fetching {source_name} page {page} for '{query}'...")

                # Ruft die jeweilige Fetch-Funktion der Quelle auf
                markdown = fetch_func(query, page=page)

                if not markdown or len(markdown.strip()) < 100:
                    print(f"  [!] Leeres oder zu kurzes Markdown von {source_name} erhalten. Breche Paginierung ab.")
                    print(f"  [!] Empty or too short markdown from {source_name} received. Stopping pagination.")
                    break

                print("  [>] Sende Text an LLM zur Extraktion (das kann etwas dauern)...")
                print("  [>] Sending text to LLM for extraction (this may take a while)...")
                raw_list = _extract_conferences(markdown, model, ollama_base_url)

                print(f"  [<] LLM hat geantwortet! {len(raw_list)} potenziell passende Einträge gefunden.")
                print(f"  [<] LLM responded! {len(raw_list)} potential entries found.")

                if not raw_list:
                    print("  [!] LLM hat keine Konferenzen im JSON-Format zurückgegeben oder Parsing schlug fehl.")
                    print("  [!] LLM returned no conferences in JSON format or parsing failed.")
                    continue

                for raw in raw_list:
                    raw_name = raw.get('name', 'Unbekannt')
                    raw_start = raw.get('start_date', 'Kein Datum')
                    print(f"\n    Prüfe extrahierten Eintrag: {raw_name[:50]}... ({raw_start})")
                    print(f"    [*] Checking entry: {raw_name[:50]}... ({raw_start})")

                    # Übergebe nun auch den Namen der Quelle für das Tracking
                    conf = _normalize(raw, source_name, query)

                    if conf is None:
                        print(
                            "      [x] Abgelehnt: Normalisierung fehlgeschlagen (meist wegen ungültigem/fehlendem Datum).")
                        print("      [x] Rejected: Normalization failed (usually invalid or missing date).")
                        continue

                    if conf.id in seen_ids:
                        print(f"      [x] Abgelehnt: Konferenz bereits im Cache (ID: {conf.id}).")
                        print(f"      [x] Rejected: Conference already in cache (ID: {conf.id}).")
                        continue

                    if conf.dates.start > cutoff:
                        print(
                            f"      [x] Abgelehnt: Startdatum ({conf.dates.start}) liegt zu weit in der Zukunft (> {cutoff}).")
                        print(
                            f"      [x] Rejected: Start date ({conf.dates.start}) too far in the future (> {cutoff}).")
                        continue

                    if conf.dates.start < date.today():
                        print(f"      [x] Abgelehnt: Startdatum ({conf.dates.start}) liegt in der Vergangenheit.")
                        print(f"      [x] Rejected: Start date ({conf.dates.start}) is in the past.")
                        continue

                    print(f"      [✓] Valide neue Konferenz: {conf.name}")
                    print(f"      [✓] Valid new conference: {conf.name}")
                    seen_ids.add(conf.id)

                    if lookup_core and conf.acronym:
                        print(f"      [>] Hole CORE-Ranking für {conf.acronym} (Warte auf LLM...)")
                        print(f"      [>] Fetching CORE rank for {conf.acronym} (waiting for LLM...)")
                        conf.core_rank = _lookup_core_rank(conf.acronym, model, ollama_base_url)
                        print(f"      [<] CORE-Ranking erhalten: {conf.core_rank}")
                        print(f"      [<] CORE rank received: {conf.core_rank}")

                    conferences.append(conf)

                # Nach jeder bearbeiteten Seite speichern wir zur Sicherheit den Zwischenstand
                print(f"  [i] Speichere Zwischenstand ({len(conferences)} Konferenzen in {cache_path})...")
                print(f"  [i] Saving progress ({len(conferences)} conferences in {cache_path})...")
                _save_cache(cache_path, conferences)

    return conferences