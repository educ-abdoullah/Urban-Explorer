# Score d’Investissement Immobilier — Paris

## 1. Objectif

Construire un indicateur composite permettant d’évaluer la pertinence d’un investissement immobilier à Paris en combinant quatre dimensions principales :

- la rentabilité du bien
- la tension locative
- la liquidité
- le taux de criminalité

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
- normalisation du taux de criminalité

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

### 2.7 Criminalité

**Sources :**
- https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales
- https://opendata.paris.fr/explore/dataset/dans-ma-rue/information/?disjunctive.conseilquartier&disjunctive.intervenant&disjunctive.type&disjunctive.soustype&disjunctive.arrondissement&disjunctive.prefixe&disjunctive.code_postal

**Contenu :**
- faits de délinquance enregistrés
- signalements urbains par arrondissement ou zone
- informations territorialisées sur les nuisances et incivilités

**Utilisation :**
- calcul d’un indicateur de risque territorial
- intégration d’un facteur de sécurité dans le score d’investissement

---

## 3. Formules

### 3.1 Charges

On suppose que les charges représentent 5 % du prix du bien.

```math
charges = 0.05 \times prix



3.2 Rendement net

Le rendement net estime la rentabilité annuelle du bien après déduction des charges.

rendement=loyerannuel−chargesprix
rendement=
prix
loyer
a
	​

nnuel−charges
	​


Forme détaillée :

rendement=(loyerm2×surface×12)−(0.05×prix)prix
rendement=
prix
(loyer
m
	​

2×surface×12)−(0.05×prix)
	​

3.3 Demande locative

La demande locative est approchée par le rapport entre la population et le nombre de logements, ajusté par le taux de vacance.

demandelocative=populationnombrelogements×(1−tauxvacance)
demande
l
	​

ocative=
nombre
l
	​

ogements
population
	​

×(1−taux
v
	​

acance)
3.4 Liquidité

La liquidité mesure la facilité théorique de revente d’un bien dans une zone donnée.

liquidite=nombretransactionsannuellespopulation
liquidite=
population
nombre
t
	​

ransactions
a
	​

nnuelles
	​

3.5 Taux de criminalité

Le taux de criminalité mesure le niveau de risque territorial observé dans une zone donnée. Il peut être approché par le nombre de faits ou signalements rapporté à la population.

tauxcriminalite=nombrefaitscriminelspopulation
taux
c
	​

riminalite=
population
nombre
f
	​

aits
c
	​

riminels
	​


Comme un niveau élevé de criminalité réduit l’attractivité d’un investissement, on utilise dans le score une composante de sécurité définie comme l’inverse du risque.

securite=1−tauxcriminalite
securite=1−taux
c
	​

riminalite
4. Construction du score composite

Le score d’investissement combine les quatre dimensions précédentes avec la pondération suivante :

50 % pour le rendement
20 % pour la demande locative
5 % pour la liquidité
25 % pour la sécurité liée au taux de criminalité
4.1 Formule simplifiée
ScoreInvestissement=0.50×rendement+0.20×demandelocative+0.05×liquidite+0.25×securite
Score
I
	​

nvestissement=0.50×rendement+0.20×demande
l
	​

ocative+0.05×liquidite+0.25×securite
4.2 Formule détaillée
ScoreInvestissement=0.50×((loyerm2×surface×12)−(0.05×prix)prix)+0.20×(populationnombrelogements×(1−tauxvacance))+0.05×(nombretransactionsannuellespopulation)+0.25×(1−nombrefaitscriminelspopulation)
Score
I
	​

nvestissement=0.50×(
prix
(loyer
m
	​

2×surface×12)−(0.05×prix)
	​

)+0.20×(
nombre
l
	​

ogements
population
	​

×(1−taux
v
	​

acance))+0.05×(
population
nombre
t
	​

ransactions
a
	​

nnuelles
	​

)+0.25×(1−
population
nombre
f
	​

aits
c
	​

riminels
	​

)
