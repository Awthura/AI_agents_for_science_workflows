import time
from dotenv import load_dotenv

# Passe den Import an, falls die Funktionen in einem anderen Modul liegen
from agents.scraper import fetch_wikicfp, fetch_cfplist


def main():
    load_dotenv()

    # 3 eigenständige, breite Themenfelder, die garantiert mehrere Seiten Ergebnisse liefern
    themen = [
        "Deep Learning",
        "Cybersecurity",
        "Robotics"
    ]

    print("Starte Batch-Scraping für Benchmarking...")
    print("Ziel: 3 Themenbereiche, jeweils Seiten 1 bis 3.")
    print("-" * 60)

    for thema in themen:
        print(f"\n=== Thema: '{thema}' ===")

        # Iteriere durch die Seiten 1, 2 und 3
        for page in range(1, 4):
            print(f" -> Scrape WikiCFP | Seite {page}...")
            try:
                fetch_wikicfp(query=thema, page=page)

                # Optional: Falls du später auch CFPList scrapen willst,
                # einkommentieren (ergibt dann insgesamt 18 Dateien statt 9).
                # fetch_cfplist(query=thema, page=page)

            except Exception as e:
                print(f"    [!] Fehler bei WikiCFP: {e}")

            # Kurze Pause schont den Server und verhindert IP-Bans
            time.sleep(1.5)

    print("-" * 60)
    print("[✓] Skript beendet. Die 9 Markdown-Dateien liegen nun im Ordner 'benchmark'.")


if __name__ == "__main__":
    main()