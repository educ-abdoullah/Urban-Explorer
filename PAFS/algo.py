import pandas as pd
import geopandas as gpd
from pathlib import Path

PROJECT_ROOT = Path.cwd().parents[0]
RAW_DATA_DIR = PROJECT_ROOT / "data/gold/quartier_scores.csv"


df = pd.read_csv(RAW_DATA_DIR)

# Liste des catégories pour l'indicateur Paris Age-Friendly Score (PAFS)
categories = [
    "score_health",    # Santé : Pharmacies, médecins, centres de santé
    "score_edu",       # Éducation : Écoles, crèches, ludothèques
    "score_sport",     # Sport : Gymnases, piscines, city-stades, boulodromes
    "score_vibrance",  # Vie locale : Restaurants, cafés, cinémas, culture
    "score_env",       # Environnement : Parcs, jardins, bancs, sanisettes
    "score_noise"      # Nuisances : Bruit et pollution sonore (poids négatif)
]


# Définition des profils (Exemples)
weights_senior = {
    'score_health': 5, 
    'score_sport': 2,    # Pour les boulodromes/piscines
    'score_noise': -4,   # Le bruit fait baisser la note
    'score_vibrance': 3,
    'score_env': 2,
    'score_edu': 1
}

weights_actifs = {
    'score_health': 4,
    'score_sport': 5,
    'score_noise': -2,   # Le bruit est un inconvénient mais pas rédhibitoire
    'score_vibrance': 4,
    'score_env': 3,
    'score_edu': 2
}
weights_jeune_adult = {
    'score_health': 1,
    'score_sport': 4,
    'score_noise': 0,    # Le bruit n'est pas un problème majeur
    'score_vibrance': 5,
    'score_env': 2,
    'score_edu': 1
}

weights_junior = {
    'score_health': 2,
    'score_sport': 4,
    'score_noise': -1,   # Le bruit est un inconvénient mais pas    rédhibitoire
    'score_vibrance': 3,
    'score_env': 5,
    'score_edu': 4
}


profiles = {
    "senior": weights_senior,
    "actifs": weights_actifs,
    "jeune_adult": weights_jeune_adult,
    "junior": weights_junior
}

quartiers = {}

def init_quartier_dic(df):

    return score


def calculate_scoring(df, profiles):
    for profile_name, weights in profiles.items():
        # Somme pondérée
        weighted_sum = sum(df[cat] * weight for cat, weight in weights.items())
        
        # Somme des poids absolus pour la normalisation
        total_weight = sum(abs(w) for w in weights.values())
        
        # Attribution de la nouvelle colonne
        df[profile_name] = weighted_sum / total_weight
    
    return df