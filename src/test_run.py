import json
from pathlib import Path
from langchain_ollama import ChatOllama
from agents.scraper import run_scraper


def generate_dynamic_queries(base_topic: str, num_queries: int = 3) -> list[str]:
    """Lässt Llama 3 dynamische Suchbegriffe generieren."""
    print(f"Generiere {num_queries} zufällige Forschungsbereiche für: {base_topic}...")

    llm = ChatOllama(model="llama3.2", base_url="http://localhost:11434", format="json")

    prompt = f"""Du bist ein KI-Forscher. Nenne mir {num_queries} hochspezifische, 
    aktuelle Forschungs-Nischen im Bereich '{base_topic}'. Benutze nur maximal 2 Wörter pro Nische.
    Nutze englische Begriffe (z.B. 'Zero-Shot Learning', 'Swarm Robotics').
    Antworte AUSSCHLIESSLICH in diesem JSON Format:
    {{
      "queries": ["nische 1", "nische 2", "nische 3"]
    }}"""

    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        raw_queries = data.get("queries", [])

        # Wir bereinigen die Ausgabe, egal ob sie als String oder als Dict kommt
        clean_queries = []
        for item in raw_queries:
            if isinstance(item, dict):
                # Zieht den Text aus dem Dict heraus (z.B. 'Explainable AI (XAI)')
                val = item.get("name") or (list(item.values())[0] if item else "")
                if val:
                    clean_queries.append(str(val))
            elif isinstance(item, str):
                # Wenn Llama brav war und direkt einen String geliefert hat
                clean_queries.append(item)

        print(f"-> LLM hat sich ausgedacht: {clean_queries}")
        return clean_queries

    except Exception as e:
        print(f"[!] Fehler bei der Query-Generierung: {e}")
        # Fallback, falls das Modell völlig stolpert
        return [base_topic]

def main():
    print("Starte den Web-Scraping Agenten...")

    test_queries = generate_dynamic_queries("Artificial Intelligence", num_queries=3)

    # Parameter für lokales Modell
    ollama_model = "llama3.2" # oder "gemma4:e4b"
    ollama_url = "http://localhost:11434"

    # Speicherort für den Cache
    cache_file = Path("temp/conferences.json")

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

        print(f"\n Erfolgreich abgeschlossen! {len(results)} Konferenzen gefunden.")

        for conf in results:
            print("-" * 40)
            print(f"Name:    {conf.name}")
            print(f"Akronym: {conf.acronym}")
            print(f"Datum:   {conf.dates.start} bis {conf.dates.end}")
            print(f"Ranking: {conf.core_rank}")
            print(f"Ort:     {conf.location.city if conf.location else 'Unbekannt'}")

    except Exception as e:
        print(f"\n Ein Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    main()