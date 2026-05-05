from pathlib import Path


from agents.scraper import run_scraper


def main():
    print("Starte den Web-Scraping Agenten...")

    test_queries = ["ICML", "NeurIPS"]


    ollama_model = "llama3"
    ollama_url = "http://localhost:11434"

    cache_file = Path("temp/conferences.json")

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