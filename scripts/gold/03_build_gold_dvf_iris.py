import os 
import re 
import glob 
from pathlib import Path
from datetime import datetime
import warnings


import pandas as pd
import geopandas as gpd

warnings.filterwarnings("ignore")


# ============================================================
# CHEMINS
# ============================================================

DATE_JOUR = datetime.now().strftime("%Y%m%d")

BASE_DIR = (Path(__file__).resolve().parents[2] / "data").resolve()

BRONZE_DVF_DIR = BASE_DIR / "raw" / DATE_JOUR / "vf" 

IRIS_PATH = BASE_DIR / "raw" / DATE_JOUR / "ville" / "iris.geojson"

ADRESSE_PARIS_PATH = BASE_DIR / "raw" / DATE_JOUR / "ville" / "adresse_paris.geojson"

OUTPUT_DIR = BASE_DIR / "gold" / DATE_JOUR


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_ADRESSES_IRIS_PARQUET = OUTPUT_DIR / "adresse_paris_iris.parquet"
OUTPUT_MUTATIONS_PARQUET = OUTPUT_DIR / "dvf_mutations_adresse_iris.parquet"
OUTPUT_PRIX_IRIS_PARQUET = OUTPUT_DIR / "dvf_prix_iris.parquet"
OUTPUT_PRIX_IRIS_GEOJSON = OUTPUT_DIR / "dvf_prix_iris.geojson"

# ============================================================
# PARAMÈTRES
# ============================================================

YEARS = [2022, 2023, 2024]

CHUNKSIZE = 300_000

CRS_WEB = "EPSG:4326"
CRS_WORK = "EPSG:2154"

PARIS_COMMUNES = {str(75100 + i) for i in range(1, 21)}


# ============================================================
# OUTILS
# ============================================================

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()
    value = value.upper()

    replacements = {
        "É": "E",
        "È": "E",
        "Ê": "E",
        "Ë": "E",
        "À": "A",
        "Â": "A",
        "Ä": "A",
        "Î": "I",
        "Ï": "I",
        "Ô": "O",
        "Ö": "O",
        "Û": "U",
        "Ü": "U",
        "Ç": "C",
        "’": "'",
        "‐": "-",
        "–": "-",
        "—": "-"
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_suffix(value):
    value = clean_text(value)

    if value in ["", "NAN", "NONE", "NULL"]:
        return ""

    value = value.replace(" ", "")

    return value


def normalize_num_voie(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value == "":
        return ""

    try:
        return str(int(float(value)))
    except ValueError:
        return clean_text(value)


def normalize_type_voie(value):
    value = clean_text(value)

    mapping = {
        "BOULEVARD": "BD",
        "BD": "BD",
        "AVENUE": "AV",
        "AV": "AV",
        "RUE": "RUE",
        "PLACE": "PL",
        "PL": "PL",
        "IMPASSE": "IMP",
        "IMP": "IMP",
        "PASSAGE": "PAS",
        "PAS": "PAS",
        "VILLA": "VLA",
        "VLA": "VLA",
        "QUAI": "QU",
        "QU": "QU",
        "SQUARE": "SQ",
        "SQ": "SQ",
        "ALLEE": "ALL",
        "ALL": "ALL",
        "CHEMIN": "CHE",
        "CHE": "CHE",
        "ROUTE": "RTE",
        "RTE": "RTE",
        "COUR": "COUR",
        "CITE": "CITE",
        "GALERIE": "GAL",
        "GAL": "GAL"
    }

    return mapping.get(value, value)


def normalize_voie(value):
    value = clean_text(value)

    # DVF peut avoir "DE LA", "DU", etc. On garde tel quel.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_full_address(num, suffix, type_voie, voie):
    num = normalize_num_voie(num)
    suffix = normalize_suffix(suffix)
    type_voie = normalize_type_voie(type_voie)
    voie = normalize_voie(voie)

    num_suffix = f"{num}{suffix}".strip()

    parts = []

    if num_suffix:
        parts.append(num_suffix)

    if type_voie:
        parts.append(type_voie)

    if voie:
        parts.append(voie)

    return " ".join(parts).strip()


def to_float_fr(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value == "":
        return pd.NA

    value = value.replace(",", ".").replace(" ", "")

    try:
        return float(value)
    except ValueError:
        return pd.NA


def to_int_safe(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value == "":
        return pd.NA

    try:
        return int(float(value))
    except ValueError:
        return pd.NA


def extract_arrondissement(code_commune):
    code_commune = str(code_commune).strip()

    if code_commune.startswith("751") and len(code_commune) == 5:
        return int(code_commune[-2:])

    return pd.NA


def build_code_commune(code_departement, code_commune_dvf):
    dep = str(code_departement).strip().zfill(2)
    com = str(code_commune_dvf).strip().zfill(3)

    return dep + com


def find_dvf_file(year):
    patterns = [
        f"ValeursFoncieres-{year}.txt",
        f"*{year}*.txt",
        f"*{year}*.csv"
    ]

    for pattern in patterns:
        files = glob.glob(os.path.join(BRONZE_DVF_DIR, pattern))

        if files:
            return files[0]

    return None


# ============================================================
# LECTURE IRIS
# ============================================================

def read_iris():
    print("\n==================== LECTURE IRIS ====================")
    print("[READ]", IRIS_PATH)

    iris = gpd.read_file(IRIS_PATH)

    iris.columns = [c.strip() for c in iris.columns]

    if "code_iris" not in iris.columns:
        raise ValueError(f"Colonne code_iris introuvable. Colonnes : {list(iris.columns)}")

    if "insee_com" not in iris.columns:
        raise ValueError(f"Colonne insee_com introuvable. Colonnes : {list(iris.columns)}")

    iris["code_iris"] = iris["code_iris"].astype(str).str.strip()
    iris["code_commune"] = iris["insee_com"].astype(str).str.strip()

    if "nom_com" in iris.columns:
        iris["nom_commune"] = iris["nom_com"].astype(str).str.strip()
    else:
        iris["nom_commune"] = pd.NA

    if "nom_iris" in iris.columns:
        iris["nom_iris"] = iris["nom_iris"].astype(str).str.strip()
    else:
        iris["nom_iris"] = pd.NA

    iris = iris[iris["code_commune"].isin(PARIS_COMMUNES)].copy()

    iris["arrondissement"] = iris["code_commune"].apply(extract_arrondissement)

    iris = iris[
        [
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "geometry"
        ]
    ].copy()

    if iris.crs is None:
        iris = iris.set_crs(CRS_WEB)

    iris = iris.to_crs(CRS_WORK)

    print("✅ IRIS Paris :", len(iris))
    print(iris[["code_iris", "code_commune", "arrondissement", "nom_iris"]].head())

    return iris


# ============================================================
# ADRESSES PARIS -> IRIS
# ============================================================

def build_adresses_iris(iris):
    print("\n==================== CONSTRUCTION ADRESSES -> IRIS ====================")
    print("[READ]", ADRESSE_PARIS_PATH)

    adresses = gpd.read_file(ADRESSE_PARIS_PATH)

    adresses.columns = [c.strip().lower() for c in adresses.columns]

    required = [
        "n_voie",
        "c_suf1",
        "c_suf2",
        "c_suf3",
        "c_ar",
        "l_adr"
    ]

    for col in required:
        if col not in adresses.columns:
            adresses[col] = pd.NA

    if adresses.crs is None:
        adresses = adresses.set_crs(CRS_WEB)

    adresses = adresses.to_crs(CRS_WORK)

    adresses["arrondissement"] = adresses["c_ar"].apply(to_int_safe)
    adresses["code_commune"] = adresses["arrondissement"].apply(
        lambda x: f"751{int(x):02d}" if pd.notna(x) else pd.NA
    )

    # Adresse normalisée Open Data Paris
    adresses["adresse_norm"] = adresses["l_adr"].apply(clean_text)

    # Variante avec suffixes si besoin
    adresses["suffix"] = (
        adresses["c_suf1"].apply(normalize_suffix)
        + adresses["c_suf2"].apply(normalize_suffix)
        + adresses["c_suf3"].apply(normalize_suffix)
    )

    adresses["numero_norm"] = adresses["n_voie"].apply(normalize_num_voie)

    adresses = adresses[
        adresses["code_commune"].isin(PARIS_COMMUNES)
    ].copy()

    adresses = adresses[
        adresses["adresse_norm"].notna()
        & adresses["adresse_norm"].ne("")
        & adresses.geometry.notna()
    ].copy()

    iris_small = iris[
        [
            "code_iris",
            "nom_iris",
            "geometry"
        ]
    ].copy()

    # Jointure spatiale : chaque point adresse reçoit son IRIS
    adresses_iris = gpd.sjoin(
        adresses,
        iris_small,
        how="left",
        predicate="within"
    )

    adresses_iris = adresses_iris[
        adresses_iris["code_iris"].notna()
    ].copy()

    adresses_iris = adresses_iris[
        [
            "adresse_norm",
            "numero_norm",
            "suffix",
            "code_commune",
            "arrondissement",
            "code_iris",
            "nom_iris",
            "geometry"
        ]
    ].copy()

    adresses_iris = adresses_iris.drop_duplicates(
        subset=[
            "adresse_norm",
            "code_commune",
            "code_iris"
        ]
    )

    adresses_iris.to_parquet(
        OUTPUT_ADRESSES_IRIS_PARQUET,
        index=False
    )

    print("✅ Table adresse -> IRIS :", len(adresses_iris))
    print("Parquet adresses IRIS :", OUTPUT_ADRESSES_IRIS_PARQUET)
    print(adresses_iris[["adresse_norm", "code_commune", "code_iris", "nom_iris"]].head())

    return adresses_iris


# ============================================================
# LECTURE DVF
# ============================================================

def read_dvf_year(year):
    file_path = find_dvf_file(year)

    if file_path is None:
        print(f"⚠️ Aucun fichier DVF trouvé pour {year}")
        return None

    print("\n")
    print("=" * 100)
    print(f"TRAITEMENT DVF ANNÉE {year}")
    print("=" * 100)
    print("[READ]", file_path)

    selected_rows = []

    usecols = [
        "No disposition",
        "Date mutation",
        "Nature mutation",
        "Valeur fonciere",
        "No voie",
        "B/T/Q",
        "Type de voie",
        "Code voie",
        "Voie",
        "Code postal",
        "Commune",
        "Code departement",
        "Code commune",
        "Section",
        "No plan",
        "Nombre de lots",
        "Code type local",
        "Type local",
        "Surface reelle bati",
        "Nombre pieces principales",
        "Surface terrain"
    ]

    chunk_id = 0
    total_kept = 0

    for chunk in pd.read_csv(
        file_path,
        sep="|",
        dtype=str,
        chunksize=CHUNKSIZE,
        encoding="utf-8",
        low_memory=False
    ):
        chunk_id += 1

        chunk.columns = [c.strip() for c in chunk.columns]

        for col in usecols:
            if col not in chunk.columns:
                chunk[col] = pd.NA

        chunk = chunk[usecols].copy()

        chunk["code_commune"] = chunk.apply(
            lambda row: build_code_commune(row["Code departement"], row["Code commune"]),
            axis=1
        )

        chunk = chunk[chunk["code_commune"].isin(PARIS_COMMUNES)].copy()

        if chunk.empty:
            continue

        chunk["nature_mutation"] = chunk["Nature mutation"].astype(str).str.strip()

        chunk = chunk[
            chunk["nature_mutation"].str.lower().eq("vente")
        ].copy()

        if chunk.empty:
            continue

        chunk["code_type_local"] = chunk["Code type local"].apply(to_int_safe)

        # 1 = Maison, 2 = Appartement
        chunk = chunk[
            chunk["code_type_local"].isin([1, 2])
        ].copy()

        if chunk.empty:
            continue

        chunk["type_local"] = chunk["Type local"].astype(str).str.strip()

        chunk["valeur_fonciere"] = chunk["Valeur fonciere"].apply(to_float_fr)
        chunk["surface_reelle_bati"] = chunk["Surface reelle bati"].apply(to_float_fr)
        chunk["nombre_pieces"] = chunk["Nombre pieces principales"].apply(to_int_safe)
        chunk["surface_terrain"] = chunk["Surface terrain"].apply(to_float_fr)
        chunk["nombre_lots"] = chunk["Nombre de lots"].apply(to_int_safe)

        chunk = chunk[
            chunk["valeur_fonciere"].notna()
            & chunk["surface_reelle_bati"].notna()
            & (chunk["surface_reelle_bati"] > 0)
            & (chunk["valeur_fonciere"] > 0)
        ].copy()

        if chunk.empty:
            continue

        chunk["prix_m2"] = chunk["valeur_fonciere"] / chunk["surface_reelle_bati"]

        # Filtre anti-valeurs aberrantes
        chunk = chunk[
            (chunk["prix_m2"] >= 1000)
            & (chunk["prix_m2"] <= 50000)
        ].copy()

        if chunk.empty:
            continue

        chunk["annee"] = year
        chunk["date_mutation"] = chunk["Date mutation"].astype(str).str.strip()
        chunk["code_postal"] = chunk["Code postal"].astype(str).str.strip()
        chunk["commune"] = chunk["Commune"].astype(str).str.strip()
        chunk["arrondissement"] = chunk["code_commune"].apply(extract_arrondissement)

        chunk["adresse_norm"] = chunk.apply(
            lambda row: normalize_full_address(
                row["No voie"],
                row["B/T/Q"],
                row["Type de voie"],
                row["Voie"]
            ),
            axis=1
        )

        chunk["adresse"] = chunk["adresse_norm"]

        chunk["section"] = chunk["Section"].astype(str).str.strip()
        chunk["no_plan"] = chunk["No plan"].astype(str).str.strip()
        chunk["no_disposition"] = chunk["No disposition"].astype(str).str.strip()

        chunk["mutation_id"] = (
            chunk["annee"].astype(str)
            + "_"
            + chunk["date_mutation"].astype(str)
            + "_"
            + chunk["no_disposition"].astype(str)
            + "_"
            + chunk["code_commune"].astype(str)
            + "_"
            + chunk["section"].astype(str)
            + "_"
            + chunk["no_plan"].astype(str)
            + "_"
            + chunk["valeur_fonciere"].astype(str)
        )

        out = chunk[
            [
                "mutation_id",
                "annee",
                "date_mutation",
                "nature_mutation",
                "code_commune",
                "arrondissement",
                "code_postal",
                "commune",
                "adresse",
                "adresse_norm",
                "type_local",
                "code_type_local",
                "valeur_fonciere",
                "surface_reelle_bati",
                "nombre_pieces",
                "surface_terrain",
                "nombre_lots",
                "prix_m2"
            ]
        ].copy()

        selected_rows.append(out)

        total_kept += len(out)

        print(f"  chunk {chunk_id} -> lignes Paris utiles cumulées : {total_kept}")

    if not selected_rows:
        print(f"⚠️ Aucune ligne utile pour {year}")
        return None

    df = pd.concat(selected_rows, ignore_index=True)

    df = df.drop_duplicates(
        subset=[
            "mutation_id",
            "type_local",
            "surface_reelle_bati",
            "nombre_pieces",
            "prix_m2"
        ]
    ).copy()

    print("✅ Mutations utiles année :", len(df))
    print(df.head())

    return df


# ============================================================
# JOINTURE DVF -> ADRESSE IRIS
# ============================================================

def attach_iris_to_dvf(dvf, adresses_iris):
    print("\n==================== JOINTURE DVF -> ADRESSE -> IRIS ====================")

    addr = adresses_iris[
        [
            "adresse_norm",
            "code_commune",
            "code_iris",
            "nom_iris"
        ]
    ].copy()

    addr = addr.drop_duplicates(
        subset=[
            "adresse_norm",
            "code_commune"
        ]
    )

    dvf_iris = dvf.merge(
        addr,
        on=[
            "adresse_norm",
            "code_commune"
        ],
        how="left"
    )

    matched = dvf_iris["code_iris"].notna().sum()
    total = len(dvf_iris)

    print("Mutations DVF :", total)
    print("Mutations rattachées IRIS :", matched)
    print("Taux de rattachement :", round(matched / total * 100, 2), "%")

    dvf_iris = dvf_iris[
        dvf_iris["code_iris"].notna()
    ].copy()

    dvf_iris["methode_rattachement"] = "join_adresse_paris"

    print("✅ Mutations avec IRIS :", len(dvf_iris))
    print(dvf_iris[["annee", "adresse", "code_commune", "code_iris", "prix_m2"]].head())

    return dvf_iris


# ============================================================
# AGRÉGATION IRIS
# ============================================================

def aggregate_iris(dvf_iris):
    print("\n==================== AGRÉGATION DVF PAR IRIS ====================")

    agg = dvf_iris.groupby(
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement"
        ],
        as_index=False
    ).agg(
        prix_m2_median=("prix_m2", "median"),
        prix_m2_moyen=("prix_m2", "mean"),
        valeur_fonciere_mediane=("valeur_fonciere", "median"),
        surface_mediane=("surface_reelle_bati", "median"),
        nb_mutations=("mutation_id", "nunique")
    )

    agg["methode_spatialisation"] = "adresse_paris_to_iris"

    print("✅ Stats IRIS :", len(agg))
    print(agg.head())

    return agg


# ============================================================
# EXPORT FINAL
# ============================================================

def export_final(agg_iris, iris, dvf_iris):
    print("\n==================== EXPORT ====================")

    iris_attrs = iris[
        [
            "code_iris",
            "nom_commune",
            "nom_iris",
            "geometry"
        ]
    ].copy()

    final_geo = iris_attrs.merge(
        agg_iris,
        on="code_iris",
        how="inner"
    )

    final_geo = gpd.GeoDataFrame(
        final_geo,
        geometry="geometry",
        crs=CRS_WORK
    )

    final_geo = final_geo[
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "prix_m2_median",
            "prix_m2_moyen",
            "valeur_fonciere_mediane",
            "surface_mediane",
            "nb_mutations",
            "methode_spatialisation",
            "geometry"
        ]
    ].copy()

    final_geo["annee"] = pd.to_numeric(final_geo["annee"], errors="coerce").astype("Int64")
    final_geo["arrondissement"] = pd.to_numeric(final_geo["arrondissement"], errors="coerce").astype("Int64")
    final_geo["nb_mutations"] = pd.to_numeric(final_geo["nb_mutations"], errors="coerce").astype("Int64")

    float_cols = [
        "prix_m2_median",
        "prix_m2_moyen",
        "valeur_fonciere_mediane",
        "surface_mediane"
    ]

    for col in float_cols:
        final_geo[col] = pd.to_numeric(final_geo[col], errors="coerce")

    final_geo = final_geo.sort_values(
        by=[
            "annee",
            "code_iris"
        ]
    ).reset_index(drop=True)

    final_geo.to_parquet(
        OUTPUT_PRIX_IRIS_PARQUET,
        index=False
    )

    final_geo.to_crs(CRS_WEB).to_file(
        OUTPUT_PRIX_IRIS_GEOJSON,
        driver="GeoJSON"
    )

    dvf_iris.to_parquet(
        OUTPUT_MUTATIONS_PARQUET,
        index=False
    )

    print("✅ Mutations DVF avec IRIS :", OUTPUT_MUTATIONS_PARQUET)
    print("✅ Parquet IRIS :", OUTPUT_PRIX_IRIS_PARQUET)
    print("✅ GeoJSON IRIS :", OUTPUT_PRIX_IRIS_GEOJSON)

    print("Lignes stats IRIS :", len(final_geo))
    print("IRIS uniques :", final_geo["code_iris"].nunique())
    print("Années :", sorted(final_geo["annee"].dropna().unique().tolist()))

    print("\nAperçu final :")
    print(
        final_geo[
            [
                "annee",
                "code_iris",
                "code_commune",
                "arrondissement",
                "nom_iris",
                "prix_m2_median",
                "prix_m2_moyen",
                "valeur_fonciere_mediane",
                "surface_mediane",
                "nb_mutations",
                "methode_spatialisation"
            ]
        ].head(30)
    )


# ============================================================
# MAIN
# ============================================================

def main():
    ensure_dirs()

    iris = read_iris()

    adresses_iris = build_adresses_iris(iris)

    all_dvf = []

    for year in YEARS:
        df_year = read_dvf_year(year)

        if df_year is not None:
            all_dvf.append(df_year)

    if not all_dvf:
        raise RuntimeError("Aucune donnée DVF utile trouvée.")

    dvf = pd.concat(all_dvf, ignore_index=True)

    dvf = dvf.sort_values(
        by=[
            "annee",
            "code_commune",
            "date_mutation"
        ]
    ).reset_index(drop=True)

    dvf_iris = attach_iris_to_dvf(
        dvf=dvf,
        adresses_iris=adresses_iris
    )

    agg_iris = aggregate_iris(dvf_iris)

    export_final(
        agg_iris=agg_iris,
        iris=iris,
        dvf_iris=dvf_iris
    )


if __name__ == "__main__":
    main()