const RankingPage = (() => {
  const INDICATOR_OPTIONS = {
    expensive: "Zones les plus chères",
    cheapest: "Zones les moins chères",
    prix_m2_median: "Prix médian au m²",
    loyer_m2_median: "Meilleurs loyers au m²",
    rendement_net_pct: "Meilleurs rendements nets",
    score_accessibilite_logement: "Accessibilité logement",
    score_logement_social: "Logement social",
    taux_effort: "Taux d’effort le plus faible",
    taux_effort_high: "Taux d’effort le plus élevé",
    loyer_theorique_35m2_low: "Loyer 35 m² le plus faible",
    median_income_monthly_uc: "Revenu médian le plus élevé",
    nb_logmt_total: "Nombre total de logements",
    nb_appartements: "Appartements",
    nb_maisons: "Maisons",
    nb_1_piece: "Studios",
    nb_2_pieces: "Logements 2 pièces",
    nb_3_pieces: "Logements 3 pièces",
    nb_logements_familiaux: "Logements familiaux",
    score_urbain_global: "Score urbain global",
    score_investissement: "Score investissement",
    score_liquidite: "Liquidité",
    nb_mutations: "Nombre de mutations",
    score_securite: "Meilleure sécurité",
    score_environnement: "Meilleur environnement",
    score_mobilite: "Meilleure mobilité",
    score_services_quartier: "Meilleurs services de quartier",
    score_criminalite: "Criminalité la plus élevée",
    low_security: "Sécurité la plus faible",
    expensive_low_yield: "Prix élevé avec rendement faible",
    crowded_housing: "Forte population avec peu de logements",
    score_jeune_adulte: "Meilleur profil jeunes adultes",
    score_actifs: "Meilleur profil actifs",
    score_senior: "Meilleur profil seniors",
    score_junior: "Meilleur profil juniors"
  };

  const SORT_DIRECTIONS = {
    taux_effort: "asc",
    cheapest: "asc",
    loyer_theorique_35m2_low: "asc",
    low_security: "asc"
  };

  const FIELD_ALIASES = {
    expensive: "prix_m2_median",
    cheapest: "prix_m2_median",
    taux_effort_high: "taux_effort",
    loyer_theorique_35m2_low: "loyer_theorique_35m2",
    low_security: "score_securite"
  };

  let currentField = "prix_m2_median";
  let currentTop = 10;
  let cachedRows = [];

  async function init() {
    populateIndicators();
    bindEvents();
    cachedRows = await Api.getAreas("arrondissement", false);
    await renderDecisionCards();
    await renderRanking();
  }

  function populateIndicators(query = "") {
    const select = document.getElementById("ranking-indicator");
    const normalized = normalize(query);
    const entries = Object.entries(INDICATOR_OPTIONS)
      .filter(([field, label]) => !normalized || normalize(`${field} ${label} ${UI.label(displayField(field))}`).includes(normalized));
    select.innerHTML = entries
      .map(([field, label]) => `<option value="${field}">${label}</option>`)
      .join("");
    if (entries.some(([field]) => field === currentField)) {
      select.value = currentField;
    } else if (entries[0]) {
      currentField = entries[0][0];
      select.value = currentField;
      renderRanking();
    }
  }

  function bindEvents() {
    document.getElementById("ranking-indicator").addEventListener("change", async event => {
      currentField = event.target.value;
      await renderRanking();
    });

    document.getElementById("ranking-top").addEventListener("change", async event => {
      currentTop = Number(event.target.value);
      await renderRanking();
    });
    document.getElementById("ranking-search").addEventListener("input", event => {
      populateIndicators(event.target.value);
    });
  }

  async function renderDecisionCards() {
    const container = document.getElementById("decision-cards");
    const fields = ["prix_m2_median", "score_urbain_global", "score_accessibilite_logement"];
    const cards = fields.map(field => {
      const first = getRankedRows(field, 1)[0];
      const value = getValue(first, field);
      const progress = progressForField(value, field);
      const zoneName = first?.area_name || "Aucune zone";
      return `
        <article class="decision-card neutral">
          <div class="decision-card-top">
            <span>${UI.label(field)}</span>
            <em>${zoneName}</em>
          </div>
          <strong>${first ? UI.formatValue(value, displayField(field)) : "Donnée indisponible"}</strong>
          <div class="score-track"><span style="width:${progress}%;background:${UI.scoreColor(displayField(field))}"></span></div>
        </article>
      `;
    });
    container.innerHTML = cards.join("");
  }

  async function renderRanking() {
    const tbody = document.getElementById("ranking-table-body");
    tbody.innerHTML = `<tr><td colspan="5">Chargement</td></tr>`;

    try {
      const rows = getRankedRows(currentField, currentTop);
      tbody.innerHTML = rows.map((row, index) => {
        const value = getValue(row, currentField);
        const progress = progressForField(value, currentField);
        const visualField = displayField(currentField);
        return `
          <tr class="${index < 3 ? `top-row top-${index + 1}` : ""}">
            <td><span class="rank-medal">${index + 1}</span></td>
            <td><strong>${row.area_name}</strong><small>${row.year ?? row.properties?.annee ?? ""}</small></td>
            <td>${INDICATOR_OPTIONS[currentField]}</td>
            <td><span class="value-badge neutral">${UI.formatValue(value, visualField)}</span></td>
            <td><div class="ranking-progress"><span style="width:${progress}%;background:${UI.scoreColor(visualField)}"></span></div></td>
          </tr>
        `;
      }).join("");
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="5">${error.message}</td></tr>`;
    }
  }

  function getRankedRows(field, top) {
    const sorted = latestByArea(cachedRows).sort((a, b) => {
      const aValue = Number(getValue(a, field));
      const bValue = Number(getValue(b, field));
      if (!Number.isFinite(aValue) && !Number.isFinite(bValue)) return 0;
      if (!Number.isFinite(aValue)) return 1;
      if (!Number.isFinite(bValue)) return -1;
      return SORT_DIRECTIONS[field] === "asc" ? aValue - bValue : bValue - aValue;
    });
    return sorted.slice(0, top);
  }

  function latestByArea(rows) {
    const map = new Map();
    rows.forEach(row => {
      const key = String(row.area_id);
      const year = Number(row.year ?? row.properties?.annee) || 0;
      const currentYear = Number(map.get(key)?.year ?? map.get(key)?.properties?.annee) || 0;
      if (!map.has(key) || year >= currentYear) map.set(key, row);
    });
    return [...map.values()];
  }

  function progressForField(value, field) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    if (SCORE_FIELDS.has(displayField(field))) return Math.max(0, Math.min(100, number));

    const rows = latestByArea(cachedRows).map(row => Number(getValue(row, field))).filter(Number.isFinite);
    if (!rows.length) return 0;
    const min = Math.min(...rows);
    const max = Math.max(...rows);
    if (max === min) return 100;
    const normalized = (number - min) / (max - min) * 100;
    return SORT_DIRECTIONS[field] === "asc" ? 100 - normalized : normalized;
  }

  function getValue(row, field) {
    if (!row) return null;
    const props = row.properties || {};
    if (field === "nb_logements_familiaux") return toNumber(props.nb_4_pieces) + toNumber(props.nb_5_pieces_plus);
    if (field === "expensive_low_yield") return toNumber(props.prix_m2_median) - toNumber(props.rendement_net_pct) * 1000;
    if (field === "crowded_housing") return toNumber(props.population) / Math.max(1, toNumber(props.nb_logmt_total));
    return props[FIELD_ALIASES[field] || field];
  }

  function displayField(field) {
    if (field === "expensive" || field === "cheapest") return "prix_m2_median";
    if (field === "taux_effort_high") return "taux_effort";
    if (field === "loyer_theorique_35m2_low") return "loyer_theorique_35m2";
    if (field === "low_security") return "score_securite";
    if (field === "expensive_low_yield") return "prix_m2_median";
    if (field === "crowded_housing") return "population";
    return field;
  }

  function toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function normalize(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", RankingPage.init);
