const Charts = (() => {
  let charts = [];

  const CHART_COLORS = {
    prix_m2_median: "#2563eb",
    loyer_m2_median: "#10b981",
    score_investissement: "#7c3aed",
    score_urbain_global: "#1e3a8a",
    population: "#0f766e"
  };

  function renderEvolution(selectedFeature, allFeatures) {
    const container = document.getElementById("evolution-charts");
    if (!container || !window.Chart) return;

    destroyCharts();
    const rows = getRowsForSelectedArea(selectedFeature, allFeatures);

    container.innerHTML = TREND_FIELDS.map(field => `
      <article class="chart-card">
        <h3>${UI.label(field)}</h3>
        <canvas data-chart-field="${field}"></canvas>
      </article>
    `).join("");

    TREND_FIELDS.forEach(field => {
      const canvas = container.querySelector(`[data-chart-field="${field}"]`);
      const points = rows
        .map(feature => ({
          year: Number(feature.properties.year ?? feature.properties.annee),
          value: toNumberOrNull(feature.properties[field])
        }))
        .filter(point => Number.isFinite(point.year));

      if (!points.some(point => point.value !== null)) {
        canvas.replaceWith(emptyMessage());
        return;
      }

      charts.push(new Chart(canvas, {
        type: "line",
        data: {
          labels: points.map(point => point.year),
          datasets: [{
            label: UI.label(field),
            data: points.map(point => point.value),
            borderColor: CHART_COLORS[field] || "#2563eb",
            backgroundColor: hexToRgba(CHART_COLORS[field] || "#2563eb", 0.12),
            fill: true,
            tension: 0.35,
            spanGaps: true,
            pointRadius: 3,
            pointHoverRadius: 5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          resizeDelay: 80,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: context => UI.tooltipValue(context.raw, field)
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { precision: 0 }
            },
            y: {
              beginAtZero: false,
              ticks: {
                callback: value => UI.formatAxisValue(value, field)
              }
            }
          }
        }
      }));
    });
  }

  function getRowsForSelectedArea(selectedFeature, allFeatures) {
    const props = selectedFeature.properties;
    const keys = (props.level === "iris"
      ? [props.id, props.code_iris, props.name]
      : [props.id, props.code_commune, props.name]
    ).filter(Boolean).map(String);

    const rows = allFeatures
      .filter(feature => {
        const candidate = feature.properties;
        return keys.some(key => [
          candidate.id,
          candidate.code_iris,
          props.level === "iris" ? candidate.code_iris : candidate.code_commune,
          candidate.name
        ].filter(Boolean).map(String).includes(key));
      })
      .sort((a, b) => Number(a.properties.year ?? a.properties.annee) - Number(b.properties.year ?? b.properties.annee));

    return rows.length ? rows : [selectedFeature];
  }

  function destroyCharts() {
    charts.forEach(chart => chart.destroy());
    charts = [];
  }

  function toNumberOrNull(value) {
    if (value === null || value === undefined || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function emptyMessage() {
    const p = document.createElement("p");
    p.className = "chart-empty";
    p.textContent = "Donnée indisponible";
    return p;
  }

  function hexToRgba(hex, alpha) {
    const value = hex.replace("#", "");
    const bigint = parseInt(value, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  return { renderEvolution };
})();



