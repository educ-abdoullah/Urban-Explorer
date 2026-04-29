import os
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime

# CONFIGURATION DES CHEMINS

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../../data/raw"))
SILVER_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../../data/silver"))
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

# TRAITEMENT DES ARBRES

print(" 1/4 - Traitement des arbres...")
arbres = gpd.read_file(os.path.join(latest_raw_dir, "arbres.geojson"))

# Sélection des colonnes validées
colonnes_arbres = ['idbase', 'circonferenceencm', 'domanialite', 'adresse', 'geometry']
arbres = arbres[colonnes_arbres]

# Reprojection en mètres (Lambert 93)
arbres = arbres.to_crs(epsg=2154)

# Nettoyage et Imputation : Remplacer les 0 ou NaN par la médiane
mediane_circ = arbres['circonferenceencm'].replace(0, np.nan).median()
arbres['circonferenceencm'] = arbres['circonferenceencm'].replace(0, mediane_circ).fillna(mediane_circ)

# Feature Engineering : Calcul de la canopée
ALPHA = 20
arbres['diametre_m'] = (arbres['circonferenceencm'] / np.pi) / 100
arbres['rayon_canopee'] = arbres['diametre_m'] * ALPHA
arbres['surface_canopee_m2'] = np.pi * (arbres['rayon_canopee'] ** 2)

arbres.to_file(os.path.join(SILVER_DAY_DIR, "arbres_silver.geojson"), driver="GeoJSON")
print(f"   -> {len(arbres)} arbres traités et sauvegardés.")

# 2. TRAITEMENT DES ESPACES VERTS

print("2/4 - Traitement des espaces verts...")
parcs = gpd.read_file(os.path.join(latest_raw_dir, "espaces_verts.geojson"))

# ASTUCE DEBUG : Décommenter la ligne ci-dessous pour voir les vrais noms des colonnes dans mon terminal
# print("Colonnes disponibles :", parcs.columns.tolist())

# Utilisation de .get() pour éviter le KeyError.
# Si le nom n'est pas exact, on cherche les variantes fréquentes, sinon on met du vide.
type_voie = parcs.get('adresse_type_voie', parcs.get('adresse_typevoie', pd.Series('', index=parcs.index)))
libelle = parcs.get('adresse_libelle_voie', parcs.get('adresse_libellevoie', pd.Series('', index=parcs.index)))
cp = parcs.get('adresse_codepostal', parcs.get('adresse_code_postal', pd.Series('', index=parcs.index)))

parcs['adresse_complete'] = (
    type_voie.fillna('') + ' ' + 
    libelle.fillna('') + ', ' + 
    cp.astype(str).str.replace(r'\.0$', '', regex=True).fillna('')
).str.strip()

# On définit les colonnes idéales
colonnes_parcs_ideales = ['nom_ev', 'categorie', 'surface_horticole', 'adresse_complete', 'geometry']

# Sécurité : on ne garde QUE les colonnes qui existent vraiment pour éviter un autre KeyError
colonnes_existantes = [col for col in colonnes_parcs_ideales if col in parcs.columns]
parcs = parcs[colonnes_existantes]

# Reprojection et réparation des polygones cassés
parcs = parcs.to_crs(epsg=2154)
parcs['geometry'] = parcs.geometry.buffer(0)

# Sécurité pour la surface horticole
if 'surface_horticole' in parcs.columns:
    parcs['surface_horticole'] = parcs['surface_horticole'].fillna(parcs.geometry.area)
else:
    # Si la colonne est introuvable, on prend la surface géométrique calculée par Python
    parcs['surface_horticole'] = parcs.geometry.area

# Feature Engineering : Pondération de la qualité
def attribuer_lambda(categorie):
    if pd.isna(categorie): return 0.5
    cat = str(categorie).lower()
    if 'bois' in cat or 'foret' in cat: return 1.0
    if 'square' in cat or 'parc' in cat or 'jardin' in cat: return 0.8
    if 'cimetiere' in cat: return 0.4
    return 0.1

if 'categorie' in parcs.columns:
    parcs['lambda'] = parcs['categorie'].apply(attribuer_lambda)
else:
    parcs['lambda'] = 0.5 # Au cas où la colonne catégorie manque

parcs['surface_ponderee_m2'] = parcs['surface_horticole'] * parcs['lambda']

parcs.to_file(os.path.join(SILVER_DAY_DIR, "espaces_verts_silver.geojson"), driver="GeoJSON")
print(f"   -> {len(parcs)} espaces verts traités.")

# 3. TRAITEMENT DES QUARTIERS ET ARRONDISSEMENTS

print("3/4 - Traitement des iris et création des quartiers, arrondissements...")
iris = gpd.read_file(os.path.join(latest_raw_dir, "iris.geojson"))

col_code = 'code_iris' if 'code_iris' in iris.columns else 'iris'
colonnes_iris_ideales = [col_code, 'nom_com', 'nom_iris', 'geometry']

iris[col_code] = iris[col_code].astype(str)
# On ne garde QUE les lignes dont le code commence par "751"
iris = iris[iris[col_code].str.startswith('751')]

colonnes_existantes = [col for col in colonnes_iris_ideales if col in iris.columns]
iris = iris[colonnes_existantes].to_crs(epsg=2154)

if col_code == 'iris':
    iris = iris.rename(columns={'iris': 'code_iris'})

# Calcul de la surface de chaque IRIS
iris['surface_m2'] = iris.geometry.area
iris.to_file(os.path.join(SILVER_DAY_DIR, "iris_silver.geojson"), driver="GeoJSON")

# --- 2. L'Astuce INSEE : Extraction des codes ---
# Extraction des 7 premiers chiffres pour le Quartier, et 5 pour l'Arrondissement
iris['code_quartier'] = iris['code_iris'].astype(str).str[:7]
iris['code_arrondissement'] = iris['code_iris'].astype(str).str[:5]

# --- 3. Création des 80 Quartiers ---
print("   -> Fusion des IRIS pour recréer les 80 Quartiers...")
quartiers = iris.dissolve(by='code_quartier', aggfunc={'surface_m2': 'sum'}).reset_index()
quartiers.to_file(os.path.join(SILVER_DAY_DIR, "quartiers_silver.geojson"), driver="GeoJSON")

# --- 4. Création des 20 Arrondissements ---
print("   -> Fusion des IRIS pour recréer les 20 Arrondissements...")
arrondissements = iris.dissolve(by='code_arrondissement', aggfunc={'surface_m2': 'sum'}).reset_index()
arrondissements.to_file(os.path.join(SILVER_DAY_DIR, "arrondissements_silver.geojson"), driver="GeoJSON")

print(f"   -> Bilan : {len(iris)} IRIS, {len(quartiers)} Quartiers et {len(arrondissements)} Arrondissements générés.")

# 4. TRAITEMENT DES JARDINS PARTAGÉS

print("4/4 - Traitement des jardins partagés...")
# CORRECTION : On cherche "jardins_partages" avec un underscore
jardins = gpd.read_file(os.path.join(latest_raw_dir, "jardins_partages.geojson"))

# Gérer le nom de la colonne adresse (souvent 'adresse' ou 'adresse_cp')
col_adresse = 'adresse' if 'adresse' in jardins.columns else 'adresse_cp' if 'adresse_cp' in jardins.columns else None
colonnes_jardins = ['nom_ev', 'geometry']
if col_adresse: colonnes_jardins.insert(1, col_adresse)

jardins = jardins[colonnes_jardins].to_crs(epsg=2154)
jardins.to_file(os.path.join(SILVER_DAY_DIR, "jardins_partages_silver.geojson"), driver="GeoJSON")
print(f"   -> {len(jardins)} initiatives citoyennes traitées.")

print("\nÉTAPE SILVER TERMINÉE AVEC SUCCÈS.")
print(f"Vos données ultra-propres vous attendent dans le dossier : {SILVER_DAY_DIR}")