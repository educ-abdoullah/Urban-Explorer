import os
import requests
from datetime import datetime

# CONFIGURATION

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../../data/raw"))

# dossier du jour : raw/YYYYMMDD
date_jour = datetime.now().strftime("%Y%m%d")
RAW_DAY_DIR = os.path.join(RAW_DIR, date_jour)
os.makedirs(RAW_DAY_DIR, exist_ok=True)

# URL de téléchargement direct des sources
URL_DVF = "https://www.data.gouv.fr/fr/datasets/r/d8da0d27-91e0-4d44-a4f2-1848db7a4b8a"
URL_LOYERS = "https://www.data.gouv.fr/fr/datasets/r/21c3fb90-8a30-4c2d-b8c1-85a8b5d23d72"
URL_POPULATION = "https://www.insee.fr/fr/statistiques/fichier/7728806/base-cc-evol-struct-pop-2020_csv.zip"
URL_CRIMINALITE = "https://www.data.gouv.fr/fr/datasets/r/6c4935e5-5b9a-48fc-8fb0-5f4c5b28a44c"

# Liste des fichiers à récupérer
DATASETS = {
    "dvf": URL_DVF,
    "loyers_oll": URL_LOYERS,
    "population_insee": URL_POPULATION,
    "criminalite": URL_CRIMINALITE
}

# FONCTION D'INGESTION

def telecharger_dataset(nom, url):
    # enregistrement dans raw/YYYYMMDD/
    fichier_dest = os.path.join(RAW_DAY_DIR, f"{nom}.zip")

    print(f"Téléchargement de {nom}...")
    print(f"URL : {url}")
    print(f"Destination : {fichier_dest}")

    try:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()

            with open(fichier_dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        print(f"Succès : Enregistré sous {fichier_dest}")

    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement de {nom} : {e}")

# EXÉCUTION

if __name__ == "__main__":
    print("DÉMARRAGE DE L'ÉTAPE RAW (INGESTION)...\n")
    print(f"Dossier du jour : {RAW_DAY_DIR}\n")

    for nom, url in DATASETS.items():
        telecharger_dataset(nom, url)

    print("\nÉTAPE RAW TERMINÉE.")
