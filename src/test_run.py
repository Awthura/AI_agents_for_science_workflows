from pathlib import Path

# Passe den Importpfad an, falls deine scraper.py in einem Unterordner liegt
from agents.scraper import run_scraper


def main():
    print("🚀 Starte den Web-Scraping Agenten...")

    # 1. Parameter definieren
    # Wir suchen gezielt nach einer bekannten Konferenz, um die Datenmenge klein zu halten
    test_queries = ["ICML 2024", "NeurIPS 2024"]

    # Trage hier das Modell ein, das du in Ollama heruntergeladen hast
    ollama_model = "llama3"
    ollama_url = "http://localhost:11434"

    # Der Pfad, wo die Daten gespeichert werden sollen
    cache_file = Path("temp/conferences.json")

    # 2. Den Scraper aufrufen
    try:
        results = run_scraper(
            queries=test_queries,
            model=ollama_model,
            ollama_base_url=ollama_url,
            cache_path=cache_file,
            ttl_days=1,  # Cache nur für 1 Tag gültig beim Testen
            months_ahead=24,  # Auch Konferenzen im nächsten Jahr zulassen
            lookup_core=True  # Wir wollen testen, ob das zweite LLM-Prompt auch klappt
        )

        # 3. Ergebnisse ausgeben
        print(f"\n✅ Erfolgreich abgeschlossen! {len(results)} Konferenzen gefunden.")

        for conf in results:
            print("-" * 40)
            print(f"Name:    {conf.name}")
            print(f"Akronym: {conf.acronym}")
            print(f"Datum:   {conf.dates.start} bis {conf.dates.end}")
            print(f"Ranking: {conf.core_rank}")
            print(f"Ort:     {conf.location.city if conf.location else 'Unbekannt'}")

    except Exception as e:
        print(f"\n❌ Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    main()