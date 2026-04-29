import pandas as pd
import geopandas as gpd
from shapely import wkb
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


BRONZE_IRIS = DATA_LAKE / "raw" /date_jour/ "iris"
GOLD_IRIS = GOLD_DIR 


def normalize_code(value):
    value = str(value).strip()
    if value.endswith(".0"):
        value = value[:-2]
    return value


def normalize_20_80(series):
    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val) or min_val == max_val:
        return pd.Series([50.0] * len(series), index=series.index)

    return 20 + 60 * ((series - min_val) / (max_val - min_val))


def convert_wkb_to_geometry(value):
    if value is None:
        return None

    if isinstance(value, bytes):
        return wkb.loads(value)

    return value


def build_score_urbain_iris():
    GOLD_IRIS.mkdir(parents=True, exist_ok=True)

    imvu = pd.read_parquet(BRONZE_IRIS / "imvu_scores_iris.parquet")
    iris_scores = pd.read_parquet(BRONZE_IRIS / "iris_scores.parquet")
    invest = pd.read_parquet(BRONZE_IRIS / "score_investissement_iris.parquet")
    mobilite = pd.read_parquet(BRONZE_IRIS / "score_mobilite.parquet")

    # =========================
    # Normalisation clés
    # =========================
    imvu["code_iris"] = imvu["code_iris"].apply(normalize_code)
    iris_scores["code_iris"] = iris_scores["iris_code"].apply(normalize_code)
    invest["code_iris"] = invest["code_iris"].apply(normalize_code)
    mobilite["code_iris"] = mobilite["code_iris"].apply(normalize_code)

    imvu = imvu[imvu["code_iris"].str.startswith("751")].copy()
    iris_scores = iris_scores[iris_scores["code_iris"].str.startswith("751")].copy()
    invest = invest[invest["code_iris"].str.startswith("751")].copy()
    mobilite = mobilite[mobilite["code_iris"].str.startswith("751")].copy()

    # =========================
    # Base investissement IRIS
    # =========================
    base_cols = [
        "annee",
        "code_iris",
        "code_commune",
        "arrondissement",
        "nom_commune",
        "nom_iris",
        "code_quartier",
        "code_quartier_insee",
        "nom_quartier",
        "prix_m2_median",
        "prix_m2_moyen",
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct",
        "charges_estimees_pct_loyer",
        "nb_mutations",
        "liquidite_brute",
        "population",
        "population_hommes",
        "population_femmes",
        "population_0_14",
        "population_15_29",
        "population_30_44",
        "population_45_59",
        "population_60_74",
        "population_75_plus",
        "indice_criminalite_brut",
        "nombre_faits_estime_iris",
        "score_criminalite",
        "score_securite",
        "score_rendement",
        "score_liquidite",
        "score_investissement",
        "zone_olap",
        "lib_zone",
        "geometry"
    ]

    df = invest[base_cols].copy()

    # =========================
    # IMVU environnement
    # =========================
    imvu_cols = [
        "code_iris",
        "surface_m2",
        "nb_arbres_alignement",
        "nb_initiatives",
        "ratio_parcs_pct",
        "ratio_canopee_pct",
        "score_parcs",
        "score_rues",
        "score_initiatives",
        "IMVU_Global"
    ]

    df = df.merge(
        imvu[imvu_cols],
        on="code_iris",
        how="left"
    )

    # =========================
    # Scores services IRIS
    # =========================
    services_cols = [
        "code_iris",
        "iris_name",
        "iris_commune",
        "iris_surface_m2",
        "score_health",
        "score_edu",
        "score_sport",
        "score_vibrance",
        "score_noise",
        "score_env",
        "score_senior",
        "score_actifs",
        "score_jeune_adult",
        "score_junior"
    ]

    df = df.merge(
        iris_scores[services_cols],
        on="code_iris",
        how="left"
    )

    # =========================
    # Mobilité
    # =========================
    mobilite_cols = [
        "code_iris",
        "velib_station",
        "capacity",
        "nb_places_ouvrage",
        "nb_places_auto",
        "stationnement_total",
        "places_km2",
        "trafic_moyen_q",
        "occupation_moyenne_k",
        "Bus",
        "Metro",
        "Tramway",
        "RapidTransit",
        "regionalRail",
        "nb_arrets",
        "score_velib",
        "score_stationnement",
        "score_tc",
        "score_trafic",
        "score_trafic_inverse",
        "score_mobilite"
    ]

    df = df.merge(
        mobilite[mobilite_cols],
        on="code_iris",
        how="left"
    )

    # =========================
    # Scores lisibles
    # =========================
    df["score_vegetation"] = df["IMVU_Global"]
    df["score_rues_vegetalisees"] = df["score_rues"]
    df["score_initiatives_vertes"] = df["score_initiatives"]

    df["score_sante"] = df["score_health"]
    df["score_education"] = df["score_edu"]

    # Score bruit brut inversé : score_noise élevé = plus bruyant
    df["score_bruit_inverse_brut"] = 100 - (df["score_noise"] * 100)

    df["score_services_quartier_brut"] = (
        df[
            [
                "score_health",
                "score_edu",
                "score_sport",
                "score_vibrance"
            ]
        ].mean(axis=1)
        * 100
    )

    df["score_environnement_brut"] = (
        0.70 * df["score_vegetation"].fillna(0)
        + 0.30 * (df["score_env"].fillna(0) * 100)
    )

    # =========================
    # Normalisation par année
    # =========================
    df["score_environnement"] = (
        df.groupby("annee")["score_environnement_brut"]
        .transform(lambda s: normalize_20_80(s))
    )

    df["score_mobilite_norm"] = (
        df.groupby("annee")["score_mobilite"]
        .transform(lambda s: normalize_20_80(s))
    )

    df["score_services_quartier"] = (
        df.groupby("annee")["score_services_quartier_brut"]
        .transform(lambda s: normalize_20_80(s))
    )

    df["score_bruit_inverse_norm"] = (
        df.groupby("annee")["score_bruit_inverse_brut"]
        .transform(lambda s: normalize_20_80(s))
    )

    # =========================
    # Score urbain global IRIS
    # =========================
    df["score_urbain_global"] = (
        0.35 * df["score_investissement"].fillna(0)
        + 0.25 * df["score_environnement"].fillna(0)
        + 0.20 * df["score_mobilite_norm"].fillna(0)
        + 0.20 * df["score_services_quartier"].fillna(0)
    )

    # =========================
    # Renommage clair
    # =========================
    df = df.rename(columns={
        "score_mobilite": "score_mobilite_brut",
        "score_mobilite_norm": "score_mobilite",
        "score_tc": "score_transport_commun",
        "velib_station": "nb_stations_velib",
        "capacity": "capacite_velib",
        "nb_arrets": "nb_arrets_transport",
        "score_bruit_inverse_norm": "score_bruit_inverse"
    })

    # Supprime toute colonne doublon éventuelle
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # =========================
    # Arrondis
    # =========================
    round_cols = [
        "score_urbain_global",
        "score_investissement",
        "score_rendement",
        "score_criminalite",
        "score_securite",
        "score_liquidite",
        "score_environnement",
        "score_vegetation",
        "score_parcs",
        "score_rues_vegetalisees",
        "score_initiatives_vertes",
        "score_mobilite",
        "score_velib",
        "score_stationnement",
        "score_transport_commun",
        "score_trafic_inverse",
        "score_services_quartier",
        "score_sante",
        "score_education",
        "score_sport",
        "score_vibrance",
        "score_bruit_inverse",
        "prix_m2_median",
        "prix_m2_moyen",
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct",
        "ratio_parcs_pct",
        "ratio_canopee_pct"
    ]

    for col in round_cols:
        if col in df.columns:
            df[col] = df[col].round(2)

    final_cols = [
        "annee",
        "code_iris",
        "code_commune",
        "arrondissement",
        "nom_commune",
        "nom_iris",
        "nom_quartier",
        "code_quartier",
        "code_quartier_insee",

        "score_urbain_global",

        "score_investissement",
        "score_rendement",
        "score_criminalite",
        "score_securite",
        "score_liquidite",

        "score_environnement",
        "score_vegetation",
        "score_parcs",
        "score_rues_vegetalisees",
        "score_initiatives_vertes",

        "score_mobilite",
        "score_velib",
        "score_stationnement",
        "score_transport_commun",
        "score_trafic_inverse",

        "score_services_quartier",
        "score_sante",
        "score_education",
        "score_sport",
        "score_vibrance",
        "score_bruit_inverse",

        "prix_m2_median",
        "prix_m2_moyen",
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct",
        "charges_estimees_pct_loyer",
        "nb_mutations",
        "liquidite_brute",

        "population",
        "population_hommes",
        "population_femmes",
        "population_0_14",
        "population_15_29",
        "population_30_44",
        "population_45_59",
        "population_60_74",
        "population_75_plus",

        "nb_arbres_alignement",
        "nb_initiatives",
        "nb_stations_velib",
        "capacite_velib",
        "nb_arrets_transport",
        "stationnement_total",

        "ratio_parcs_pct",
        "ratio_canopee_pct",

        "zone_olap",
        "lib_zone",
        "geometry"
    ]

    df = df[final_cols].copy()

    df = df.sort_values(
        ["annee", "score_urbain_global"],
        ascending=[True, False]
    ).reset_index(drop=True)

    # Sécurité finale : aucun doublon de colonnes
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # =========================
    # Export Parquet
    # =========================
    parquet_output = GOLD_IRIS / "score_urbain_iris.parquet"
    df.to_parquet(parquet_output, index=False)

    print(f"✅ Gold score urbain IRIS parquet créé : {parquet_output}")
    print(f"✅ Lignes : {len(df)}")
    print(df.head(20))

    # =========================
    # Export GeoJSON
    # =========================
    df_geo = df.copy()
    df_geo["geometry"] = df_geo["geometry"].apply(convert_wkb_to_geometry)

    gdf = gpd.GeoDataFrame(
        df_geo,
        geometry="geometry",
        crs="EPSG:4326"
    )

    geojson_output = GOLD_IRIS / "score_urbain_iris.geojson"
    gdf.to_file(geojson_output, driver="GeoJSON")

    print(f"✅ Gold score urbain IRIS GeoJSON créé : {geojson_output}")
    print(f"✅ Features : {len(gdf)}")


if __name__ == "__main__":
    build_score_urbain_iris()