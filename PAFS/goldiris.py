#!/usr/bin/env python3
"""Build iris-level Gold metrics and scores (same schema as quartiers outputs)."""

from __future__ import annotations
from pathlib import Path
import re

import geopandas as gpd
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DATA_DIR = PROJECT_ROOT / "data" / "silver"
INDICE_IMVU_SILVER = PROJECT_ROOT / "Indice_imvu" / "data" / "silver"
GOLD_DATA_DIR = PROJECT_ROOT / "data" / "gold"
TARGET_CRS = "EPSG:2154"

BDCOM_FOOD_CODES = {"102"}
BDCOM_RESTAURANT_CODES = {"111"}
BDCOM_LOISIR_CODES = {"101", "106", "112"}

BASE_OUTPUT_COLUMNS_IRIS = [
    "iris_code",
    "iris_name",
    "iris_commune",
    "arrondissement",
    "iris_surface_m2",
]
SCORE_OUTPUT_COLUMNS = [
    "score_health",
    "score_edu",
    "score_sport",
    "score_vibrance",
    "score_noise",
    "score_env",
    "score_senior",
    "score_actifs",
    "score_jeune_adult",
    "score_junior",
]
METRIC_OUTPUT_COLUMNS = [
    "shops_count",
    "food_stores_count",
    "restaurants_count",
    "loisir_count",
    "pharmacies_count",
    "colleges_count",
    "schools_count",
    "lycees_count",
    "hospitals_count",
    "green_spaces_count",
    "sports_count",
    "health_services",
    "education_sites",
    "sports_sites",
    "local_life_sites",
    "health_density",
    "education_density",
    "sport_density",
    "vibrance_density",
    "green_space_density",
    "avg_noise_db",
]

PROFILE_WEIGHTS = {
    "senior": {
        "score_health": 5,
        "score_sport": 2,
        "score_noise": -4,
        "score_vibrance": 3,
        "score_env": 2,
        "score_edu": 1,
    },
    "actifs": {
        "score_health": 4,
        "score_sport": 5,
        "score_noise": -2,
        "score_vibrance": 4,
        "score_env": 3,
        "score_edu": 2,
    },
    "jeune_adult": {
        "score_health": 1,
        "score_sport": 4,
        "score_noise": 0,
        "score_vibrance": 5,
        "score_env": 2,
        "score_edu": 1,
    },
    "junior": {
        "score_health": 2,
        "score_sport": 4,
        "score_noise": -1,
        "score_vibrance": 3,
        "score_env": 5,
        "score_edu": 4,
    },
}


def build_points_gdf(
    df: pd.DataFrame,
    *,
    x_col: str | None = None,
    y_col: str | None = None,
    lon_col: str | None = None,
    lat_col: str | None = None,
) -> gpd.GeoDataFrame:
    work_df = df.copy()
    if x_col and y_col and {x_col, y_col}.issubset(work_df.columns):
        work_df[x_col] = pd.to_numeric(work_df[x_col], errors="coerce")
        work_df[y_col] = pd.to_numeric(work_df[y_col], errors="coerce")
        work_df = work_df.dropna(subset=[x_col, y_col]).copy()
        gdf = gpd.GeoDataFrame(
            work_df,
            geometry=gpd.points_from_xy(work_df[x_col], work_df[y_col]),
            crs=TARGET_CRS,
        )
        return gdf

    if lon_col and lat_col and {lon_col, lat_col}.issubset(work_df.columns):
        work_df[lon_col] = pd.to_numeric(work_df[lon_col], errors="coerce")
        work_df[lat_col] = pd.to_numeric(work_df[lat_col], errors="coerce")
        work_df = work_df.dropna(subset=[lon_col, lat_col]).copy()
        gdf = gpd.GeoDataFrame(
            work_df,
            geometry=gpd.points_from_xy(work_df[lon_col], work_df[lat_col]),
            crs="EPSG:4326",
        )
        return gdf.to_crs(TARGET_CRS)

    return gpd.GeoDataFrame(work_df.iloc[0:0].copy(), geometry=[], crs=TARGET_CRS)


def min_max_normalize(series: pd.Series, reverse: bool = False) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_value = numeric_series.min()
    max_value = numeric_series.max()
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        normalized = pd.Series(0.0, index=series.index)
    else:
        normalized = (numeric_series - min_value) / (max_value - min_value)
    return 1 - normalized if reverse else normalized


def calculate_profile_score(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    weighted_sum = pd.Series(0.0, index=df.index)
    total_weight = sum(abs(w) for w in weights.values())
    for col, w in weights.items():
        if col in df.columns:
            weighted_sum += df[col].fillna(0) * w
    return (weighted_sum / total_weight * 100).round(2)


def load_silver_tables() -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for file_path in sorted(SILVER_DATA_DIR.glob("*.parquet")):
        tables[file_path.stem] = pd.read_parquet(file_path)
    return tables


def build_noise_table(noise_df: pd.DataFrame) -> pd.DataFrame:
    work_df = noise_df.copy()
    work_df["arrondissement"] = (pd.to_numeric(work_df["arrondissement"], errors="coerce").astype("Int64")) - 75000
    work_df["avg_noise_db"] = pd.to_numeric(work_df["value_db"], errors="coerce")
    work_df = work_df.dropna(subset=["arrondissement", "avg_noise_db"])
    return work_df.groupby("arrondissement", as_index=False)["avg_noise_db"].mean()


def load_iris() -> gpd.GeoDataFrame:
    path = INDICE_IMVU_SILVER / "iris_silver.geojson"
    iris = gpd.read_file(path)
    if iris.crs is None:
        iris = iris.set_crs(TARGET_CRS)
    else:
        iris = iris.to_crs(TARGET_CRS)
    # rename to standard column names
    rename_map = {
        "code_iris": "iris_code",
        "nom_iris": "iris_name",
        "nom_com": "iris_commune",
        "surface_m2": "iris_surface_m2",
    }
    iris = iris.rename(columns=rename_map)
    if "geometry" not in iris.columns and "geom" in iris.columns:
        iris = iris.set_geometry("geom")
    # arrondissement: try parsing commune label (e.g. "Paris 3e Arrondissement")
    iris["arrondissement"] = iris["iris_commune"].astype(str).str.extract(r"(\d{1,2})", expand=False)
    iris["arrondissement"] = pd.to_numeric(iris["arrondissement"], errors="coerce").astype("Int64")
    # fallback from code_iris (first 5 digits -> subtract 75100)
    missing_mask = iris["arrondissement"].isna() & iris["iris_code"].notna()
    def _from_code(code):
        try:
            prefix = int(str(code)[:5])
            val = prefix - 75100
            return int(val) if val > 0 else pd.NA
        except Exception:
            return pd.NA
    if missing_mask.any():
        iris.loc[missing_mask, "arrondissement"] = iris.loc[missing_mask, "iris_code"].map(_from_code).astype("Int64")
    return iris[["iris_code", "iris_name", "iris_commune", "arrondissement", "iris_surface_m2", "geometry"]].copy()


def aggregate_bdcom_to_polygons(bdcom_df: pd.DataFrame, polygons_gdf: gpd.GeoDataFrame, polygon_code_col: str) -> pd.DataFrame:
    points_gdf = build_points_gdf(bdcom_df, x_col="x_coord", y_col="y_coord")
    if points_gdf.empty:
        return pd.DataFrame(columns=[polygon_code_col, "shops_count", "food_stores_count", "restaurants_count", "loisir_count"])
    joined = gpd.sjoin(points_gdf, polygons_gdf[[polygon_code_col, "geometry"]], how="inner", predicate="within")
    joined["niv18_code"] = joined["niv18"].astype("string").str.extract(r"(\d+)", expand=False)
    aggregated = (
        joined.groupby(polygon_code_col)
        .agg(
            shops_count=(polygon_code_col, "size"),
            food_stores_count=("niv18_code", lambda s: s.isin(BDCOM_FOOD_CODES).sum()),
            restaurants_count=("niv18_code", lambda s: s.isin(BDCOM_RESTAURANT_CODES).sum()),
            loisir_count=("niv18_code", lambda s: s.isin(BDCOM_LOISIR_CODES).sum()),
        )
        .reset_index()
    )
    return aggregated


def aggregate_points_to_polygons(
    df: pd.DataFrame,
    polygons_gdf: gpd.GeoDataFrame,
    polygon_code_col: str,
    output_column: str,
    *,
    x_col: str | None = None,
    y_col: str | None = None,
    lon_col: str | None = None,
    lat_col: str | None = None,
) -> pd.DataFrame:
    points_gdf = build_points_gdf(df, x_col=x_col, y_col=y_col, lon_col=lon_col, lat_col=lat_col)
    if points_gdf.empty:
        return pd.DataFrame(columns=[polygon_code_col, output_column])
    joined = gpd.sjoin(points_gdf, polygons_gdf[[polygon_code_col, "geometry"]], how="inner", predicate="within")
    counts = joined.groupby(polygon_code_col).size().rename(output_column).reset_index()
    return counts


def build_gold_iris_table() -> pd.DataFrame:
    silver_tables = load_silver_tables()
    iris_gdf = load_iris()
    iris_df = iris_gdf.drop(columns="geometry").copy()

    # BDCOM categories
    bdcom_counts = aggregate_bdcom_to_polygons(silver_tables["BDCOM_2023"], iris_gdf, "iris_code")
    iris_df = iris_df.merge(bdcom_counts, left_on="iris_code", right_on="iris_code", how="left")

    # point datasets (same set as quartiers)
    point_datasets = [
        ("carte-des-pharmacies-de-paris", "pharmacies_count", {"lon_col": "longitude", "lat_col": "latitude"}),
        ("Colleges_ile-de-France", "colleges_count", {"x_col": "x_coord", "y_col": "y_coord"}),
        ("Ecoles_elementaires_et_maternelles_ile-de-France", "schools_count", {"x_col": "x_coord", "y_col": "y_coord"}),
        ("Lycees_ile-de-France", "lycees_count", {"x_col": "x_coord", "y_col": "y_coord"}),
        ("les_etablissements_hospitaliers_franciliens", "hospitals_count", {"lon_col": "longitude", "lat_col": "latitude"}),
        ("recensement_des_equipements_sportifs_a_paris", "sports_count", {"lon_col": "longitude", "lat_col": "latitude"}),
        ("espaces_verts", "green_spaces_count", {"lon_col": "longitude", "lat_col": "latitude"}),
    ]

    for dataset_name, output_column, coord_kwargs in point_datasets:
        if dataset_name in silver_tables:
            agg = aggregate_points_to_polygons(silver_tables[dataset_name], iris_gdf, "iris_code", output_column, **coord_kwargs)
            iris_df = iris_df.merge(agg, left_on="iris_code", right_on="iris_code", how="left")

    # noise by arrondissement
    if "bruit_2024" in silver_tables:
        noise_df = build_noise_table(silver_tables["bruit_2024"])
        iris_df = iris_df.merge(noise_df, on="arrondissement", how="left")

    # cleanup counts
    count_columns = [
        "shops_count",
        "food_stores_count",
        "restaurants_count",
        "loisir_count",
        "pharmacies_count",
        "colleges_count",
        "schools_count",
        "lycees_count",
        "hospitals_count",
        "green_spaces_count",
        "sports_count",
    ]
    for col in count_columns:
        if col in iris_df.columns:
            iris_df[col] = iris_df[col].fillna(0).astype(int)

    iris_area_km2 = (iris_df["iris_surface_m2"].replace(0, pd.NA) / 1_000_000).astype(float)

    iris_df["health_services"] = iris_df.get("pharmacies_count", 0) + iris_df.get("hospitals_count", 0)
    iris_df["education_sites"] = (
        iris_df.get("schools_count", 0) + iris_df.get("colleges_count", 0) + iris_df.get("lycees_count", 0)
    )
    iris_df["sports_sites"] = iris_df.get("sports_count", 0)
    iris_df["local_life_sites"] = iris_df.get("food_stores_count", 0) + iris_df.get("restaurants_count", 0) + iris_df.get("loisir_count", 0)

    iris_df["health_density"] = iris_df["health_services"] / iris_area_km2
    iris_df["education_density"] = iris_df["education_sites"] / iris_area_km2
    iris_df["sport_density"] = iris_df["sports_sites"] / iris_area_km2
    iris_df["vibrance_density"] = iris_df["local_life_sites"] / iris_area_km2
    iris_df["green_space_density"] = iris_df.get("green_spaces_count", 0) / iris_area_km2

    iris_df["score_health"] = min_max_normalize(iris_df["health_density"])
    iris_df["score_edu"] = min_max_normalize(iris_df["education_density"])
    iris_df["score_sport"] = min_max_normalize(iris_df["sport_density"])
    iris_df["score_vibrance"] = min_max_normalize(iris_df["vibrance_density"])
    iris_df["score_noise"] = min_max_normalize(iris_df.get("avg_noise_db", pd.Series(dtype=float)))
    iris_df["score_env"] = min_max_normalize(iris_df["green_space_density"])

    for profile_name, weights in PROFILE_WEIGHTS.items():
        iris_df[f"score_{profile_name}"] = calculate_profile_score(iris_df, weights)

    return iris_df.sort_values(["iris_commune", "iris_name"]).reset_index(drop=True)


def run_iris_pipeline() -> None:
    GOLD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    iris_df = build_gold_iris_table()

    metrics_columns = [c for c in BASE_OUTPUT_COLUMNS_IRIS + METRIC_OUTPUT_COLUMNS if c in iris_df.columns]
    score_columns = [c for c in BASE_OUTPUT_COLUMNS_IRIS + SCORE_OUTPUT_COLUMNS if c in iris_df.columns]

    iris_metrics_df = iris_df[metrics_columns].copy()
    iris_scores_df = iris_df[score_columns].copy()

    metrics_csv_path = GOLD_DATA_DIR / "iris_metrics.csv"
    metrics_parquet_path = GOLD_DATA_DIR / "iris_metrics.parquet"
    scores_csv_path = GOLD_DATA_DIR / "iris_scores.csv"
    scores_parquet_path = GOLD_DATA_DIR / "iris_scores.parquet"

    iris_metrics_df.to_csv(metrics_csv_path, index=False)
    iris_metrics_df.to_parquet(metrics_parquet_path, index=False)
    iris_scores_df.to_csv(scores_csv_path, index=False)
    iris_scores_df.to_parquet(scores_parquet_path, index=False)

    print("Iris gold pipeline completed.")
    print(f"Rows: {len(iris_df)}")
    print(f"Saved metrics CSV: {metrics_csv_path}")
    print(f"Saved metrics Parquet: {metrics_parquet_path}")
    print(f"Saved scores CSV: {scores_csv_path}")
    print(f"Saved scores Parquet: {scores_parquet_path}")


if __name__ == "__main__":
    run_iris_pipeline()