import os
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

# Configuration des chemins
BASE_DIR = Path(__file__).resolve().parents[2]
BRONZE_DIR = BASE_DIR/"data"/"raw"
SILVER_DIR = BASE_DIR/"data"/"silver"
GOLD_DIR = BASE_DIR/"data"/"gold"

def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]

BRONZE_DIR = get_latest_day_dir(BRONZE_DIR)
SILVER_DIR = get_latest_day_dir(SILVER_DIR)
GOLD_DIR = get_latest_day_dir(GOLD_DIR)

os.makedirs(GOLD_DIR, exist_ok=True)

def normaliser(serie):
    """Normalise une série sur une échelle de 0 à 100."""
    if serie.max() == serie.min():
        return 0
    return ((serie - serie.min()) / (serie.max() - serie.min())) * 100

def main():
    print("--- DÉBUT DE L'ÉTAPE GOLD ---")
    
    # 1. Chargement des données
    print("Chargement des données silver et des fonds de carte...")
    gdf_silver = gpd.read_file(os.path.join(SILVER_DIR, "ils_silver.geojson"))
    gdf_arr = gpd.read_file(os.path.join(BRONZE_DIR, "ils_bronze_arrondissements.geojson"))
    
    # 2. Agrégation par arrondissement
    print("Agrégation des logements par arrondissement...")
    # On utilise 'c_ar' qui vient de la jointure spatiale dans silver
    stats_arr = gdf_silver.groupby('c_ar').agg({
        'nb_logmt_total': 'sum'
    }).reset_index()
    
    # 3. Calcul du score
    print("Calcul du score normalisé...")
    stats_arr['score_logement_social'] = normaliser(stats_arr['nb_logmt_total'])
    
    # 4. Fusion avec la géométrie des arrondissements
    gdf_arr['c_ar'] = gdf_arr['c_ar'].astype(int)
    gdf_gold = gdf_arr.merge(stats_arr, on='c_ar', how='left')
    gdf_gold['nb_logmt_total'] = gdf_gold['nb_logmt_total'].fillna(0)
    gdf_gold['score_logement_social'] = gdf_gold['score_logement_social'].fillna(0)
    
    # 5. Exports
    print("Export des fichiers Gold (GeoJSON et Parquet)...")
    
    # Export GeoJSON
    gold_geojson_path = os.path.join(GOLD_DIR, "ils_gold.geojson")
    gdf_gold.to_file(gold_geojson_path, driver='GeoJSON')
    
    # Export Parquet
    gold_parquet_path = os.path.join(GOLD_DIR, "ils_gold.parquet")
    try:
        # Utilisation de GeoParquet si possible
        gdf_gold.to_parquet(gold_parquet_path)
    except Exception as e:
        print(f"Note: Export GeoParquet a échoué ({e}), export Parquet standard sans géométrie...")
        df_gold_no_geo = pd.DataFrame(gdf_gold.drop(columns='geometry'))
        df_gold_no_geo.to_parquet(gold_parquet_path)

    print(f"Fichiers générés dans {GOLD_DIR}")
    print("--- FIN DE L'ÉTAPE GOLD ---")

if __name__ == "__main__":
    main()
