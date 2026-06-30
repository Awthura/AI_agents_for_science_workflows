import json
import re


def evaluate_extraction(groundtruth_data, llm_raw_output):
    # Metriken initialisieren
    metrics = {
        "syntax": {
            "markdown_fences_present": False,
            "valid_json": False,
            "correct_schema": False
        },
        "recall": {
            "groundtruth_total": len(groundtruth_data.get("conferences", [])),
            "extracted_total": 0,
            "true_positives": 0,  # Gefunden und gematcht
            "false_negatives": 0,  # Verpasst
            "false_positives": 0  # Vom LLM erfunden/zusätzlich
        },
        "accuracy": {
            "attributes_checked": 0,
            "exact_matches": 0,
            "hallucinations": 0  # LLM liefert Daten, wo Groundtruth leer ist
        }
    }

    expected_keys = {"name", "acronym", "start_date", "end_date", "city", "country", "submission_deadline", "url",
                     "topics"}

    # ==========================================
    # 1. Syntax-Validität (Format-Treue)
    # ==========================================

    # Prüfen, ob Markdown-Fences verwendet wurden (sollte im Idealfall nicht so sein, wenn strenges JSON gefordert ist)
    if re.search(r"```(?:json)?", llm_raw_output):
        metrics["syntax"]["markdown_fences_present"] = True

    # Versuche Fences zu entfernen für den Parse-Vorgang
    clean_json_str = re.sub(r"```json\n?|\n?```", "", llm_raw_output).strip()

    try:
        llm_data = json.loads(clean_json_str)
        metrics["syntax"]["valid_json"] = True
    except json.JSONDecodeError:
        return metrics  # Abbruch, da nicht weiter auswertbar

    llm_conferences = llm_data.get("conferences", [])
    metrics["recall"]["extracted_total"] = len(llm_conferences)

    # Schema-Prüfung über alle extrahierten Objekte
    schema_correct = True
    for conf in llm_conferences:
        if set(conf.keys()) != expected_keys:
            schema_correct = False
            break
    metrics["syntax"]["correct_schema"] = schema_correct

    # ==========================================
    # 2. Extraktions-Recall (Vollständigkeit)
    # ==========================================

    gt_conferences = groundtruth_data.get("conferences", [])

    # Helfer-Funktion für einen robusten Abgleich (Normalisierung)
    def normalize(text):
        return str(text).lower().replace(" ", "").replace("-", "") if text else ""

    matched_llm_indices = set()

    for gt_conf in gt_conferences:
        gt_acronym = normalize(gt_conf.get("acronym"))
        gt_name = normalize(gt_conf.get("name"))
        match_found = False

        for i, llm_conf in enumerate(llm_conferences):
            if i in matched_llm_indices:
                continue

            llm_acronym = normalize(llm_conf.get("acronym"))
            llm_name = normalize(llm_conf.get("name"))

            # Match-Kriterium: Entweder Acronym oder Name stimmt überein
            if (gt_acronym and gt_acronym == llm_acronym) or (gt_name and gt_name == llm_name):
                match_found = True
                matched_llm_indices.add(i)
                metrics["recall"]["true_positives"] += 1

                # ==========================================
                # 3. Attribut-Genauigkeit & Halluzinationen
                # ==========================================

                for key in expected_keys:
                    # Überspringe Name und Acronym, da diese für das Matching genutzt wurden
                    if key in ["name", "acronym"]:
                        continue

                    gt_val = gt_conf.get(key)
                    llm_val = llm_conf.get(key)

                    metrics["accuracy"]["attributes_checked"] += 1

                    # Exakter Match
                    if gt_val == llm_val:
                        metrics["accuracy"]["exact_matches"] += 1

                    # Halluzinations-Prüfung: Groundtruth ist leer, LLM hat aber etwas generiert
                    # (z.B. bei der VPAD 2026 Konferenz, wo city/country fehlen)
                    elif gt_val == "" and llm_val != "":
                        metrics["accuracy"]["hallucinations"] += 1

                break  # Nächste Groundtruth-Konferenz

        if not match_found:
            metrics["recall"]["false_negatives"] += 1

    # False Positives berechnen (Konferenzen, die das LLM gefunden hat, aber nicht in der Groundtruth stehen)
    metrics["recall"]["false_positives"] = len(llm_conferences) - len(matched_llm_indices)

    return metrics
