import geopandas as gpd
import pandas as pd
import numpy as np
from pymongo import MongoClient
from datetime import datetime, timezone
from pathlib import Path

DATA_LAKE = (Path(__file__).resolve().parents[1] / "data").resolve()

def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]

GOLD_DIR = DATA_LAKE / "gold"

GOLD_DIR = get_latest_day_dir(GOLD_DIR)
datejour = GOLD_DIR.name

MONGODB_URI = "mongodb+srv://admin:admin@urbanexplorer.6oxlveb.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "urban_explorer"

ARR_PATH = GOLD_DIR/"score_urbain_arrondissement.geojson"
IRIS_PATH = GOLD_DIR/"score_urbain_iris.geojson"

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db["scores"]


def clean_value(v):
    if pd.isna(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def import_geojson_full(path, level, id_col, name_col, year=None, year_col=None):
    gdf = gpd.read_file(path)

    for _, row in gdf.iterrows():
        props = {
            col: clean_value(row[col])
            for col in gdf.columns
            if col != "geometry"
        }

        # priorité à la colonne du fichier si year_col est fournie
        doc_year = None
        if year_col is not None and year_col in row.index:
            doc_year = clean_value(row[year_col])
        elif year is not None:
            doc_year = year

        doc = {
            "area_id": clean_value(row[id_col]),
            "area_name": clean_value(row[name_col]),
            "level": level,
            "geometry": row["geometry"].__geo_interface__,
            "properties": props,
            "updated_at": datetime.now(timezone.utc)
        }

        if doc_year is not None:
            doc["year"] = int(doc_year)

        filter_query = {
            "area_id": doc["area_id"],
            "level": doc["level"]
        }

        if doc_year is not None:
            filter_query["year"] = int(doc_year)

        collection.update_one(
            filter_query,
            {"$set": doc},
            upsert=True
        )

    print(f"{len(gdf)} documents importés pour {level}")


# Exemple 1 : tout le fichier correspond à une seule année
import_geojson_full(
    path=ARR_PATH,
    level="arrondissement",
    id_col="c_ar",
    name_col="l_ar",
    year_col="annee"
)

import_geojson_full(
    path=IRIS_PATH,
    level="iris",
    id_col="code_iris",
    name_col="nom_iris",
    year_col="annee"
)