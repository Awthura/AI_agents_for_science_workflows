import os
import re
import glob
import yaml
import json
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

REPO_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "ccf-deadlines", "conference"))


def get_safe_str(obj, attr_path, default=""):
    """Safe access to nested dictionaries."""
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


def parse_start_date(date_str) -> str:
    """
    Parse human-readable date ranges like 'February 8-11, 2027' or 'May 10 - 15, 2026'
    into ISO format 'YYYY-MM-DD' using the start of the range.
    """
    if not date_str:
        return ""
    try:
        # Normalize range: "8-11" or "10 - 15" → keep only the start day
        cleaned = re.sub(r'(\d+)\s*[-–]\s*\d+', r'\1', str(date_str))
        dt = dateutil_parser.parse(cleaned, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def get_acronym(conf, year_data) -> str:
    """
    Derive the conference acronym.
    ccfddl stores the short name in 'title' (e.g. 'AAAI').
    The year-specific id (e.g. 'aaai27') can be used as fallback.
    """
    title = get_safe_str(conf, 'title')
    if title:
        return title.upper()
    # Fallback: strip trailing digits from year_data id (e.g. 'aaai27' → 'AAAI')
    year_id = get_safe_str(year_data, 'id')
    if year_id:
        return re.sub(r'\d+$', '', year_id).upper()
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
    "MX": "Interdiscipline/Mixture/Emerging",
}


def build_conference_json():
    print(f"Agent 1: Lese lokale YAML-Dateien aus {REPO_PATH}...")
    print(f"[*] Reading local YAML files from {REPO_PATH}...")

    yaml_files = glob.glob(os.path.join(REPO_PATH, "**", "*.yml"), recursive=True)
    yaml_files.extend(glob.glob(os.path.join(REPO_PATH, "**", "*.yaml"), recursive=True))

    if not yaml_files:
        print(f"[!] Keine YAML-Dateien gefunden unter {REPO_PATH}. Bitte zuerst fetcher/ccf-deadlines_fetcher.py ausführen.")
        print(f"[!] No YAML files found at {REPO_PATH}. Run fetcher/ccf-deadlines_fetcher.py first.")
        return

    now = datetime.now(timezone.utc)
    formatted_conferences = []
    skipped = 0

    for file_path in yaml_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
                if not data:
                    continue
                if isinstance(data, dict):
                    data = [data]

                for conf in data:
                    years = conf.get('confs', [])

                    for year_data in years:
                        timelines = year_data.get('timeline', [])
                        deadline_obj = None
                        if timelines and isinstance(timelines, list):
                            deadline_obj = timelines[0].get('deadline')

                        # Skip past deadlines
                        is_past = False
                        try:
                            if deadline_obj and str(deadline_obj).lower() != "tbd":
                                dt = datetime.strptime(str(deadline_obj)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                if dt < now:
                                    is_past = True
                        except ValueError:
                            pass

                        if is_past:
                            skipped += 1
                            continue

                        raw_sub = get_safe_str(conf, 'sub')
                        topic = CATEGORY_TRANSLATION.get(raw_sub.upper().strip(), raw_sub) if raw_sub else ""

                        acronym = get_acronym(conf, year_data)
                        start_date = parse_start_date(get_safe_str(year_data, 'date'))

                        # Read CORE rank directly from YAML
                        core_rank = None
                        rank_data = conf.get('rank', {})
                        if isinstance(rank_data, dict):
                            core_raw = rank_data.get('core', '')
                            if core_raw:
                                core_rank = str(core_raw).strip()

                        conf_dict = {
                            "name": acronym,
                            "acronym": acronym,
                            "start_date": start_date,
                            "end_date": "",
                            "city": get_safe_str(year_data, 'place'),
                            "country": "",
                            "submission_deadline": str(deadline_obj)[:10] if deadline_obj and str(deadline_obj).lower() != "tbd" else "",
                            "notification_date": "",
                            "url": get_safe_str(year_data, 'link'),
                            "topics": [topic] if topic else [],
                            "core_rank": core_rank,
                        }
                        formatted_conferences.append(conf_dict)

            except yaml.YAMLError as exc:
                print(f"[!] Fehler beim Lesen von {file_path}: {exc}")
                print(f"[!] YAML parse error in {file_path}: {exc}")

    final_output = {"conferences": formatted_conferences}

    output_filename = "future_conferences.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"Agent 1: Erfolgreich {len(formatted_conferences)} zukünftige Konferenzen extrahiert und in '{output_filename}' gespeichert. ({skipped} vergangene Einträge übersprungen.)")
    print(f"[✓] Extracted {len(formatted_conferences)} future conferences ({skipped} past entries skipped). Saved to '{output_filename}'.")


if __name__ == "__main__":
    build_conference_json()
