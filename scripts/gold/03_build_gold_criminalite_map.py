import pandas as pd
import geopandas as gpd
from pathlib import Path

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


GOLD_CRIMINALITE_BASE = DATA_LAKE / "gold"
SILVER_CRIMINALITE_BASE = DATA_LAKE / "silver"

GOLD_CRIMINALITE = get_latest_day_dir(GOLD_CRIMINALITE_BASE)
date_jour = GOLD_CRIMINALITE.name
SILVER_CRIMINALITE = SILVER_CRIMINALITE_BASE / date_jour

GEO_ARRONDISSEMENTS = DATA_LAKE / "raw" / date_jour / "ville" / "arrondissements.geojson"


def normalize_code_commune(value):
    value = str(value).strip()
    if value.endswith(".0"):
        value = value[:-2]
    return value.zfill(5)


def build_gold_criminalite_map():
    GOLD_CRIMINALITE.mkdir(parents=True, exist_ok=True)

    silver_path = SILVER_CRIMINALITE / "criminalite_silver.parquet"
    df = pd.read_parquet(silver_path)

    gold = (
        df.groupby(["annee", "code_commune", "arrondissement"], as_index=False)
        .agg(
            indice_criminalite_brut=("taux_pour_mille_final", "sum"),
            nombre_faits_estime=("nombre_final", "sum"),
            population=("insee_pop", "max"),
            nb_indicateurs=("indicateur", "nunique")
        )
    )

    gold["code_commune"] = gold["code_commune"].apply(normalize_code_commune)

    # Min / max par année pour score relatif 20-80
    gold["min_annee"] = gold.groupby("annee")["indice_criminalite_brut"].transform("min")
    gold["max_annee"] = gold.groupby("annee")["indice_criminalite_brut"].transform("max")

    denominator = gold["max_annee"] - gold["min_annee"]

    
    gold["score_criminalite"] = 50.0
    mask = denominator != 0

    gold.loc[mask, "score_criminalite"] = (
        20.0
        + 60.0
        * (
            (gold.loc[mask, "indice_criminalite_brut"] - gold.loc[mask, "min_annee"])
            / denominator.loc[mask]
        )
    )

    gold = gold.drop(columns=["min_annee", "max_annee"])

    gold["score_criminalite"] = gold["score_criminalite"].round(2)
    gold["indice_criminalite_brut"] = gold["indice_criminalite_brut"].round(2)
    gold["nombre_faits_estime"] = gold["nombre_faits_estime"].round(0)

    gold = gold[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "indice_criminalite_brut",
            "nombre_faits_estime",
            "population",
            "nb_indicateurs",
            "score_criminalite"
        ]
    ].copy()

    parquet_output = GOLD_CRIMINALITE / "criminalite_score_arrondissement.parquet"
    gold.to_parquet(parquet_output, index=False)

    print(f"✅ Gold criminalité tabulaire créée : {parquet_output}")
    print(f"✅ Lignes : {len(gold)}")
    print(gold.head(10))

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

    geojson_output = GOLD_CRIMINALITE / "criminalite_score_arrondissement.geojson"
    geo_gold.to_file(geojson_output, driver="GeoJSON")

    print(f"✅ Gold criminalité GeoJSON créée : {geojson_output}")
    print(f"✅ Features : {len(geo_gold)}")


if __name__ == "__main__":
    build_gold_criminalite_map()