import os
import geopandas as gpd
import pandas as pd
import numpy as np
import glob
from datetime import datetime

# CONFIGURATION DES CHEMINS

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
GOLD_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../gold"))
SILVER_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../silver"))
RAW_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../raw"))
os.makedirs(GOLD_DIR, exist_ok=True)

def get_latest_silver_dir(silver_dir):
    subdirs = [
        os.path.join(silver_dir, d)
        for d in os.listdir(silver_dir)
        if os.path.isdir(os.path.join(silver_dir, d))
    ]
    
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {silver_dir}")
    
    latest_dir = sorted(subdirs)[-1]
    return latest_dir

date_jour = datetime.now().strftime("%Y%m%d")
GOLD_DAY_DIR = os.path.join(GOLD_DIR, date_jour)
os.makedirs(GOLD_DAY_DIR, exist_ok=True)

latest_silver_dir = get_latest_silver_dir(SILVER_DIR)
latest_raw_dir = get_latest_silver_dir(RAW_DIR)

df_arrets= pd.read_parquet(os.path.join(latest_silver_dir, "arrets_iris.parquet"))
df_parkings = pd.read_parquet(os.path.join(latest_silver_dir, "parkings_iris.parquet"))
df_stations = pd.read_parquet(os.path.join(latest_silver_dir, "stations_iris.parquet"))
df_voie_publique = pd.read_parquet(os.path.join(latest_silver_dir, "voie_publique_iris.parquet"))
iris_gdf = gpd.read_file(os.path.join(latest_raw_dir, "iris.geojson"))

#trafic
files = glob.glob(latest_silver_dir+"/trafic/*.parquet")

results = []

for f in files:
    chunk = gpd.read_parquet(f)

    agg_chunk = (
        chunk.groupby(["code_iris", "nom_iris"], as_index=False)
        .agg(
            trafic_total_q=("q", "sum"),
            trafic_moyen_q=("q", "mean"),
            occupation_moyenne_k=("k", "mean"),
            nb_mesures=("iu_ac", "count"),
            nb_arcs=("iu_ac", "nunique")
        )
    )

    results.append(agg_chunk)

gold_trafic = (
    pd.concat(results, ignore_index=True)
    .groupby(["code_iris", "nom_iris"], as_index=False)
    .agg(
        trafic_total_q=("trafic_total_q", "sum"),
        nb_mesures=("nb_mesures", "sum"),
        nb_arcs=("nb_arcs", "sum"),
        occupation_moyenne_k=("occupation_moyenne_k", "mean")
    )
)

gold_trafic["trafic_moyen_q"] = (
    gold_trafic["trafic_total_q"] / gold_trafic["nb_mesures"]
)

#parkings et voie publiqe
categories_stationnement = [
    "PAYANT MIXTE",
    "PAYANT ROTATIF",
    "GRATUIT",
    "GIG/GIC",
    "ELECTRIQUE"
]
parking_auto = df_voie_publique[
    df_voie_publique["regpri"].isin(categories_stationnement)
].copy()

parking_auto["plarel"] = pd.to_numeric(
    parking_auto["plarel"], errors="coerce"
).fillna(0)

stationnement_auto_iris = (
    parking_auto.groupby(["code_iris", "nom_iris"], as_index=False)
    .agg(nb_places_auto=("plarel", "sum"))
)


df_parkings["nb_places"] = pd.to_numeric(
    df_parkings["nb_places"], errors="coerce"
).fillna(0)

parking_ouvrage_iris = (
    df_parkings.groupby(["code_iris", "nom_iris"], as_index=False)
    .agg(nb_places_ouvrage=("nb_places", "sum"))
)

stationnement_quartier = parking_ouvrage_iris.merge(
    stationnement_auto_iris,
    on=["code_iris", "nom_iris"],
    how="outer"
).fillna(0)

stationnement_quartier["stationnement_total"] = (
    stationnement_quartier["nb_places_ouvrage"] +
    stationnement_quartier["nb_places_auto"]
)
iris_gdf["code_iris"] = pd.to_numeric(iris_gdf["code_iris"])
stationnement_quartier["code_iris"] = pd.to_numeric(stationnement_quartier["code_iris"])
iris_gdf = iris_gdf.to_crs("EPSG:2154")
iris_gdf["surface"] = iris_gdf.geometry.area
stationnement_quartier = stationnement_quartier.merge(
    iris_gdf[["code_iris","surface"]],
    on="code_iris",
    how="left"
)
stationnement_quartier["places_km2"] = (
    stationnement_quartier["stationnement_total"]/
    (stationnement_quartier["surface"]/1000000)
)

#ratp
df_aggregated_arrets = (df_arrets.groupby(["code_iris","nom_iris","mode"]).agg(nb_arrets=("id_left","count"),nb_lignes=("id_left","nunique")).reset_index())

#velib
df_aggregated_stations = (df_stations.groupby(["code_iris","nom_iris"]).agg(velib_station=("stationcode","count"),capacity=("capacity","sum")).reset_index())

#score
df_aggregated_arrets["code_iris"] = pd.to_numeric(df_aggregated_arrets["code_iris"])
df_aggregated_stations["code_iris"] = pd.to_numeric(df_aggregated_stations["code_iris"])
stationnement_quartier["code_iris"] = pd.to_numeric(stationnement_quartier["code_iris"])
gold_trafic["code_iris"] = pd.to_numeric(gold_trafic["code_iris"])

tc_modes = (
    df_aggregated_arrets.pivot_table(
        index=["code_iris", "nom_iris"],
        columns="mode",
        values="nb_lignes",
        aggfunc="sum",
        fill_value=0
    )
    .reset_index()
)

gold_mobilite = df_aggregated_stations.merge(
    stationnement_quartier,
    on=["code_iris", "nom_iris"],
    how="outer"
).merge(
    gold_trafic,
    on=["code_iris", "nom_iris"],
    how="outer"
).merge(
    tc_modes,
    on=["code_iris", "nom_iris"],
    how="outer"
)

gold_mobilite["nb_arrets"] = gold_mobilite["Bus"] + gold_mobilite["Funicular"] + gold_mobilite["LocalTrain"] + gold_mobilite["Metro"]+ gold_mobilite["Tramway"] +gold_mobilite["regionalRail"]

#normalisation
def min_max_normalize(series):
    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return pd.Series([100] * len(series), index=series.index)

    return 100 * (series - min_val) / (max_val - min_val)

gold_mobilite["velib_station_norm"] = min_max_normalize(gold_mobilite["velib_station"])
gold_mobilite["capacity_norm"] = min_max_normalize(gold_mobilite["capacity"])

gold_mobilite["places_km2_norm"] = min_max_normalize(gold_mobilite["places_km2"])

gold_mobilite["nb_arrets_norm"] = min_max_normalize(gold_mobilite["nb_arrets"])

gold_mobilite["trafic_moyen_norm"] = min_max_normalize(gold_mobilite["trafic_moyen_q"])
gold_mobilite["occupation_norm"] = min_max_normalize(gold_mobilite["occupation_moyenne_k"])

gold_mobilite["score_velib"] = (
    0.5 * gold_mobilite["velib_station_norm"] +
    0.5 * gold_mobilite["capacity_norm"]
)

gold_mobilite["score_stationnement"] = gold_mobilite["places_km2_norm"]

gold_mobilite["score_tc"] = (
    1 * gold_mobilite["nb_arrets_norm"] + 0
    #0.5 * gold_mobilite["nb_lignes_norm"]
)

gold_mobilite["score_trafic"] = (
    0.5 * gold_mobilite["trafic_moyen_norm"] +
    0.5 * gold_mobilite["occupation_norm"]
)

gold_mobilite["score_trafic_inverse"] = 100 - gold_mobilite["score_trafic"]

gold_mobilite["score_mobilite"] = (
    0.4 * gold_mobilite["score_tc"] +
    0.1 * gold_mobilite["score_velib"] +
    0.3* gold_mobilite["score_stationnement"] +
    0.2 * gold_mobilite["score_trafic_inverse"]
)

gold_mobilite.to_parquet(os.path.join(GOLD_DAY_DIR, "score_mobilite.parquet"))