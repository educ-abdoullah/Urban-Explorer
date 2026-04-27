import os
import geopandas as gpd
import pandas as pd
import numpy as np

# CONFIGURATION DES CHEMINS
DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
SILVER_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../data/silver"))
GOLD_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../data/gold"))
os.makedirs(GOLD_DIR, exist_ok=True)

print("DÉMARRAGE DE L'ÉTAPE GOLD (Calculs Métiers et Agrégation)...\n")

# CHARGEMENT DES DONNÉES SILVER
print("1/4 - Chargement des bases de données propres (Silver)...")
iris = gpd.read_file(os.path.join(SILVER_DIR, "iris_silver.geojson"))
arbres = gpd.read_file(os.path.join(SILVER_DIR, "arbres_silver.geojson"))
parcs = gpd.read_file(os.path.join(SILVER_DIR, "espaces_verts_silver.geojson"))
jardins = gpd.read_file(os.path.join(SILVER_DIR, "jardins_partages_silver.geojson"))

# FILTRAGE : ISOLER LES ARBRES DE RUE
print("2/4 - Isolation des arbres d'alignement (anti double-comptabilité)...")

# On utilise la colonne domanialite pour ne garder QUE les arbres de rue.
arbres_rues = arbres[arbres['domanialite'].str.contains('Alignement|Voirie', case=False, na=False)]

print(f"   -> Sur {len(arbres)} arbres totaux à Paris, {len(arbres_rues)} sont des arbres de rue (alignement).")

# JOINTURE SPATIALE : ARBRES -> IRIS (Version 100% Pro)
print("3/4 - Agrégation spatiale des arbres par IRIS...")

# Utilisation de sjoin_nearest : Rattache chaque arbre à l'IRIS le plus proche (Même s'il déborde d'un mètre !)
arbres_avec_iris = gpd.sjoin_nearest(arbres_rues, iris[['code_iris', 'geometry']], how="left")

stats_arbres = arbres_avec_iris.groupby('code_iris').agg(
    nb_arbres_alignement=('idbase', 'count'),
    surface_canopee_m2=('surface_canopee_m2', 'sum')
).reset_index()

# Fusion des statistiques avec le fond de carte géométrique IRIS
iris = iris.merge(stats_arbres, on='code_iris', how='left')

iris['nb_arbres_alignement'] = iris['nb_arbres_alignement'].fillna(0).astype(int)
iris['surface_canopee_m2'] = iris['surface_canopee_m2'].fillna(0)

# Calcul du ratio
iris['ratio_canopee_pct'] = (iris['surface_canopee_m2'] / iris['surface_m2']) * 100

print(f"   -> Resultat : {int(iris['nb_arbres_alignement'].sum())} arbres sur {len(arbres_rues)} ont été rattachés (100% de rétention).")

# INTERSECTION ET JOINTURE : PARCS & JARDINS
print("4/4 - Traitement des Espaces Verts et Jardins Partagés...")

# On superpose les Parcs et les IRIS, et on ne garde que l'intersection exacte
parcs_decoupes = gpd.overlay(iris[['code_iris', 'geometry', 'surface_m2']], 
                             parcs[['lambda', 'geometry']], 
                             how='intersection')

# On recalcule l'aire (en m²) des nouveaux petits morceaux de parcs découpés
parcs_decoupes['surface_intersectee_m2'] = parcs_decoupes.geometry.area
# On applique notre coefficient de qualité (bois = 1.0, cimetière = 0.4, etc.)
parcs_decoupes['surface_ponderee_m2'] = parcs_decoupes['surface_intersectee_m2'] * parcs_decoupes['lambda']

stats_parcs = parcs_decoupes.groupby('code_iris')['surface_ponderee_m2'].sum().reset_index()

iris = iris.merge(stats_parcs, on='code_iris', how='left')
iris['surface_ponderee_m2'] = iris['surface_ponderee_m2'].fillna(0)
iris['ratio_parcs_pct'] = (iris['surface_ponderee_m2'] / iris['surface_m2']) * 100

print("   -> Rapprochement des jardins partagés (Initiatives)...")
jardins_avec_iris = gpd.sjoin_nearest(jardins, iris[['code_iris', 'geometry']], how='left')
stats_jardins = jardins_avec_iris.groupby('code_iris').size().reset_index(name='nb_initiatives')

iris = iris.merge(stats_jardins, on='code_iris', how='left')
iris['nb_initiatives'] = iris['nb_initiatives'].fillna(0).astype(int)

# 5. NORMALISATION (0-100), SCORE IMVU ET EXPORT
import numpy as np

# ==========================================
# 5. NORMALISATION (MASQUAGE CIBLÉ), SCORE IMVU ET EXPORT
# ==========================================
print("\n🏆 CALCUL DU SCORE IMVU FINAL ET EXPORT...")

# NOUVELLE FONCTION : L'approche "Intra-muros"
def normaliser_intramuros(df, nom_colonne):
    serie = df[nom_colonne]
    
    # 1. Identifier la frontière des "Géants"
    # On considère que les 2% des IRIS les plus verts sont nos "Bois/Grands Parcs"
    seuil_geants = np.percentile(serie.dropna(), 98)
    
    # 2. Créer un filtre (masque) pour isoler la "Ville normale"
    masque_ville_normale = serie <= seuil_geants
    
    # 3. Calculer le Min et le Max UNIQUEMENT sur la ville normale
    min_ville = serie[masque_ville_normale].min()
    max_ville = serie[masque_ville_normale].max()
    
    # Sécurité anti-division par zéro
    if max_ville == min_ville: return serie * 0
    
    # 4. Appliquer la notation classique sur TOUT LE MONDE
    scores = ((serie - min_ville) / (max_ville - min_ville)) * 100
    
    # 5. Le coup de grâce : np.clip
    # Tous ceux qui dépassaient le "max_ville" (donc nos géants) se retrouvent avec 
    # un score supérieur à 100 (ex: 450/100). 
    # np.clip force tout ce qui dépasse 100 à redescendre à exactement 100.
    scores_finaux = np.clip(scores, 0, 100)
    
    return scores_finaux

# Application de la nouvelle fonction
# Attention, on lui passe tout le dataframe (iris) et le nom de la colonne en texte
iris['score_parcs'] = normaliser_intramuros(iris, 'ratio_parcs_pct').round(1)
iris['score_rues'] = normaliser_intramuros(iris, 'ratio_canopee_pct').round(1)

# Pour les initiatives, l'écart est moins violent, une normalisation simple ou plafonnée à 98% suffit
iris['score_initiatives'] = normaliser_intramuros(iris, 'nb_initiatives').round(1)

# Poids de ton indicateur
W1, W2, W3 = 0.5, 0.3, 0.2
iris['IMVU_Global'] = ((W1 * iris['score_parcs']) + 
                       (W2 * iris['score_rues']) + 
                       (W3 * iris['score_initiatives'])).round(1)

# --- Préparation des fichiers d'export ---
cols_finales = ['code_iris', 'nom_com', 'nom_iris', 'surface_m2',
                'nb_arbres_alignement', 'nb_initiatives',
                'ratio_parcs_pct', 'ratio_canopee_pct',
                'score_parcs', 'score_rues', 'score_initiatives', 'IMVU_Global', 'geometry']
iris_final = iris[cols_finales]

fichier_csv = os.path.join(GOLD_DIR, "imvu_scores_iris.csv")
iris_final.drop(columns='geometry').to_csv(fichier_csv, index=False)

print("   -> Conversion en degrés (WGS84) pour l'affichage Web...")
iris_final['geometry'] = iris_final.geometry.simplify(2)
iris_final_web = iris_final.to_crs(epsg=4326)

fichier_geojson = os.path.join(GOLD_DIR, "imvu_carte_iris_web.geojson")
iris_final_web.to_file(fichier_geojson, driver="GeoJSON")

print("\n🎉 FÉLICITATIONS ! L'Étape Gold est parfaite.")

print(f"   -> Données tabulaires prêtes : {fichier_csv}")
print(f"   -> Carte interactive prête : {fichier_geojson}")