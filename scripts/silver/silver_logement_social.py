import os
import geopandas as gpd
import pandas as pd
from pathlib import Path

# Configuration des chemins
BASE_DIR = Path(__file__).resolve().parents[2]
BRONZE_DIR = BASE_DIR/"data"/"raw"
SILVER_DIR = BASE_DIR/"data"/"silver"

def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]

BRONZE_DIR = get_latest_day_dir(BRONZE_DIR)
SILVER_DIR = get_latest_day_dir(SILVER_DIR)

os.makedirs(SILVER_DIR, exist_ok=True)

def main():
    print("--- DÉBUT DE L'ÉTAPE SILVER ---")
    
    # 1. Chargement des données
    print("Chargement des données bronze...")
    gdf_logements = gpd.read_file(os.path.join(BRONZE_DIR, "ils_bronze_logements.geojson"))
    gdf_arr = gpd.read_file(os.path.join(BRONZE_DIR, "ils_bronze_arrondissements.geojson"))
    
    # 2. Nettoyage des logements
    print("Nettoyage des données de logements...")
    # Colonnes identifiées : 'nb_logmt_total', 'code_postal', 'annee', 'arrdt'
    cols_logements = ['nb_logmt_total', 'code_postal', 'annee', 'arrdt']
    available_cols = [c for c in cols_logements if c in gdf_logements.columns]
    gdf_logements = gdf_logements[available_cols + ['geometry']]
    
    # Conversion du nombre de logements en numérique
    gdf_logements['nb_logmt_total'] = pd.to_numeric(gdf_logements['nb_logmt_total'], errors='coerce').fillna(0)
    
    # 3. Nettoyage des arrondissements
    print("Nettoyage des données d'arrondissements...")
    # Colonnes identifiées : 'c_ar', 'l_ar'
    gdf_arr = gdf_arr[['c_ar', 'l_ar', 'geometry']]
    gdf_arr['c_ar'] = gdf_arr['c_ar'].astype(int)
    
    # 4. Jointure Spatiale
    print("Réalisation de la jointure spatiale...")
    if gdf_logements.crs != gdf_arr.crs:
        gdf_logements = gdf_logements.to_crs(gdf_arr.crs)
        
    # On rattache chaque programme à son arrondissement
    gdf_silver = gpd.sjoin(gdf_logements, gdf_arr, how="left", predicate="within")
    
    # 5. Sauvegarde
    print(f"Sauvegarde vers {SILVER_DIR}/ils_silver.geojson...")
    gdf_silver.to_file(os.path.join(SILVER_DIR, "ils_silver.geojson"), driver='GeoJSON')
    
    print("--- FIN DE L'ÉTAPE SILVER ---")

if __name__ == "__main__":
    main()
