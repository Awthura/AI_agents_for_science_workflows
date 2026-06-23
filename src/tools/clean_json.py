import json
from datetime import datetime


def clean_conferences(input_filepath: str, output_filepath: str):
    """
    Liest eine JSON-Datei mit Konferenzen ein, entfernt Duplikate und
    veraltete Einträge und speichert das bereinigte Ergebnis.
    Gibt die entfernten Konferenzen in der Konsole aus.
    """
    try:
        with open(input_filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Fehler: Die Datei {input_filepath} wurde nicht gefunden.")
        return
    except json.JSONDecodeError:
        print("Fehler: Die Datei enthält kein gültiges JSON.")
        return

    conferences = data.get("conferences", [])
    cleaned_conferences = []

    seen_identifiers = set()
    today = datetime.now().date()

    duplicates_removed = 0
    outdated_removed = 0

    print("Starte Bereinigung...\n")

    for conf in conferences:
        name = conf.get("name", "").strip()
        name_lower = name.lower()
        year = conf.get("year")
        identifier = (name_lower, year)

        # 1. Duplikat-Prüfung
        if identifier in seen_identifiers:
            print(f"[Entfernt - Duplikat]  {name} ({year})")
            duplicates_removed += 1
            continue

        # 2. Aktualitäts-Prüfung
        start_date_str = conf.get("dates", {}).get("start")
        is_current = True

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if start_date < today:
                    is_current = False
            except ValueError:
                print(f"[Warnung] Ungültiges Datumsformat bei '{name}' ({start_date_str}). Wird behalten.")

        if not is_current:
            print(f"[Entfernt - Veraltet]  {name} (Startdatum: {start_date_str})")
            outdated_removed += 1
            continue

        # Wenn beide Prüfungen bestanden sind
        seen_identifiers.add(identifier)
        cleaned_conferences.append(conf)

    data["conferences"] = cleaned_conferences
    data["scraped_at"] = datetime.now().isoformat()

    with open(output_filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print("\n" + "-" * 40)
    print("Zusammenfassung der Bereinigung:")
    print(f"Ursprüngliche Anzahl:  {len(conferences)}")
    print(f"Duplikate entfernt:    {duplicates_removed}")
    print(f"Veraltete entfernt:    {outdated_removed}")
    print(f"Neue Anzahl:           {len(cleaned_conferences)}")
    print("-" * 40)


if __name__ == "__main__":
    INPUT_JSON = "../temp/conferences.json"
    OUTPUT_JSON = "../temp/conferences_cleaned.json"

    clean_conferences(INPUT_JSON, OUTPUT_JSON)