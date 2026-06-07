import os
import glob
import yaml
import json
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

REPO_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "ccf-deadlines", "conference"))

def get_safe_str(obj, attr_path, default=""):
    """Sicherer Zugriff auf verschachtelte Dictionaries."""
    current = obj
    try:
        for attr in attr_path.split('.'):
            if isinstance(current, dict) and attr in current:
                current = current[attr]
            else:
                return default
        return str(current) if current is not None else default
    except Exception:
        return default

def get_safe_date_str(date_obj):
    """Formatiert das Datum als YYYY-MM-DD."""
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d")
    elif isinstance(date_obj, str) and len(date_obj) >= 10:
        return date_obj[:10]
    return ""

CATEGORY_TRANSLATION = {
    "DS": "Computer Architecture/Parallel Programming/Storage Technology",
    "NW": "Network System",
    "SC": "Network and System Security",
    "SE": "Software Engineering/Operating System/Programming Language Design",
    "DB": "Database/Data Mining/Information Retrieval",
    "CT": "Computing Theory",
    "CG": "Graphics",
    "AI": "Artificial Intelligence",
    "HI": "Computer-Human Interaction",
    "MX": "Interdiscipline/Mixture/Emerging"
}

def build_conference_json():
    print(f"Agent 1: Lese lokale YAML-Dateien aus {REPO_PATH}...")
    
    # Suche alle YAML-Dateien im conference-Ordner und Unterordnern
    yaml_files = glob.glob(os.path.join(REPO_PATH, "**", "*.yml"), recursive=True)
    yaml_files.extend(glob.glob(os.path.join(REPO_PATH, "**", "*.yaml"), recursive=True))
    
    now = datetime.now(timezone.utc)
    formatted_conferences = []

    for file_path in yaml_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                # YAML Datei laden (oft ist es eine Liste von Konferenzen)
                data = yaml.safe_load(f)
                if not data:
                    continue
                
                # Falls die Datei nur ein Dict ist, in eine Liste packen
                if isinstance(data, dict):
                    data = [data]

                for conf in data:
                    years = conf.get('confs', []) # In der Raw-YAML heißt das Feld oft 'confs' statt 'years'
                    
                    for year_data in years:
                        # Deadlines sind in der YAML oft in einem Array namens 'timeline'
                        timelines = year_data.get('timeline', [])
                        deadline_obj = None
                        if timelines and isinstance(timelines, list):
                            deadline_obj = timelines[0].get('deadline')
                        
                        is_past = False
                        # Datumsprüfung (String in Datetime umwandeln, falls nötig)
                        try:
                            if deadline_obj and deadline_obj.lower() != "tbd":
                                # Annahme: Format ist YYYY-MM-DD
                                dt = datetime.strptime(deadline_obj[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                if dt < now:
                                    is_past = True
                        except ValueError:
                            pass # Falls das Datum unleserlich ist, behalten wir es lieber als es wegzuwerfen

                        if not is_past:
                            raw_sub = get_safe_str(conf, 'sub')
                            translated_sub = CATEGORY_TRANSLATION.get(raw_sub.upper().strip(), raw_sub) if raw_sub else ""
                            conf_dict = {
                                "name": get_safe_str(conf, 'title'),
                                "acronym": get_safe_str(conf, 'id').upper(),
                                "start_date": get_safe_date_str(get_safe_str(year_data, 'date')),
                                "end_date": "", # Ist im Raw-YAML oft nur ein einzelnes Date-Feld
                                "city": get_safe_str(year_data, 'place'),
                                "country": "", # Oft mit im 'place' Feld integriert
                                "submission_deadline": get_safe_date_str(deadline_obj),
                                "notification_date": "", # Kann bei Bedarf aus der Timeline extrahiert werden
                                "url": get_safe_str(year_data, 'link'),
                                "topics": [translated_sub] if translated_sub else []
                            }
                            formatted_conferences.append(conf_dict)

            except yaml.YAMLError as exc:
                print(f"Fehler beim Lesen von {file_path}: {exc}")

    final_output = {
        "conferences": formatted_conferences
    }

    output_filename = "future_conferences.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Agent 1: Erfolgreich {len(formatted_conferences)} zukünftige Konferenzen extrahiert und in '{output_filename}' gespeichert.")

if __name__ == "__main__":
    build_conference_json()
