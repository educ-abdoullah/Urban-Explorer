from pathlib import Path
from datetime import datetime
import warnings
import os

import pandas as pd
import geopandas as gpd


warnings.filterwarnings("ignore")


# ============================================================
# CHEMINS
# ============================================================

DATE_JOUR = datetime.now().strftime("%Y%m%d")

BASE_DIR = Path(__file__).resolve().parents[2] / "data"

POP_PATH = BASE_DIR / "raw" / DATE_JOUR / "pop" / "base-ic-evol-struct-pop-2022.xlsx"

IRIS_PATH = BASE_DIR / "raw" / DATE_JOUR / "ville" / "iris.geojson"

OUTPUT_DIR = BASE_DIR / "gold" / DATE_JOUR


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PARQUET = OUTPUT_DIR / "population_iris.parquet"
OUTPUT_GEOJSON = OUTPUT_DIR / "population_iris.geojson"


# ============================================================
# PARAMÈTRES
# ============================================================

ANNEE_POP = 2022

PARIS_COMMUNES = {str(75100 + i) for i in range(1, 21)}

CRS_WEB = "EPSG:4326"


# ============================================================
# OUTILS
# ============================================================

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_code(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(9) if value.isdigit() and len(value) <= 9 else value


def clean_commune_code(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5) if value.isdigit() and len(value) <= 5 else value


def to_float(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value == "":
        return pd.NA

    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return pd.NA


def to_int_nullable(value):
    val = to_float(value)

    if pd.isna(val):
        return pd.NA

    return int(round(val))


def extract_arrondissement(code_commune):
    code_commune = str(code_commune).strip()

    if code_commune.startswith("751") and len(code_commune) == 5:
        return int(code_commune[-2:])

    return pd.NA


def find_header_row(raw_df):
    """
    Dans le fichier INSEE, il y a plusieurs lignes descriptives avant la vraie ligne d'en-tête.
    On cherche la ligne où les colonnes commencent par :
    IRIS, REG, DEP, UU2020, COM...
    """
    for idx in range(len(raw_df)):
        row_values = raw_df.iloc[idx].astype(str).str.strip().str.upper().tolist()

        if "IRIS" in row_values and "COM" in row_values and "P22_POP" in row_values:
            return idx

    raise ValueError("Impossible de trouver la ligne d'en-tête contenant IRIS, COM et P22_POP.")


# ============================================================
# LECTURE IRIS GEOJSON
# ============================================================

def read_iris_geometry():
    print("\n==================== LECTURE IRIS GEOJSON ====================")
    print("[READ]", IRIS_PATH)

    iris = gpd.read_file(IRIS_PATH)

    iris.columns = [c.strip() for c in iris.columns]

    if "code_iris" not in iris.columns:
        raise ValueError(f"Colonne code_iris introuvable dans iris.geojson. Colonnes : {list(iris.columns)}")

    if "insee_com" not in iris.columns:
        raise ValueError(f"Colonne insee_com introuvable dans iris.geojson. Colonnes : {list(iris.columns)}")

    iris["code_iris"] = iris["code_iris"].astype(str).str.strip()
    iris["code_commune"] = iris["insee_com"].astype(str).str.strip()

    if "nom_com" in iris.columns:
        iris["nom_commune_geo"] = iris["nom_com"].astype(str).str.strip()
    else:
        iris["nom_commune_geo"] = pd.NA

    if "nom_iris" in iris.columns:
        iris["nom_iris_geo"] = iris["nom_iris"].astype(str).str.strip()
    else:
        iris["nom_iris_geo"] = pd.NA

    iris = iris[iris["code_commune"].isin(PARIS_COMMUNES)].copy()

    if iris.crs is None:
        iris = iris.set_crs(CRS_WEB)

    iris = iris.to_crs(CRS_WEB)

    iris = iris[
        [
            "code_iris",
            "code_commune",
            "nom_commune_geo",
            "nom_iris_geo",
            "geometry"
        ]
    ].copy()

    print("✅ IRIS géométriques Paris :", len(iris))
    print(iris[["code_iris", "code_commune", "nom_iris_geo"]].head())

    return iris


# ============================================================
# LECTURE POPULATION INSEE
# ============================================================

def read_population_insee():
    print("\n==================== LECTURE POPULATION INSEE ====================")
    print("[READ]", POP_PATH)

    if not os.path.exists(POP_PATH):
        raise FileNotFoundError(f"Fichier introuvable : {POP_PATH}")

    xls = pd.ExcelFile(POP_PATH)

    print("Onglets détectés :", xls.sheet_names)

    sheet_name = None

    for s in xls.sheet_names:
        if s.strip().lower() == "iris":
            sheet_name = s
            break

    if sheet_name is None:
        for s in xls.sheet_names:
            if "iris" in s.strip().lower():
                sheet_name = s
                break

    if sheet_name is None:
        raise ValueError("Aucun onglet Iris trouvé dans le fichier Excel.")

    print("✅ Onglet utilisé :", sheet_name)

    raw = pd.read_excel(
        POP_PATH,
        sheet_name=sheet_name,
        header=None,
        dtype=str
    )

    header_row = find_header_row(raw)

    print("✅ Ligne d'en-tête détectée :", header_row)

    df = pd.read_excel(
        POP_PATH,
        sheet_name=sheet_name,
        header=header_row,
        dtype=str
    )

    df.columns = [str(c).strip() for c in df.columns]

    required_cols = [
        "IRIS",
        "REG",
        "DEP",
        "UU2020",
        "COM",
        "LIBCOM",
        "LIBIRIS",
        "TYP_IRIS",
        "LAB_IRIS",
        "P22_POP"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Colonne obligatoire manquante : {col}. Colonnes disponibles : {list(df.columns)}")

    df["code_iris"] = df["IRIS"].apply(clean_code)
    df["code_commune"] = df["COM"].apply(clean_commune_code)

    # Paris uniquement : 75101 à 75120
    df = df[df["code_commune"].isin(PARIS_COMMUNES)].copy()

    # On garde les vrais IRIS, pas les communes non irisées.
    df = df[~df["code_iris"].str.endswith("0000", na=False)].copy()

    df["annee"] = ANNEE_POP
    df["arrondissement"] = df["code_commune"].apply(extract_arrondissement)

    df["nom_commune"] = df["LIBCOM"].astype(str).str.strip()
    df["nom_iris"] = df["LIBIRIS"].astype(str).str.strip()
    df["type_iris"] = df["TYP_IRIS"].astype(str).str.strip()
    df["label_iris"] = df["LAB_IRIS"].astype(str).str.strip()

    df["population"] = df["P22_POP"].apply(to_int_nullable)

    # Quelques colonnes utiles supplémentaires
    optional_numeric_cols = {
        "P22_POPH": "population_hommes",
        "P22_POPF": "population_femmes",
        "P22_POP0014": "population_0_14",
        "P22_POP1529": "population_15_29",
        "P22_POP3044": "population_30_44",
        "P22_POP4559": "population_45_59",
        "P22_POP6074": "population_60_74",
        "P22_POP75P": "population_75_plus",
        "P22_POP_FR": "population_francais",
        "P22_POP_ETR": "population_etrangers",
        "P22_POP_IMM": "population_immigres",
        "P22_PMEN": "population_menages",
        "P22_PHORMEN": "population_hors_menages"
    }

    for src_col, out_col in optional_numeric_cols.items():
        if src_col in df.columns:
            df[out_col] = df[src_col].apply(to_int_nullable)
        else:
            df[out_col] = pd.NA

    final = df[
        [
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
            "population_hors_menages"
        ]
    ].copy()

    final["mesure_population"] = "P22_POP"

    print("✅ Lignes population Paris IRIS :", len(final))
    print(final.head())

    return final


# ============================================================
# EXPORT FINAL
# ============================================================

def export_population_iris(pop, iris_geom):
    print("\n==================== JOINTURE POPULATION + GÉOMÉTRIE ====================")

    final_geo = iris_geom[
        [
            "code_iris",
            "geometry"
        ]
    ].merge(
        pop,
        on="code_iris",
        how="inner"
    )

    final_geo = gpd.GeoDataFrame(
        final_geo,
        geometry="geometry",
        crs=CRS_WEB
    )

    final_geo = final_geo[
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "type_iris",
            "label_iris",
            "population",
            "mesure_population",
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
    ].copy()

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
        "population_hors_menages"
    ]

    for col in int_cols:
        final_geo[col] = pd.to_numeric(final_geo[col], errors="coerce").astype("Int64")

    final_geo = final_geo.sort_values(
        by=[
            "code_iris"
        ]
    ).reset_index(drop=True)

    final_geo.to_parquet(
        OUTPUT_PARQUET,
        index=False
    )

    final_geo.to_file(
        OUTPUT_GEOJSON,
        driver="GeoJSON"
    )

    print("\n")
    print("=" * 100)
    print("✅ GOLD POPULATION IRIS CRÉÉE")
    print("=" * 100)

    print("Parquet :", OUTPUT_PARQUET)
    print("GeoJSON :", OUTPUT_GEOJSON)

    print("Lignes :", len(final_geo))
    print("IRIS uniques :", final_geo["code_iris"].nunique())
    print("Année :", ANNEE_POP)
    print("Population totale Paris IRIS :", int(final_geo["population"].sum()))

    print("\nAperçu :")
    print(
        final_geo[
            [
                "annee",
                "code_iris",
                "code_commune",
                "arrondissement",
                "nom_commune",
                "nom_iris",
                "type_iris",
                "population",
                "mesure_population"
            ]
        ].head(30)
    )

    return final_geo


# ============================================================
# MAIN
# ============================================================

def main():
    ensure_dirs()

    iris_geom = read_iris_geometry()

    pop = read_population_insee()

    export_population_iris(
        pop=pop,
        iris_geom=iris_geom
    )


if __name__ == "__main__":
    main()