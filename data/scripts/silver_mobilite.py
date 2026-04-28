import os
import geopandas as gpd
import pandas as pd
import numpy as np
import glob
from datetime import datetime

# CONFIGURATION DES CHEMINS

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../raw"))
SILVER_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../silver"))
os.makedirs(SILVER_DIR, exist_ok=True)

def get_latest_raw_dir(raw_dir):
    subdirs = [
        os.path.join(raw_dir, d)
        for d in os.listdir(raw_dir)
        if os.path.isdir(os.path.join(raw_dir, d))
    ]
    
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {raw_dir}")
    
    latest_dir = sorted(subdirs)[-1]
    return latest_dir

latest_raw_dir = get_latest_raw_dir(BRONZE_DIR)

# dossier silver du jour
date_jour = datetime.now().strftime("%Y%m%d")
SILVER_DAY_DIR = os.path.join(SILVER_DIR, date_jour)
os.makedirs(SILVER_DAY_DIR, exist_ok=True)

#files
iris_gdf = gpd.read_file(os.path.join(latest_raw_dir, "iris.geojson"))
parkings_gdf = gpd.read_file(os.path.join(latest_raw_dir, "stationnement-en-ouvrage.geojson"))
voie_publique_gdf = gpd.read_file(os.path.join(latest_raw_dir, "stationnement-voie-publique-emplacements.geojson"))
arrets_gdf = gpd.read_file(os.path.join(latest_raw_dir, "arrets-lignes.geojson"))
comptage_routier_gdf = gpd.read_file(os.path.join(latest_raw_dir, "referentiel-comptages-routiers.geojson"))
stations_velib_gdf = gpd.read_file(os.path.join(latest_raw_dir, "velib-emplacement-des-stations.geojson"))

files = glob.glob("./data/raw/20260428/trafic/2025/*.txt")

df_list = [pd.read_csv(f, sep=";") for f in files]
trafic_df = pd.concat(df_list, ignore_index=True)


iris_gdf = iris_gdf[iris_gdf["dep"] == "75"].copy()

arrets_gdf = arrets_gdf.to_crs(iris_gdf.crs)
voie_publique_gdf = voie_publique_gdf.to_crs(iris_gdf.crs)
parkings_gdf = parkings_gdf.to_crs(iris_gdf.crs)
stations_velib_gdf = stations_velib_gdf.to_crs(iris_gdf.crs)
comptage_routier_gdf = comptage_routier_gdf.to_crs(iris_gdf.crs)

comptage_routier_gdf["iu_ac"]=pd.to_numeric(comptage_routier_gdf["iu_ac"])
trafic_arcs = trafic_df.merge(comptage_routier_gdf,on="iu_ac",how="inner")
comptage_routier_gdf["geometry"]=comptage_routier_gdf.geometry.representative_point()

arrets_iris = gpd.sjoin(
    arrets_gdf,
    iris_gdf,
    how="inner",
    predicate="within"
)

parkings_iris = gpd.sjoin(
    parkings_gdf,
    iris_gdf,
    how="inner",
    predicate="within"
)

voie_publique_iris = gpd.sjoin(
    voie_publique_gdf,
    iris_gdf,
    how="inner",
    predicate="within"
)

stations_iris = gpd.sjoin(
    stations_velib_gdf,
    iris_gdf,
    how="inner",
    predicate="within"
)

trafic_arcs = gpd.GeoDataFrame(
    trafic_arcs,
    geometry="geometry",
    crs=comptage_routier_gdf.crs
)

arcs_arrondissements = gpd.sjoin(
    comptage_routier_gdf,
    iris_gdf,
    how="inner",
    predicate="within"
)

arrets_iris = arrets_iris[["id_left","route_long_name","stop_id","stop_name","mode","code_iris","nom_iris"]]
parkings_iris = parkings_iris[["code_iris","nom_iris","id_left","nom","geometry","nb_places"]]
voie_publique_iris = voie_publique_iris[["code_iris","nom_iris","geometry","regpri","plarel","id_old"]]
stations_iris = stations_iris[[
    "stationcode",
    "name",
    "capacity",
    "geometry",
    "iris",
    "geo_point_2d",
    "code_iris",
    "nom_iris"
]]
trafic_arcs = trafic_arcs[["iu_ac","t_1h","q","k","etat_trafic","etat_barre","geometry"]]
arcs_arrondissements = arcs_arrondissements[[
    "iu_ac",
    "geometry",
    "code_iris",
    "nom_iris"
]]

arcs_arrondissements = (
    arcs_arrondissements[["iu_ac", "code_iris", "nom_iris"]]
    .drop_duplicates()
    .drop_duplicates(subset=["iu_ac"])
)

arrets_iris.to_parquet(os.path.join(SILVER_DAY_DIR, "arrets_iris.parquet"))
parkings_iris.to_parquet(os.path.join(SILVER_DAY_DIR, "parkings_iris.parquet"))
voie_publique_iris.to_parquet(os.path.join(SILVER_DAY_DIR, "voie_publique_iris.parquet"))
stations_iris.to_parquet(os.path.join(SILVER_DAY_DIR, "stations_iris.parquet"))
arcs_arrondissements.to_parquet(os.path.join(SILVER_DAY_DIR, "arcs_arrondissements.parquet"), index=False)

output_dir = os.path.abspath(os.path.join(DOSSIER_SCRIPT, f"../silver/{date_jour}/trafic"))
os.makedirs(output_dir, exist_ok=True)

chunk_size = 500_000

for i, start in enumerate(range(0, len(trafic_arcs), chunk_size)):
    chunk = trafic_arcs.iloc[start:start + chunk_size].copy()

    merged = chunk.merge(
        arcs_arrondissements,
        on="iu_ac",
        how="left",
        validate="many_to_one"
    )

    gdf_chunk = gpd.GeoDataFrame(
        merged,
        geometry="geometry",
        crs=trafic_arcs.crs
    )

    output_file = os.path.join(output_dir, f"silver_trafic_chunk_{i:03d}.parquet")
    gdf_chunk.to_parquet(output_file)


print(f"Fichiers silver enregistrés dans : {SILVER_DAY_DIR}")