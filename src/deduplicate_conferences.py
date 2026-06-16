"""
Deduplizierung von Konferenzen in conferences.json

Strategie:
  - Duplikate werden anhand eines zusammengesetzten Schlüssels erkannt:
    (acronym_lower, year, start_date, city_lower)
  - Bei Duplikaten werden die Einträge gemerged, sodass möglichst viele
    Informationen erhalten bleiben (z.B. nicht-null URL, CORE-Rank, längste
    Topic-Liste).
  - Laufzeit: O(n) – ein einziger Durchlauf über die Liste mit Dict-Lookup.
"""

import json
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _normalise(text: str | None) -> str:
    """Kleinbuchstaben und Whitespace-Normalisierung."""
    if text is None:
        return ""
    return " ".join(text.lower().split())


def _conference_key(conf: dict[str, Any]) -> tuple:
    """
    Erzeugt einen Deduplizierungs-Schlüssel.

    Zwei Konferenzen gelten als identisch, wenn sie dasselbe Akronym,
    dasselbe Jahr, denselben Starttermin und dieselbe Stadt haben.
    """
    acronym = _normalise(conf.get("acronym"))
    year = conf.get("year")
    start = conf.get("dates", {}).get("start")
    city = _normalise(conf.get("location", {}).get("city"))
    return (acronym, year, start, city)


def _pick_best(a: Any, b: Any) -> Any:
    """Gibt den ‚reicheren' Wert zurück (nicht-None > None, längerer String)."""
    if a is None:
        return b
    if b is None:
        return a
    # Bei Strings den längeren bevorzugen
    if isinstance(a, str) and isinstance(b, str):
        return a if len(a) >= len(b) else b
    return a


def _merge_topics(a: list[str] | None, b: list[str] | None) -> list[str]:
    """Vereinigt zwei Topic-Listen ohne Duplikate (Reihenfolge bleibt stabil)."""
    seen: set[str] = set()
    merged: list[str] = []
    for topic in (a or []) + (b or []):
        key = topic.lower().strip()
        if key not in seen:
            seen.add(key)
            merged.append(topic)
    return merged


def _merge_conferences(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """
    Mergt zwei Konferenz-Einträge.  Felder werden so zusammengeführt, dass
    möglichst keine Information verloren geht.
    """
    merged = existing.copy()

    # Einfache Top-Level-Felder
    for field in ("name", "url", "source_url", "description", "core_rank"):
        merged[field] = _pick_best(existing.get(field), new.get(field))

    # Datum-Felder
    existing_dates = existing.get("dates", {})
    new_dates = new.get("dates", {})
    merged_dates = existing_dates.copy()
    for date_field in ("start", "end", "submission_deadline",
                       "notification_date", "camera_ready_deadline"):
        merged_dates[date_field] = _pick_best(
            existing_dates.get(date_field), new_dates.get(date_field)
        )
    merged["dates"] = merged_dates

    # Standort-Felder
    existing_loc = existing.get("location", {})
    new_loc = new.get("location", {})
    merged_loc = existing_loc.copy()
    for loc_field in ("city", "country", "continent", "coordinates"):
        merged_loc[loc_field] = _pick_best(
            existing_loc.get(loc_field), new_loc.get(loc_field)
        )
    merged["location"] = merged_loc

    # Topics vereinigen
    merged["topics"] = _merge_topics(existing.get("topics"), new.get("topics"))

    return merged


# ---------------------------------------------------------------------------
# Haupt-Deduplizierungslogik  –  O(n)
# ---------------------------------------------------------------------------

def deduplicate(conferences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Entfernt Duplikate aus der Konferenzliste.

    Laufzeit:  O(n)  (ein Durchlauf, Dict-Lookup je Eintrag)
    Speicher:  O(n)  (Dict der Schlüssel → Index)
    """
    seen: dict[tuple, int] = {}          # key → Index in result
    result: list[dict[str, Any]] = []

    for conf in conferences:
        key = _conference_key(conf)

        if key in seen:
            idx = seen[key]
            result[idx] = _merge_conferences(result[idx], conf)
        else:
            seen[key] = len(result)
            result.append(conf.copy())

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    default_path = Path(__file__).resolve().parent.parent / "temp" / "conferences.json"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    if not path.exists():
        print(f"Datei nicht gefunden: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    original = data.get("conferences", [])
    deduplicated = deduplicate(original)

    removed = len(original) - len(deduplicated)
    print(f"Konferenzen vorher:   {len(original)}")
    print(f"Duplikate entfernt:   {removed}")
    print(f"Konferenzen nachher:  {len(deduplicated)}")

    data["conferences"] = deduplicated

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Datei aktualisiert:   {path}")


if __name__ == "__main__":
    main()
