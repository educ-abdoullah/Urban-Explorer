import json
from pathlib import Path
from pymongo import MongoClient, GEOSPHERE
from pathlib import Path

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()

def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


GOLD_DIR = DATA_LAKE / "gold"

GOLD_DIR = get_latest_day_dir(GOLD_DIR)
date_jour = GOLD_DIR.name


MONGO_URI = "mongodb+srv://admin:admin@urbanexplorer.6oxlveb.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "urban_explorer"


GEOJSON_FILES = {
    "loyers_arrondissements": GOLD_DIR / "loyers_arrondissement.geojson",
    "dvf_arrondissements": GOLD_DIR / "dvf_prix_arrondissement.geojson",
    "criminalite_arrondissements": GOLD_DIR / "criminalite_score_arrondissement.geojson",
    "population_arrondissements": GOLD_DIR / "population_arrondissement.geojson",
    "score_investissement_arrondissements": GOLD_DIR / "score_arrondissement" / "score_investissement_arrondissement.geojson",
}


def load_geojson_features(path: Path):
    if not path.exists():
        print(f"⚠️ Fichier absent : {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") == "FeatureCollection":
        return data.get("features", [])

    if data.get("type") == "Feature":
        return [data]

    raise ValueError(f"Format GeoJSON non reconnu : {path}")


def prepare_document(feature):
    props = feature.get("properties", {})
    geometry = feature.get("geometry")

    return {
        **props,
        "geometry": geometry,
        "geojson_type": feature.get("type", "Feature")
    }


def import_collection(db, collection_name, geojson_path):
    print(f"\nImport collection : {collection_name}")
    print(f"Fichier : {geojson_path}")

    features = load_geojson_features(geojson_path)

    if not features:
        print("Aucune feature à importer.")
        return

    documents = [prepare_document(feature) for feature in features]

    collection = db[collection_name]

    collection.delete_many({})
    collection.insert_many(documents)

    collection.create_index([("geometry", GEOSPHERE)])
    collection.create_index("annee")
    collection.create_index("arrondissement")
    collection.create_index("code_commune")

    print(f"✅ {len(documents)} documents insérés dans {collection_name}")


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    for collection_name, geojson_path in GEOJSON_FILES.items():
        import_collection(db, collection_name, geojson_path)

    print("\n✅ Import MongoDB terminé.")


if __name__ == "__main__":
    main()