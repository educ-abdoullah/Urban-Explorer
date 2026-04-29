import os
import shutil
from pathlib import Path

# Configuration des chemins
BASE_DIR = Path(__file__).resolve().parents[2]
BRONZE_DIR = BASE_DIR/"data"/"raw"

def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]

BRONZE_DIR = get_latest_day_dir(BRONZE_DIR)

def main():
    print("--- DÉBUT DE L'ÉTAPE BRONZE ---")
    
    # Dans cette architecture, les fichiers ont été téléchargés manuellement ou via curl
    # Le script bronze s'assure que les fichiers attendus sont présents et les renomme si nécessaire
    
    files_to_check = {
        "logements_sociaux.geojson": "ils_bronze_logements.geojson",
        "arrondissements.geojson": "ils_bronze_arrondissements.geojson"
    }
    
    for original, target in files_to_check.items():
        original_path = os.path.join(BRONZE_DIR, original)
        target_path = os.path.join(BRONZE_DIR, target)
        
        if os.path.exists(original_path):
            shutil.copy2(original_path, target_path)
            print(f"Fichier {original} copié vers {target}")
        else:
            print(f"ERREUR : Le fichier {original} est manquant dans {BRONZE_DIR}")

    # Création du fichier demandé par l'énoncé (ils_bronze.geojson)
    # Note: L'énoncé demande un seul fichier ils_bronze.geojson, 
    # mais nous avons deux sources. Nous allons utiliser le fichier des logements comme base bronze principale.
    shutil.copy2(os.path.join(BRONZE_DIR, "logements_sociaux.geojson"), os.path.join(BRONZE_DIR, "ils_bronze.geojson"))
    print("Fichier ils_bronze.geojson créé.")
    
    print("--- FIN DE L'ÉTAPE BRONZE ---")

if __name__ == "__main__":
    main()
