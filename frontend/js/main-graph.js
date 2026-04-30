const GraphPage = (() => {
  const state = { level: "arrondissement", docs: [], selectedId: null, charts: [] };

  const LOCAL_FIELDS = [
    "prix_m2_median", "loyer_m2_median", "rendement_net_pct", "score_investissement",
    "score_urbain_global", "score_accessibilite_logement", "score_logement_social",
    "score_jeune_adulte", "score_actifs", "score_senior", "score_junior",
    "taux_effort", "population", "nb_logmt_total", "nb_appartements", "nb_maisons",
    "nb_1_piece", "nb_2_pieces", "nb_3_pieces", "nb_4_pieces", "nb_5_pieces_plus"
  ];

  const COLORS = ["#3A86FF", "#2A9D8F", "#8338EC", "#80ED99", "#F4A261", "#00B4D8", "#E63946", "#FFBE0B"];

  async function init() {
    bindEvents();
    await loadLevel("arrondissement");
  }

  function bindEvents() {
    document.getElementById("graph-level").addEventListener("change", event => loadLevel(event.target.value));
    document.getElementById("graph-zone").addEventListener("change", event => {
      state.selectedId = event.target.value;
      renderCharts();
    });
    document.getElementById("graph-search").addEventListener("input", event => populateZones(event.target.value));
  }

  async function loadLevel(level) {
    state.level = level;
    state.docs = await Api.getAreas(level, false);
    populateZones("");
  }

  function populateZones(query) {
    const select = document.getElementById("graph-zone");
    const normalizedQuery = normalize(query);
    const byArea = new Map();

    state.docs.forEach(doc => {
      const props = doc.properties || {};
      const label = getAreaLabel(doc);
      const searchable = normalize([label, doc.area_id, props.code_commune, props.code_iris, props.nom_quartier, props.nom_iris, props.arrondissement].filter(Boolean).join(" "));
      if (normalizedQuery && !searchable.includes(normalizedQuery)) return;
      if (!byArea.has(String(doc.area_id))) byArea.set(String(doc.area_id), label);
    });

    const options = [...byArea.entries()].sort((a, b) => {
      if (state.level === "arrondissement") return Number(a[0]) - Number(b[0]);
      return a[1].localeCompare(b[1], "fr");
    }).slice(0, 250);

    select.innerHTML = options.map(([id, label]) => `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`).join("");
    state.selectedId = options[0]?.[0] || null;
    if (state.selectedId) select.value = state.selectedId;
    renderCharts();
  }

  function renderCharts() {
    const grid = document.getElementById("graph-grid");
    destroyCharts();

    if (!state.selectedId) {
      grid.innerHTML = `<article class="dashboard-card"><h2>Aucune zone</h2><p class="chart-empty">Donnée indisponible</p></article>`;
      return;
    }

    const rows = state.docs
      .filter(doc => String(doc.area_id) === String(state.selectedId))
      .sort((a, b) => Number(a.year ?? a.properties?.annee) - Number(b.year ?? b.properties?.annee));

    grid.innerHTML = LOCAL_FIELDS.map(field => chartCard(field, `Évolution ${UI.label(field).toLowerCase()}`)).join("");
    LOCAL_FIELDS.forEach((field, index) => renderLineChart(grid.querySelector(`[data-field="${field}"]`), rows, field, index));
  }

  function renderLineChart(canvas, rows, field, index) {
    const points = rows.map(doc => ({
      year: Number(doc.year ?? doc.properties?.annee),
      value: toNumberOrNull(doc.properties?.[field])
    })).filter(point => Number.isFinite(point.year));

    if (!points.some(point => point.value !== null)) {
      canvas.replaceWith(emptyMessage(`Aucune donnée disponible pour ${UI.label(field).toLowerCase()}.`));
      return;
    }

    const color = SCORE_COLORS[field] || COLORS[index % COLORS.length];
    state.charts.push(new Chart(canvas, {
      type: "line",
      data: {
        labels: points.map(point => point.year),
        datasets: [{
          label: UI.label(field),
          data: points.map(point => point.value),
          borderColor: color,
          backgroundColor: rgba(color, 0.12),
          fill: true,
          tension: 0.35,
          spanGaps: true,
          pointRadius: 4
        }]
      },
      options: chartOptions(field)
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

  function chartCard(field, title) {
    return `<article class="dashboard-card"><h2>${escapeHtml(title)}</h2><p>Données multi-années disponibles</p><canvas data-field="${escapeHtml(field)}"></canvas></article>`;
  }

  function getAreaLabel(doc) {
    const props = doc.properties || {};
    return props.nom_iris || doc.area_name || props.nom_commune || String(doc.area_id);
  }

  function destroyCharts() {
    state.charts.forEach(chart => chart.destroy());
    state.charts = [];
  }

  function normalize(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function toNumberOrNull(value) {
    if (value === null || value === undefined || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function emptyMessage(text) {
    const p = document.createElement("p");
    p.className = "chart-empty";
    p.textContent = text || "Donnée indisponible";
    return p;
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

document.addEventListener("DOMContentLoaded", GraphPage.init);
