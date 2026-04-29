from pathlib import Path
from datetime import datetime
import warnings
import os
import pandas as pd
import geopandas as gpd
from shapely import wkb
from shapely.validation import make_valid


warnings.filterwarnings("ignore")


# ============================================================
# CHEMINS
# ============================================================

DATE_JOUR = datetime.now().strftime("%Y%m%d")

BASE_DIR = Path(__file__).resolve().parents[2] / "data"


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


GOLD_POP_IRIS_BASE = BASE_DIR / "gold"
GOLD_LOYERS_IRIS_BASE = BASE_DIR / "gold"
GOLD_DVF_IRIS_BASE = BASE_DIR / "gold"
GOLD_CRIM_BASE = BASE_DIR / "gold" 

GOLD_POP_IRIS_DIR = get_latest_day_dir(GOLD_POP_IRIS_BASE)
GOLD_LOYERS_IRIS_DIR = get_latest_day_dir(GOLD_LOYERS_IRIS_BASE)
GOLD_DVF_IRIS_DIR = get_latest_day_dir(GOLD_DVF_IRIS_BASE)
GOLD_CRIM_DIR = get_latest_day_dir(GOLD_CRIM_BASE)

OUTPUT_DIR = BASE_DIR / "gold" / DATE_JOUR

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

POP_IRIS_PATH = GOLD_POP_IRIS_DIR / "population_iris.parquet"
LOYERS_IRIS_PATH = GOLD_LOYERS_IRIS_DIR / "loyers_iris.parquet"
DVF_IRIS_PATH = GOLD_DVF_IRIS_DIR / "dvf_prix_iris.parquet"
CRIM_ARR_PATH = GOLD_CRIM_DIR / "criminalite_score_arrondissement.parquet"

QUARTIER_PATH = BASE_DIR / "raw" /DATE_JOUR/ "ville" / "quartier_paris.geojson"

OUTPUT_PARQUET = OUTPUT_DIR / "score_investissement_iris.parquet"
OUTPUT_GEOJSON_GOLD = OUTPUT_DIR / "score_investissement_iris.geojson"
OUTPUT_GEOJSON_WEB = OUTPUT_DIR / "score_investissement_iris.geojson"


# ============================================================
# PARAMÈTRES SCORE
# ============================================================

CHARGES_RATE_LOYER = 0.20

WEIGHT_RENDEMENT = 0.60
WEIGHT_SECURITE = 0.30
WEIGHT_LIQUIDITE = 0.10

CRS_WEB = "EPSG:4326"
CRS_WORK = "EPSG:2154"


# ============================================================
# OUTILS
# ============================================================

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def normalize_code_commune(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def normalize_code_iris(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(9)


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def normalize_20_80_by_year(df, value_col, score_col, higher_is_better=True):
    df = df.copy()

    min_col = f"{value_col}_min"
    max_col = f"{value_col}_max"

    df[min_col] = df.groupby("annee")[value_col].transform("min")
    df[max_col] = df.groupby("annee")[value_col].transform("max")

    denominator = df[max_col] - df[min_col]

    df[score_col] = 50.0

    mask = (
        denominator.notna()
        & (denominator != 0)
        & df[value_col].notna()
    )

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

    df[score_col] = df[score_col].clip(20, 80)

    return df.drop(columns=[min_col, max_col])


def read_geo_parquet(path):
    try:
        return gpd.read_parquet(path)
    except Exception:
        return pd.read_parquet(path)


def force_geodataframe(df, crs=CRS_WEB):
    if "geometry" not in df.columns:
        raise ValueError("Colonne geometry absente. Impossible de générer un GeoJSON.")

    df = df.copy()

    if not isinstance(df, gpd.GeoDataFrame):
        if df["geometry"].apply(lambda x: isinstance(x, (bytes, bytearray))).any():
            df["geometry"] = df["geometry"].apply(
                lambda geom: wkb.loads(geom) if isinstance(geom, (bytes, bytearray)) else geom
            )

        df = gpd.GeoDataFrame(df, geometry="geometry", crs=crs)

    if df.crs is None:
        df = df.set_crs(crs)

    df = df[df.geometry.notna()].copy()
    df = df[~df.geometry.is_empty].copy()

    df["geometry"] = df["geometry"].apply(
        lambda geom: make_valid(geom) if geom is not None and not geom.is_valid else geom
    )

    df = df[df.geometry.notna()].copy()
    df = df[~df.geometry.is_empty].copy()

    return df


def prepare_geojson_export(gdf):
    out = gdf.copy()

    if out.crs is None:
        out = out.set_crs(CRS_WEB)

    out = out.to_crs(CRS_WEB)

    for col in out.columns:
        if col == "geometry":
            continue

        if str(out[col].dtype) == "Int64":
            out[col] = out[col].astype("float64")

    return out


def check_output(path, label):
    if os.path.exists(path):
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"✅ {label} créé : {path}")
        print(f"   Taille : {size_mb:.2f} Mo")
    else:
        print(f"❌ {label} NON créé : {path}")


# ============================================================
# LECTURE POPULATION IRIS
# ============================================================

def read_population_iris():
    print("\n==================== LECTURE POPULATION IRIS ====================")
    print("[READ]", POP_IRIS_PATH)

    pop = read_geo_parquet(POP_IRIS_PATH)
    pop = force_geodataframe(pop, crs=CRS_WEB)

    pop["code_iris"] = pop["code_iris"].apply(normalize_code_iris)
    pop["code_commune"] = pop["code_commune"].apply(normalize_code_commune)
    pop["annee"] = to_numeric(pop["annee"]).astype("Int64")
    pop["arrondissement"] = to_numeric(pop["arrondissement"]).astype("Int64")
    pop["population"] = to_numeric(pop["population"])

    keep_cols = [
        "annee",
        "code_iris",
        "code_commune",
        "arrondissement",
        "nom_commune",
        "nom_iris",
        "type_iris",
        "label_iris",
        "population",
        "population_hommes",
        "population_femmes",
        "population_0_14",
        "population_15_29",
        "population_30_44",
        "population_45_59",
        "population_60_74",
        "population_75_plus",
        "population_francais",
        "population_etrangers",
        "population_immigres",
        "population_menages",
        "population_hors_menages",
        "geometry"
    ]

    existing = [c for c in keep_cols if c in pop.columns]
    pop = pop[existing].copy()

    print("✅ Population IRIS :", len(pop))
    print("IRIS uniques :", pop["code_iris"].nunique())
    print("Population totale :", int(pop["population"].sum()))

    return pop


# ============================================================
# LECTURE LOYERS IRIS
# ============================================================

def read_loyers_iris():
    print("\n==================== LECTURE LOYERS IRIS ====================")
    print("[READ]", LOYERS_IRIS_PATH)

    loyers = read_geo_parquet(LOYERS_IRIS_PATH)

    if isinstance(loyers, gpd.GeoDataFrame):
        loyers = pd.DataFrame(loyers.drop(columns="geometry"))

    loyers["code_iris"] = loyers["code_iris"].apply(normalize_code_iris)
    loyers["code_commune"] = loyers["code_commune"].apply(normalize_code_commune)
    loyers["annee"] = to_numeric(loyers["annee"]).astype("Int64")
    loyers["arrondissement"] = to_numeric(loyers["arrondissement"]).astype("Int64")

    loyers = loyers[loyers["nb_pieces"].astype(str).str.strip().eq("Tous")].copy()

    numeric_cols = [
        "loyer_m2_median",
        "loyer_m2_moyen",
        "loyer_mensuel_median",
        "loyer_mensuel_moyen",
        "nb_observations",
        "nb_logements",
        "part_surface_iris"
    ]

    for col in numeric_cols:
        if col in loyers.columns:
            loyers[col] = to_numeric(loyers[col])

    loyers = loyers[
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "zone_olap",
            "lib_zone",
            "loyer_m2_median",
            "loyer_m2_moyen",
            "loyer_mensuel_median",
            "loyer_mensuel_moyen",
            "nb_observations",
            "nb_logements",
            "part_surface_iris"
        ]
    ].copy()

    loyers = loyers.drop_duplicates(
        subset=[
            "annee",
            "code_iris"
        ]
    )

    print("✅ Loyers IRIS Tous :", len(loyers))
    print("Années loyers :", sorted(loyers["annee"].dropna().astype(int).unique().tolist()))

    return loyers


# ============================================================
# LECTURE DVF IRIS
# ============================================================

def read_dvf_iris():
    print("\n==================== LECTURE DVF IRIS ====================")
    print("[READ]", DVF_IRIS_PATH)

    dvf = read_geo_parquet(DVF_IRIS_PATH)

    if isinstance(dvf, gpd.GeoDataFrame):
        dvf = pd.DataFrame(dvf.drop(columns="geometry"))

    dvf["code_iris"] = dvf["code_iris"].apply(normalize_code_iris)
    dvf["code_commune"] = dvf["code_commune"].apply(normalize_code_commune)
    dvf["annee"] = to_numeric(dvf["annee"]).astype("Int64")
    dvf["arrondissement"] = to_numeric(dvf["arrondissement"]).astype("Int64")

    numeric_cols = [
        "prix_m2_median",
        "prix_m2_moyen",
        "valeur_fonciere_mediane",
        "surface_mediane",
        "nb_mutations"
    ]

    for col in numeric_cols:
        if col in dvf.columns:
            dvf[col] = to_numeric(dvf[col])

    dvf = dvf[
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "prix_m2_median",
            "prix_m2_moyen",
            "valeur_fonciere_mediane",
            "surface_mediane",
            "nb_mutations"
        ]
    ].copy()

    dvf = dvf.drop_duplicates(
        subset=[
            "annee",
            "code_iris"
        ]
    )

    print("✅ DVF IRIS :", len(dvf))
    print("IRIS uniques DVF :", dvf["code_iris"].nunique())
    print("Années DVF :", sorted(dvf["annee"].dropna().astype(int).unique().tolist()))

    return dvf


# ============================================================
# LECTURE CRIMINALITÉ ARRONDISSEMENT
# ============================================================

def read_criminalite_arrondissement():
    print("\n==================== LECTURE CRIMINALITÉ ARRONDISSEMENT ====================")
    print("[READ]", CRIM_ARR_PATH)

    crim = pd.read_parquet(CRIM_ARR_PATH)

    crim["code_commune"] = crim["code_commune"].apply(normalize_code_commune)
    crim["annee"] = to_numeric(crim["annee"]).astype("Int64")
    crim["arrondissement"] = to_numeric(crim["arrondissement"]).astype("Int64")

    numeric_cols = [
        "indice_criminalite_brut",
        "nombre_faits_estime",
        "population",
        "nb_indicateurs",
        "score_criminalite"
    ]

    for col in numeric_cols:
        if col in crim.columns:
            crim[col] = to_numeric(crim[col])

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

    crim = crim.rename(columns={
        "population": "population_crim_arrondissement",
        "nombre_faits_estime": "nombre_faits_estime_arrondissement",
        "indice_criminalite_brut": "indice_criminalite_brut_arrondissement",
        "score_criminalite": "score_criminalite_arrondissement",
        "nb_indicateurs": "nb_indicateurs_crim"
    })

    print("✅ Criminalité arrondissements :", len(crim))
    print("Années criminalité :", sorted(crim["annee"].dropna().astype(int).unique().tolist()))

    return crim


# ============================================================
# LECTURE QUARTIERS PARIS
# ============================================================

def read_quartiers_paris():
    print("\n==================== LECTURE QUARTIERS PARIS ====================")
    print("[READ]", QUARTIER_PATH)

    if not os.path.exists(QUARTIER_PATH):
        print("⚠️ Fichier quartier absent :", QUARTIER_PATH)
        return None

    quartiers = gpd.read_file(QUARTIER_PATH)
    quartiers.columns = [c.strip() for c in quartiers.columns]

    required_cols = [
        "c_qu",
        "c_quinsee",
        "l_qu",
        "c_ar",
        "geometry"
    ]

    for col in required_cols:
        if col not in quartiers.columns:
            raise ValueError(
                f"Colonne absente dans quartier_paris.geojson : {col}\n"
                f"Colonnes disponibles : {quartiers.columns.tolist()}"
            )

    quartiers = quartiers[
        [
            "c_qu",
            "c_quinsee",
            "l_qu",
            "c_ar",
            "geometry"
        ]
    ].copy()

    quartiers = quartiers.rename(columns={
        "c_qu": "code_quartier",
        "c_quinsee": "code_quartier_insee",
        "l_qu": "nom_quartier",
        "c_ar": "arrondissement_quartier"
    })

    quartiers["code_quartier"] = quartiers["code_quartier"].astype(str).str.strip()
    quartiers["code_quartier_insee"] = quartiers["code_quartier_insee"].astype(str).str.strip()
    quartiers["arrondissement_quartier"] = to_numeric(
        quartiers["arrondissement_quartier"]
    ).astype("Int64")

    if quartiers.crs is None:
        quartiers = quartiers.set_crs(CRS_WEB)

    quartiers = force_geodataframe(quartiers, crs=CRS_WEB)

    print("✅ Quartiers Paris :", len(quartiers))
    print(quartiers[["code_quartier", "code_quartier_insee", "nom_quartier", "arrondissement_quartier"]].head())

    return quartiers


# ============================================================
# SPATIALISATION CRIMINALITÉ VERS IRIS
# ============================================================

def build_criminalite_iris(pop_iris, crim_arr):
    print("\n==================== SPATIALISATION CRIMINALITÉ ARRONDISSEMENT -> IRIS ====================")

    pop_base = pop_iris[
        [
            "code_iris",
            "code_commune",
            "arrondissement",
            "population"
        ]
    ].copy()

    pop_base = pop_base.rename(columns={
        "population": "population_iris"
    })

    pop_base["population_arrondissement_calculee"] = pop_base.groupby(
        "code_commune"
    )["population_iris"].transform("sum")

    years_crim = sorted(crim_arr["annee"].dropna().astype(int).unique().tolist())

    frames = []

    for year in years_crim:
        temp = pop_base.copy()
        temp["annee"] = year
        frames.append(temp)

    pop_years = pd.concat(frames, ignore_index=True)

    crim_iris = pop_years.merge(
        crim_arr,
        on=[
            "annee",
            "code_commune",
            "arrondissement"
        ],
        how="left"
    )

    crim_iris["part_population_iris_arrondissement"] = (
        crim_iris["population_iris"]
        / crim_iris["population_arrondissement_calculee"]
    )

    crim_iris["nombre_faits_estime_iris"] = (
        crim_iris["nombre_faits_estime_arrondissement"]
        * crim_iris["part_population_iris_arrondissement"]
    )

    crim_iris["indice_criminalite_brut"] = crim_iris["indice_criminalite_brut_arrondissement"]
    crim_iris["score_criminalite"] = crim_iris["score_criminalite_arrondissement"]

    crim_iris["methode_criminalite"] = "arrondissement_reparti_population_iris"

    crim_iris = crim_iris[
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "indice_criminalite_brut",
            "nombre_faits_estime_iris",
            "nombre_faits_estime_arrondissement",
            "population_iris",
            "population_arrondissement_calculee",
            "population_crim_arrondissement",
            "part_population_iris_arrondissement",
            "score_criminalite",
            "nb_indicateurs_crim",
            "methode_criminalite"
        ]
    ].copy()

    print("✅ Criminalité IRIS estimée :", len(crim_iris))
    print(crim_iris.head())

    return crim_iris


# ============================================================
# AJOUT QUARTIER PAR INTERSECTION SPATIALE
# ============================================================

def add_quartier_to_score(score, quartiers):
    if quartiers is None:
        print("⚠️ Quartiers non ajoutés : fichier quartier absent.")
        return score

    print("\n==================== AJOUT DES QUARTIERS AUX IRIS ====================")

    iris_unique = score[
        [
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_iris",
            "geometry"
        ]
    ].drop_duplicates(
        subset=["code_iris"]
    ).copy()

    iris_unique = force_geodataframe(iris_unique, crs=score.crs)

    iris_work = iris_unique.to_crs(CRS_WORK)
    quartiers_work = quartiers.to_crs(CRS_WORK)

    iris_work["surface_iris_m2"] = iris_work.geometry.area

    quartiers_work = quartiers_work[
        [
            "code_quartier",
            "code_quartier_insee",
            "nom_quartier",
            "arrondissement_quartier",
            "geometry"
        ]
    ].copy()

    inter = gpd.overlay(
        iris_work,
        quartiers_work,
        how="intersection",
        keep_geom_type=True
    )

    inter = inter[inter.geometry.notna()].copy()
    inter = inter[~inter.geometry.is_empty].copy()

    inter["surface_intersection_quartier_m2"] = inter.geometry.area
    inter["part_surface_iris_quartier"] = (
        inter["surface_intersection_quartier_m2"]
        / inter["surface_iris_m2"]
    )

    idx = inter.groupby("code_iris")["surface_intersection_quartier_m2"].idxmax()

    mapping = inter.loc[idx].copy()

    mapping = mapping[
        [
            "code_iris",
            "code_quartier",
            "code_quartier_insee",
            "nom_quartier",
            "arrondissement_quartier",
            "surface_intersection_quartier_m2",
            "part_surface_iris_quartier"
        ]
    ].copy()

    mapping["surface_intersection_quartier_m2"] = mapping["surface_intersection_quartier_m2"].round(2)
    mapping["part_surface_iris_quartier"] = mapping["part_surface_iris_quartier"].round(4)

    print("✅ Correspondance IRIS -> quartier :", len(mapping))
    print("IRIS sans quartier :", score["code_iris"].nunique() - mapping["code_iris"].nunique())
    print(mapping.head(10))

    score = score.drop(
        columns=[
            "code_quartier",
            "code_quartier_insee",
            "nom_quartier",
            "arrondissement_quartier",
            "surface_intersection_quartier_m2",
            "part_surface_iris_quartier"
        ],
        errors="ignore"
    )

    score = score.merge(
        mapping,
        on="code_iris",
        how="left"
    )

    print("✅ Score enrichi avec quartier :", len(score))
    print("Quartiers uniques :", score["nom_quartier"].nunique())
    print("Lignes sans quartier :", score["nom_quartier"].isna().sum())

    return score


# ============================================================
# BUILD SCORE
# ============================================================

def build_score_investissement_iris():
    ensure_dirs()

    pop_iris = read_population_iris()
    loyers_iris = read_loyers_iris()
    dvf_iris = read_dvf_iris()
    crim_arr = read_criminalite_arrondissement()
    quartiers = read_quartiers_paris()

    crim_iris = build_criminalite_iris(pop_iris, crim_arr)

    print("\n==================== CONSTRUCTION SCORE INVESTISSEMENT IRIS ====================")

    years = sorted(
        set(loyers_iris["annee"].dropna().astype(int).unique().tolist())
        & set(dvf_iris["annee"].dropna().astype(int).unique().tolist())
    )

    print("Années communes loyers/DVF :", years)

    pop_base = pop_iris.drop(columns=["annee"]).copy()

    pop_frames = []

    for year in years:
        temp = pop_base.copy()
        temp["annee"] = year
        pop_frames.append(temp)

    pop_years = pd.concat(pop_frames, ignore_index=True)

    score = dvf_iris.merge(
        loyers_iris,
        on=[
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement"
        ],
        how="inner"
    )

    print("Après jointure DVF + loyers :", len(score))

    score = score.merge(
        pop_years,
        on=[
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement"
        ],
        how="inner"
    )

    print("Après jointure population :", len(score))

    score = score.merge(
        crim_iris,
        on=[
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement"
        ],
        how="left"
    )

    print("Après jointure criminalité :", len(score))

    score["rendement_brut"] = (
        (score["loyer_m2_median"] * 12)
        / score["prix_m2_median"]
    )

    score["rendement_net"] = (
        (score["loyer_m2_median"] * 12 * (1 - CHARGES_RATE_LOYER))
        / score["prix_m2_median"]
    )

    score["liquidite_brute"] = score["nb_mutations"]

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
        "loyer_m2_moyen",
        "rendement_brut_pct",
        "rendement_net_pct",
        "charges_estimees_pct_loyer",
        "indice_criminalite_brut",
        "nombre_faits_estime_iris",
        "nombre_faits_estime_arrondissement",
        "part_population_iris_arrondissement",
        "score_criminalite",
        "score_securite",
        "score_rendement",
        "score_liquidite",
        "score_investissement",
        "valeur_fonciere_mediane",
        "surface_mediane",
        "population",
        "population_iris"
    ]

    for col in round_cols:
        if col in score.columns:
            score[col] = to_numeric(score[col]).round(2)

    int_cols = [
        "annee",
        "arrondissement",
        "population",
        "population_hommes",
        "population_femmes",
        "population_0_14",
        "population_15_29",
        "population_30_44",
        "population_45_59",
        "population_60_74",
        "population_75_plus",
        "population_francais",
        "population_etrangers",
        "population_immigres",
        "population_menages",
        "population_hors_menages",
        "nb_mutations",
        "nb_indicateurs_crim"
    ]

    for col in int_cols:
        if col in score.columns:
            score[col] = pd.to_numeric(score[col], errors="coerce").astype("Int64")

    score["methode_score"] = "iris_dvf_loyer_population_crim_arrondissement"

    final_columns = [
        "annee",
        "code_iris",
        "code_commune",
        "arrondissement",
        "nom_commune",
        "nom_iris",
        "type_iris",

        "prix_m2_median",
        "prix_m2_moyen",
        "loyer_m2_median",
        "loyer_m2_moyen",

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
        "nombre_faits_estime_arrondissement",
        "score_criminalite",
        "score_securite",
        "nb_indicateurs_crim",
        "methode_criminalite",

        "score_rendement",
        "score_liquidite",
        "score_investissement",

        "zone_olap",
        "lib_zone",
        "valeur_fonciere_mediane",
        "surface_mediane",

        "part_surface_iris",
        "part_population_iris_arrondissement",

        "methode_score",
        "geometry"
    ]

    existing_final_columns = [c for c in final_columns if c in score.columns]

    score = score[existing_final_columns].copy()

    score = force_geodataframe(score, crs=CRS_WEB)

    score = add_quartier_to_score(score, quartiers)

    quartier_cols = [
        "code_quartier",
        "code_quartier_insee",
        "nom_quartier",
        "arrondissement_quartier",
        "surface_intersection_quartier_m2",
        "part_surface_iris_quartier"
    ]

    cols = list(score.columns)

    for col in quartier_cols:
        if col in cols:
            cols.remove(col)

    if "nom_iris" in cols:
        idx = cols.index("nom_iris") + 1
        cols = cols[:idx] + quartier_cols + cols[idx:]
    else:
        cols = quartier_cols + cols

    cols = [c for c in cols if c in score.columns]
    score = score[cols].copy()

    score = force_geodataframe(score, crs=CRS_WEB)

    score = score.sort_values(
        [
            "annee",
            "score_investissement"
        ],
        ascending=[
            True,
            False
        ]
    ).reset_index(drop=True)

    print("\n==================== EXPORT SCORE IRIS ====================")

    score.to_parquet(
        OUTPUT_PARQUET,
        index=False
    )

    score_geojson = prepare_geojson_export(score)

    score_geojson.to_file(
        OUTPUT_GEOJSON_GOLD,
        driver="GeoJSON"
    )

    score_geojson.to_file(
        OUTPUT_GEOJSON_WEB,
        driver="GeoJSON"
    )

    print("\n")
    print("=" * 100)
    print("✅ GOLD SCORE INVESTISSEMENT IRIS CRÉÉE")
    print("=" * 100)

    check_output(OUTPUT_PARQUET, "Parquet")
    check_output(OUTPUT_GEOJSON_GOLD, "GeoJSON GOLD")
    check_output(OUTPUT_GEOJSON_WEB, "GeoJSON WEB")

    print("Lignes :", len(score))
    print("IRIS uniques :", score["code_iris"].nunique())
    print("Quartiers uniques :", score["nom_quartier"].nunique() if "nom_quartier" in score.columns else 0)
    print("Années :", sorted(score["annee"].dropna().astype(int).unique().tolist()))

    print("\nAperçu :")
    print(
        score[
            [
                "annee",
                "code_iris",
                "code_commune",
                "arrondissement",
                "nom_iris",
                "nom_quartier",
                "prix_m2_median",
                "loyer_m2_median",
                "rendement_net_pct",
                "nb_mutations",
                "population",
                "score_securite",
                "score_rendement",
                "score_liquidite",
                "score_investissement"
            ]
        ].head(30)
    )


if __name__ == "__main__":
    build_score_investissement_iris()