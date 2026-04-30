const API_BASE_URL = "http://localhost:8000";

const MAPBOX_TOKEN = "test";

const DEFAULT_STATE = {
  level: "arrondissement",
  year: 2024,
  colorIndicator: "score_urbain_global",
  circleIndicator: "score_mobilite",
  mapStyle: "warm",
  polygonPalette: "urbanDynamic",
  circleColor: "yellow"
};

const PARIS_VIEW = {
  center: [2.3522, 48.8566],
  zoom: 11.2,
  bounds: [[2.224, 48.815], [2.47, 48.902]]
};

const MAP_STYLES = {
  warm: { label: "Beige clair", url: "mapbox://styles/mapbox/light-v11", swatch: "#f4ead8", warm: true },
  light: { label: "Clair", url: "mapbox://styles/mapbox/light-v11", swatch: "#f8fafc" },
  neutral: { label: "Neutre", url: "mapbox://styles/mapbox/streets-v12", swatch: "#d6d3d1" },
  dark: { label: "Sombre", url: "mapbox://styles/mapbox/dark-v11", swatch: "#1f2937" }
};

const POLYGON_PALETTES = {
  parisScore: { label: "Score parisien", colors: ["#D73027", "#FEE08B", "#1A9850"] },
  youngInvestor: { label: "Jeune investisseur", colors: ["#EFE7FF", "#F97316", "#1E1B4B"] },
  familyProfile: { label: "Famille", colors: ["#F8E7C8", "#F4A261", "#7F1D1D"] },
  seniorProfile: { label: "Senior", colors: ["#FFE5E5", "#F4A261", "#2A9D8F"] },
  profitability: { label: "Rentabilité", colors: ["#FFF4E6", "#FF8C42", "#7A2E0E"] },
  ecology: { label: "Écologie", colors: ["#F5F0E1", "#A7C957", "#1B5E20"] },
  urbanDynamic: { label: "Dynamique urbain", colors: ["#E5E7EB", "#22D3EE", "#0D47A1"] },
  investment: { label: "Investissement", colors: ["#EDE9FE", "#F97316", "#0B132B"] },
  accessibility: { label: "Accessibilité", colors: ["#FCE7F3", "#9B5DE5", "#312E81"] },
  socialHousing: { label: "Logement social", colors: ["#FEF3C7", "#2EC4B6", "#005F73"] },
  mobility: { label: "Mobilité", colors: ["#E5E7EB", "#22D3EE", "#0D47A1"] },
  blue: { label: "Bleu premium", colors: ["#dbeafe", "#60a5fa", "#1e3a8a"] },
  teal: { label: "Bleu vert", colors: ["#ccfbf1", "#2dd4bf", "#0f766e"] },
  violet: { label: "Violet sobre", colors: ["#ede9fe", "#a78bfa", "#5b21b6"] },
  slate: { label: "Neutre professionnel", colors: ["#f1f5f9", "#94a3b8", "#334155"] }
};

const CIRCLE_COLORS = {
  green: { label: "Vert", value: "#10b981" },
  blue: { label: "Bleu", value: "#2563eb" },
  violet: { label: "Violet", value: "#7c3aed" },
  slate: { label: "Ardoise", value: "#475569" },
  orange: { label: "Orange", value: "#FF6B35" },
  turquoise: { label: "Turquoise", value: "#2EC4B6" },
  pink: { label: "Rose", value: "#F15BB5" },
  amber: { label: "Ambre", value: "#FFB703" },
  lime: { label: "Vert clair", value: "#A3D977" },
  yellow: { label: "Jaune", value: "#FFC857" },
  coral: { label: "Corail", value: "#EF476F" },
  redOrange: { label: "Rouge orange", value: "#EE6C4D" },
  navy: { label: "Bleu nuit", value: "#1D3557" }
};

const ANALYSIS_PRESETS = {
  youngInvestor: {
    label: "Investisseur jeune actif",
    description: "Repérer les zones attractives pour un jeune actif investisseur.",
    colorIndicator: "score_investissement",
    circleIndicator: "score_jeune_adulte",
    polygonPalette: "youngInvestor",
    circleColor: "orange",
    rankingFields: ["score_investissement", "score_jeune_adulte", "rendement_net_pct", "nb_mutations"],
    chartFields: ["prix_m2_median", "rendement_net_pct", "score_investissement", "score_jeune_adulte"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  familyProfile: {
    label: "Famille",
    description: "Identifier les zones adaptées aux familles et aux logements plus grands.",
    colorIndicator: "score_junior",
    circleIndicator: "nb_logements_familiaux",
    polygonPalette: "familyProfile",
    circleColor: "coral",
    rankingFields: ["score_junior", "score_services_quartier", "nb_logements_familiaux"],
    chartFields: ["score_junior", "score_services_quartier", "nb_4_pieces", "nb_5_pieces_plus"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  seniorProfile: {
    label: "Senior",
    description: "Comparer sécurité, accessibilité et confort urbain pour les seniors.",
    colorIndicator: "score_senior",
    circleIndicator: "score_securite",
    polygonPalette: "seniorProfile",
    circleColor: "navy",
    rankingFields: ["score_senior", "score_securite", "score_accessibilite_logement"],
    chartFields: ["score_senior", "score_securite", "score_accessibilite_logement"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  pureProfitability: {
    label: "Rentabilité pure",
    description: "Trouver les zones avec le meilleur rendement locatif.",
    colorIndicator: "score_rendement",
    circleIndicator: "rendement_net_pct",
    polygonPalette: "profitability",
    circleColor: "turquoise",
    rankingFields: ["score_rendement", "rendement_net_pct", "prix_m2_median"],
    chartFields: ["rendement_net_pct", "loyer_m2_median", "prix_m2_median"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  ecological: {
    label: "Écologique",
    description: "Visualiser le cadre de vie environnemental.",
    colorIndicator: "score_environnement",
    circleIndicator: "nb_arbres_alignement",
    polygonPalette: "ecology",
    circleColor: "lime",
    rankingFields: ["score_environnement", "score_vegetation", "nb_arbres_alignement"],
    chartFields: ["score_environnement", "score_vegetation", "nb_arbres_alignement"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  urbanDynamic: {
    label: "Dynamique urbain",
    description: "Analyser les zones animées, mobiles et bien équipées.",
    colorIndicator: "score_urbain_global",
    circleIndicator: "score_mobilite",
    polygonPalette: "urbanDynamic",
    circleColor: "yellow",
    rankingFields: ["score_urbain_global", "score_mobilite", "score_services_quartier"],
    chartFields: ["score_urbain_global", "score_mobilite", "score_services_quartier", "nb_mutations"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  investment: {
    label: "Investissement locatif",
    description: "Repérer les zones attractives pour investir.",
    colorIndicator: "score_investissement",
    circleIndicator: "rendement_net_pct",
    polygonPalette: "investment",
    circleColor: "orange",
    rankingFields: ["score_investissement", "rendement_net_pct", "nb_mutations"],
    chartFields: ["prix_m2_median", "rendement_net_pct", "score_investissement", "nb_mutations"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  accessibility: {
    label: "Accessibilité logement",
    description: "Comprendre où le logement est le plus accessible.",
    colorIndicator: "score_accessibilite_logement",
    circleIndicator: "taux_effort",
    polygonPalette: "accessibility",
    circleColor: "pink",
    rankingFields: ["score_accessibilite_logement", "taux_effort", "median_income_monthly_uc"],
    chartFields: ["score_accessibilite_logement", "taux_effort", "median_income_monthly_uc", "loyer_theorique_35m2"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  },
  socialHousing: {
    label: "Logement social",
    description: "Visualiser la présence du logement social et le volume de logements.",
    colorIndicator: "score_logement_social",
    circleIndicator: "nb_logmt_total",
    polygonPalette: "socialHousing",
    circleColor: "amber",
    rankingFields: ["score_logement_social", "nb_logmt_total", "nb_appartements"],
    chartFields: ["score_logement_social", "nb_logmt_total", "nb_appartements", "nb_maisons"],
    popupFields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"]
  }
};

const INDICATORS = [
  "score_urbain_global",
  "score_investissement",
  "score_accessibilite_logement",
  "score_logement_social",
  "score_rendement",
  "score_securite",
  "score_criminalite",
  "score_liquidite",
  "score_environnement",
  "score_vegetation",
  "score_mobilite",
  "score_services_quartier",
  "score_jeune_adulte",
  "score_actifs",
  "score_senior",
  "score_junior",
  "prix_m2_median",
  "loyer_m2_median",
  "rendement_net_pct",
  "median_income_monthly_uc",
  "loyer_theorique_35m2",
  "taux_effort",
  "population",
  "nb_logmt_total",
  "nb_logements_dvf",
  "nb_appartements",
  "nb_maisons",
  "nb_logements_familiaux",
  "nb_mutations"
];

const CIRCLE_INDICATORS = [
  "none",
  "prix_m2_median",
  "population",
  "nb_mutations",
  "rendement_net_pct",
  "score_investissement",
  "score_accessibilite_logement",
  "score_logement_social",
  "score_urbain_global",
  "score_mobilite",
  "score_jeune_adulte",
  "score_actifs",
  "score_senior",
  "score_junior",
  "nb_stations_velib",
  "nb_arrets_transport",
  "nb_logmt_total",
  "nb_appartements",
  "nb_logements_familiaux"
];

const COMPARISON_FIELDS = [
  "score_urbain_global",
  "score_investissement",
  "score_accessibilite_logement",
  "score_logement_social",
  "score_jeune_adulte",
  "score_actifs",
  "score_senior",
  "score_junior",
  "prix_m2_median",
  "loyer_m2_median",
  "rendement_net_pct",
  "taux_effort",
  "score_securite",
  "population",
  "nb_logmt_total",
  "nb_appartements",
  "nb_logements_familiaux",
  "nb_maisons",
  "nb_mutations"
];

const TREND_FIELDS = [
  "prix_m2_median",
  "loyer_m2_median",
  "score_urbain_global",
  "score_investissement",
  "score_accessibilite_logement",
  "score_logement_social",
  "score_jeune_adulte",
  "score_actifs",
  "score_senior",
  "score_junior",
  "taux_effort",
  "population",
  "nb_logmt_total",
  "nb_appartements",
  "nb_maisons",
  "nb_1_piece",
  "nb_2_pieces",
  "nb_3_pieces",
  "nb_4_pieces",
  "nb_5_pieces_plus"
];

const SCORE_FIELDS = new Set([
  "score_urbain_global",
  "score_investissement",
  "score_accessibilite_logement",
  "score_logement_social",
  "score_rendement",
  "score_securite",
  "score_criminalite",
  "score_liquidite",
  "score_environnement",
  "score_vegetation",
  "score_parcs",
  "score_rues_vegetalisees",
  "score_initiatives_vertes",
  "score_mobilite",
  "score_velib",
  "score_stationnement",
  "score_transport_commun",
  "score_trafic_inverse",
  "score_services_quartier",
  "score_sante",
  "score_education",
  "score_sport",
  "score_vibrance",
  "score_bruit_inverse",
  "score_senior",
  "score_actifs",
  "score_jeune_adulte",
  "score_junior"
]);

const SCORE_COLORS = {
  score_urbain_global: "#3A86FF",
  score_investissement: "#2A9D8F",
  score_mobilite: "#8338EC",
  score_environnement: "#80ED99",
  score_logement_social: "#F4A261",
  score_accessibilite_logement: "#00B4D8",
  score_securite: "#E63946",
  score_liquidite: "#FFBE0B",
  score_rendement: "#F97316",
  score_criminalite: "#D73027",
  score_vegetation: "#52B788",
  score_services_quartier: "#6D597A",
  score_senior: "#8B5CF6",
  score_actifs: "#2A9D8F",
  score_jeune_adulte: "#3A86FF",
  score_junior: "#F4A261"
};

const FIELD_LABELS = {
  year: "Année",
  profil_ideal: "Profil dominant",
  score_urbain_global: "Score urbain global",
  score_investissement: "Score investissement",
  score_accessibilite_logement: "Accessibilité logement",
  score_logement_social: "Logement social",
  score_rendement: "Score rendement",
  score_criminalite: "Score criminalité",
  score_securite: "Score sécurité",
  score_liquidite: "Score liquidité",
  score_environnement: "Score environnement",
  score_vegetation: "Score végétation",
  score_parcs: "Score parcs",
  score_rues_vegetalisees: "Score rues végétalisées",
  score_initiatives_vertes: "Score initiatives vertes",
  score_mobilite: "Score mobilité",
  score_velib: "Score Vélib",
  score_stationnement: "Score stationnement",
  score_transport_commun: "Score transport",
  score_trafic_inverse: "Score trafic inverse",
  score_services_quartier: "Score services quartier",
  score_sante: "Score santé",
  score_education: "Score éducation",
  score_sport: "Score sport",
  score_vibrance: "Score dynamisme",
  score_bruit_inverse: "Score bruit inverse",
  score_senior: "Seniors",
  score_actifs: "Actifs",
  score_jeune_adulte: "Jeunes adultes",
  score_junior: "Juniors",
  prix_m2_median: "Prix médian au m²",
  prix_m2_moyen: "Prix moyen au m²",
  loyer_m2_median: "Loyer médian au m²",
  rendement_brut_pct: "Rendement brut",
  rendement_net_pct: "Rendement net",
  median_income_monthly_uc: "Revenu médian mensuel",
  loyer_theorique_35m2: "Loyer théorique 35 m²",
  taux_effort: "Taux d’effort",
  nb_logmt_total: "Nombre total de logements",
  nb_logements_dvf: "Logements DVF",
  nb_appartements: "Appartements",
  nb_maisons: "Maisons",
  nb_logements_familiaux: "Logements familiaux",
  nb_1_piece: "Logements 1 pièce",
  nb_2_pieces: "Logements 2 pièces",
  nb_3_pieces: "Logements 3 pièces",
  nb_4_pieces: "Logements 4 pièces",
  nb_5_pieces_plus: "Logements 5 pièces et plus",
  nb_mutations: "Mutations",
  population: "Population",
  arrondissement: "Arrondissement",
  nom_quartier: "Quartier",
  nb_stations_velib: "Stations Vélib",
  nb_arrets_transport: "Arrêts de transport",
  stationnement_total: "Stationnement total",
  surface: "Surface",
  densite_population: "Densité de population"
};

const FIELD_UNITS = {
  prix_m2_median: "€/m²",
  prix_m2_moyen: "€/m²",
  loyer_m2_median: "€/m²",
  median_income_monthly_uc: "€",
  loyer_theorique_35m2: "€",
  taux_effort: "%",
  rendement_brut_pct: "%",
  rendement_net_pct: "%",
  ratio_parcs_pct: "%",
  ratio_canopee_pct: "%"
};

const FIELD_TOOLTIPS = {
  score_urbain_global: "Score global qui combine investissement, environnement, mobilité et services de quartier.",
  score_investissement: "Score basé sur le rendement estimé, la sécurité et la liquidité du marché.",
  score_accessibilite_logement: "Score indiquant le niveau d’accessibilité du logement dans la zone.",
  score_logement_social: "Score lié à la présence ou au poids du logement social.",
  score_rendement: "Score basé sur le rendement net estimé.",
  score_securite: "Score inverse du score de criminalité.",
  score_criminalite: "Score relatif de criminalité. Plus il est élevé, plus l’indice est fort.",
  score_liquidite: "Score basé sur le nombre de mutations immobilières.",
  score_environnement: "Score lié aux espaces verts, arbres, parcs et initiatives végétales.",
  score_mobilite: "Score lié aux transports, Vélib, stationnement et trafic.",
  score_services_quartier: "Score lié aux services, santé, éducation, sport et dynamisme.",
  score_senior: "Score indiquant l’adéquation de la zone avec un profil senior.",
  score_actifs: "Score indiquant l’adéquation de la zone avec un profil actif.",
  score_jeune_adulte: "Score indiquant l’adéquation de la zone avec un profil jeune adulte.",
  score_junior: "Score indiquant l’adéquation de la zone avec un profil junior ou familial.",
  prix_m2_median: "Prix de vente médian au mètre carré.",
  loyer_m2_median: "Loyer médian au mètre carré.",
  rendement_net_pct: "Rendement locatif estimé après charges.",
  median_income_monthly_uc: "Revenu médian mensuel par unité de consommation.",
  loyer_theorique_35m2: "Loyer théorique estimé pour un logement de 35 m².",
  taux_effort: "Part du revenu nécessaire pour payer le loyer."
};
