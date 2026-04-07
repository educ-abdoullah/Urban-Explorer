# Méthodologie — Score de mobilité par quartier administratif à Paris

## 1. Objectif

L’objectif est de construire un **score de mobilité** pour chacun des **quartiers administratifs de Paris**.  
Le score cherche à résumer, à une échelle locale, l’accessibilité et l’intensité des différentes formes de mobilité disponibles dans un quartier.  
La maille retenue est celle des **quartiers administratifs**, car elle est plus fine que l’arrondissement tout en restant lisible pour une analyse urbaine. Paris compte **80 quartiers administratifs**.

---

## 2. Sources de données

### 2.1. Géographie de référence : quartiers administratifs

Le découpage spatial de référence est le jeu de données des **quartiers administratifs de Paris** publié par la Ville de Paris.  
Il permet d’agréger l’ensemble des autres données à une même échelle géographique.

**Usage dans le projet :**
- base géographique du score ;
- jointure spatiale avec les stations Vélib’, les arrêts de transport, les tronçons de trafic et les emplacements de stationnement.

---

### 2.2. Vélib’

Pour la composante vélo partagé, la source principale est le jeu **Vélib’ - emplacement des stations** publié sur l’open data parisien.  
Ce jeu permet d’identifier la **localisation des stations**, leur **capacité**.
**Variables mobilisables :**
- nombre de stations dans le quartier ;
- capacité totale des stations ;

**Rôle dans le score :** mesurer l’accessibilité à une solution de mobilité de proximité.

---

### 2.3. Trafic routier

Pour mesurer la pression automobile, deux jeux de données de la Ville de Paris sont utilisés :

- **Comptage routier - Historique - Données trafic issues des capteurs permanents** ;
- **Comptage routier - Référentiel géographique**.

Le premier contient les mesures historiques de trafic issues des capteurs permanents depuis **2010 jusqu’à l’année A-1**.  
Le second contient la géométrie des arcs routiers et permet la jointure avec les comptages via l’identifiant **`iu_ac`**.

**Variables mobilisables :**
- débit moyen annuel ;
- somme annuelle des débits ;
- pression de trafic rapportée à la longueur d’arc ou à la surface du quartier.

**Rôle dans le score :** mesurer la pression routière locale.  
Dans une logique de mobilité durable, un trafic plus élevé est interprété comme un facteur qui **dégrade** le score.

---

### 2.4. Stationnement

Pour l’offre de stationnement, deux sources peuvent être combinées :

- **Stationnement sur voie publique - emplacements** ;
- **Stationnement en ouvrage**.

Le jeu sur voie publique recense des emplacements de stationnement de différents types.  
Le jeu sur le stationnement en ouvrage recense les parcs de stationnement et leurs points d’entrée.

**Variables mobilisables :**
- nombre d’emplacements de stationnement sur voirie ;
- densité d’emplacements par km² ;
- présence de parkings en ouvrage ;
- nombre total de points de stationnement à proximité.

**Rôle dans le score :** mesurer l’offre de stationnement dans ou autour du quartier.

> Remarque : selon l’objectif de l’étude, le stationnement peut être interprété soit comme une **facilité d’accès**, soit comme un marqueur d’orientation plus automobile du quartier. Ce choix doit être explicité dans l’analyse.

---

### 2.5. Métro, bus et tramway

Pour les transports en commun, les sources utilisées proviennent d’**Île-de-France Mobilités** :

- **Arrêts et lignes associées** ;
- **Horaires prévus sur les lignes de transport en commun d’Île-de-France (GTFS)** ;
- éventuellement **Tracés des lignes de transport en commun d’Île-de-France**.

Le jeu **Arrêts et lignes associées** liste les lignes du réseau francilien et les arrêts desservis.  
Le jeu **GTFS** décrit l’offre théorique de transport sur les 30 prochains jours pour les trains, RER, métros, tramways, bus et cars franciliens.

**Variables mobilisables :**
- nombre d’arrêts dans le quartier ;
- nombre de lignes desservant le quartier ;
- présence d’un arrêt de métro ;
- présence d’un arrêt de tramway ;
- nombre de lignes de bus ;
- offre théorique de desserte.

**Rôle dans le score :** mesurer l’accessibilité aux transports collectifs, qui constitue la composante principale du score de mobilité globale.

---

## 3. Principe général de calcul

Le score repose sur plusieurs **sous-indicateurs**, calculés séparément puis agrégés :

1. **Score transports collectifs** ;
2. **Score Vélib’** ;
3. **Score stationnement** ;
4. **Score trafic**.

Chaque sous-indicateur est calculé à l’échelle du **quartier administratif** à partir d’une jointure spatiale entre les objets géographiques (stations, arrêts, arcs, emplacements) et les polygones des quartiers.

---

## 4. Construction des sous-scores

### 4.1. Sous-score transports collectifs

Le sous-score transports collectifs vise à mesurer la facilité d’accès au métro, au tram et au bus.

Exemple de variables retenues :
- nombre d’arrêts de transport collectif dans le quartier ;
- nombre de lignes différentes desservant le quartier ;
- bonus si présence de métro ;
- bonus si présence de tramway.

Exemple de formule :

\[
TC = 0.4 \times \text{nb\_arrets\_norm} + 0.3 \times \text{nb\_lignes\_norm} + 0.2 \times \text{metro\_norm} + 0.1 \times \text{tram\_norm}
\]

Le métro et le tram peuvent être davantage valorisés car ils représentent des modes plus structurants que le bus. Cette pondération relève d’un **choix méthodologique**.

---

### 4.2. Sous-score Vélib’

Le sous-score Vélib’ mesure l’accessibilité locale à la mobilité partagée à vélo.

Exemple de variables retenues :
- nombre de stations ;
- capacité totale ;
- disponibilité moyenne en vélos ;
- distance moyenne à la station la plus proche.

Exemple de formule :

\[
Velib = 0.35 \times \text{stations\_norm} + 0.25 \times \text{capacite\_norm} + 0.25 \times \text{velos\_dispo\_norm} + 0.15 \times (1 - \text{distance\_norm})
\]

Plus la densité de stations et la disponibilité sont élevées, plus le sous-score est fort.

---

### 4.3. Sous-score stationnement

Le sous-score stationnement mesure la disponibilité d’emplacements de stationnement à proximité.

Exemple de variables retenues :
- nombre d’emplacements sur voirie ;
- densité d’emplacements ;
- présence d’un parking en ouvrage.

Exemple de formule :

\[
Stationnement = 0.6 \times \text{emplacements\_norm} + 0.4 \times \text{ouvrage\_norm}
\]

Ce sous-score peut être inclus ou non selon l’orientation du projet :
- **oui** si l’on veut mesurer l’accessibilité tous modes ;
- **avec prudence** si l’on cherche un indicateur centré sur la mobilité durable.

---

### 4.4. Sous-score trafic

Le sous-score trafic mesure la pression routière dans le quartier.

Exemple de variables retenues :
- débit routier moyen annuel ;
- intensité du trafic rapportée à la longueur de voirie mesurée.

Exemple de formule :

\[
Trafic = \text{debit\_annuel\_norm}
\]

Contrairement aux autres composantes, le trafic est utilisé **en négatif** dans le score final : plus il est élevé, plus il traduit une forte pression automobile, du bruit, de la congestion et un environnement moins favorable à certaines mobilités du quotidien.

---

## 5. Normalisation des indicateurs

Les variables n’étant pas exprimées dans la même unité, elles doivent être **normalisées** avant agrégation.

Une normalisation min-max peut être utilisée :

\[
X_{norm} = 100 \times \frac{X - X_{min}}{X_{max} - X_{min}}
\]

Cette transformation permet d’obtenir pour chaque variable une valeur comprise entre **0 et 100**.

---

## 6. Formule du score global

### Option retenue : score de mobilité globale

Une formule simple et lisible peut être :

\[
Score\_mobilite = 0.45 \times TC + 0.25 \times Velib + 0.15 \times Stationnement - 0.15 \times Trafic
\]

### Interprétation
- **TC** a le poids le plus fort, car les transports collectifs structurent fortement la mobilité urbaine parisienne ;
- **Vélib’** joue un rôle important dans la mobilité locale et de courte distance ;
- **Stationnement** est pris en compte mais avec un poids plus limité ;
- **Trafic** est soustrait, car il traduit une pression routière défavorable à une mobilité fluide et apaisée.

Le score final est donc d’autant plus élevé qu’un quartier dispose :
- d’une bonne desserte en transports collectifs ;
- d’une bonne accessibilité Vélib’ ;
- d’une certaine offre de stationnement ;
- et d’un niveau de trafic relativement modéré.

---

## 7. Étapes de traitement

1. Télécharger les polygones des quartiers administratifs de Paris.  
2. Télécharger les données Vélib’, trafic, stationnement et transports collectifs.  
3. Harmoniser les systèmes de coordonnées si nécessaire.  
4. Faire une **jointure spatiale** pour rattacher chaque objet au quartier correspondant.  
5. Calculer les indicateurs bruts par quartier.  
6. Normaliser chaque indicateur sur une échelle commune.  
7. Calculer les sous-scores.  
8. Calculer le score global.

---

## 8. Limites de l’indicateur

Ce score est un **indicateur synthétique**, donc il simplifie nécessairement la réalité.  
Plusieurs limites doivent être mentionnées :

- certaines données sont **dynamiques** (Vélib’, offre théorique TC) et peuvent varier selon l’heure ou le jour ;
- les pondérations choisies relèvent d’une **décision méthodologique** et peuvent être discutées ;
- le stationnement ne reflète pas toujours une “bonne mobilité”, selon l’angle retenu ;
- le trafic mesuré dépend des capteurs disponibles et de leur couverture spatiale.

Il peut donc être utile de produire en complément :
- le **score global** ;
- mais aussi les **sous-scores séparés** pour mieux interpréter les différences entre quartiers.

---

## 9. Résultat attendu

Le résultat final est un tableau du type :

| quartier | score_mobilite | score_tc | score_velib | score_stationnement | score_trafic |
|----------|----------------|----------|-------------|---------------------|--------------|

Ce tableau peut ensuite être cartographié pour comparer les niveaux de mobilité entre quartiers administratifs parisiens.

---

## 10. Références de données

- Ville de Paris — quartiers administratifs, Vélib’, comptages routiers, stationnement.
- Île-de-France Mobilités — arrêts et lignes associées.
- Île-de-France Mobilités — offre théorique GTFS.