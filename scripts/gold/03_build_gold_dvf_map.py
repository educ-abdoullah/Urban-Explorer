import pandas as pd
import geopandas as gpd
from pathlib import Path

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


GOLD_DVF_BASE = DATA_LAKE / "gold"
SILVER_DVF_BASE = DATA_LAKE / "silver"

GOLD_DVF = get_latest_day_dir(GOLD_DVF_BASE)
date_jour = GOLD_DVF.name
SILVER_DVF = SILVER_DVF_BASE / date_jour

GEO_ARRONDISSEMENTS = DATA_LAKE / "raw" / date_jour / "ville" / "arrondissements.geojson"


def normalize_code_commune(value):
    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def build_gold_dvf_map():
    GOLD_DVF.mkdir(parents=True, exist_ok=True)

    silver_path = SILVER_DVF / "dvf_silver.parquet"

    if not silver_path.exists():
        raise FileNotFoundError(f"Silver DVF absent : {silver_path}")

    df = pd.read_parquet(silver_path)

    df["code_commune"] = df["code_commune"].apply(normalize_code_commune)

    # Analyse principale : appartements seulement
    appartements = df[df["type_local"] == "Appartement"].copy()

    gold = (
        appartements
        .groupby(["annee", "code_commune", "arrondissement"], as_index=False)
        .agg(
            prix_m2_median=("prix_m2", "median"),
            prix_m2_moyen=("prix_m2", "mean"),
            valeur_fonciere_mediane=("valeur_fonciere", "median"),
            surface_mediane=("surface_reelle_bati", "median"),
            nb_mutations=("prix_m2", "count")
        )
    )

    gold["code_commune"] = gold["code_commune"].apply(normalize_code_commune)

    parquet_output = GOLD_DVF / "dvf_prix_arrondissement.parquet"
    gold.to_parquet(parquet_output, index=False)

    print(f"✅ Gold DVF tabulaire créée : {parquet_output}")
    print(f"✅ Lignes : {len(gold)}")
    print("Exemples Gold :")
    print(gold.head(10))

    maisons = df[df["type_local"] == "Maison"].copy()
    maisons_output = GOLD_DVF / "dvf_maisons_silver_extract.parquet"
    maisons.to_parquet(maisons_output, index=False)

    print(f"✅ Maisons conservées à part : {maisons_output}")
    print(f"✅ Lignes maisons : {len(maisons)}")

    if not GEO_ARRONDISSEMENTS.exists():
        print(f"⚠️ GeoJSON arrondissements absent : {GEO_ARRONDISSEMENTS}")
        return

    geo = gpd.read_file(GEO_ARRONDISSEMENTS)

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
            f"Aucune colonne code commune trouvée. Colonnes GeoJSON : {geo.columns.tolist()}"
        )

    geo["code_commune"] = geo[code_col].apply(normalize_code_commune)

    print("Codes GeoJSON :")
    print(sorted(geo["code_commune"].unique())[:25])

    print("Codes DVF Gold :")
    print(sorted(gold["code_commune"].unique())[:25])

    geo_gold = geo.merge(
        gold,
        on="code_commune",
        how="inner"
    )

    geojson_output = GOLD_DVF / "dvf_prix_arrondissement.geojson"
    geo_gold.to_file(geojson_output, driver="GeoJSON")

    print(f"✅ Gold DVF GeoJSON créée : {geojson_output}")
    print(f"✅ Features : {len(geo_gold)}")


if __name__ == "__main__":
    build_gold_dvf_map()