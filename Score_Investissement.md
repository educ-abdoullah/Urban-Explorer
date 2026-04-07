# 🏠 Score d’Investissement Immobilier — Paris

## 🎯 Objectif
Construire un **indicateur composite** permettant d’évaluer la pertinence d’un investissement immobilier à Paris en combinant :
- rentabilité
- tension locative
- liquidité du marché

---

# 📊 1. Données utilisées

## 💰 Prix immobiliers (DVF)
- Source : https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres  
- Contenu :
  - prix de vente
  - surface
  - localisation

---

## 💸 Loyers
- Source : https://www.data.gouv.fr/organizations/observatoires-locaux-des-loyers/datasets  
- Contenu :
  - loyers médian €/m²

---

## 🧑‍🤝‍🧑 Population
- Sources :
  - https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_RP_POPULATION_COMP
  - https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_POPULATIONS_REFERENCE
  - https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_ESTIMATION_POPULATION
  - https://www.data.gouv.fr/reuses/population-paris

---

## 🏢 Logements / Bâtiments
- Source : https://www.data.gouv.fr/reuses/cartographie-des-batiments-de-paris  
- Contenu :
  - nombre de bâtiments
  - proxy du nombre de logements

---

## 🏚️ Taux de vacance
- Source : https://www.data.gouv.fr/datasets/logements-vacants-du-parc-prive-par-commune-departement-region-france  
- Contenu :
  - % logements vacants

---

# ⚙️ 2. Feature Engineering

## 💰 Rendement

```math
rendement = \frac{loyer\_m2 \times surface}{prix} - charges
