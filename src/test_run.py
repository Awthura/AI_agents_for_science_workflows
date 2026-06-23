import json
from pathlib import Path
from dotenv import load_dotenv  # Neu: Lädt Umgebungsvariablen (.env)
from langchain_ollama import ChatOllama
from agents.scraper import run_scraper

# Lade Umgebungsvariablen direkt beim Start (wichtig für Firecrawl)
load_dotenv()


def generate_dynamic_queries(base_topic: str, num_queries: int = 3) -> list[str]:
    """Lässt ein lokales LLM dynamische Suchbegriffe generieren."""
    print(f"Generiere {num_queries} zufällige Forschungsbereiche für: {base_topic}...")

    llm = ChatOllama(model="llama3.2", base_url="http://localhost:11434", format="json")

    prompt = f"""You are an AI researcher. Give me {num_queries} highly specific, current research niches in the field of '{base_topic}'.
Use at most 3 words per niche. Use English terms only (e.g. 'Zero-Shot Learning', 'Swarm Robotics').
Reply ONLY in this exact JSON format:
{{
  "queries": ["niche 1", "niche 2", "niche 3"]
}}"""

    try:
        response = llm.invoke(prompt)

        # --- FIX: Robustes Markdown/JSON Parsing ---
        raw_content = response.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        if raw_content.startswith("```"):
            raw_content = raw_content[3:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]

        data = json.loads(raw_content.strip())
        raw_queries = data.get("queries", [])

        # Wir bereinigen die Ausgabe, egal ob sie als String oder als Dict kommt
        clean_queries = []
        for item in raw_queries:
            if isinstance(item, dict):
                # Zieht den Text aus dem Dict heraus
                val = item.get("name") or (list(item.values())[0] if item else "")
                if val:
                    clean_queries.append(str(val).strip())
            elif isinstance(item, str):
                clean_queries.append(item.strip())

        print(f"-> LLM hat generiert: {clean_queries}")
        return clean_queries

    except Exception as e:
        print(f"[!] Fehler bei der Query-Generierung: {e}")
        print(f"[!] Fallback auf Basis-Thema: ['{base_topic}']")
        return [base_topic]


def main():
    print("Starte den Web-Scraping Agenten...")

    # Konfiguration
    base_topic = "Artificial Intelligence"
    ollama_model = "llama3.2"
    ollama_url = "http://localhost:11434"

    # Stelle sicher, dass der temp-Ordner existiert, bevor Dateien übergeben werden
    cache_dir = Path("temp")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "conferences.json"

    test_queries = generate_dynamic_queries(base_topic, num_queries=3)

    if not test_queries:
        print("Keine Suchbegriffe generiert. Breche ab.")
        return

    try:
        results = run_scraper(
            queries=test_queries,
            model=ollama_model,
            ollama_base_url=ollama_url,
            cache_path=cache_file,
            ttl_days=1,
            months_ahead=24,
            lookup_core=True
        )

        print(f"\n[✓] Erfolgreich abgeschlossen! {len(results)} Konferenzen gefunden/geprüft.")

        for conf in results:
            print("-" * 40)
            print(f"Name:           {conf.name}")
            print(f"Akronym:        {conf.acronym or 'Keins'}")
            print(f"Datum:          {conf.dates.start} bis {conf.dates.end or 'Unbekannt'}")
            print(f"Ranking:        {conf.core_rank.name if conf.core_rank else 'Nicht gerankt'}")
            print(f"Ort:            {conf.location.city if conf.location else 'Unbekannt'}")
            print(f"Quelle:         {conf.source_url}")

    except Exception as e:
        print(f"\n[!] Ein kritischer Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    main()