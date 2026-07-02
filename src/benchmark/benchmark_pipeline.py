import json
import os

from agents.scraper import _extract_conferences
from json_comparer import evaluate_extraction


def run_pipeline():
    # 1. Konfiguration
    base_url = "http://localhost:11434"
    md_filepath = "www.wikicfp.com_cfp_servlet_tool.search_q_Deep+Learning_year_2026_page_1.md"
    groundtruth_filepath = "groundtruth_deep_learning.json"
    results_md_filepath = "evaluation_results_1.md"

    models_to_test = ["llama3.2", "llama3", "gemma4:e4b", "qwen2.5:7b", "mistral:7b"]

    # 2. Dateien einmalig einlesen (spart Zeit bei mehreren Modellen)
    if not os.path.exists(md_filepath) or not os.path.exists(groundtruth_filepath):
        print(f"[!] Fehler: Eingabedateien fehlen. Bitte Pfade prüfen.")
        return

    with open(md_filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    with open(groundtruth_filepath, "r", encoding="utf-8") as f:
        groundtruth_data = json.load(f)

    # Markdown-String initialisieren
    md_output = "# Evaluierungs-Ergebnisse: Konferenz-Extraktion\n\n"

    # 3. Schleife über alle Modelle
    for model_name in models_to_test:
        print(f"\n{'=' * 40}")
        print(f"Teste Modell: {model_name}")
        print(f"{'=' * 40}")

        # Ersetze Doppelpunkte für Dateinamen (z.B. bei llama3.2:3b)
        safe_model_name = model_name.replace(":", "_")
        output_filepath = f"extracted_conferences_{safe_model_name}.json"

        print("[1] Starte LLM-Extraktion...")
        extracted_list = _extract_conferences(md_content, model=model_name, base_url=base_url)

        if not extracted_list:
            print("[!] Warnung: Keine Konferenzen extrahiert oder Fehler beim Parsen.")
            extracted_list = []  # Leere Liste als Fallback für die Auswertung

        extracted_data = {"conferences": extracted_list}

        # Extrahierte Daten als JSON speichern
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=4, ensure_ascii=False)
        print(f"[2] Extrahierte Daten gespeichert in: {output_filepath}")

        # Evaluation durchführen
        print("[3] Führe Evaluation durch...")
        llm_raw_string = json.dumps(extracted_data)
        metrics = evaluate_extraction(groundtruth_data, llm_raw_string)

        # 4. Ergebnisse formatiert an den Markdown-String anhängen
        md_output += f"## Modell: `{model_name}`\n"

        md_output += "### Syntax & Format\n"
        md_output += f"- **Valides JSON:** {'Ok' if metrics['syntax']['valid_json'] else 'NO'}\n"
        md_output += f"- **Korrektes Schema:** {'Ok' if metrics['syntax']['correct_schema'] else 'NO'}\n\n"

        md_output += "### Vollständigkeit (Recall)\n"
        md_output += f"- **Gefunden:** {metrics['recall']['extracted_total']} von {metrics['recall']['groundtruth_total']} (Groundtruth)\n"
        md_output += f"- **True Positives (Korrekt gematcht):** {metrics['recall']['true_positives']}\n"
        md_output += f"- **False Negatives (Verpasst):** {metrics['recall']['false_negatives']}\n"
        md_output += f"- **False Positives (Zusätzlich/Erfunden):** {metrics['recall']['false_positives']}\n\n"

        md_output += "### Genauigkeit (Accuracy)\n"
        md_output += f"- **Exakte Attribut-Matches:** {metrics['accuracy']['exact_matches']} von {metrics['accuracy']['attributes_checked']} geprüften Attributen\n"
        md_output += f"- **Halluzinationen (Daten erfunden):** {metrics['accuracy']['hallucinations']}\n\n"
        md_output += "---\n\n"

    # 5. Finale Markdown-Datei speichern
    with open(results_md_filepath, "w", encoding="utf-8") as f:
        f.write(md_output)

    print(f"\n[✓] Pipeline abgeschlossen! Gesamtergebnis gespeichert in: {results_md_filepath}")


if __name__ == "__main__":
    run_pipeline()