import pandas as pd
import json
from pathlib import Path
from typing import Final
import os

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
RAW_DATA_DIR: Final[Path] = PROJECT_ROOT / "data"

def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]

GOLD_DIR = RAW_DATA_DIR / "gold"

GOLD_DIR = get_latest_day_dir(GOLD_DIR)
date_jour = GOLD_DIR.name

# 1. Charger les revenus (le CSV que nous avons créé précédemment)
income_path = RAW_DATA_DIR/"raw"/date_jour / "paris_revenu_median_arrondissement.csv"
if not income_path.exists():
    raise FileNotFoundError(f"Missing income CSV at {income_path}")
# Charger le CSV des revenus via un chemin absolu déterminé depuis le projet
income_df = pd.read_csv(income_path)
# On crée une clé simple (ex: 13 pour le 13ème) pour faciliter la jointure
income_df['arr_key'] = income_df['arrondissement'].astype(int) % 100

def process_affordability(geojson_path, level_name):
    # Résolution robuste du chemin GeoJSON (supporte chemins relatifs et emplacement dans data/gold)
    geojson_path = Path(geojson_path)
    if not geojson_path.exists():
        candidates = [
            GOLD_DIR / geojson_path,
            GOLD_DIR/date_jour / geojson_path.name
        ]
        for c in candidates:
            if c.exists():
                geojson_path = c
                break
        else:
            raise FileNotFoundError(
                f"GeoJSON not found: {geojson_path}. Tried: {', '.join(str(p) for p in candidates)}"
            )

    # Charger le GeoJSON
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extraire les propriétés en DataFrame
    rows = [feature['properties'] for feature in data['features']]
    df = pd.DataFrame(rows)
    
    # Jointure avec les revenus
    # Note : dans vos JSON, 'arrondissement' est déjà un entier (ex: 13)
    df = df.merge(income_df[['arr_key', 'median_income_monthly_uc']], 
                  left_on='arrondissement', right_on='arr_key', how='left')
    
    # Calculs
    surface_standard = 35
    df['loyer_theorique_35m2'] = df['loyer_m2_median'] * surface_standard
    df['taux_effort'] = df['loyer_theorique_35m2'] / df['median_income_monthly_uc']
    
    # Score Accessibilité (Normalisation 0-10)
    # Plus le taux d'effort est élevé, plus le score est bas
    e_min = df['taux_effort'].min()
    e_max = df['taux_effort'].max()
    df['score_affordability'] = 10 * (1 - (df['taux_effort'] - e_min) / (e_max - e_min))
    
    # Trim outputs per level to keep only the fields we use downstream
    if level_name == 'arrondissement':
        keep_cols = [
            "n_sq_ar",
            "c_ar",
            "c_arinsee",
            "l_ar",
            "l_aroff",
            "n_sq_co",
            "prix_m2_median",
            "loyer_m2_median",
            "median_income_monthly_uc",
            "loyer_theorique_35m2",
            "taux_effort",
            "score_affordability",
        ]
        available = [c for c in keep_cols if c in df.columns]
        df_out = df[available].copy()
    elif level_name == 'iris':
        # keep identifying and affordability-related fields for IRIS
        keep_cols = [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "nom_quartier",
            "code_quartier",
            "prix_m2_median",
            "loyer_m2_median",
            "median_income_monthly_uc",
            "loyer_theorique_35m2",
            "taux_effort",
            "score_affordability",
        ]
        available = [c for c in keep_cols if c in df.columns]
        df_out = df[available].copy()
    else:
        df_out = df

    # Sauvegarde (écrire dans data/gold)
    out_dir = PROJECT_ROOT / "data" / "gold"/date_jour
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"accessibilite_{level_name}.csv"
    out_parquet = out_dir / f"accessibilite_{level_name}.parquet"
    df_out.to_csv(out_csv, index=False)
    df_out.to_parquet(out_parquet)  # Nécessite pyarrow
    return df_out

# Exécution pour vos fichiers
df_iris = process_affordability('score_urbain_iris.geojson', 'iris')
df_arr = process_affordability('score_urbain_arrondissement.geojson', 'arrondissement')

# Pour le niveau QUARTIER (agrégation des IRIS)
df_quartier = df_iris.groupby(['nom_quartier', 'arrondissement']).agg({
     'loyer_m2_median': 'mean',
     'score_affordability': 'mean',
     'taux_effort': 'mean'
}).reset_index()
out_dir = PROJECT_ROOT / "data" / "gold"/date_jour
out_dir.mkdir(parents=True, exist_ok=True)
out_quartier_csv = out_dir / 'accessibilite_quartier.csv'
out_quartier_parquet = out_dir / 'accessibilite_quartier.parquet'
# Keep only the minimal quartier columns
quartier_keep = [
    'nom_quartier',
    'arrondissement',
    'loyer_m2_median',
    'taux_effort',
    'score_affordability',
]
available_q = [c for c in quartier_keep if c in df_quartier.columns]
df_quartier_out = df_quartier[available_q].copy()
df_quartier_out.to_csv(out_quartier_csv, index=False)
df_quartier_out.to_parquet(out_quartier_parquet)