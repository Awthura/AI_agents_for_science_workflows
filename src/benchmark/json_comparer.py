import json
import re
from dateutil import parser


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
            "true_positives": 0,
            "false_negatives": 0,
            "false_positives": 0
        },
        "accuracy": {
            "attributes_checked": 0,
            "exact_matches": 0,
            "swapped_ids": 0,  # NEU: Zählt vertauschte Name/Akronym Felder
            "hallucinations": 0
        },
        "overall_score": 0.0  # NEU: Der finale Score (0-100)
    }

    expected_keys = {"name", "acronym", "start_date", "end_date", "city", "country", "submission_deadline", "url",
                     "topics"}

    # ==========================================
    # 1. Syntax-Validität
    # ==========================================
    if re.search(r"```(?:json)?", llm_raw_output):
        metrics["syntax"]["markdown_fences_present"] = True

    clean_json_str = re.sub(r"```json\n?|\n?```", "", llm_raw_output).strip()

    try:
        llm_data = json.loads(clean_json_str)
        metrics["syntax"]["valid_json"] = True
    except json.JSONDecodeError:
        return metrics  # Abbruch bei komplett kaputtem JSON (Score bleibt 0)

    llm_conferences = llm_data.get("conferences", [])
    metrics["recall"]["extracted_total"] = len(llm_conferences)

    schema_correct = True
    for conf in llm_conferences:
        if set(conf.keys()) != expected_keys:
            schema_correct = False
            break
    metrics["syntax"]["correct_schema"] = schema_correct

    # ==========================================
    # Hilfsfunktionen
    # ==========================================
    def normalize_id(text):
        return str(text).lower().replace(" ", "").replace("-", "") if text else ""

    def normalize_string(text):
        return str(text).strip().lower() if text else ""

    def compare_dates(d1, d2):
        if not d1 and not d2: return True
        if not d1 or not d2: return False
        try:
            return parser.parse(str(d1)).date() == parser.parse(str(d2)).date()
        except (ValueError, TypeError, parser.ParserError):
            return normalize_string(d1) == normalize_string(d2)

    def compare_lists(l1, l2):
        if not isinstance(l1, list): l1 = [l1] if l1 else []
        if not isinstance(l2, list): l2 = [l2] if l2 else []
        return set(normalize_string(x) for x in l1) == set(normalize_string(x) for x in l2)

    # ==========================================
    # 2. Extraktions-Recall (Mit Swap-Erkennung)
    # ==========================================
    gt_conferences = groundtruth_data.get("conferences", [])
    matched_gt_indices = set()
    matched_llm_indices = set()
    potential_matches = []

    for gt_idx, gt_conf in enumerate(gt_conferences):
        gt_acronym = normalize_id(gt_conf.get("acronym"))
        gt_name = normalize_id(gt_conf.get("name"))

        for llm_idx, llm_conf in enumerate(llm_conferences):
            llm_acronym = normalize_id(llm_conf.get("acronym"))
            llm_name = normalize_id(llm_conf.get("name"))

            # Logik trennt zwischen exaktem Match und vertauschtem Match
            is_exact_match = (gt_acronym and gt_acronym == llm_acronym) or (gt_name and gt_name == llm_name)
            is_swapped_match = (gt_acronym and gt_acronym == llm_name) or (gt_name and gt_name == llm_acronym)

            if is_exact_match or is_swapped_match:
                score = 0
                for key in ["city", "country", "url"]:
                    if normalize_string(gt_conf.get(key)) == normalize_string(llm_conf.get(key)):
                        score += 1

                # Wir übergeben auch, ob es ein Swap war
                potential_matches.append((score, gt_idx, llm_idx, is_swapped_match and not is_exact_match))

    potential_matches.sort(reverse=True, key=lambda x: x[0])

    # ==========================================
    # 3. Attribut-Genauigkeit & Halluzinationen
    # ==========================================
    for score, gt_idx, llm_idx, is_swapped in potential_matches:
        if gt_idx not in matched_gt_indices and llm_idx not in matched_llm_indices:
            matched_gt_indices.add(gt_idx)
            matched_llm_indices.add(llm_idx)
            metrics["recall"]["true_positives"] += 1

            if is_swapped:
                metrics["accuracy"]["swapped_ids"] += 1

            gt_conf = gt_conferences[gt_idx]
            llm_conf = llm_conferences[llm_idx]

            for key in expected_keys:
                if key in ["name", "acronym"]: continue

                gt_val = gt_conf.get(key)
                llm_val = llm_conf.get(key)
                metrics["accuracy"]["attributes_checked"] += 1

                if not gt_val and llm_val:
                    metrics["accuracy"]["hallucinations"] += 1
                elif not gt_val and not llm_val:
                    metrics["accuracy"]["exact_matches"] += 1
                else:
                    is_match = False
                    if key in ["start_date", "end_date", "submission_deadline"]:
                        is_match = compare_dates(gt_val, llm_val)
                    elif key == "topics":
                        is_match = compare_lists(gt_val, llm_val)
                    else:
                        is_match = normalize_string(gt_val) == normalize_string(llm_val)

                    if is_match:
                        metrics["accuracy"]["exact_matches"] += 1

    metrics["recall"]["false_negatives"] = len(gt_conferences) - len(matched_gt_indices)
    metrics["recall"]["false_positives"] = len(llm_conferences) - len(matched_llm_indices)

    # ==========================================
    # 4. SCORING SYSTEM (0 - 100 Punkte)
    # ==========================================
    tp = metrics["recall"]["true_positives"]
    fp = metrics["recall"]["false_positives"]
    fn = metrics["recall"]["false_negatives"]

    # F1-Score für Recall/Precision (Wertebereich 0.0 - 1.0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Attribut-Genauigkeit (Wertebereich 0.0 - 1.0)
    attr_acc = metrics["accuracy"]["exact_matches"] / metrics["accuracy"]["attributes_checked"] if metrics["accuracy"][
                                                                                                       "attributes_checked"] > 0 else 0

    # Basis-Score: 60% Gewichtung auf F1 (Finden), 40% auf Attribute (Details)
    base_score = (f1_score * 60) + (attr_acc * 40)

    # Strafabzüge
    if not metrics["syntax"]["correct_schema"]:
        base_score -= 10
    if metrics["syntax"]["markdown_fences_present"]:
        base_score -= 5
    base_score -= (metrics["accuracy"]["swapped_ids"] * 2)  # -2 Punkte pro Vertauschung
    base_score -= (metrics["accuracy"]["hallucinations"] * 2)  # -2 Punkte pro erfundenem Attribut

    # Score auf 0-100 begrenzen und runden
    metrics["overall_score"] = max(0.0, min(100.0, round(base_score, 2)))

    return metrics