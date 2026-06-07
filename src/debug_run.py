from pathlib import Path
from agents.scraper import run_scraper

def main():
    print("=== DEBUG RUN START ===")
    print("Starte den Web-Scraping Agenten im Debug-Modus...")

    test_queries = ["ICML", "NeurIPS"]
    ollama_model = "llama3.2:latest"
    ollama_url = "http://localhost:11434"
    cache_file = Path("temp/debug_conferences.json")

    # Ensure we start fresh by deleting the debug cache if it exists
    if cache_file.exists():
        cache_file.unlink()

    try:
        results = run_scraper(
            queries=test_queries,
            model=ollama_model,
            ollama_base_url=ollama_url,
            cache_path=cache_file,
            ttl_days=0,  # Force refresh
            months_ahead=24,
            lookup_core=True
        )

        print("\n=== DEBUG RUN ERGEBNISSE ===")
        print(f"Erfolgreich abgeschlossen! {len(results)} Konferenzen gefunden.")

        for conf in results:
            print("-" * 40)
            print(f"Name:    {conf.name}")
            print(f"Akronym: {conf.acronym}")
            print(f"Datum:   {conf.dates.start} bis {conf.dates.end}")
            print(f"Ranking: {conf.core_rank}")
            print(f"Ort:     {conf.location.city if conf.location else 'Unbekannt'}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR]: {e}")

    print("\n=== DEBUG RUN ENDE ===")

if __name__ == "__main__":
    main()
