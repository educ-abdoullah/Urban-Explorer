# Paris Age-Friendly Score (PAFS)
**Indicateur d'attractivité urbaine par tranche d'âge**

## 1. Présentation de l'Indicateur
### Objectif du projet
L'objectif est de créer un indicateur qui permet de visualiser le "niveau d'intérêt" d'un quartier en fonction de l'âge de l'utilisateur. 

Plutôt que de dire qu'un quartier est "bien" ou "mauvais" de manière absolue, notre indicateur **PAFS** (Paris Age-Friendly Score) reconnaît que les besoins d'un étudiant ne sont pas les mêmes que ceux d'une famille avec enfants ou d'un retraité. La carte s'adaptera dynamiquement pour révéler les zones les mieux équipées pour chaque profil.

### Les 4 profils cibles
* **Junior (Enfants & Parents) :** Priorité à l'éducation, aux parcs et à la sécurité.
* **Jeunes Adultes (Étudiants & Actifs) :** Priorité à la vie nocturne, à la culture et à la mobilité.
* **Actifs (Familles & Travailleurs) :** Priorité aux services, au sport et à la connectivité.
* **Senior :** Priorité à la santé, au calme, au confort urbain et aux commerces de proximité.

---

## 2. Les Datasets
Pour construire cet indicateur, nous croisons des données provenant de sources officielles en Open Data :

* **Commerces & Vie Locale :** `BDCOM de l'Apur` (Recense tous les restaurants, cafés, brasseries et commerces de bouche).
https://opendata.apur.org/datasets/Apur::bdcom-2023/about
* **Sport :** `RES (Data ES)` (Inventaire complet des équipements sportifs : du skatepark au boulodrome).
* **Espaces Verts :** `Espaces verts et boisés (Île-de-France)` (Cartographie des parcs, jardins et forêts ouverts au public).
https://opendata.paris.fr/explore/dataset/espaces_verts/export/?disjunctive.type_ev&disjunctive.categorie&disjunctive.adresse_codepostal&disjunctive.presence_cloture&basemap=jawg.dark&location=13,48.8315,2.34112
* **Éducation :** `Secteurs scolaires (Paris Data)` (Localisation des écoles primaires, collèges et lycées).
https://data-iau-idf.opendata.arcgis.com/
* **Santé :** `FINESS / Paris Data` (Emplacement des pharmacies, centres de santé et hôpitaux).
https://www.data.gouv.fr/datasets/les-etablissements-hospitaliers-franciliens-idf
https://www.data.gouv.fr/datasets/carte-des-pharmacies-de-paris-idf
* **Qualité de Vie :** `Cartographie du bruit (Bruitparif)` (Identification des zones bruyantes pour ajuster le score de confort).
https://www.bfmtv.com/immobilier/renovation-travaux/carte-quels-sont-les-arrondissements-les-plus-bruyants-de-paris_AV-202407220475.html#:~:text=L'%C3%A9tude%20r%C3%A9v%C3%A8le%20que%20les,sonore%20est%20autour%20de%2040dB.


---

## 3. Méthodologie de Calcul
Le score n'est pas une simple moyenne, mais une **somme pondérée**. Chaque équipement reçoit un "poids" différent selon le profil choisi.

### La Formule Simplifiée
Pour chaque quartier, on calcule le score comme suit :
$$Score = (Équipement_A \times Poids_A) + (Équipement_B \times Poids_B) - (Nuisance \times Poids_N)$$

### Exemples de pondération (Logique de l'algorithme)

| Type d'équipement | Impact Junior | Impact Jeune Adulte | Impact Senior |
| :--- | :---: | :---: | :---: |
| **Écoles & Crèches** | Très Fort (+) | Neutre | Neutre |
| **Bars & Brasseries** | Neutre | Très Fort (+) | Faible (+) |
| **Pharmacies & Santé** | Moyen (+) | Faible (+) | Très Fort (+) |
| **Bruit (Avenue bruyante)** | Négatif (-) | Neutre | Très Négatif (-) |
| **Piscines & Tennis** | Fort (+) | Fort (+) | Moyen (+) |
| **Bancs & Espaces Verts** | Fort (+) | Moyen (+) | Très Fort (+) |

---

## 4. Visualisation attendue
La carte finale permettra à l'utilisateur de :
1.  **Sélectionner son âge** via un curseur ou des boutons de profils.
2.  **Visualiser les zones de chaleur (Heatmap)** : Les arrondissements ou quartiers les plus adaptés s'illuminent en vert.
3.  **Comparer les quartiers** : Cliquer sur une zone pour voir son "bulletin de notes" (ex: 9/10 en sport, mais 3/10 en calme).

---
