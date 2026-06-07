import os
import urllib.request
import zipfile
import shutil

# GitHub ZIP-URL des main-Branches
REPO_ZIP_URL = "https://github.com/ccfddl/ccf-deadlines/archive/refs/heads/main.zip"
ZIP_FILENAME = "repo_temp.zip"
EXTRACT_FOLDER = "ccf-deadlines-main"
TARGET_FOLDER = "conference"

def download_and_extract_conferences():
    print("Agent 1 (Data Fetcher): Lade aktuelle Konferenzdaten herunter...")
    print("Agent 1 (Data Fetcher): Downloading latest conference data...")
    
    # 1. ZIP-Datei herunterladen
    urllib.request.urlretrieve(REPO_ZIP_URL, ZIP_FILENAME)
    
    print("Agent 1 (Data Fetcher): Entpacke den 'conference' Ordner...")
    print("Agent 1 (Data Fetcher): Extracting 'conference' folder...")
    
    # 2. ZIP-Datei öffnen und gezielt nur den conference-Ordner entpacken
    with zipfile.ZipFile(ZIP_FILENAME, 'r') as zip_ref:
        # Finde alle Dateien, die im Pfad "ccf-deadlines-main/conference/" liegen
        conference_files = [
            f for f in zip_ref.namelist() 
            if f.startswith(f"{EXTRACT_FOLDER}/conference/")
        ]
        
        # Extrahiere nur diese speziellen Dateien
        zip_ref.extractall(members=conference_files)
        
    print("Agent 1 (Data Fetcher): Räume temporäre Dateien auf...")
    print("Agent 1 (Data Fetcher): Cleaning up temporary files...")
    
    # 3. Ordnerstruktur aufräumen
    # Verschiebe den entpackten conference-Ordner ins Hauptverzeichnis
    if os.path.exists(TARGET_FOLDER):
        shutil.rmtree(TARGET_FOLDER)  # Alten Ordner überschreiben, falls er existiert
        
    shutil.move(os.path.join(EXTRACT_FOLDER, "conference"), TARGET_FOLDER)
    
    # Lösche das übrig gebliebene leere Verzeichnis und die ZIP-Datei
    shutil.rmtree(EXTRACT_FOLDER)
    os.remove(ZIP_FILENAME)
    
    print(f"Erfolg! Der Ordner '{TARGET_FOLDER}' ist nun lokal auf dem neuesten Stand.")
    print(f"[✓] Success! The '{TARGET_FOLDER}' folder is now up to date.")

if __name__ == "__main__":
    download_and_extract_conferences()