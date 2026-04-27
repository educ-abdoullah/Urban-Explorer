import os

import folium
import geopandas as gpd
import pandas as pd
from folium.features import GeoJsonTooltip

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
SILVER_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../data/silver"))
GOLD_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../data/gold"))
MAPS_DIR = os.path.join(GOLD_DIR, "maps")
os.makedirs(MAPS_DIR, exist_ok=True)

IRIS_WEB = os.path.join(GOLD_DIR, "imvu_carte_iris_web.geojson")
QUARTIERS_SILVER = os.path.join(SILVER_DIR, "quartiers_silver.geojson")
ARONDISS_SILVER = os.path.join(SILVER_DIR, "arrondissements_silver.geojson")


def safe_spatial_join(left, right, how="left", predicate="within"):
    """Support geopandas versions using predicate or op."""
    try:
        return gpd.sjoin(left, right, how=how, predicate=predicate)
    except TypeError:
        return gpd.sjoin(left, right, how=how, op=predicate)


def build_map(gdf, key_field, title, tooltip_fields, output_html):
    bounds = gdf.total_bounds
    center = [
        (bounds[1] + bounds[3]) / 2,
        (bounds[0] + bounds[2]) / 2,
    ]

    m = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")

    choropleth = folium.Choropleth(
        geo_data=gdf,
        name=title,
        data=gdf,
        columns=[key_field, "IMVU_Global"],
        key_on=f"feature.properties.{key_field}",
        fill_color="YlGnBu",
        fill_opacity=0.75,
        line_opacity=0.3,
        nan_fill_color="gray",
        legend_name="IMVU Global",
        highlight=True,
    )
    choropleth.add_to(m)

    tooltip = GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=[f.replace("_", " ").title() + ":" for f in tooltip_fields],
        localize=True,
        sticky=True,
    )

    folium.GeoJson(
        gdf,
        style_function=lambda feature: {
            "fillColor": "transparent",
            "color": "#444444",
            "weight": 0.6,
        },
        tooltip=tooltip,
    ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(output_html)
    print(f"Carte générée : {output_html}")


def aggregate_scores(iris, boundaries, boundary_key):
    iris_proj = iris.to_crs(epsg=3857).copy()
    boundaries_proj = boundaries.to_crs(epsg=3857).copy()
    iris_proj.geometry = iris_proj.geometry.centroid
    joined = safe_spatial_join(
        iris_proj[["code_iris", "IMVU_Global", "surface_m2", "geometry"]],
        boundaries_proj[[boundary_key, "geometry"]],
        how="left",
        predicate="within",
    )

    joined["weighted_imvu"] = joined["IMVU_Global"] * joined["surface_m2"]
    aggregated = (
        joined.groupby(boundary_key, as_index=False)
        .agg(
            total_weighted_imvu=("weighted_imvu", "sum"),
            total_surface_m2=("surface_m2", "sum"),
            n_iris=("code_iris", "count"),
        )
    )
    aggregated["IMVU_Global"] = (
        aggregated["total_weighted_imvu"] / aggregated["total_surface_m2"]
    ).round(1)
    return aggregated[[boundary_key, "IMVU_Global", "total_surface_m2", "n_iris"]]


def main():
    print("Chargement des données...")
    iris = gpd.read_file(IRIS_WEB)
    quartiers = gpd.read_file(QUARTIERS_SILVER)
    arrondissements = gpd.read_file(ARONDISS_SILVER)

    if quartiers.crs != "EPSG:4326":
        quartiers = quartiers.to_crs(epsg=4326)
    if arrondissements.crs != "EPSG:4326":
        arrondissements = arrondissements.to_crs(epsg=4326)

    print("Agrégation des scores sur les quartiers...")
    agg_quartiers = aggregate_scores(iris, quartiers, "code_quartier")
    quartiers = quartiers.merge(agg_quartiers, on="code_quartier", how="left")
    quartiers["IMVU_Global"] = quartiers["IMVU_Global"].fillna(0)
    quartiers["n_iris"] = quartiers["n_iris"].fillna(0).astype(int)

    print("Agrégation des scores sur les arrondissements...")
    agg_arrondissements = aggregate_scores(iris, arrondissements, "code_arrondissement")
    arrondissements = arrondissements.merge(agg_arrondissements, on="code_arrondissement", how="left")
    arrondissements["IMVU_Global"] = arrondissements["IMVU_Global"].fillna(0)
    arrondissements["n_iris"] = arrondissements["n_iris"].fillna(0).astype(int)

    print("Export des GeoJSON web...")
    quartiers.to_file(os.path.join(GOLD_DIR, "imvu_quartiers_web.geojson"), driver="GeoJSON")
    arrondissements.to_file(os.path.join(GOLD_DIR, "imvu_arrondissements_web.geojson"), driver="GeoJSON")

    print("Création des cartes interactives...")
    build_map(
        iris,
        key_field="code_iris",
        title="Indice IMVU par IRIS",
        tooltip_fields=[
            "code_iris",
            "nom_iris",
            "IMVU_Global",
            "score_parcs",
            "score_rues",
            "score_initiatives",
        ],
        output_html=os.path.join(MAPS_DIR, "imvu_iris_map.html"),
    )

    build_map(
        quartiers,
        key_field="code_quartier",
        title="Indice IMVU par Quartier",
        tooltip_fields=["code_quartier", "IMVU_Global", "n_iris"],
        output_html=os.path.join(MAPS_DIR, "imvu_quartiers_map.html"),
    )

    build_map(
        arrondissements,
        key_field="code_arrondissement",
        title="Indice IMVU par Arrondissement",
        tooltip_fields=["code_arrondissement", "IMVU_Global", "n_iris"],
        output_html=os.path.join(MAPS_DIR, "imvu_arrondissements_map.html"),
    )

    print("\nToutes les cartes sont prêtes dans :", MAPS_DIR)


if __name__ == "__main__":
    main()
