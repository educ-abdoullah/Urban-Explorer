import pandas as pd
import geopandas as gpd
from pathlib import Path

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


GOLD_POP = DATA_LAKE / "gold"
SILVER_POP = DATA_LAKE / "silver"

GOLD_POP = get_latest_day_dir(GOLD_POP)
date_jour = GOLD_POP.name
SILVER_POP = SILVER_POP / date_jour
GEO_ARRONDISSEMENTS = DATA_LAKE / "raw" /date_jour/ "ville" / "arrondissements.geojson"

def normalize_code_commune(value):
    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def build_gold_population_map():
    GOLD_POP.mkdir(parents=True, exist_ok=True)

    silver_path = SILVER_POP / "population_arrondissement_silver.parquet"

    if not silver_path.exists():
        raise FileNotFoundError(f"Silver population absent : {silver_path}")

    pop = pd.read_parquet(silver_path)

    pop["code_commune"] = pop["code_commune"].apply(normalize_code_commune)

    gold = pop[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "nom_arrondissement",
            "population",
            "mesure_population"
        ]
    ].copy()

    gold = gold.sort_values(["annee", "arrondissement"]).reset_index(drop=True)

    parquet_output = GOLD_POP / "population_arrondissement.parquet"
    gold.to_parquet(parquet_output, index=False)

    print(f"✅ Gold population tabulaire créée : {parquet_output}")
    print(f"✅ Lignes : {len(gold)}")
    print(gold)

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

    geo_gold = geo.merge(
        gold,
        on="code_commune",
        how="inner"
    )

    geojson_output = GOLD_POP / "population_arrondissement.geojson"
    geo_gold.to_file(geojson_output, driver="GeoJSON")

    print(f"✅ Gold population GeoJSON créée : {geojson_output}")
    print(f"✅ Features : {len(geo_gold)}")


if __name__ == "__main__":
    build_gold_population_map()