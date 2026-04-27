import os
import requests
from datetime import datetime

# CONFIGURATION

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../data/bronze"))
os.makedirs(BRONZE_DIR, exist_ok=True)

# URL de base de l'API d'export des datasets
BASE_URL_PARIS = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/{}/exports/geojson"
BASE_URL_ILE_DE_FRANCE = "https://data.iledefrance.fr/api/explore/v2.1/catalog/datasets/{}/exports/geojson"

# Liste des identifiants exacts des datasets et de leur source
DATASETS = {
    "iris": (BASE_URL_ILE_DE_FRANCE, "iris"),
    "espaces_verts": (BASE_URL_PARIS, "espaces_verts"),
    "arbres": (BASE_URL_PARIS, "arbres-plantes-hors-peuplement-forestier"),
    "jardins_partages": (BASE_URL_PARIS, "jardins-partages")
}

# FONCTION D'INGESTION

def telecharger_dataset(nom, url_template, dataset_id):
    url = url_template.format(dataset_id)
    # Ajout d'un timestamp pour garder un historique des versions
    date_jour = datetime.now().strftime("%Y%m%d")
    fichier_dest = os.path.join(BRONZE_DIR, f"{nom}_raw_{date_jour}.geojson")
    
    print(f"Téléchargement de {nom} depuis {dataset_id}...")
    
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            
            with open(fichier_dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        print(f"Succès : Enregistré sous {fichier_dest}")
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement de {nom} : {e}")

# EXÉCUTION

if __name__ == "__main__":
    print("DÉMARRAGE DE L'ÉTAPE BRONZE (INGESTION)...\n")
    for nom, (url_template, dataset_id) in DATASETS.items():
        telecharger_dataset(nom, url_template, dataset_id)
    print("\nÉTAPE BRONZE TERMINÉE.")