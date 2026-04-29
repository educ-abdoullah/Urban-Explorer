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


GOLD_LOYERS = DATA_LAKE / "gold" / date_jour
GOLD_DVF = DATA_LAKE / "gold" / date_jour
GOLD_CRIM = DATA_LAKE / "gold" / date_jour
GOLD_SCORE = DATA_LAKE / "gold" / date_jour

GEO_ARRONDISSEMENTS = DATA_LAKE / "raw" /date_jour/ "ville" / "arrondissements.geojson"


CHARGES_RATE_LOYER = 0.20

WEIGHT_RENDEMENT = 0.60
WEIGHT_SECURITE = 0.30
WEIGHT_LIQUIDITE = 0.10


def normalize_code_commune(value):
    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def normalize_20_80_by_year(df, value_col, score_col, higher_is_better=True):
    df = df.copy()

    min_col = f"{value_col}_min"
    max_col = f"{value_col}_max"

    df[min_col] = df.groupby("annee")[value_col].transform("min")
    df[max_col] = df.groupby("annee")[value_col].transform("max")

    denominator = df[max_col] - df[min_col]

    df[score_col] = 50.0
    mask = denominator != 0

    if higher_is_better:
        df.loc[mask, score_col] = (
            20.0
            + 60.0
            * (
                (df.loc[mask, value_col] - df.loc[mask, min_col])
                / denominator.loc[mask]
            )
        )
    else:
        df.loc[mask, score_col] = (
            80.0
            - 60.0
            * (
                (df.loc[mask, value_col] - df.loc[mask, min_col])
                / denominator.loc[mask]
            )
        )

    return df.drop(columns=[min_col, max_col])


def build_score_investissement():
    GOLD_SCORE.mkdir(parents=True, exist_ok=True)

    loyers = pd.read_parquet(GOLD_LOYERS / "loyers_arrondissement.parquet")
    dvf = pd.read_parquet(GOLD_DVF / "dvf_prix_arrondissement.parquet")
    crim = pd.read_parquet(GOLD_CRIM / "criminalite_score_arrondissement.parquet")

    # Loyer général uniquement
    loyers = loyers[loyers["nb_pieces"] == "Tous"].copy()

    loyers = loyers[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "zone_olap",
            "lib_zone",
            "loyer_m2_median"
        ]
    ].copy()

    dvf = dvf[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "prix_m2_median",
            "prix_m2_moyen",
            "valeur_fonciere_mediane",
            "surface_mediane",
            "nb_mutations"
        ]
    ].copy()

    crim = crim[
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

    for df in [loyers, dvf, crim]:
        df["code_commune"] = df["code_commune"].apply(normalize_code_commune)
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype(int)
        df["arrondissement"] = pd.to_numeric(
            df["arrondissement"],
            errors="coerce"
        ).astype(int)

    score = dvf.merge(
        loyers,
        on=["annee", "code_commune", "arrondissement"],
        how="inner"
    )

    score = score.merge(
        crim,
        on=["annee", "code_commune", "arrondissement"],
        how="inner"
    )

    # Rendement brut annuel
    score["rendement_brut"] = (
        (score["loyer_m2_median"] * 12)
        / score["prix_m2_median"]
    )

    # Rendement net avec charges estimées à 20% des loyers annuels
    score["rendement_net"] = (
        (score["loyer_m2_median"] * 12 * (1 - CHARGES_RATE_LOYER))
        / score["prix_m2_median"]
    )

    score["liquidite_brute"] = score["nb_mutations"]

    # score_criminalite : 20 = faible criminalité, 80 = forte criminalité
    # score_securite : 80 = forte sécurité, 20 = faible sécurité
    score["score_securite"] = 100 - score["score_criminalite"]
    score["score_securite"] = score["score_securite"].clip(20, 80)

    score = normalize_20_80_by_year(
        score,
        value_col="rendement_net",
        score_col="score_rendement",
        higher_is_better=True
    )

    score = normalize_20_80_by_year(
        score,
        value_col="liquidite_brute",
        score_col="score_liquidite",
        higher_is_better=True
    )

    score["score_investissement"] = (
        WEIGHT_RENDEMENT * score["score_rendement"]
        + WEIGHT_SECURITE * score["score_securite"]
        + WEIGHT_LIQUIDITE * score["score_liquidite"]
    )

    score["rendement_brut_pct"] = score["rendement_brut"] * 100
    score["rendement_net_pct"] = score["rendement_net"] * 100
    score["charges_estimees_pct_loyer"] = CHARGES_RATE_LOYER * 100

    round_cols = [
        "prix_m2_median",
        "prix_m2_moyen",
        "loyer_m2_median",
        "rendement_brut_pct",
        "rendement_net_pct",
        "charges_estimees_pct_loyer",
        "indice_criminalite_brut",
        "score_criminalite",
        "score_securite",
        "score_rendement",
        "score_liquidite",
        "score_investissement"
    ]

    for col in round_cols:
        score[col] = score[col].round(2)

    final_columns = [
        "annee",
        "code_commune",
        "arrondissement",

        "prix_m2_median",
        "prix_m2_moyen",
        "loyer_m2_median",

        "rendement_brut_pct",
        "rendement_net_pct",
        "charges_estimees_pct_loyer",

        "nb_mutations",
        "liquidite_brute",

        "indice_criminalite_brut",
        "nombre_faits_estime",
        "population",
        "score_criminalite",
        "score_securite",

        "score_rendement",
        "score_liquidite",
        "score_investissement",

        "zone_olap",
        "lib_zone",
        "valeur_fonciere_mediane",
        "surface_mediane",
        "nb_indicateurs"
    ]

    score = score[final_columns].copy()
    score = score.sort_values(
        ["annee", "score_investissement"],
        ascending=[True, False]
    )

    parquet_output = GOLD_SCORE / "score_investissement_arrondissement.parquet"
    score.to_parquet(parquet_output, index=False)

    print(f"✅ Score investissement tabulaire créé : {parquet_output}")
    print(f"✅ Lignes : {len(score)}")
    print(score.head(20))

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

    geo_score = geo.merge(
        score,
        on="code_commune",
        how="inner"
    )

    geojson_output = GOLD_SCORE / "score_investissement_arrondissement.geojson"
    geo_score.to_file(geojson_output, driver="GeoJSON")

    print(f"✅ Score investissement GeoJSON créé : {geojson_output}")
    print(f"✅ Features : {len(geo_score)}")


if __name__ == "__main__":
    build_score_investissement()