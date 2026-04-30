const Comparison = (() => {
  const state = { a: null, b: null };
  let barChart;
  let radarChart;

  const BAR_FIELDS = [
    "prix_m2_median",
    "loyer_m2_median",
    "rendement_net_pct",
    "score_investissement",
    "score_urbain_global",
    "score_securite",
    "score_accessibilite_logement",
    "score_logement_social",
    "population",
    "nb_logmt_total"
  ];

  const RADAR_FIELDS = [
    "score_investissement",
    "score_securite",
    "score_mobilite",
    "score_environnement",
    "score_services_quartier",
    "score_accessibilite_logement",
    "score_logement_social"
  ];

  function setZone(slot, feature) {
    if (!feature) return;
    state[slot] = feature;
    render();
  }

  function clear() {
    state.a = null;
    state.b = null;
    destroyCharts();
    render();
  }

  function render() {
    const container = document.getElementById("comparison-view");
    if (!container) return;

    if (!state.a && !state.b) {
      container.innerHTML = `<p>Sélectionnez une zone, puis assignez-la en Zone A ou Zone B.</p>`;
      destroyCharts();
      return;
    }

    if (!state.a || !state.b) {
      const selected = state.a || state.b;
      container.innerHTML = `<p><strong>${selected.properties.name}</strong> est sélectionnée. Ajoutez une seconde zone pour comparer.</p>`;
      destroyCharts();
      return;
    }

    container.innerHTML = `
      <div class="detail-line"><span>Zone A</span><strong>${state.a.properties.name}</strong></div>
      <div class="detail-line"><span>Zone B</span><strong>${state.b.properties.name}</strong></div>
      ${COMPARISON_FIELDS.map(field => row(field, state.a.properties[field], state.b.properties[field])).join("")}
      <div class="comparison-chart-card"><h3>Comparaison des indicateurs clés</h3><canvas id="comparison-bar-chart"></canvas></div>
      <div class="comparison-chart-card"><h3>Profil comparatif</h3><canvas id="comparison-radar-chart"></canvas></div>
    `;
    renderCharts();
  }

  function row(field, valueA, valueB) {
    const numericA = Number(valueA);
    const numericB = Number(valueB);
    const max = Math.max(Number.isFinite(numericA) ? numericA : 0, Number.isFinite(numericB) ? numericB : 0, 1);
    const widthA = Number.isFinite(numericA) ? Math.max(4, numericA / max * 100) : 0;
    const widthB = Number.isFinite(numericB) ? Math.max(4, numericB / max * 100) : 0;

    return `
      <div class="comparison-row">
        <span>${UI.label(field)}</span>
        <strong>${UI.formatValue(valueA, field)}</strong>
        <strong>${UI.formatValue(valueB, field)}</strong>
        <div class="comparison-bars">
          <div class="bar-track"><div class="bar-fill" style="width:${widthA}%"></div></div>
          <div class="bar-track"><div class="bar-fill alt" style="width:${widthB}%"></div></div>
        </div>
      </div>
    `;
  }

  function renderCharts() {
    if (!window.Chart) return;
    destroyCharts();
    const a = state.a.properties;
    const b = state.b.properties;

    barChart = new Chart(document.getElementById("comparison-bar-chart"), {
      type: "bar",
      data: {
        labels: BAR_FIELDS.map(UI.label),
        datasets: [
          { label: a.name, data: BAR_FIELDS.map(field => normalizedValue(a[field], field)), backgroundColor: "rgba(37, 99, 235, 0.72)" },
          { label: b.name, data: BAR_FIELDS.map(field => normalizedValue(b[field], field)), backgroundColor: "rgba(16, 185, 129, 0.72)" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              label: context => {
                const field = BAR_FIELDS[context.dataIndex];
                const source = context.datasetIndex === 0 ? a : b;
                return `${context.dataset.label}: ${UI.formatValue(source[field], field)}`;
              }
            }
          }
        },
        scales: { y: { beginAtZero: true, max: 100, ticks: { callback: value => `${value} %` } } }
      }
    });

    radarChart = new Chart(document.getElementById("comparison-radar-chart"), {
      type: "radar",
      data: {
        labels: RADAR_FIELDS.map(UI.label),
        datasets: [
          { label: a.name, data: RADAR_FIELDS.map(field => Number(a[field]) || 0), borderColor: "#2563eb", backgroundColor: "rgba(37, 99, 235, 0.16)" },
          { label: b.name, data: RADAR_FIELDS.map(field => Number(b[field]) || 0), borderColor: "#10b981", backgroundColor: "rgba(16, 185, 129, 0.16)" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { r: { min: 0, max: 100, ticks: { callback: value => `${value} %` } } }
      }
    });
  }

  function normalizedValue(value, field) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    if (SCORE_FIELDS.has(field) || field.includes("pct")) return Math.max(0, Math.min(100, number));
    if (field === "taux_effort") return Math.max(0, Math.min(100, number <= 1 ? number * 100 : number));
    return Math.max(0, Math.min(100, number / 1000));
  }

  function destroyCharts() {
    if (barChart) barChart.destroy();
    if (radarChart) radarChart.destroy();
    barChart = null;
    radarChart = null;
  }

  return { setZone, clear, render };
})();


