import pandas as pd
import geopandas as gpd
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


BRONZE_INDICATEUR = DATA_LAKE / "raw" /date_jour/ "indicateur"
GOLD_SCORE_INVEST = DATA_LAKE / "gold" /date_jour 
GOLD_URBAIN = DATA_LAKE / "gold" / date_jour

GEO_ARRONDISSEMENTS = DATA_LAKE / "raw" /date_jour/ "ville" / "arrondissements.geojson"


def normalize_code_commune(value):
    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def extract_arrondissement_from_iris(code_iris):
    code_iris = str(code_iris).strip()
    return int(code_iris[3:5])


def normalize_20_80(series):
    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val) or min_val == max_val:
        return pd.Series([50.0] * len(series), index=series.index)

    return 20 + 60 * ((series - min_val) / (max_val - min_val))


def build_score_urbain_arrondissement():
    GOLD_URBAIN.mkdir(parents=True, exist_ok=True)

    imvu_path = BRONZE_INDICATEUR / "imvu_scores_iris.parquet"
    mobilite_path = BRONZE_INDICATEUR / "score_mobilite.parquet"
    quartier_path = BRONZE_INDICATEUR / "quartier_scores.parquet"
    investissement_path = GOLD_SCORE_INVEST / "score_investissement_arrondissement.parquet"

    imvu = pd.read_parquet(imvu_path)
    mobilite = pd.read_parquet(mobilite_path)
    quartier = pd.read_parquet(quartier_path)
    investissement = pd.read_parquet(investissement_path)

    # =========================
    # 1. IMVU → arrondissement
    # =========================
    imvu["code_iris"] = imvu["code_iris"].astype(str)
    imvu = imvu[imvu["code_iris"].str.startswith("751")].copy()
    imvu["arrondissement"] = imvu["code_iris"].apply(extract_arrondissement_from_iris)

    imvu_arr = (
        imvu.groupby("arrondissement", as_index=False)
        .agg(
            score_vegetation=("IMVU_Global", "mean"),
            score_parcs=("score_parcs", "mean"),
            score_rues_vegetalisees=("score_rues", "mean"),
            score_initiatives_vertes=("score_initiatives", "mean"),
            ratio_parcs_pct=("ratio_parcs_pct", "mean"),
            ratio_canopee_pct=("ratio_canopee_pct", "mean"),
            nb_arbres_alignement=("nb_arbres_alignement", "sum"),
            nb_initiatives=("nb_initiatives", "sum")
        )
    )

    # =========================
    # 2. Mobilité → arrondissement
    # =========================
    mobilite["code_iris"] = mobilite["code_iris"].astype(str)
    mobilite = mobilite[mobilite["code_iris"].str.startswith("751")].copy()
    mobilite["arrondissement"] = mobilite["code_iris"].apply(extract_arrondissement_from_iris)

    mobilite_arr = (
        mobilite.groupby("arrondissement", as_index=False)
        .agg(
            score_mobilite=("score_mobilite", "mean"),
            score_velib=("score_velib", "mean"),
            score_stationnement=("score_stationnement", "mean"),
            score_transport_commun=("score_tc", "mean"),
            score_trafic=("score_trafic", "mean"),
            score_trafic_inverse=("score_trafic_inverse", "mean"),
            nb_arrets_transport=("nb_arrets", "sum"),
            nb_stations_velib=("velib_station", "sum"),
            capacite_velib=("capacity", "sum"),
            stationnement_total=("stationnement_total", "sum")
        )
    )

    # =========================
    # 3. Quartier → arrondissement
    # =========================
    quartier = quartier[
        quartier["arrondissement"].between(1, 20)
    ].copy()

    quartier_arr = (
        quartier.groupby("arrondissement", as_index=False)
        .agg(
            score_sante=("score_health", "mean"),
            score_education=("score_edu", "mean"),
            score_sport=("score_sport", "mean"),
            score_vibrance=("score_vibrance", "mean"),
            score_bruit=("score_noise", "mean"),
            score_environnement_quartier=("score_env", "mean"),
            score_senior=("score_senior", "mean"),
            score_actifs=("score_actifs", "mean"),
            score_jeune_adulte=("score_jeune_adult", "mean"),
            score_junior=("score_junior", "mean")
        )
    )

    # =========================
    # 4. Investissement
    # =========================
    investissement["code_commune"] = investissement["code_commune"].apply(normalize_code_commune)

    invest_cols = [
        "annee",
        "code_commune",
        "arrondissement",
        "prix_m2_median",
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct",
        "score_rendement",
        "score_criminalite",
        "score_securite",
        "score_liquidite",
        "score_investissement",
        "nb_mutations",
        "population"
    ]

    investissement = investissement[invest_cols].copy()

    # =========================
    # 5. Jointures finales
    # =========================
    df = investissement.merge(imvu_arr, on="arrondissement", how="left")
    df = df.merge(mobilite_arr, on="arrondissement", how="left")
    df = df.merge(quartier_arr, on="arrondissement", how="left")

    # =========================
    # 6. Scores composés
    # =========================
    df["score_environnement"] = (
        0.60 * df["score_vegetation"].fillna(0)
        + 0.40 * df["score_environnement_quartier"].fillna(0)
    )

    df["score_services_quartier"] = (
        df[
            [
                "score_sante",
                "score_education",
                "score_sport",
                "score_vibrance"
            ]
        ]
        .mean(axis=1)
    )

    df["score_bruit_inverse"] = 100 - df["score_bruit"]

    # Normalisation des scores urbains sur 20-80
    for col in [
        "score_environnement",
        "score_mobilite",
        "score_services_quartier",
        "score_bruit_inverse"
    ]:
        df[col] = normalize_20_80(df[col])

    # =========================
    # 7. Score urbain global
    # =========================
    df["score_urbain_global"] = (
        0.35 * df["score_investissement"]
        + 0.25 * df["score_environnement"]
        + 0.20 * df["score_mobilite"]
        + 0.20 * df["score_services_quartier"]
    )

    # =========================
    # 8. Arrondis
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
        "score_trafic",
        "score_trafic_inverse",
        "score_services_quartier",
        "score_sante",
        "score_education",
        "score_sport",
        "score_vibrance",
        "score_bruit",
        "score_bruit_inverse",
        "score_environnement_quartier",
        "prix_m2_median",
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct"
    ]

    for col in round_cols:
        if col in df.columns:
            df[col] = df[col].round(2)

    final_cols = [
        "annee",
        "code_commune",
        "arrondissement",

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
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct",
        "nb_mutations",
        "population",

        "nb_arbres_alignement",
        "nb_initiatives",
        "nb_arrets_transport",
        "nb_stations_velib",
        "capacite_velib",
        "stationnement_total"
    ]

    df = df[final_cols].copy()
    df = df.sort_values(["annee", "score_urbain_global"], ascending=[True, False])

    parquet_output = GOLD_URBAIN / "score_urbain_arrondissement.parquet"
    df.to_parquet(parquet_output, index=False)

    print(f"✅ Gold score urbain tabulaire créée : {parquet_output}")
    print(f"✅ Lignes : {len(df)}")
    print(df.head(20))

    # =========================
    # 9. GeoJSON arrondissement
    # =========================
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

    geo_df = geo.merge(df, on="code_commune", how="inner")

    geojson_output = GOLD_URBAIN / "score_urbain_arrondissement.geojson"
    geo_df.to_file(geojson_output, driver="GeoJSON")

    print(f"✅ Gold score urbain GeoJSON créée : {geojson_output}")
    print(f"✅ Features : {len(geo_df)}")


if __name__ == "__main__":
    build_score_urbain_arrondissement()