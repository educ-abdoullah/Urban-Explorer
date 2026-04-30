# Data Catalog — Urban Data Explorer

## Vue d'ensemble

Le projet mobilise **11 sources de données ouvertes** issues de quatre producteurs principaux : la Ville de Paris, l'INSEE, Île-de-France Mobilités et data.gouv.fr. Toutes les sources sont en licence ouverte (Etalab / ODbL). Le millésime de référence est **2022–2025** selon les indicateurs.

---

## 1. Demandes de Valeurs Foncières (DVF)

| Champ | Détail |
|---|---|
| **Producteur** | Direction générale des Finances publiques (DGFiP) |
| **URL** | https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres |
| **Licence** | Licence Ouverte Etalab 2.0 |
| **Format** | CSV |
| **Maille géographique** | Parcelle cadastrale |
| **Millésime utilisé** | 2022 |
| **Variables clés** | prix de vente, surface, type de bien, localisation |

**Rôle dans le projet :** calcul du prix au m² médian, du rendement brut et de la liquidité (nombre de transactions) pour le **Score Investissement**. Agrégé à la maille IRIS et arrondissement.

**Justification du choix :** seule source publique exhaustive recensant l'ensemble des transactions immobilières notariées en France. Granularité parcellaire permettant une agrégation fine à l'IRIS.

---

## 2. Loyers médians (Observatoires Locaux des Loyers)

| Champ | Détail |
|---|---|
| **Producteur** | Observatoires Locaux des Loyers / DRIHL |
| **URL** | https://www.data.gouv.fr/organizations/observatoires-locaux-des-loyers |
| **Licence** | Licence Ouverte Etalab 2.0 |
| **Format** | CSV |
| **Maille géographique** | Zone OLAP (infra-arrondissement) |
| **Millésime utilisé** | 2022 |
| **Variables clés** | loyer médian au m², segmentation géographique |

**Rôle dans le projet :** estimation du revenu locatif théorique (`loyer_m2_median × 35` pour un 35 m²), calcul du `taux_effort` et du `score_affordability`. Utilisé dans le **Score Investissement** et le pipeline d'accessibilité financière.

**Justification du choix :** données collectées par des observatoires agréés, plus fiables que les annonces en ligne pour représenter les loyers réels du marché. Seule source publique offrant une segmentation infra-arrondissement à Paris.

---

## 3. Population (INSEE — Recensement)

| Champ | Détail |
|---|---|
| **Producteur** | INSEE |
| **URL** | https://catalogue-donnees.insee.fr |
| **Licence** | Licence Ouverte Etalab 2.0 |
| **Format** | CSV |
| **Maille géographique** | IRIS |
| **Millésime utilisé** | 2022 |
| **Variables clés** | population totale, ventilation par sexe et tranche d'âge (0–14, 15–29, 30–44, 45–59, 60–74, 75+) |

**Rôle dans le projet :** normalisation des indicateurs de densité (criminalité, liquidité, pression locative), calcul de la demande locative. Présent dans le **Score Investissement** et les sorties Gold IRIS (`population_hommes`, `population_femmes`, `population_0_14`, etc.).

**Justification du choix :** source de référence officielle pour la démographie française. La maille IRIS permet une granularité fine et cohérente avec les autres données géographiques du projet.

---

## 4. Criminalité (Bases statistiques de la délinquance)

| Champ | Détail |
|---|---|
| **Producteur** | Ministère de l'Intérieur / Préfecture de Police |
| **URL** | https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance |
| **Complémentaire** | https://opendata.paris.fr — "Dans ma rue" (signalements urbains) |
| **Licence** | Licence Ouverte Etalab 2.0 |
| **Format** | CSV |
| **Maille géographique** | Arrondissement |
| **Millésime utilisé** | 2022–2023 |
| **Variables clés** | faits de délinquance enregistrés, signalements d'incivilités |

**Rôle dans le projet :** calcul du `taux_criminalite` (faits / population) et de son inverse `score_securite`. Composante à 25 % du **Score Investissement** et score dédié `score_criminalite` dans les sorties Gold.

**Justification du choix :** données officielles enregistrées par les forces de l'ordre. Le dataset "Dans ma rue" complète avec des signalements citoyens pour capter les nuisances non criminelles. Limite connue : la maille arrondissement est moins fine que l'IRIS.

---

## 5. Stations et capacité Vélib'

| Champ | Détail |
|---|---|
| **Producteur** | Ville de Paris / Smovengo |
| **URL** | https://opendata.paris.fr |
| **Licence** | ODbL (Open Database Licence) |
| **Format** | GeoJSON / CSV |
| **Maille géographique** | Point géolocalisé |
| **Millésime utilisé** | 2025 (données temps réel archivées) |
| **Variables clés** | localisation station, capacité totale, nombre de stations |

**Rôle dans le projet :** calcul du `score_velib` (0.5 × stations normalisées + 0.5 × capacité normalisée). Composante du **Score Mobilité**.

**Justification du choix :** seule source officielle exhaustive des stations Vélib' à Paris. La capacité est retenue en plus du simple comptage car elle reflète mieux l'offre réelle de mobilité partagée.

---

## 6. Trafic routier (Capteurs permanents)

| Champ | Détail |
|---|---|
| **Producteur** | Ville de Paris — Direction de la Voirie et des Déplacements |
| **URL** | https://opendata.paris.fr |
| **Licence** | ODbL |
| **Format** | CSV + GeoJSON (référentiel géographique) |
| **Maille géographique** | Arc routier (tronçon) |
| **Millésime utilisé** | 2025 |
| **Variables clés** | débit moyen, occupation moyenne, identifiant arc (`iu_ac`) |

**Rôle dans le projet :** calcul du `score_trafic_inverse` — le trafic est utilisé **en négatif** dans le Score Mobilité (forte pression automobile = score dégradé). Jointure spatiale avec les polygones de quartiers via l'identifiant `iu_ac`.

**Justification du choix :** données issues de capteurs permanents, plus fiables que des estimations modélisées. L'interprétation inverse (trafic élevé = mobilité dégradée) est cohérente avec une logique de mobilité durable.

---

## 7. Stationnement (Voirie et ouvrages)

| Champ | Détail |
|---|---|
| **Producteur** | Ville de Paris |
| **URL** | https://opendata.paris.fr |
| **Licence** | ODbL |
| **Format** | GeoJSON |
| **Maille géographique** | Point / polygone géolocalisé |
| **Millésime utilisé** | 2024–2025 |
| **Variables clés** | emplacements sur voirie, parkings en ouvrage, densité au km² |

**Rôle dans le projet :** calcul du `score_stationnement` (densité d'emplacements normalisée). Composante du **Score Mobilité**.

**Justification du choix :** deux jeux combinés (voirie + ouvrages) pour une vision complète de l'offre. Limite : le stationnement peut être interprété soit comme une facilité d'accès, soit comme un marqueur d'orientation automobile — ce choix est documenté dans la méthodologie du Score Mobilité.

---

## 8. Arrêts et lignes de transport (Île-de-France Mobilités)

| Champ | Détail |
|---|---|
| **Producteur** | Île-de-France Mobilités |
| **URL** | https://data.iledefrance-mobilites.fr |
| **Licence** | ODbL |
| **Format** | CSV / GTFS |
| **Maille géographique** | Point géolocalisé |
| **Millésime utilisé** | 2025 |
| **Variables clés** | localisation des arrêts, lignes desservies (métro, bus, tram, RER) |

**Rôle dans le projet :** calcul du `score_transport_commun` (nombre d'arrêts par quartier normalisé). Composante à 40 % du **Score Mobilité** — poids le plus élevé, reflétant le rôle structurant des transports collectifs dans la mobilité parisienne.

**Justification du choix :** source de référence officielle du réseau francilien. Le GTFS permet de croiser l'offre théorique (fréquences, horaires) au-delà du simple comptage d'arrêts.

---

## 9. Espaces verts et arbres d'alignement

| Champ | Détail |
|---|---|
| **Producteur** | Ville de Paris / IAU Île-de-France |
| **URL** | https://opendata.paris.fr |
| **Licence** | ODbL |
| **Format** | GeoJSON (polygones espaces verts) + CSV (arbres géolocalisés) |
| **Maille géographique** | Polygone / point géolocalisé |
| **Millésime utilisé** | 2023–2024 |
| **Variables clés** | surface, catégorie et type d'espace vert (`categorie`, `type_ev`), circonférence des arbres |

**Rôle dans le projet :** calcul de l'**IMVU** (Indice de Morphologie Végétale Urbaine) avec trois composantes — Taux de Couverture Pondéré (TCP), Volume de Canopée des Rues (DC), et Diversité végétale (jardins partagés). Alimentent les scores `score_vegetation`, `score_parcs`, `score_rues_vegetalisees` et `score_initiatives_vertes`.

**Justification du choix :** les attributs `categorie` et `type_ev` permettent une pondération qualitative (bois λ=1.0, squares λ=0.8, cimetières λ=0.4) plutôt qu'un simple comptage de surface. La circonférence des arbres permet d'estimer la canopée réelle plutôt que de compter les individus.

---

## 10. Équipements PAFS (Santé, Éducation, Sport, Commerces, Bruit)

| Source | Producteur | URL | Variables clés | Score concerné |
|---|---|---|---|---|
| **BDCOM Apur** | Apur | https://opendata.apur.org | restaurants, cafés, commerces de bouche | `score_vibrance`, `score_services_quartier` |
| **RES (Data ES)** | Ministère des Sports | https://data.gouv.fr | équipements sportifs géolocalisés | `score_sport` |
| **FINESS** | Ministère de la Santé | https://www.data.gouv.fr | pharmacies, centres de santé, hôpitaux | `score_sante` |
| **Secteurs scolaires** | IAU Île-de-France | https://data-iau-idf.opendata.arcgis.com | écoles primaires, collèges, lycées | `score_education` |
| **Bruitparif** | Bruitparif | https://www.bruitparif.fr | niveaux sonores par zone | `score_bruit_inverse` |

**Rôle dans le projet :** ces cinq sources alimentent le **Paris Age-Friendly Score (PAFS)** avec des pondérations différenciées selon le profil utilisateur (Junior, Jeune Adulte, Actif, Senior). Le bruit est utilisé en négatif (`score_bruit_inverse`).

**Justification du choix :** chaque source est la référence officielle pour sa catégorie d'équipements. La combinaison permet de couvrir les quatre dimensions du cadre de vie urbain sans recourir à des données privées ou des proxies approximatifs.

---

## 11. Logements vacants

| Champ | Détail |
|---|---|
| **Producteur** | DGALN / SDES |
| **URL** | https://www.data.gouv.fr/datasets/logements-vacants-du-parc-prive-par-commune |
| **Licence** | Licence Ouverte Etalab 2.0 |
| **Format** | CSV |
| **Maille géographique** | Commune |
| **Millésime utilisé** | 2022 |
| **Variables clés** | taux de vacance du parc privé |

**Rôle dans le projet :** ajustement de la demande locative dans le **Score Investissement** (`demande_locative = population / nb_logements × (1 − taux_vacance)`).

**Justification du choix :** indicateur indispensable pour ne pas surestimer la tension locative dans des zones où une part du parc est inoccupée. Limite : maille communale uniquement, pas de déclinaison IRIS disponible.

---

## Synthèse des sources par score

| Score | Sources principales |
|---|---|
| **Score Investissement** | DVF, Loyers OLL, Population INSEE, Criminalité, Logements vacants |
| **Score Mobilité** | Vélib', Trafic routier, Stationnement, Arrêts IDFM |
| **Score Environnement (IMVU)** | Espaces verts Paris, Arbres d'alignement, Jardins partagés |
| **Score Age-Friendly (PAFS)** | BDCOM Apur, RES, FINESS, Secteurs scolaires, Bruitparif |
| **Score Urbain Global** | Agrégation pondérée des quatre scores ci-dessus |

---

## Limites transversales

- **Hétérogénéité des mailles** : certaines sources (criminalité, logements vacants) ne descendent pas en dessous de l'arrondissement, ce qui contraint la précision des scores IRIS pour ces composantes.
- **Millésimes différents** : les données couvrent 2022 à 2025 selon les sources — les comparaisons inter-indicateurs supposent une relative stabilité structurelle sur cette période.
- **Pondérations méthodologiques** : les poids choisis dans chaque score (ex : 50 % rendement dans le Score Investissement, 40 % TC dans le Score Mobilité) relèvent de choix délibérés documentés dans les fichiers `scores/`. Ils peuvent être discutés et ajustés.
- **Données dynamiques** : Vélib' et l'offre TC varient selon l'heure et le jour — les valeurs utilisées correspondent à des agrégats ou des snapshots archivés.
