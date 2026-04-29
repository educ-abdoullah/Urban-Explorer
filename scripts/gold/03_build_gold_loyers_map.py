import pandas as pd
import geopandas as gpd
from pathlib import Path

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


GOLD_LOYERS_BASE = DATA_LAKE / "gold"
SILVER_LOYERS_BASE = DATA_LAKE / "silver"

GOLD_LOYERS = get_latest_day_dir(GOLD_LOYERS_BASE)
date_jour = GOLD_LOYERS.name
SILVER_LOYERS = SILVER_LOYERS_BASE / date_jour



def normalize_code_commune(value):
    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def clean_piece_category(row):
    nb_pieces = str(row.get("nb_pieces", "")).strip()
    nb_pieces_local = str(row.get("nb_pieces_local", "")).strip()

    if nb_pieces and nb_pieces.lower() not in ["nan", "none"]:
        value = nb_pieces
    elif nb_pieces_local and nb_pieces_local.lower() not in ["nan", "none"]:
        value = nb_pieces_local
    else:
        value = "Tous"

    if value.startswith("L7501"):
        return None

    if value in ["", "nan", "None"]:
        return "Tous"

    return value


def build_gold_loyers_map():
    GOLD_LOYERS.mkdir(parents=True, exist_ok=True)

    loyers_path = SILVER_LOYERS / "loyers_clean.parquet"
    mapping_path = SILVER_LOYERS / "mapping_arrondissement_zone.parquet"
    geo_path = DATA_LAKE / "raw" /date_jour/ "ville" / "arrondissements.geojson"

    loyers = pd.read_parquet(loyers_path)
    mapping = pd.read_parquet(mapping_path)

    loyers = loyers[loyers["annee"].isin([2022, 2023, 2024])].copy()
    mapping = mapping[mapping["annee"].isin([2022, 2023, 2024])].copy()

    loyers = loyers[loyers["loyer_m2_median"].notna()].copy()

    loyers["nb_pieces"] = loyers.apply(clean_piece_category, axis=1)
    loyers = loyers[loyers["nb_pieces"].notna()].copy()

    allowed_categories = [
        "Tous",
        "Ensemble 1P",
        "Ensemble 2P",
        "Ensemble 3P",
        "Ensemble 4P+",
        "Appart 1P",
        "Appart 2P",
        "Appart 3P",
        "Appart 4P+"
    ]

    loyers = loyers[loyers["nb_pieces"].isin(allowed_categories)].copy()

    gold = loyers.merge(
        mapping,
        on=["annee", "zone_olap"],
        how="inner"
    )

    selected_columns = [
        "annee",
        "code_commune",
        "arrondissement",
        "nom_commune",
        "zone_olap",
        "lib_zone",
        "nb_pieces",
        "loyer_m2_median",
        "loyer_m2_moyen",
        "loyer_mensuel_median",
        "loyer_mensuel_moyen",
        "surface_moyenne",
        "nb_observations",
        "nb_logements"
    ]

    gold = gold[selected_columns].copy()

    gold["code_commune"] = gold["code_commune"].apply(normalize_code_commune)

    gold_path = GOLD_LOYERS / "loyers_arrondissement.parquet"
    gold.to_parquet(gold_path, index=False)

    print(f"✅ Gold tabulaire créée : {len(gold)} lignes")
    print(f"✅ Fichier : {gold_path}")

    if not geo_path.exists():
        print(f"⚠️ GeoJSON absent : {geo_path}")
        return

    geo = gpd.read_file(geo_path)

    print("Colonnes GeoJSON disponibles :")
    print(geo.columns.tolist())

    possible_code_cols = [
        "code_commune",
        "c_arinsee",
        "insee",
        "INSEE",
        "code_insee",
        "CODE_INSEE",
        "code"
    ]

    code_col = None

    for col in possible_code_cols:
        if col in geo.columns:
            code_col = col
            break

    if code_col is None:
        raise ValueError(
            "Aucune colonne de code commune trouvée dans le GeoJSON. "
            "Regarde les colonnes affichées au-dessus."
        )

    geo["code_commune"] = geo[code_col].apply(normalize_code_commune)

    geo_gold = geo.merge(
        gold,
        on="code_commune",
        how="inner"
    )

    geojson_path = GOLD_LOYERS / "loyers_arrondissement.geojson"
    geo_gold.to_file(geojson_path, driver="GeoJSON")

    print(f"✅ Gold GeoJSON créée : {len(geo_gold)} features")
    print(f"✅ Fichier : {geojson_path}")


if __name__ == "__main__":
    build_gold_loyers_map()