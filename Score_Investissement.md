# Score d’Investissement Immobilier — Paris

## 1. Objectif

Construire un indicateur composite permettant d’évaluer la pertinence d’un investissement immobilier à Paris en combinant trois dimensions principales :

- la rentabilité du bien (rendement net)
- la tension locative (pression du marché locatif)
- la liquidité (facilité de revente)

---

## 2. Données utilisées

### 2.1 Prix immobiliers (DVF)
Source : https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres

Contenu :
- prix de vente
- surface du bien
- type de bien
- localisation

Utilisation :
- calcul du prix d’acquisition
- calcul du rendement

---

### 2.2 Loyers
Source : https://www.data.gouv.fr/organizations/observatoires-locaux-des-loyers/datasets

Contenu :
- loyers médians au m²
- segmentation géographique

Utilisation :
- estimation du revenu locatif

---

### 2.3 Population
Sources :
- https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_RP_POPULATION_COMP
- https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_POPULATIONS_REFERENCE
- https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_ESTIMATION_POPULATION
- https://www.data.gouv.fr/reuses/population-paris

Contenu :
- population totale par zone

Utilisation :
- calcul de la pression locative
- normalisation de la liquidité

---

### 2.4 Logements / Bâtiments
Source : https://www.data.gouv.fr/reuses/cartographie-des-batiments-de-paris

Contenu :
- nombre de bâtiments
- proxy du nombre de logements

Utilisation :
- estimation du parc immobilier

---

### 2.5 Taux de vacance
Source : https://www.data.gouv.fr/datasets/logements-vacants-du-parc-prive-par-commune-departement-region-france

Contenu :
- pourcentage de logements vacants

Utilisation :
- ajustement de la tension locative

---

### 2.6 Transactions immobilières
Source : DVF (même dataset que les prix)

Contenu :
- nombre de ventes par zone et par année

Utilisation :
- calcul de la liquidité

---

## 3. Feature Engineering

### 3.1 Loyer annuel

Le loyer annuel estimé est calculé à partir du loyer médian au m², de la surface du bien et de 12 mois de location.

```math
loyer\_annuel = loyer\_m2 \times surface \times 12
