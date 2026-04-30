const UI = (() => {
  const numberFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

  function formatValue(value, field) {
    if (value === null || value === undefined || value === "" || Number.isNaN(value)) {
      return "Donnée indisponible";
    }

    const number = Number(value);
    if (Number.isFinite(number)) {
      if (field === "year" || field === "annee") return String(Math.round(number));
      if (SCORE_FIELDS.has(field)) return `${numberFormatter.format(Math.round(Math.max(0, number)))} %`;

      if (field === "taux_effort") {
        const pct = number <= 1 ? number * 100 : number;
        return `${numberFormatter.format(Math.max(0, pct))} %`;
      }

      if (field === "rendement_net_pct" || field === "rendement_brut_pct") {
        return `${new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Math.max(0, number))} %`;
      }

      if (field === "prix_m2_median" || field === "prix_m2_moyen" || field === "loyer_m2_median") {
        return `${numberFormatter.format(number)} €/m²`;
      }

      if (field === "population") return `${numberFormatter.format(number)} habitants`;

      if (["nb_logmt_total", "nb_logements_dvf", "nb_appartements", "nb_maisons", "nb_1_piece", "nb_2_pieces", "nb_3_pieces", "nb_4_pieces", "nb_5_pieces_plus", "nb_logements_familiaux"].includes(field)) {
        return `${numberFormatter.format(number)} logements`;
      }

      if (field === "nb_mutations") return `${numberFormatter.format(number)} mutations`;
      if (field === "median_income_monthly_uc" || field === "loyer_theorique_35m2") return `${numberFormatter.format(number)} €`;
      if (FIELD_UNITS[field] === "%") return `${numberFormatter.format(number)} %`;

      return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: number % 1 ? 1 : 0 }).format(number);
    }

    return value;
  }

  function formatClientValue(value, field) {
    return formatValue(value, field);
  }

  function formatAxisValue(value, field) {
    const number = Number(value);
    if (!Number.isFinite(number)) return value;
    if (SCORE_FIELDS.has(field)) return `${Math.round(Math.max(0, number))} %`;
    if (field === "taux_effort") return `${Math.round(Math.max(0, number <= 1 ? number * 100 : number))} %`;
    if (field === "rendement_net_pct" || field === "rendement_brut_pct") {
      return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(Math.max(0, number))} %`;
    }
    return numberFormatter.format(number);
  }

  function tooltipValue(value, field) {
    return formatValue(value, field);
  }

  function label(field) {
    return FIELD_LABELS[field] || String(field).replaceAll("_", " ");
  }

  function setLoading(isLoading, text = "Chargement des données territoriales") {
    const loader = document.getElementById("loader");
    if (!loader) return;
    const labelNode = loader.querySelector("span");
    if (labelNode) labelNode.textContent = text;
    loader.classList.toggle("is-visible", isLoading);
  }

  function showError(message) {
    const panel = document.getElementById("zone-details");
    if (!panel) return;
    panel.className = "details-section empty-state";
    panel.innerHTML = `<h2>Une erreur est survenue</h2><p>${message}</p>`;
  }

  function populateSelect(select, fields, includeNone = false) {
    if (!select) return;
    select.innerHTML = "";
    fields.forEach(field => {
      const option = document.createElement("option");
      option.value = field;
      option.textContent = field === "none" ? "Désactiver les cercles" : label(field);
      select.appendChild(option);
    });
    if (includeNone) select.value = "none";
  }

  function populateObjectSelect(select, options) {
    if (!select) return;
    select.innerHTML = "";
    Object.entries(options).forEach(([value, config]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = config.label;
      select.appendChild(option);
    });
  }

  function populateSwatches(container, options, activeValue, type) {
    if (!container) return;
    container.innerHTML = Object.entries(options).map(([value, config]) => {
      const style = getSwatchStyle(config, type);
      const activeClass = value === activeValue ? " is-active" : "";
      const paletteClass = type === "palette" ? " palette-swatch" : "";
      return `<button class="swatch-button${paletteClass}${activeClass}" style="${style}" data-swatch-type="${type}" data-swatch-value="${value}" title="${config.label}" aria-label="${config.label}"></button>`;
    }).join("");
  }

  function getSwatchStyle(config, type) {
    if (type === "palette") return `--swatch-a:${config.colors[0]};--swatch-b:${config.colors[1]};--swatch-c:${config.colors[2]}`;
    return `--swatch:${config.swatch || config.value}`;
  }

  function setActiveSwatch(type, value) {
    document.querySelectorAll(`[data-swatch-type="${type}"]`).forEach(button => {
      button.classList.toggle("is-active", button.dataset.swatchValue === value);
    });
  }

  function updateIndicatorHelp(field) {
    const help = document.getElementById("indicator-help");
    if (help) help.textContent = FIELD_TOOLTIPS[field] || "Indicateur disponible dans les données de la zone.";
  }

  function updateLegend(field, domain, palette = POLYGON_PALETTES.blue.colors) {
    const legend = document.getElementById("legend");
    if (!legend) return;
    legend.innerHTML = `
      <span class="panel-label">${label(field)}</span>
      <div class="legend-gradient" style="background: linear-gradient(90deg, ${palette[0]}, ${palette[1]}, ${palette[2]})"></div>
      <div class="legend-labels">
        <span>${formatValue(domain.min, field)}</span>
        <span>${formatValue(domain.mid, field)}</span>
        <span>${formatValue(domain.max, field)}</span>
      </div>
    `;
  }

  function updateCircleLegend(field, domain = null) {
    const legend = document.getElementById("circle-legend");
    if (!legend) return;
    if (!field || field === "none") {
      legend.innerHTML = `<span class="panel-label">Taille des cercles</span><p class="helper-text">Cercles désactivés.</p>`;
      return;
    }
    const min = domain ? formatValue(domain.min, field) : "Donnée indisponible";
    const max = domain ? formatValue(domain.max, field) : "Donnée indisponible";
    legend.innerHTML = `
      <span class="panel-label">Taille des cercles : ${label(field)}</span>
      <div class="circle-scale">
        <span class="circle-dot small"></span>
        <span class="circle-line"></span>
        <span class="circle-dot large"></span>
      </div>
      <div class="legend-labels">
        <span>${min}</span>
        <span>${max}</span>
      </div>
    `;
  }

  function renderDetails(feature) {
    const panel = document.getElementById("zone-details");
    if (!panel) return;
    const props = feature.properties;
    const groups = getDetailGroups(props);

    panel.className = "details-section is-refreshing";
    panel.innerHTML = `
      <div class="zone-title">
        <span class="badge">${props.level === "iris" ? "IRIS" : "Arrondissement"} · ${formatValue(props.year ?? props.annee, "year")}</span>
        <h2>${props.name}</h2>
      </div>
      <div class="kpi-grid">
        ${["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement"].map(field => kpiCard(props, field)).join("")}
      </div>
      ${profileBlock(props)}
      ${groups.map(group => detailGroup(props, group)).join("")}
    `;
    window.requestAnimationFrame(() => panel.classList.remove("is-refreshing"));
  }

  function kpiCard(props, field) {
    const value = props[field];
    const scoreBar = SCORE_FIELDS.has(field) && Number.isFinite(Number(value))
      ? `<div class="score-track"><span style="width:${Math.max(0, Math.min(100, Number(value)))}%;background:${scoreColor(field)}"></span></div>`
      : "";
    return `
      <div class="kpi-card" title="${FIELD_TOOLTIPS[field] || ""}">
        <span>${label(field)}</span>
        <strong>${formatValue(value, field)}</strong>
        ${scoreBar}
      </div>
    `;
  }

  function profileBlock(props) {
    const fields = ["score_jeune_adulte", "score_actifs", "score_senior", "score_junior"].filter(field => field in props);
    if (!fields.length && !props.profil_ideal) return "";
    const dominant = props.profil_ideal || "Donnée indisponible";
    return `
      <div class="detail-group profile-group">
        <h3>Profil démographique</h3>
        <div class="profile-highlight">
          <span>Profil dominant</span>
          <strong>${dominant}</strong>
        </div>
        <div class="detail-list">
          ${fields.map(field => detailLine(props, field)).join("")}
        </div>
      </div>
    `;
  }

  function detailGroup(props, group) {
    return `
      <div class="detail-group">
        <h3>${group.title}</h3>
        <div class="detail-list">
          ${group.fields.map(field => detailLine(props, field)).join("")}
        </div>
      </div>
    `;
  }

  function detailLine(props, field) {
    const value = props[field];
    const bar = SCORE_FIELDS.has(field) && Number.isFinite(Number(value))
      ? `<div class="mini-score"><span style="width:${Math.max(0, Math.min(100, Number(value)))}%;background:${scoreColor(field)}"></span></div>`
      : "";
    return `
      <div class="detail-line">
        <span>${label(field)}</span>
        <strong>${formatValue(value, field)}</strong>
        ${bar}
      </div>
    `;
  }

  function getDetailGroups(props) {
    const base = [
      { title: "Scores clés", fields: ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"] }
    ];
    return base.map(group => ({ ...group, fields: group.fields.filter(field => field in props) })).filter(group => group.fields.length);
  }

  function buildPopupHTML(props) {
    const fields = ["score_urbain_global", "score_investissement", "score_mobilite", "score_environnement", "score_logement_social"];
    const arrondissement = props.arrondissement || props.c_ar || props.id || "Donnée indisponible";
    const year = props.year ?? props.annee;

    return `
      <div class="popup-title">${props.name}</div>
      <div class="popup-level">Année : ${formatValue(year, "year")}</div>
      <div class="popup-level">Arrondissement : ${formatValue(arrondissement, "arrondissement")}</div>
      <div class="popup-grid">
        ${fields.map(field => `
          <div>
            <span>${field === "score_logement_social" ? "Logement social" : label(field).replace("Score ", "")}</span>
            <strong>${formatClientValue(props[field], field)}</strong>
          </div>
        `).join("")}
      </div>
    `;
  }

  function buildHoverPopupHTML(props, fields = {}) {
    const colorField = fields.colorIndicator || "score_urbain_global";
    const circleField = fields.circleIndicator && fields.circleIndicator !== "none" ? fields.circleIndicator : null;
    const rows = [
      ["Score global", "score_urbain_global"],
      [label(colorField), colorField],
      circleField ? [label(circleField), circleField] : null
    ].filter(Boolean);
    const uniqueRows = rows.filter((row, index, array) => array.findIndex(item => item[1] === row[1]) === index);
    return `
      <div class="hover-popup-card">
        <strong>${props.name}</strong>
        ${uniqueRows.map(([rowLabel, field]) => `<div><span>${rowLabel}</span><b>${formatValue(props[field], field)}</b></div>`).join("")}
      </div>
    `;
  }

  function renderRanking(items, field) {
    const container = document.getElementById("ranking-list");
    if (!container) return;
    if (!items.length) {
      container.innerHTML = `<p>Donnée indisponible</p>`;
      return;
    }
    container.innerHTML = items.map((item, index) => `
      <div class="ranking-item">
        <span class="ranking-rank">${index + 1}</span>
        <div><strong>${item.area_name}</strong><small>${item.level}</small></div>
        <strong>${formatValue(item.properties?.[field], field)}</strong>
      </div>
    `).join("");
  }

  function scoreClass(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "neutral";
    if (number >= 75) return "high";
    if (number >= 50) return "mid";
    return "low";
  }

  function scoreColor(field) {
    return SCORE_COLORS[field] || "#3A86FF";
  }

  function toggleDetails(open = true) {
    const panel = document.getElementById("details-panel");
    if (panel) panel.classList.toggle("is-open", open);
  }

  return {
    formatValue,
    formatClientValue,
    formatAxisValue,
    tooltipValue,
    label,
    setLoading,
    showError,
    populateSelect,
    populateObjectSelect,
    populateSwatches,
    setActiveSwatch,
    updateIndicatorHelp,
    updateLegend,
    updateCircleLegend,
    renderDetails,
    buildPopupHTML,
    buildHoverPopupHTML,
    renderRanking,
    scoreClass,
    scoreColor,
    toggleDetails
  };
})();
