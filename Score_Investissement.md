# Score d’Investissement Immobilier — Paris

## 1. Objectif

Construire un indicateur synthétique permettant d’évaluer la qualité d’un investissement immobilier à Paris.

Le score repose sur 4 dimensions :

- la rentabilité (rendement)
- la tension locative
- la liquidité du marché
- la sécurité (inverse de la criminalité)

L’objectif est de comparer des zones (IRIS ou arrondissements) avec un score homogène.

---

## 2. Données utilisées

### 2.1 DVF — Transactions immobilières

Source : https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres

Utilisation :
- prix d’acquisition
- surface
- nombre de transactions
- calcul du prix au m²
- calcul du rendement

---

### 2.2 Loyers

Source : Observatoires Locaux des Loyers

Utilisation :
- estimation du revenu locatif
- base du rendement

---

### 2.3 Population

Source : INSEE

Utilisation :
- normalisation des indicateurs
- calcul tension locative
- calcul liquidité
- calcul criminalité

---

### 2.4 Criminalité

Sources :
- données police/gendarmerie
- données "Dans Ma Rue" (Paris)

Utilisation :
- construction d’un score de risque
- transformation en score de sécurité

---

## 3. Construction des indicateurs

### 3.1 Rendement net

Le rendement mesure la rentabilité d’un bien.

Formule :

rendement = ((loyer_m2 × surface × 12) − (0.05 × prix)) / prix

Puis :

score_rendement = normalize(rendement)

---

### 3.2 Tension locative

Elle mesure la pression de la demande sur le logement.

demande = (population / nombre_logements) × (1 − taux_vacance)

Puis :

score_demande = normalize(demande)

---

### 3.3 Liquidité

La liquidité mesure la facilité de revente.

liquidite = nombre_transactions / population

Puis :

score_liquidite = normalize(liquidite)

---

### 3.4 Sécurité (inverse de la criminalité)

taux_criminalite = nombre_faits / population

Transformation :

score_securite_brut = 1 − taux_criminalite

Puis :

score_securite = normalize(score_securite_brut)

Important :
- criminalité élevée → score faible
- zone sûre → score élevé

---

## 4. Normalisation

Tous les indicateurs sont normalisés pour être comparables.

score = 20 + 60 × (x − min(x)) / (max(x) − min(x))

Chaque score est donc compris entre :

[20 ; 80]

---

## 5. Score d’investissement final

Pondérations :

- Rendement : 50 %
- Demande locative : 20 %
- Liquidité : 5 %
- Sécurité : 25 %

Formule :

Score_Investissement =  
0.50 × score_rendement +  
0.20 × score_demande +  
0.05 × score_liquidite +  
0.25 × score_securite

---

## 6. Interprétation

- Score élevé → zone attractive pour investir
- Score faible → zone risquée ou peu rentable

---

## 7. Points importants

- Tous les indicateurs sont data-driven (DVF + INSEE + loyers)
- Les scores sont comparables entre zones
- Le modèle est simple mais robuste
- La sécurité a un poids significatif (25 %)

---

## 8. Limites

- approximation des loyers
- estimation de la criminalité
- absence de fiscalité détaillée
- charges simplifiées (5 %)

---

## 9. Conclusion

Ce score permet de :

- comparer rapidement des zones
- détecter des opportunités
- intégrer plusieurs dimensions clés de l’investissement immobilier
