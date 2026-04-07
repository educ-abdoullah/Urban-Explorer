# Méthodologie — Indice de Valeur Verte Micro-Locale (IVVM) par arrondissement

## 1. Objectif
L'objectif est de construire un **Indice de Valeur Verte Micro-Locale (IVVM)** pour évaluer les disparités de prix de l'immobilier *au sein même* des arrondissements parisiens. 

Le score cherche à démontrer et quantifier la "prime à l'aménagement" : la surcote financière acceptée par les acheteurs pour résider à proximité immédiate d'une transformation urbaine écologique (végétalisation, apaisement) bénéficiant d'une bonne qualité environnementale. La maille d'analyse compare des micro-zones (buffers spatiaux) par rapport à la maille plus large de l'arrondissement.

---

## 2. Sources de données

### 2.1. Transactions immobilières
La source principale pour les prix est la base **Demandes de Valeurs Foncières (DVF)** publiée par la DGFiP sur data.gouv.fr.
* **Variables mobilisables :** Valeur foncière (prix de vente), surface réelle bâtie, latitude, longitude, date de mutation.
* **Rôle dans le score :** Fournir la vérité terrain du marché immobilier et permettre le calcul du prix au mètre carré.

### 2.2. Dynamique de transformation urbaine
Le jeu de données **Paris se transforme** (Open Data Paris).
* **Variables mobilisables :** Coordonnées géographiques du point central du chantier, catégorie (Végétalisation, Piétonnisation, Rue aux écoles), statut (Livré).
* **Rôle dans le score :** Identifier les épicentres de l'amélioration du cadre de vie.

### 2.3. Qualité environnementale
Le jeu de données lié à l'**Exposition au bruit** (Bruitparif) ou à la **Qualité de l'air** (Open Data Paris / Airparif).
* **Variables mobilisables :** Indices de pollution spatiaux ou décibels moyens (Lden) modélisés par rues.
* **Rôle dans le score :** Filtrer les projets de transformation pour ne retenir que ceux qui offrent un réel bénéfice environnemental (exclusion des aménagements verts situés sur des carrefours à forte nuisance sonore).

---

## 3. Principe général de calcul

Le score repose sur la segmentation spatiale des transactions immobilières en deux groupes pour un même arrondissement :
1. **Groupe "Intra-ZEE" (Zone d'Excellence Environnementale) :** Les ventes situées dans un rayon de 150 mètres autour d'un aménagement écologique majeur ET qualitatif.
2. **Groupe "Extra-ZEE" :** Le reste des ventes de l'arrondissement.

L'indicateur final est le delta (la différence en pourcentage) entre ces deux groupes.

---

## 4. Construction de l'Indicateur

### 4.1. Définition des Zones d'Excellence Environnementale (ZEE)
Il s'agit d'une opération géospatiale :
1. Isoler les points du jeu "Paris se transforme" relatifs à la végétalisation et aux mobilités douces.
2. Générer un buffer (rayon) de 150 mètres autour de chaque point.
3. Croiser ces polygones avec la carte de "Qualité environnementale". Si le polygone intersecte une zone critique (ex: > 68 dB pour le bruit), il est disqualifié. Les polygones restants forment les **ZEE**.

### 4.2. Segmentation des prix au m²
Pour chaque transaction de la base DVF dans un arrondissement donné :
* Si les coordonnées GPS de la vente sont *à l'intérieur* d'un polygone ZEE, elle est intégrée au calcul du `prix_m2_median_intra`.
* Si elle est à l'extérieur, elle est intégrée au `prix_m2_median_extra`.

---

## 5. Formule de l'Indice Global

La formule mathématique permettant d'obtenir le ratio de disparité est la suivante :

$$IVVM = \left( \frac{Prix\_m2\_median\_intra}{Prix\_m2\_median\_extra} \right) - 1$$

**Interprétation :**
* **Si IVVM = 0.08 (+8 %) :** Les biens situés dans les micro-zones vertes et calmes se vendent 8 % plus cher que la moyenne du reste de l'arrondissement. La disparité est forte.
* **Si IVVM ≤ 0 :** L'aménagement n'a pas (ou pas encore) créé de surcote locale par rapport au reste du quartier.

---

## 6. Étapes de traitement (Architecture Pipeline Data)

1. **Zone Bronze (Ingestion) :** Récupération brute des jeux DVF (fichiers TXT) et des API Open Data Paris (JSON).
2. **Zone Silver (Nettoyage & Calcul Spatial) :** Nettoyage des valeurs DVF aberrantes. Utilisation de librairies géospatiales (ex: GeoPandas) pour réaliser les jointures spatiales entre les coordonnées des ventes et les polygones des ZEE.
3. **Zone Gold (Agrégation) :** Regroupement par arrondissement et par année pour calculer les médianes et l'IVVM final.
4. **Exposition :** L'API web sert les données agrégées au format JSON pour alimenter le dashboard interactif (Mapbox, Chart.js, D3.js).

---

## 7. Limites de l'indicateur

* **Latence de la donnée DVF :** Les transactions remontent avec un décalage de plusieurs mois. L'impact immédiat d'un aménagement met du temps à être visible sur les prix officiels.
* **L'Effet de bord :** Un buffer strict de 150 mètres crée une frontière géographique binaire artificielle (un bien à 151 mètres est classé "Extra-ZEE").
* **Biais de typologie :** Les zones réaménagées (hyper-centres, places historiques) concentrent parfois des immeubles d'un standing architectural supérieur, ce qui influence déjà le prix de base.

---

## 8. Résultat attendu (Format API)

Le résultat final exposé par l'API pour le front-end devra ressembler à la structure suivante :

| arrondissement | annee | prix_median_intra | prix_median_extra | ivvm_score |
| :--- | :--- | :--- | :--- | :--- |
| 75011 | 2023 | 10850 € | 9900 € | +9,5 % |
| 75019 | 2023 | 8600 € | 8350 € | +2,9 % |
