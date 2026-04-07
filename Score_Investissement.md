# Score d’Investissement Immobilier — Paris

## 1. Objectif

Construire un indicateur composite permettant d’évaluer la pertinence d’un investissement immobilier à Paris en combinant trois dimensions principales :

- la rentabilité du bien
- la tension locative
- la liquidité

L’objectif est d’obtenir un **score synthétique** permettant de comparer plusieurs biens ou plusieurs zones géographiques à partir de données ouvertes.

---

## 2. Données utilisées

### 2.1 Prix immobiliers (DVF)

**Source :**  
https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres

**Contenu :**
- prix de vente
- surface du bien
- type de bien
- localisation

**Utilisation :**
- calcul du prix d’acquisition
- calcul du rendement

---

### 2.2 Loyers

**Source :**  
https://www.data.gouv.fr/organizations/observatoires-locaux-des-loyers/datasets

**Contenu :**
- loyers médians au m²
- segmentation géographique

**Utilisation :**
- estimation du revenu locatif annuel

---

### 2.3 Population

**Sources :**
- https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_RP_POPULATION_COMP
- https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_POPULATIONS_REFERENCE
- https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_ESTIMATION_POPULATION
- https://www.data.gouv.fr/reuses/population-paris

**Contenu :**
- population totale par zone

**Utilisation :**
- calcul de la pression locative
- normalisation de la liquidité

---

### 2.4 Logements / Bâtiments

**Source :**  
https://www.data.gouv.fr/reuses/cartographie-des-batiments-de-paris

**Contenu :**
- nombre de bâtiments
- proxy du nombre de logements

**Utilisation :**
- estimation du parc immobilier

---

### 2.5 Taux de vacance

**Source :**  
https://www.data.gouv.fr/datasets/logements-vacants-du-parc-prive-par-commune-departement-region-france

**Contenu :**
- pourcentage de logements vacants

**Utilisation :**
- ajustement de la tension locative

---

### 2.6 Transactions immobilières

**Source :**  
DVF (même dataset que les prix)

**Contenu :**
- nombre de ventes par zone et par année

**Utilisation :**
- calcul de la liquidité
- estimation du dynamisme du marché

---

## 3. Variables et notations

On note :

- `prix` : prix d’achat du bien
- `surface` : surface du bien en m²
- `loyer_m2` : loyer médian au m²
- `population` : population de la zone
- `nombre_logements` : nombre estimé de logements
- `taux_vacance` : part des logements vacants
- `nombre_transactions_annuelles` : nombre de ventes observées sur une année

Ces variables servent à construire les indicateurs intermédiaires puis le score final.

---

## 4. Formules

On suppose que les charges représentent 5 % du prix du bien.

```math
charges = 0.05 \times prix
```

### Rendement net

Le rendement net estime la rentabilité annuelle du bien après déduction des charges.

```math
rendement = \frac{loyer_annuel - charges}{prix}
```

Forme détaillée :

```math
rendement = \frac{(loyer_m2 \times surface \times 12) - (0.05 \times prix)}{prix}
```

### Demande locative

La demande locative est approchée par le rapport entre la population et le nombre de logements, ajusté par le taux de vacance.

```math
demande_locative = \frac{population}{nombre_logements} \times (1 - taux_vacance)
```

### Liquidité

La liquidité mesure la facilité théorique de revente d’un bien dans une zone donnée.

```math
liquidite = \frac{nombre_transactions_annuelles}{population}
```

## Construction du score composite

Le score d’investissement combine les trois dimensions précédentes avec la pondération suivante :

- 60 % pour le rendement
- 30 % pour la demande locative
- 10 % pour la liquidité

Formule simplifiée :

```math
Score_Investissement = 0.6 \times rendement + 0.3 \times demande_locative + 0.1 \times liquidite
```

Formule détaillée :

```math
Score_Investissement =
0.6 \times \left(\frac{(loyer_m2 \times surface \times 12) - (0.05 \times prix)}{prix}\right)
+ 0.3 \times \left(\frac{population}{nombre_logements} \times (1 - taux_vacance)\right)
+ 0.1 \times \left(\frac{nombre_transactions_annuelles}{population}\right)
```
