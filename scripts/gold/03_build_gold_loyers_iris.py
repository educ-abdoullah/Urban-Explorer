from pathlib import Path
from datetime import datetime
import os
import re
import glob
import warnings
import xml.etree.ElementTree as ET

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid


warnings.filterwarnings("ignore")


# ============================================================
# CHEMINS
# ============================================================

DATE_JOUR = datetime.now().strftime("%Y%m%d")

BASE_DIR = (Path(__file__).resolve().parents[2] / "data").resolve()

BRONZE_OLAP_DIR = BASE_DIR / "raw" / DATE_JOUR / "loyers_olap" 

IRIS_PATH = BASE_DIR / "raw" / DATE_JOUR / "ville" / "iris.geojson"

OUTPUT_DIR = BASE_DIR / "gold" / DATE_JOUR


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PARQUET = OUTPUT_DIR / "loyers_iris.parquet"
OUTPUT_GEOJSON = OUTPUT_DIR / "loyers_iris.geojson"
# ============================================================
# PARAMÈTRES
# ============================================================

YEARS = [2022, 2023, 2024]

PARIS_COMMUNES = {str(75100 + i) for i in range(1, 21)}

CRS_WORK = "EPSG:2154"
CRS_WEB = "EPSG:4326"


# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


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


def clean_string(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def extract_arrondissement(code_commune):
    code_commune = str(code_commune).strip()

    if code_commune.startswith("751") and len(code_commune) == 5:
        return int(code_commune[-2:])

    return pd.NA


def normalize_zone(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value == "":
        return pd.NA

    match = re.search(r"L\d{4}(?:\.\d+)+", value)

    if match:
        return match.group(0)

    match = re.search(r"\d+", value)

    if match:
        return str(int(match.group(0)))

    return value


def zone_number_from_zone_olap(value):
    if pd.isna(value):
        return pd.NA

    nums = re.findall(r"\d+", str(value))

    if not nums:
        return pd.NA

    return str(int(nums[-1]))


def detect_file(year_dir, patterns):
    for pattern in patterns:
        files = glob.glob(os.path.join(year_dir, pattern))
        if files:
            return files[0]

    return None


def safe_make_valid(gdf):
    gdf = gdf.copy()

    gdf["geometry"] = gdf["geometry"].apply(
        lambda geom: make_valid(geom)
        if geom is not None and not geom.is_valid
        else geom
    )

    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()

    return gdf


# ============================================================
# NETTOYAGE NB PIÈCES
# ============================================================

def clean_nb_pieces(value):
    """
    Corrige les codes OLAP du type L7501.1.6 en libellés propres.
    Corrige notamment le problème constaté sur 2022.
    """
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value == "":
        return ""

    mapping_exact = {
        "L7501.1.6": "Ensemble 1P",
        "L7501.1.7": "Ensemble 2P",
        "L7501.1.8": "Ensemble 3P",
        "L7501.1.9": "Ensemble 4P+",
        "L7501.1.10": "Appart 1P",
        "L7501.1.11": "Appart 2P",
        "L7501.1.12": "Appart 3P",
        "L7501.1.13": "Appart 4P+",
        "L7501.1.14": "Maison 1-3P",
        "L7501.1.15": "Maison 4P+"
    }

    if value in mapping_exact:
        return mapping_exact[value]

    lower = value.lower()

    if "ensemble" in lower and "1p" in lower:
        return "Ensemble 1P"
    if "ensemble" in lower and "2p" in lower:
        return "Ensemble 2P"
    if "ensemble" in lower and "3p" in lower:
        return "Ensemble 3P"
    if "ensemble" in lower and ("4p" in lower or "4 p" in lower):
        return "Ensemble 4P+"

    if "appart" in lower and "1p" in lower:
        return "Appart 1P"
    if "appart" in lower and "2p" in lower:
        return "Appart 2P"
    if "appart" in lower and "3p" in lower:
        return "Appart 3P"
    if "appart" in lower and ("4p" in lower or "4 p" in lower):
        return "Appart 4P+"

    if "maison" in lower and ("1-3" in lower or "1 à 3" in lower):
        return "Maison 1-3P"
    if "maison" in lower and ("4p" in lower or "4 p" in lower):
        return "Maison 4P+"

    return value


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

    if "nom_iris" not in iris.columns:
        iris["nom_iris"] = pd.NA
    else:
        iris["nom_iris"] = iris["nom_iris"].astype(str).str.strip()

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
    iris = safe_make_valid(iris)

    iris["surface_iris"] = iris.geometry.area

    print("✅ IRIS Paris :", len(iris))
    print(iris[["code_iris", "code_commune", "arrondissement", "nom_iris"]].head())

    return iris


# ============================================================
# LECTURE BASE OP
# ============================================================

def read_base_op(base_path, year):
    print("\n[READ BASE OP]", base_path)

    base = pd.read_csv(
        base_path,
        sep=";",
        encoding="latin1",
        dtype=str
    )

    base.columns = [c.strip() for c in base.columns]

    required_cols = [
        "Zone_calcul",
        "nombre_pieces_local",
        "nombre_pieces_homogene",
        "loyer_median",
        "loyer_moyen",
        "loyer_mensuel_median",
        "moyenne_loyer_mensuel",
        "surface_moyenne",
        "nombre_observations",
        "nombre_logements"
    ]

    for col in required_cols:
        if col not in base.columns:
            base[col] = pd.NA

    numeric_cols = [
        "loyer_1_decile",
        "loyer_1_quartile",
        "loyer_median",
        "loyer_3_quartile",
        "loyer_9_decile",
        "loyer_moyen",
        "loyer_mensuel_1_decile",
        "loyer_mensuel_1_quartile",
        "loyer_mensuel_median",
        "loyer_mensuel_3_quartile",
        "loyer_mensuel_9_decile",
        "moyenne_loyer_mensuel",
        "surface_moyenne",
        "nombre_observations",
        "nombre_logements"
    ]

    for col in numeric_cols:
        if col in base.columns:
            base[col] = base[col].apply(to_float_fr)

    base["annee"] = year
    base["zone_olap"] = base["Zone_calcul"].apply(normalize_zone)

    base = base[base["zone_olap"].notna()].copy()

    base["nb_pieces"] = base["nombre_pieces_local"].apply(clean_nb_pieces)

    mask_empty = base["nb_pieces"].eq("")
    base.loc[mask_empty, "nb_pieces"] = base.loc[mask_empty, "nombre_pieces_homogene"].apply(clean_nb_pieces)

    mask_empty = base["nb_pieces"].eq("")
    base.loc[mask_empty, "nb_pieces"] = "Tous"

    base = base[
        base["loyer_median"].notna()
        | base["loyer_moyen"].notna()
        | base["loyer_mensuel_median"].notna()
        | base["moyenne_loyer_mensuel"].notna()
    ].copy()

    loyers = base[
        [
            "annee",
            "zone_olap",
            "nb_pieces",
            "loyer_median",
            "loyer_moyen",
            "loyer_mensuel_median",
            "moyenne_loyer_mensuel",
            "surface_moyenne",
            "nombre_observations",
            "nombre_logements"
        ]
    ].copy()

    loyers = loyers.rename(columns={
        "loyer_median": "loyer_m2_median",
        "loyer_moyen": "loyer_m2_moyen",
        "moyenne_loyer_mensuel": "loyer_mensuel_moyen",
        "nombre_observations": "nb_observations",
        "nombre_logements": "nb_logements"
    })

    loyers = loyers.drop_duplicates(
        subset=[
            "annee",
            "zone_olap",
            "nb_pieces"
        ]
    )

    print("✅ Lignes loyers zone :", len(loyers))
    print(loyers.head())

    return loyers


# ============================================================
# LECTURE TABLE ZONES
# ============================================================

def read_table_zones(table_path):
    if table_path is None or not os.path.exists(table_path):
        return None

    print("[READ TABLE ZONES]", table_path)

    try:
        table = pd.read_excel(table_path, dtype=str)
    except ImportError:
        raise ImportError(
            "Le fichier table_zones est en .xls. Installe xlrd avec : py -m pip install xlrd"
        )

    table.columns = [c.strip() for c in table.columns]

    for col in ["Commune", "Lib_com", "Iris", "Zone", "Lib_zone"]:
        if col not in table.columns:
            table[col] = pd.NA

    table["code_commune"] = table["Commune"].astype(str).str.strip()
    table["zone_number"] = table["Zone"].apply(zone_number_from_zone_olap)
    table["lib_zone"] = table["Lib_zone"].astype(str).str.strip()

    table = table[
        [
            "code_commune",
            "zone_number",
            "lib_zone"
        ]
    ].drop_duplicates()

    return table


# ============================================================
# LECTURE KML
# ============================================================

def parse_coordinates(coord_text):
    coords = []

    for item in coord_text.strip().split():
        parts = item.split(",")

        if len(parts) < 2:
            continue

        try:
            lon = float(parts[0])
            lat = float(parts[1])
            coords.append((lon, lat))
        except ValueError:
            continue

    return coords


def extract_zone_from_text(text):
    if text is None:
        return pd.NA

    text = str(text)

    match = re.search(r"L\d{4}\.\d+\.\d+", text)
    if match:
        return match.group(0)

    match = re.search(r"L\d{4}(?:\.\d+)+", text)
    if match:
        return match.group(0)

    return pd.NA


def read_kml_with_xml(kml_path):
    ns = {
        "kml": "http://www.opengis.net/kml/2.2"
    }

    tree = ET.parse(kml_path)
    root = tree.getroot()

    rows = []

    placemarks = root.findall(".//kml:Placemark", ns)

    for placemark in placemarks:
        texts = []

        for elem in placemark.iter():
            if elem.text:
                txt = elem.text.strip()
                if txt:
                    texts.append(txt)

        joined_text = " | ".join(texts)
        zone_olap = extract_zone_from_text(joined_text)

        if pd.isna(zone_olap):
            continue

        polygon_geoms = []

        polygons = placemark.findall(".//kml:Polygon", ns)

        for polygon in polygons:
            coord_nodes = polygon.findall(".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", ns)

            for coord_node in coord_nodes:
                coords = parse_coordinates(coord_node.text or "")

                if len(coords) >= 4:
                    try:
                        poly = Polygon(coords)

                        if not poly.is_empty:
                            polygon_geoms.append(poly)
                    except Exception:
                        pass

        if not polygon_geoms:
            continue

        if len(polygon_geoms) == 1:
            geometry = polygon_geoms[0]
        else:
            geometry = MultiPolygon(polygon_geoms)

        rows.append({
            "zone_olap": zone_olap,
            "geometry": geometry
        })

    if not rows:
        raise ValueError(f"Aucune zone OLAP récupérée dans le KML : {kml_path}")

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS_WEB)
    gdf = gdf.dissolve(by="zone_olap", as_index=False)

    return gdf


def read_kml_zones(kml_path):
    print("[READ KML ZONES]", kml_path)

    try:
        zones = gpd.read_file(kml_path)
        zones.columns = [c.strip() for c in zones.columns]

        text_cols = [c for c in zones.columns if c.lower() != "geometry"]

        zone_values = []

        for _, row in zones.iterrows():
            joined = " | ".join([str(row[c]) for c in text_cols if pd.notna(row[c])])
            zone_values.append(extract_zone_from_text(joined))

        zones["zone_olap"] = zone_values
        zones = zones[zones["zone_olap"].notna()].copy()

        if len(zones) == 0:
            raise ValueError("KML lu par GeoPandas, mais aucune zone_olap détectée.")

        zones = zones[["zone_olap", "geometry"]].copy()
        zones = zones.dissolve(by="zone_olap", as_index=False)

    except Exception as e:
        print("⚠️ Lecture KML GeoPandas insuffisante, fallback XML.")
        print("   Raison :", e)
        zones = read_kml_with_xml(kml_path)

    if zones.crs is None:
        zones = zones.set_crs(CRS_WEB)

    zones = zones.to_crs(CRS_WORK)
    zones = safe_make_valid(zones)

    zones["zone_number"] = zones["zone_olap"].apply(zone_number_from_zone_olap)

    print("✅ Zones géographiques OLAP :", len(zones))
    print(zones[["zone_olap", "zone_number"]].head())

    return zones


# ============================================================
# INTERSECTION SURFACIQUE
# ============================================================

def build_iris_zone_intersection(iris, zones):
    print("\n[SPATIAL] Intersection IRIS x zones OLAP")

    iris_small = iris[
        [
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "surface_iris",
            "geometry"
        ]
    ].copy()

    zones_small = zones[
        [
            "zone_olap",
            "zone_number",
            "geometry"
        ]
    ].copy()

    inter = gpd.overlay(
        iris_small,
        zones_small,
        how="intersection",
        keep_geom_type=True
    )

    inter = inter[inter.geometry.notna()].copy()
    inter = inter[~inter.geometry.is_empty].copy()

    if len(inter) == 0:
        raise RuntimeError("Aucune intersection entre les IRIS et les zones OLAP.")

    inter["surface_intersection"] = inter.geometry.area
    inter["part_surface_iris"] = inter["surface_intersection"] / inter["surface_iris"]

    idx = inter.groupby("code_iris")["surface_intersection"].idxmax()

    iris_zone = inter.loc[idx].copy()

    iris_zone = iris_zone[
        [
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "zone_olap",
            "zone_number",
            "surface_intersection",
            "part_surface_iris"
        ]
    ].copy()

    print("✅ Correspondance IRIS -> zone OLAP :", len(iris_zone))
    print(iris_zone.head())

    missing = len(iris) - len(iris_zone)

    if missing > 0:
        print("⚠️ IRIS sans zone OLAP :", missing)

    return iris_zone


# ============================================================
# TRAITEMENT PAR ANNÉE
# ============================================================

def process_year(year, iris):
    print("\n")
    print("=" * 100)
    print(f"TRAITEMENT ANNÉE {year}")
    print("=" * 100)

    year_dir = os.path.join(BRONZE_OLAP_DIR, str(year))

    if not os.path.exists(year_dir):
        print("⚠️ Dossier absent :", year_dir)
        return None

    base_path = detect_file(
        year_dir,
        [
            "Base_OP_*_L*.csv",
            "*Base_OP*.csv",
            "*.csv"
        ]
    )

    kml_zone_path = detect_file(
        year_dir,
        [
            "*zone_cal*.kml",
            "*Zone_cal*.kml",
            "*ZONE_CAL*.kml"
        ]
    )

    table_zones_path = detect_file(
        year_dir,
        [
            "table_zones*.xls",
            "table_zones*.xlsx",
            "*zones*.xls",
            "*zones*.xlsx"
        ]
    )

    if base_path is None:
        print("❌ Aucun fichier Base_OP trouvé pour", year)
        return None

    if kml_zone_path is None:
        print("❌ Aucun fichier KML zone_cal trouvé pour", year)
        return None

    loyers = read_base_op(base_path, year)
    zones = read_kml_zones(kml_zone_path)
    table_zones = read_table_zones(table_zones_path)

    iris_zone = build_iris_zone_intersection(iris, zones)

    if table_zones is not None:
        table_zones_simple = table_zones[
            [
                "zone_number",
                "lib_zone"
            ]
        ].drop_duplicates()

        iris_zone = iris_zone.merge(
            table_zones_simple,
            on="zone_number",
            how="left"
        )
    else:
        iris_zone["lib_zone"] = pd.NA

    iris_zone["lib_zone"] = iris_zone["lib_zone"].replace("nan", pd.NA)

    iris_zone["lib_zone"] = iris_zone["lib_zone"].fillna(
        "Zone " + iris_zone["zone_number"].astype(str)
    )

    final_year = iris_zone.merge(
        loyers,
        on="zone_olap",
        how="left"
    )

    final_year["annee"] = year

    final_year = final_year[
        [
            "annee",
            "code_iris",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "nom_iris",
            "zone_olap",
            "lib_zone",
            "nb_pieces",
            "loyer_m2_median",
            "loyer_m2_moyen",
            "loyer_mensuel_median",
            "loyer_mensuel_moyen",
            "surface_moyenne",
            "nb_observations",
            "nb_logements",
            "part_surface_iris"
        ]
    ].copy()

    final_year = final_year[
        final_year["loyer_m2_median"].notna()
        | final_year["loyer_m2_moyen"].notna()
        | final_year["loyer_mensuel_median"].notna()
        | final_year["loyer_mensuel_moyen"].notna()
    ].copy()

    print("✅ Lignes finales année :", len(final_year))
    print(final_year.head(10))

    return final_year


# ============================================================
# MAIN
# ============================================================

def main():
    ensure_dirs()

    iris = read_iris()

    all_years = []

    for year in YEARS:
        result = process_year(year, iris)

        if result is not None:
            all_years.append(result)

    if not all_years:
        raise RuntimeError("Aucune année traitée. Vérifie les dossiers OLAP.")

    final = pd.concat(all_years, ignore_index=True)

    # Géométrie IRIS
    iris_geom = iris[
        [
            "code_iris",
            "geometry"
        ]
    ].copy()

    final_geo = iris_geom.merge(
        final,
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
            "zone_olap",
            "lib_zone",
            "nb_pieces",
            "loyer_m2_median",
            "loyer_m2_moyen",
            "loyer_mensuel_median",
            "loyer_mensuel_moyen",
            "surface_moyenne",
            "nb_observations",
            "nb_logements",
            "part_surface_iris",
            "geometry"
        ]
    ].copy()

    # Typage propre
    final_geo["annee"] = pd.to_numeric(final_geo["annee"], errors="coerce").astype("Int64")
    final_geo["arrondissement"] = pd.to_numeric(final_geo["arrondissement"], errors="coerce").astype("Int64")

    float_cols = [
        "loyer_m2_median",
        "loyer_m2_moyen",
        "loyer_mensuel_median",
        "loyer_mensuel_moyen",
        "surface_moyenne",
        "nb_observations",
        "nb_logements",
        "part_surface_iris"
    ]

    for col in float_cols:
        final_geo[col] = pd.to_numeric(final_geo[col], errors="coerce")

    # Tri propre
    final_geo = final_geo.sort_values(
        by=[
            "annee",
            "code_iris",
            "nb_pieces"
        ]
    ).reset_index(drop=True)

    # Export Parquet en Lambert 93
    final_geo.to_parquet(
        OUTPUT_PARQUET,
        index=False
    )

    # Export GeoJSON en WGS84
    final_geo_web = final_geo.to_crs(CRS_WEB)

    final_geo_web.to_file(
        OUTPUT_GEOJSON,
        driver="GeoJSON"
    )

    print("\n")
    print("=" * 100)
    print("✅ GOLD LOYERS IRIS CRÉÉE")
    print("=" * 100)

    print("Parquet :", OUTPUT_PARQUET)
    print("GeoJSON :", OUTPUT_GEOJSON)

    print("Lignes :", len(final_geo))
    print("IRIS uniques :", final_geo["code_iris"].nunique())
    print("Années :", sorted(final_geo["annee"].dropna().unique().tolist()))
    print("Zones :", sorted(final_geo["zone_olap"].dropna().unique().tolist()))

    print("\nRépartition nb_pieces :")
    print(final_geo["nb_pieces"].value_counts(dropna=False))

    print("\nAperçu :")
    print(
        final_geo[
            [
                "annee",
                "code_iris",
                "code_commune",
                "arrondissement",
                "nom_iris",
                "zone_olap",
                "lib_zone",
                "nb_pieces",
                "loyer_m2_median",
                "nb_observations",
                "part_surface_iris"
            ]
        ].head(30)
    )


if __name__ == "__main__":
    main()