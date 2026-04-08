# Indice de Morphologie Végétale Urbaine (IMVU)

**Indicateur de densité, de qualité et d'équité spatiale de la nature en ville**

### 1. Présentation de l'Indicateur

**Objectif du projet**
L'objectif est de créer un indicateur permettant de visualiser objectivement l'emprise physique et qualitative de la nature dans chaque quartier parisien.
Plutôt que de simplement compter les espaces verts, l'**IMVU** (Indice de Morphologie Végétale Urbaine) décompose la végétalisation en dimensions spatiales pondérées. La carte s'adapte dynamiquement pour révéler les contrastes urbains et sert d'outil d'aide à la décision (ex: analyse immobilière, cadre de vie).

**Les 3 métriques clés optimisées**
1. **Le Taux de Couverture Pondéré :** Mesure l'empreinte au sol des espaces verts en pondérant leur surface par leur qualité (pleine terre vs zones minéralisées).
2. **Le Volume de Canopée des Rues :** Remplace le simple comptage d'arbres par une estimation de leur pouvoir ombrageant réel, en excluant les arbres déjà comptés dans les parcs.
3. **La Diversité Végétale (Initiatives) :** Révèle la présence de jardins partagés gérés par le tissu associatif local.

---

### 2. Les Datasets Utilisés (Sans ajout de nouvelles sources)

L'indicateur croise les données géométriques de l'Open Data de la Ville de Paris en exploitant leurs métadonnées :

* **Quartiers administratifs :** Polygones géographiques et surface totale (dénominateur).
* **Espaces verts et assimilés :** Polygones (m²). Utilisation des attributs `categorie` et `type_ev` pour pondérer la qualité de l'espace.
* **Les Arbres :** Inventaire géolocalisé (points). Utilisation des attributs de `circonférence` pour modéliser la taille de la canopée.
* **Jardins partagés :** Localisation des micro-espaces gérés par des associations.

---

### 3. Méthodologie et Formules Mathématiques

Le score repose sur des algorithmes de traitement géospatial optimisés. Pour combiner des unités différentes (m², pourcentages, unités), chaque métrique brute est d'abord calculée, puis normalisée sur une échelle de 0 à 100 via la méthode Min-Max :

> X_norm = [(X - X_min) / (X_max - X_min)] * 100

#### A. Le Volume de Canopée des Rues (DC)
Pour refléter l'impact réel des arbres d'alignement, nous transformons chaque point en une surface d'ombrage estimée.

1. **Diamètre du tronc (D)** à partir de la circonférence :
   > D = Circonference / π

2. **Rayon de la canopée (R_canopee)** estimé via un coefficient forestier urbain (α ≈ 20) :
   > R_canopee = α * D_metres

3. **Surface de la canopée de l'arbre (S_arbre)** :
   > S_arbre = π * (R_canopee)²

4. **Densité de canopée du quartier (DC)** (somme des canopées rapportée à la surface du quartier) :
   > DC = (∑ S_arbre / Surface_Quartier) * 100
   *(Note : Une jointure spatiale exclut au préalable les arbres situés à l'intérieur des polygones d'espaces verts pour éviter la double-comptabilité).*

#### B. Le Taux de Couverture Pondéré (TCP)
La surface de chaque polygone d'espace vert est ajustée selon un coefficient de qualité végétale (λ).

1. **Surface Effective** (S_effective) :
   > S_effective = Surface_EV * λ
   *(Exemple de coefficients : Bois λ = 1.0 ; Squares λ = 0.8 ; Cimetières λ = 0.4)*

2. **Taux de Couverture Pondéré du quartier (TCP)** :
   > TCP = (∑ S_effective / Surface_Quartier) * 100

#### C. Le Score Global IMVU
Une fois les trois scores normalisés (TCP_norm, DC_norm, Initiatives_norm), l'indice final est calculé en appliquant des poids de pondération (W).

> IMVU = (W1 * TCP_norm) + (W2 * DC_norm) + (W3 * Initiatives_norm)

*Répartition recommandée : W1 = 0.5 (Emprise au sol majeure), W2 = 0.3 (Micro-climat des rues), W3 = 0.2 (Vitalité locale).*

---

### 4. Architecture et Optimisation des Performances

Pour garantir une visualisation fluide dans le dashboard *Urban Data Explorer*, l'indicateur repose sur la stratégie d'optimisation suivante :

* **Pipeline ETL (Pré-calcul) :** Les opérations géospatiales lourdes (comme l'intersection pour exclure les arbres des parcs) ne sont jamais exécutées côté client. Un script Python (`GeoPandas`) pré-calcule les scores finaux pour les 80 quartiers. Le dashboard ne charge qu'un fichier JSON/CSV léger contenant les indicateurs consolidés.
* **Simplification Géométrique :** Les polygones des parcs et des quartiers affichés sur la carte sont simplifiés via l'algorithme de Douglas-Peucker (tolérance ~5 mètres) pour réduire drastiquement le poids des fichiers GeoJSON sans altérer le rendu visuel.
* **Indexation Spatiale :** Si des requêtes spatiales dynamiques sont nécessaires (ex: sélection personnalisée par l'utilisateur), l'application utilise les *Bounding Boxes* (rectangles englobants) pour filtrer rapidement les données avant d'effectuer les calculs d'intersection géométrique précis.
