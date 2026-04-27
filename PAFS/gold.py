"""Gold layer pipeline for the Urban-Explorer project.

This script:
- loads the Silver parquet datasets
- aggregates the main indicators by Paris quartier
- normalizes the metrics
- computes first profile-based PAFS scores
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import geopandas as gpd
import pandas as pd
from shapely import wkb
import numpy as np

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SILVER_DATA_DIR: Final[Path] = PROJECT_ROOT / "data" / "silver"
QUARTIERS_DATA_DIR: Final[Path] = PROJECT_ROOT / "data" / "quartiers"
GOLD_DATA_DIR: Final[Path] = PROJECT_ROOT / "data" / "gold"
TARGET_CRS: Final[str] = "EPSG:2154"  # Lambert-93

BDCOM_FOOD_CODES: Final[set[str]] = {"102"}
BDCOM_RESTAURANT_CODES: Final[set[str]] = {"111"}
BDCOM_LOISIR_CODES: Final[set[str]] = {"101", "106", "112"}

BASE_OUTPUT_COLUMNS: Final[list[str]] = [
    "quartier_code",
    "quartier_insee",
    "quartier_name",
    "arrondissement",
    "quartier_surface_m2",
]
SCORE_OUTPUT_COLUMNS: Final[list[str]] = [
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
METRIC_OUTPUT_COLUMNS: Final[list[str]] = [
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

PROFILE_WEIGHTS: Final[dict[str, dict[str, float]]] = {
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


def to_snake_label(text: object) -> str:
    """Convert a label into a safe snake_case string."""
    value = str(text).strip().lower()
    for char in [" ", "-", "/", "(", ")", "%", "'", ","]:
        value = value.replace(char, "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")


def load_silver_tables() -> dict[str, pd.DataFrame]:
    """Load every Silver parquet file into a dictionary."""
    tables: dict[str, pd.DataFrame] = {}

    for file_path in sorted(SILVER_DATA_DIR.glob("*.parquet")):
        tables[file_path.stem] = pd.read_parquet(file_path)

    return tables


def load_quartiers() -> gpd.GeoDataFrame:
    """Load the Paris quartier polygons as a GeoDataFrame."""
    file_path = QUARTIERS_DATA_DIR / "quartier_paris.parquet"

    try:
        quartiers = gpd.read_parquet(file_path)
    except Exception:
        raw_df = pd.read_parquet(file_path)
        geometry = raw_df["geom"].apply(lambda value: wkb.loads(bytes(value)))
        quartiers = gpd.GeoDataFrame(raw_df.copy(), geometry=geometry, crs=TARGET_CRS)

    if "geometry" not in quartiers.columns and "geom" in quartiers.columns:
        quartiers = quartiers.set_geometry("geom")

    quartiers = quartiers.rename_geometry("geometry")

    if quartiers.crs is None:
        quartiers = quartiers.set_crs(TARGET_CRS)
    else:
        quartiers = quartiers.to_crs(TARGET_CRS)

    quartiers = quartiers.rename(
        columns={
            "c_qu": "quartier_code",
            "c_quinsee": "quartier_insee",
            "l_qu": "quartier_name",
            "c_ar": "arrondissement",
            "surface": "quartier_surface_m2",
        }
    )
    quartiers["arrondissement"] = pd.to_numeric(quartiers["arrondissement"], errors="coerce").astype("Int64")

    return quartiers[["quartier_code", "quartier_insee", "quartier_name", "arrondissement", "quartier_surface_m2", "geometry"]].copy()


def build_points_gdf(
    df: pd.DataFrame,
    *,
    x_col: str | None = None,
    y_col: str | None = None,
    lon_col: str | None = None,
    lat_col: str | None = None,
) -> gpd.GeoDataFrame:
    """Create a GeoDataFrame from projected or latitude/longitude coordinates."""
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


def assign_points_to_quartiers(points_gdf: gpd.GeoDataFrame, quartiers_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Spatially join point datasets to quartier polygons."""
    quartier_lookup = quartiers_gdf[["quartier_code", "quartier_name", "arrondissement", "geometry"]]

    try:
        return gpd.sjoin(points_gdf, quartier_lookup, how="inner", predicate="within")
    except Exception:
        joined_rows: list[pd.Series] = []
        for _, row in points_gdf.iterrows():
            matches = quartier_lookup[quartier_lookup.geometry.contains(row.geometry)]
            if not matches.empty:
                matched = row.copy()
                matched["quartier_code"] = matches.iloc[0]["quartier_code"]
                matched["quartier_name"] = matches.iloc[0]["quartier_name"]
                matched["arrondissement"] = matches.iloc[0]["arrondissement"]
                joined_rows.append(matched)

        if not joined_rows:
            return gpd.GeoDataFrame(points_gdf.iloc[0:0].copy(), geometry="geometry", crs=TARGET_CRS)

        return gpd.GeoDataFrame(joined_rows, geometry="geometry", crs=TARGET_CRS)


def aggregate_point_dataset(
    df: pd.DataFrame,
    quartiers_gdf: gpd.GeoDataFrame,
    output_column: str,
    *,
    x_col: str | None = None,
    y_col: str | None = None,
    lon_col: str | None = None,
    lat_col: str | None = None,
) -> pd.DataFrame:
    """Aggregate a point-based dataset into counts by quartier."""
    points_gdf = build_points_gdf(df, x_col=x_col, y_col=y_col, lon_col=lon_col, lat_col=lat_col)

    if points_gdf.empty:
        return pd.DataFrame(columns=["quartier_code", output_column])

    joined = assign_points_to_quartiers(points_gdf, quartiers_gdf)
    counts = joined.groupby("quartier_code").size().rename(output_column).reset_index()
    return counts


def aggregate_bdcom_category_counts(bdcom_df: pd.DataFrame, quartiers_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Count BDCOM commerces by quartier and selected `niv18` activity groups."""
    points_gdf = build_points_gdf(bdcom_df, x_col="x_coord", y_col="y_coord")

    if points_gdf.empty:
        return pd.DataFrame(
            columns=[
                "quartier_code",
                "shops_count",
                "food_stores_count",
                "restaurants_count",
                "loisir_count",
            ]
        )

    joined = assign_points_to_quartiers(points_gdf, quartiers_gdf)
    joined["niv18_code"] = joined["niv18"].astype("string").str.extract(r"(\d+)", expand=False)

    aggregated_df = (
        joined.groupby("quartier_code")
        .agg(
            shops_count=("quartier_code", "size"),
            food_stores_count=("niv18_code", lambda values: values.isin(BDCOM_FOOD_CODES).sum()),
            restaurants_count=("niv18_code", lambda values: values.isin(BDCOM_RESTAURANT_CODES).sum()),
            loisir_count=("niv18_code", lambda values: values.isin(BDCOM_LOISIR_CODES).sum()),
        )
        .reset_index()
    )

    return aggregated_df


def build_population_table(pop_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare arrondissement-level population metrics for later merges."""
    work_df = pop_df[[column for column in ["arrondissement", "label", "value"] if column in pop_df.columns]].copy()
    work_df = work_df.dropna(subset=["arrondissement", "label", "value"])
    work_df["arrondissement"] = pd.to_numeric(work_df["arrondissement"], errors="coerce").astype("Int64")
    work_df["label_slug"] = work_df["label"].map(to_snake_label)

    pivot_df = (
        work_df.pivot_table(index="arrondissement", columns="label_slug", values="value", aggfunc="sum", fill_value=0)
        .reset_index()
    )

    rename_map = {
        "ensemble": "population_total",
        "0_a_14_ans": "population_0_14",
        "15_a_29_ans": "population_15_29",
        "30_a_44_ans": "population_30_44",
        "45_a_59_ans": "population_45_59",
        "60_a_74_ans": "population_60_74",
        "75_ans_ou_plus": "population_75_plus",
    }
    pivot_df = pivot_df.rename(columns=rename_map)
    return pivot_df


def build_noise_table(noise_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare one average noise value per arrondissement for later merges."""
    work_df = noise_df.copy()
    work_df["arrondissement"] = (pd.to_numeric(work_df["arrondissement"], errors="coerce").astype("Int64")) - 75000
    work_df["avg_noise_db"] = pd.to_numeric(work_df["value_db"], errors="coerce")
    work_df = work_df.dropna(subset=["arrondissement", "avg_noise_db"])

    return work_df.groupby("arrondissement", as_index=False)["avg_noise_db"].mean()


def min_max_normalize(series: pd.Series, reverse: bool = False) -> pd.Series:
    """Apply a Min-Max normalization to a numeric series."""
    numeric_series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_value = numeric_series.min()
    max_value = numeric_series.max()

    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        normalized = pd.Series(0.0, index=series.index)
    else:
        normalized = (numeric_series - min_value) / (max_value - min_value)

    return 1 - normalized if reverse else normalized


def calculate_profile_score(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Compute a weighted profile score on a 0-100 scale."""
    weighted_sum = pd.Series(0.0, index=df.index)
    total_weight = sum(abs(weight) for weight in weights.values())

    for column, weight in weights.items():
        if column in df.columns:
            weighted_sum += df[column].fillna(0) * weight

    return (weighted_sum / total_weight * 100).round(2)


def build_gold_quartier_table() -> pd.DataFrame:
    """Create the main quartier-level Gold table."""
    silver_tables = load_silver_tables()
    quartiers_gdf = load_quartiers()

    gold_df = quartiers_gdf.drop(columns="geometry").copy()

    bdcom_counts_df = aggregate_bdcom_category_counts(silver_tables["BDCOM_2023"], quartiers_gdf)
    gold_df = gold_df.merge(bdcom_counts_df, on="quartier_code", how="left")

    point_datasets = [
        ("carte-des-pharmacies-de-paris", "pharmacies_count", {"lon_col": "longitude", "lat_col": "latitude"}),
        ("Colleges_ile-de-France", "colleges_count", {"x_col": "x_coord", "y_col": "y_coord"}),
        ("Ecoles_elementaires_et_maternelles_ile-de-France", "schools_count", {"x_col": "x_coord", "y_col": "y_coord"}),
        ("Lycees_ile-de-France", "lycees_count", {"x_col": "x_coord", "y_col": "y_coord"}),
        ("les_etablissements_hospitaliers_franciliens", "hospitals_count", {"lon_col": "longitude", "lat_col": "latitude"}),
        ("recensement_des_equipements_sportifs_a_paris", "sports_count", {"lon_col": "longitude", "lat_col": "latitude"}),
        ("espaces_verts", "green_spaces_count", {"lon_col": "longitude", "lat_col": "latitude"}),
    ]

    for dataset_name, output_column, coordinate_kwargs in point_datasets:
        aggregated_df = aggregate_point_dataset(silver_tables[dataset_name], quartiers_gdf, output_column, **coordinate_kwargs)
        gold_df = gold_df.merge(aggregated_df, on="quartier_code", how="left")

    noise_df = build_noise_table(silver_tables["bruit_2024"])
    gold_df = gold_df.merge(noise_df, on="arrondissement", how="left")

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
    for column in count_columns:
        if column in gold_df.columns:
            gold_df[column] = gold_df[column].fillna(0).astype(int)

    quartier_area_km2 = (gold_df["quartier_surface_m2"].replace(0, pd.NA) / 1_000_000).astype(float)
    quartier_area_km2.loc[gold_df['quartier_name'].str.lower() == 'picpus'] = 2.0
    quartier_area_km2.loc[gold_df['quartier_name'].str.lower() == 'bel-air'] = 2.0
    quartier_area_km2.loc[gold_df['quartier_name'].str.lower() == 'auteuil'] = 2.609009
    quartier_area_km2.loc[gold_df['quartier_name'].str.lower() == 'muette'] = 2.0
    quartier_area_km2.loc[gold_df['quartier_name'].str.lower() == 'porte-dauphine'] = 1.424035

    #gold_df['quartier_area_km2'] = quartier_area_km2  # Add to DataFrame for display

    gold_df["health_services"] = gold_df["pharmacies_count"] + gold_df["hospitals_count"]
    gold_df["education_sites"] = gold_df["schools_count"] + gold_df["colleges_count"] + gold_df["lycees_count"]
    gold_df["sports_sites"] = gold_df["sports_count"]
    gold_df["local_life_sites"] = gold_df["food_stores_count"] + gold_df["restaurants_count"] + gold_df["loisir_count"]

    gold_df["health_density"] = gold_df["health_services"] / quartier_area_km2
    gold_df["education_density"] = gold_df["education_sites"] / quartier_area_km2
    gold_df["sport_density"] = gold_df["sports_sites"] / quartier_area_km2
    gold_df["vibrance_density"] = gold_df["local_life_sites"] / quartier_area_km2
    gold_df["green_space_density"] = gold_df["green_spaces_count"] / quartier_area_km2

    gold_df["score_health"] = min_max_normalize(gold_df["health_density"])
    gold_df["score_edu"] = min_max_normalize(gold_df["education_density"])
    gold_df["score_sport"] = min_max_normalize(gold_df["sport_density"])
    gold_df["score_vibrance"] = min_max_normalize(gold_df["vibrance_density"])
    gold_df["score_noise"] = min_max_normalize(gold_df["avg_noise_db"])
    gold_df["score_env"] = min_max_normalize(gold_df["green_space_density"])

    for profile_name, weights in PROFILE_WEIGHTS.items():
        gold_df[f"score_{profile_name}"] = calculate_profile_score(gold_df, weights)


    return gold_df.sort_values(["arrondissement", "quartier_name"]).reset_index(drop=True)


def run_gold_pipeline() -> None:
    """Run the quartier-level Gold pipeline and save the outputs."""
    GOLD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    gold_df = build_gold_quartier_table()

    # Display quartier names and surfaces
    #print("Quartier Names and Areas (km²):")
    #print(gold_df[['quartier_name', 'quartier_area_km2']].to_string(index=False))
    #print("\n" + "="*50 + "\n")

    metrics_columns = [column for column in BASE_OUTPUT_COLUMNS + METRIC_OUTPUT_COLUMNS if column in gold_df.columns]
    score_columns = [column for column in BASE_OUTPUT_COLUMNS + SCORE_OUTPUT_COLUMNS if column in gold_df.columns]

    quartier_metrics_df = gold_df[metrics_columns].copy()
    quartier_scores_df = gold_df[score_columns].copy()

    metrics_csv_path = GOLD_DATA_DIR / "quartier_metrics.csv"
    metrics_parquet_path = GOLD_DATA_DIR / "quartier_metrics.parquet"
    scores_csv_path = GOLD_DATA_DIR / "quartier_scores.csv"
    scores_parquet_path = GOLD_DATA_DIR / "quartier_scores.parquet"

    quartier_metrics_df.to_csv(metrics_csv_path, index=False)
    quartier_metrics_df.to_parquet(metrics_parquet_path, index=False)
    quartier_scores_df.to_csv(scores_csv_path, index=False)
    quartier_scores_df.to_parquet(scores_parquet_path, index=False)

    print("Gold pipeline completed successfully.")
    print(f"Rows: {len(gold_df)}")
    print(f"Saved metrics CSV: {metrics_csv_path}")
    print(f"Saved metrics Parquet: {metrics_parquet_path}")
    print(f"Saved scores CSV: {scores_csv_path}")
    print(f"Saved scores Parquet: {scores_parquet_path}")


if __name__ == "__main__":
    run_gold_pipeline()
