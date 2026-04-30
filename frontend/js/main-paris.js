const ParisPage = (() => {
  const state = { rows: [], charts: [] };
  const COLORS = ["#3A86FF", "#2A9D8F", "#F4A261", "#8338EC", "#00B4D8", "#FFBE0B", "#E63946", "#80ED99"];

  const BEST_FIELDS = [
    "score_investissement",
    "rendement_net_pct",
    "score_accessibilite_logement",
    "score_securite",
    "score_environnement",
    "score_mobilite",
    "score_urbain_global"
  ];

  const GLOBAL_CHARTS = [
    { id: "prix-medians", title: "Prix médians au m² par arrondissement", subtitle: "Lecture directe du niveau de prix", type: "bar", fields: ["prix_m2_median"] },
    { id: "loyer-prix", title: "Loyer médian vs prix médian", subtitle: "Comparaison loyers et prix de vente", type: "bar", fields: ["loyer_m2_median", "prix_m2_median"] },
    { id: "rendement-net", title: "Rendement net par arrondissement", subtitle: "Potentiel locatif estimé", type: "bar", fields: ["rendement_net_pct"] },
    { id: "nombre-mutations", title: "Nombre de mutations par arrondissement", subtitle: "Volume de transactions observé", type: "bar", fields: ["nb_mutations"] },
    { id: "score-investissement", title: "Score investissement", subtitle: "Attractivité globale pour investir", type: "bar", fields: ["score_investissement"] },
    { id: "prix-rendement", title: "Prix vs rendement net", subtitle: "Prix, rendement et liquidité du marché", type: "bubbleInvestment", fields: ["prix_m2_median", "rendement_net_pct"] },
    { id: "accessibilite-logement", title: "Accessibilité logement", subtitle: "Capacité d’accès au logement", type: "bar", fields: ["score_accessibilite_logement"] },
    { id: "taux-effort", title: "Taux d’effort", subtitle: "Poids estimé du loyer dans le revenu", type: "bar", fields: ["taux_effort"] },
    { id: "revenu-loyer", title: "Revenu médian et loyer 35 m²", subtitle: "Comparaison revenu et coût locatif", type: "bar", fields: ["median_income_monthly_uc", "loyer_theorique_35m2"] },
    { id: "logement-social", title: "Score logement social", subtitle: "Présence relative du logement social", type: "bar", fields: ["score_logement_social"] },
    { id: "logements-total", title: "Nombre total de logements", subtitle: "Volume résidentiel disponible", type: "bar", fields: ["nb_logmt_total"] },
    { id: "appartements-maisons", title: "Appartements vs maisons", subtitle: "Structure du parc résidentiel", type: "bar", fields: ["nb_appartements", "nb_maisons"] },
    { id: "pieces-logements", title: "Répartition des logements par pièces", subtitle: "Typologie des logements", type: "bar", fields: ["nb_1_piece", "nb_2_pieces", "nb_3_pieces", "nb_4_pieces", "nb_5_pieces_plus"] }
  ];

  async function init() {
    state.rows = latestByArea(await Api.getAreas("arrondissement", false));
    renderBestCards();
    renderCharts();
  }

  function renderBestCards() {
    const container = document.getElementById("best-cards");
    container.innerHTML = BEST_FIELDS.map(field => {
      const best = bestRow(field);
      const value = best ? valueFor(best, field) : null;
      const width = progressWidth(field, value);
      return `
        <article class="decision-card neutral">
          <div class="decision-card-top">
            <span>Meilleur arrondissement</span>
            <em>${UI.label(field)}</em>
          </div>
          <strong>${best.area_name || "Donnée indisponible"}</strong>
          <p>Score : ${UI.formatValue(value, field)}</p>
          <div class="score-track"><span style="width:${width}%;background:${UI.scoreColor(field)}"></span></div>
        </article>
      `;
    }).join("");
  }

  function renderCharts() {
    const grid = document.getElementById("global-grid");
    grid.innerHTML = GLOBAL_CHARTS.map(chart => chartCard(chart)).join("");
    GLOBAL_CHARTS.forEach((config, index) => renderChart(config, index));
  }

  function renderChart(config, index) {
    const canvas = document.querySelector(`[data-field="${config.id}"]`);
    if (config.type === "bubbleInvestment") {
      const data = state.rows.map(row => ({
        x: numberOrNull(valueFor(row, "prix_m2_median")),
        y: numberOrNull(valueFor(row, "rendement_net_pct")),
        r: Math.max(4, Math.min(18, (numberOrNull(valueFor(row, "nb_mutations")) || 0) / 200)),
        score: valueFor(row, "score_investissement"),
        label: row.area_name
      })).filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
      if (!data.length) return showEmpty(canvas, "Aucune donnée disponible pour ce graphique.");
      state.charts.push(new Chart(canvas, {
        type: "bubble",
        data: { datasets: [{ label: "Arrondissements", data, backgroundColor: "rgba(42,157,143,0.38)", borderColor: "#2A9D8F" }] },
        options: bubbleOptions()
      }));
      return;
    }

    const datasets = config.fields.map((field, fieldIndex) => ({
      label: UI.label(field),
      data: state.rows.map(row => numberOrNull(valueFor(row, field))),
      backgroundColor: colorFor(field, index + fieldIndex, 0.72),
      borderColor: colorFor(field, index + fieldIndex, 1),
      borderWidth: 1
    }));
    if (!datasets.some(dataset => dataset.data.some(value => value !== null))) {
      showEmpty(canvas, "Aucune donnée disponible pour ce graphique.");
      return;
    }
    state.charts.push(new Chart(canvas, {
      type: "bar",
      data: { labels: state.rows.map(row => row.area_name), datasets },
      options: chartOptions(config.fields[0])
    }));
  }

  function chartOptions(field) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 80,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } },
        tooltip: { callbacks: { label: context => `${context.dataset.label}: ${UI.tooltipValue(context.raw, field)}` } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } },
        y: { grace: "8%", ticks: { callback: value => UI.formatAxisValue(value, field) } }
      }
    };
  }

  function bubbleOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: context => `${context.raw.label}: ${UI.formatValue(context.raw.x, "prix_m2_median")} · ${UI.formatValue(context.raw.y, "rendement_net_pct")} · score ${UI.formatValue(context.raw.score, "score_investissement")}`
          }
        }
      },
      scales: {
        x: { title: { display: true, text: "Prix médian au m²" }, ticks: { callback: value => UI.formatAxisValue(value, "prix_m2_median") } },
        y: { title: { display: true, text: "Rendement net" }, ticks: { callback: value => UI.formatAxisValue(value, "rendement_net_pct") } }
      }
    };
  }

  function chartCard(config) {
    return `<article class="dashboard-card"><h2>${escapeHtml(config.title)}</h2><p>${escapeHtml(config.subtitle)}</p><canvas data-field="${escapeHtml(config.id)}"></canvas></article>`;
  }

  function bestRow(field) {
    return [...state.rows].sort((a, b) => (Number(valueFor(b, field)) || -Infinity) - (Number(valueFor(a, field)) || -Infinity))[0];
  }

  function progressWidth(field, value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    if (field === "rendement_net_pct") return Math.max(0, Math.min(100, number / 5 * 100));
    return Math.max(0, Math.min(100, number));
  }

  function latestByArea(rows) {
    const map = new Map();
    rows.forEach(row => {
      const key = String(row.area_id);
      const year = Number(row.year ?? row.properties?.annee) || 0;
      const currentYear = Number(map.get(key)?.year ?? map.get(key)?.properties?.annee) || 0;
      const enriched = { ...row, properties: { ...row.properties } };
      enriched.properties.nb_logements_familiaux = toNumber(enriched.properties.nb_4_pieces) + toNumber(enriched.properties.nb_5_pieces_plus);
      if (!map.has(key) || year >= currentYear) map.set(key, enriched);
    });
    return [...map.values()].sort((a, b) => arrondissementNumber(a) - arrondissementNumber(b));
  }

  function arrondissementNumber(row) {
    return Number(row.properties?.arrondissement ?? row.properties?.c_ar ?? row.area_id) || 0;
  }

  function valueFor(row, field) {
    if (field === "nb_logements_familiaux") return toNumber(row.properties?.nb_4_pieces) + toNumber(row.properties?.nb_5_pieces_plus);
    return row.properties?.[field] ?? row[field];
  }

  function colorFor(field, index, alpha) {
    const hex = SCORE_COLORS[field] || COLORS[index % COLORS.length];
    return alpha === 1 ? hex : rgba(hex, alpha);
  }

  function showEmpty(canvas, text) {
    const p = document.createElement("p");
    p.className = "chart-empty";
    p.textContent = text;
    canvas.replaceWith(p);
  }

  function toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function numberOrNull(value) {
    if (value === null || value === undefined || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function rgba(hex, alpha) {
    const value = parseInt(hex.replace("#", ""), 16);
    return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", ParisPage.init);

