const App = (() => {
  const state = {
    ...DEFAULT_STATE,
    map: null,
    rawDocsByLevel: new Map(),
    allFeatures: [],
    visibleFeatureCollection: { type: "FeatureCollection", features: [] },
    selectedFeature: null,
    selectedId: null,
    drilldownArrondissement: null
  };

  async function init() {
    UI.populateSelect(document.getElementById("color-indicator"), INDICATORS);
    UI.populateSelect(document.getElementById("circle-indicator"), CIRCLE_INDICATORS, true);
    UI.populateObjectSelect(document.getElementById("analysis-preset"), ANALYSIS_PRESETS);
    UI.populateSwatches(document.getElementById("map-style-swatches"), MAP_STYLES, state.mapStyle, "map");
    document.getElementById("color-indicator").value = state.colorIndicator;
    document.getElementById("circle-indicator").value = state.circleIndicator;
    document.getElementById("analysis-preset").value = "urbanDynamic";
    updatePresetHelp("urbanDynamic");
    UI.updateIndicatorHelp(state.colorIndicator);
    Comparison.render();

    try {
      state.map = initializeMap();
      state.map.on("load", async () => {
        MapLayers.addLayers(state.map);
        await loadLevel(state.level, true);
        bindEvents();
      });
    } catch (error) {
      UI.showError(`${error.message} Vérifiez que MAPBOX_TOKEN est renseigné dans js/config.js.`);
      UI.setLoading(false);
    }
  }

  function bindEvents() {
    Filters.bind({
      onLevelChange: async level => {
        state.level = level;
        state.drilldownArrondissement = null;
        state.selectedFeature = null;
        await loadLevel(level, true);
      },
      onYearChange: year => {
        state.year = year;
        document.getElementById("year-value").textContent = String(year);
        refreshVisibleData();
      },
      onColorChange: field => {
        state.colorIndicator = field;
        UI.updateIndicatorHelp(field);
        refreshStyles();
      },
      onCircleChange: field => {
        state.circleIndicator = field;
        refreshStyles();
      },
      onPresetChange: presetKey => applyPreset(presetKey),
      onMapStyleChange: styleKey => {
        state.mapStyle = styleKey;
        applyMapStyle();
      },
      onPaletteChange: paletteKey => {
        state.polygonPalette = paletteKey;
        refreshStyles();
      },
      onCircleColorChange: colorKey => {
        state.circleColor = colorKey;
        refreshStyles();
      },
      onFitParis: () => state.map.fitBounds(PARIS_VIEW.bounds, { padding: 30, duration: 700 }),
      onSetZoneA: () => Comparison.setZone("a", state.selectedFeature),
      onSetZoneB: () => Comparison.setZone("b", state.selectedFeature),
      onClearComparison: () => Comparison.clear()
    });

    Search.bind(selectSearchResult, () => state, ensureSearchFeatures);
    MapEvents.bind(state.map, {
      onFeatureSelect: selectFeature,
      getHoverFields: () => ({
        colorIndicator: state.colorIndicator,
        circleIndicator: state.circleIndicator
      })
    });
  }

  async function loadLevel(level, fit = false) {
    UI.setLoading(true, level === "iris" ? "Chargement des IRIS par pagination" : "Chargement des arrondissements");
    try {
      const docs = await Api.getAreas(level, true);
      state.rawDocsByLevel.set(level, docs);
      state.allFeatures = MapLayers.documentsToFeatureCollection(docs).features;
      refreshVisibleData();
      if (fit) MapLayers.fitToFeatures(state.map, state.visibleFeatureCollection);
    } catch (error) {
      UI.showError(error.message);
    } finally {
      UI.setLoading(false);
    }
  }

  function refreshVisibleData() {
    let features = state.allFeatures.filter(feature => Number(feature.properties.year ?? feature.properties.annee) === Number(state.year));
    if (state.drilldownArrondissement !== null) {
      features = features.filter(feature => arrondissementNumber(feature.properties) === state.drilldownArrondissement);
    }
    if (!features.length) {
      features = getLatestFeaturesByArea(state.allFeatures);
      if (state.drilldownArrondissement !== null) {
        features = features.filter(feature => arrondissementNumber(feature.properties) === state.drilldownArrondissement);
      }
    }
    state.visibleFeatureCollection = { type: "FeatureCollection", features };
    MapLayers.updateData(state.map, state.visibleFeatureCollection);
    refreshStyles();
    MapLayers.updateLabelVisibility(state.map, state.level);
  }

  async function ensureSearchFeatures(level) {
    if (level === state.level) return state.allFeatures;
    if (!state.rawDocsByLevel.has(level)) {
      const docs = await Api.getAreas(level, true);
      state.rawDocsByLevel.set(level, docs);
    }
    return MapLayers.documentsToFeatureCollection(state.rawDocsByLevel.get(level)).features;
  }

  function getLatestFeaturesByArea(features) {
    const latest = new Map();
    features.forEach(feature => {
      const key = String(feature.properties.id);
      const year = Number(feature.properties.year ?? feature.properties.annee) || 0;
      const currentYear = Number(latest.get(key)?.properties.year ?? latest.get(key)?.properties.annee) || 0;
      if (!latest.has(key) || year > currentYear) latest.set(key, feature);
    });
    return [...latest.values()];
  }

  function refreshStyles() {
    const palette = POLYGON_PALETTES[state.polygonPalette].colors;
    const circleColor = CIRCLE_COLORS[state.circleColor].value;
    const domain = MapLayers.updateFillColor(state.map, state.visibleFeatureCollection, state.colorIndicator, palette);
    const circleDomain = MapLayers.updateCircles(state.map, state.visibleFeatureCollection, state.circleIndicator, circleColor);
    MapLayers.updateLabelVisibility(state.map, state.level);
    UI.updateLegend(state.colorIndicator, domain, palette);
    UI.updateCircleLegend(state.circleIndicator, circleDomain);
  }

  function applyPreset(presetKey) {
    const preset = ANALYSIS_PRESETS[presetKey];
    if (!preset) return;
    state.colorIndicator = preset.colorIndicator;
    state.circleIndicator = preset.circleIndicator;
    state.polygonPalette = preset.polygonPalette;
    state.circleColor = preset.circleColor;
    document.getElementById("color-indicator").value = state.colorIndicator;
    document.getElementById("circle-indicator").value = state.circleIndicator;
    UI.updateIndicatorHelp(state.colorIndicator);
    updatePresetHelp(presetKey);
    refreshStyles();
    loadRanking();
  }

  async function loadRanking() {
    const container = document.getElementById("ranking-list");
    if (!container) return;
    try {
      const rows = await Api.getRanking(state.colorIndicator, state.level, 10);
      UI.renderRanking(rows, state.colorIndicator);
    } catch (error) {
      container.innerHTML = `<p>${error.message}</p>`;
    }
  }

  function updatePresetHelp(presetKey) {
    const help = document.getElementById("preset-help");
    if (help) help.textContent = ANALYSIS_PRESETS[presetKey].description || "";
  }

  function applyMapStyle() {
    UI.setLoading(true, "Application du style de carte");
    state.map.setStyle(MAP_STYLES[state.mapStyle].url);
    state.map.once("style.load", () => {
      applyBaseMapTheme(state.map, state.mapStyle);
      MapLayers.addLayers(state.map);
      MapLayers.updateData(state.map, state.visibleFeatureCollection);
      refreshStyles();
      UI.setLoading(false);
    });
  }

  async function selectFeature(feature, lngLat) {
    UI.setLoading(true, "Préparation des indicateurs...");
    const normalized = normalizeMapboxFeature(feature);
    MapLayers.setSelected(state.map, state.selectedId, normalized.properties.id);
    state.selectedId = normalized.properties.id;
    state.selectedFeature = normalized;
    UI.renderDetails(normalized);
    UI.toggleDetails(true);

    if (normalized.properties.level === "arrondissement" && state.level === "arrondissement") {
      await drillDownToIris(normalized);
    }

    window.setTimeout(() => UI.setLoading(false), 160);
  }

  async function drillDownToIris(arrondissementFeature) {
    const arrondissement = arrondissementNumber(arrondissementFeature.properties);
    if (!Number.isFinite(arrondissement)) return;

    UI.setLoading(true, `Chargement des IRIS du ${arrondissement}e arrondissement`);
    const irisFeatures = await ensureSearchFeatures("iris");
    state.level = "iris";
    state.drilldownArrondissement = arrondissement;
    state.allFeatures = irisFeatures;

    document.querySelectorAll("[data-level]").forEach(button => {
      button.classList.toggle("is-active", button.dataset.level === "iris");
    });

    refreshVisibleData();
    if (state.visibleFeatureCollection.features.length) {
      MapLayers.fitToFeatures(state.map, state.visibleFeatureCollection);
    }
  }

  async function selectSearchResult(level, areaId) {
    if (level !== state.level) {
      state.level = level;
      document.querySelectorAll("[data-level]").forEach(button => {
        button.classList.toggle("is-active", button.dataset.level === level);
      });
      await loadLevel(level, false);
    }

    const feature = state.visibleFeatureCollection.features.find(item => String(item.properties.id) === String(areaId))
      || getLatestFeaturesByArea(state.allFeatures).find(item => String(item.properties.id) === String(areaId));

    if (!feature) {
      UI.showError("Zone trouvée par l’API, mais absente de la géométrie chargée pour l’année sélectionnée.");
      return;
    }

    if (level === "iris") {
      state.drilldownArrondissement = arrondissementNumber(feature.properties);
      refreshVisibleData();
    }

    zoomToFeature(feature);
    const center = getFeatureCenter(feature);
    selectFeature(feature, center);
  }

  function normalizeMapboxFeature(feature) {
    return {
      type: "Feature",
      geometry: feature.geometry,
      properties: { ...feature.properties }
    };
  }

  function arrondissementNumber(props) {
    const direct = Number(props.arrondissement ?? props.c_ar);
    if (Number.isFinite(direct) && direct >= 1 && direct <= 20) return direct;

    const id = String(props.id ?? props.area_id ?? "");
    const numericId = Number(id);
    if (Number.isFinite(numericId) && numericId >= 1 && numericId <= 20) return numericId;

    const code = String(props.code_commune ?? props.c_arinsee ?? id);
    const match = code.match(/(?:75|751|750)?([0-2]?\d)$/);
    if (!match) return null;
    const value = Number(match[1]);
    return value >= 1 && value <= 20 ? value : null;
  }

  function zoomToFeature(feature) {
    const bounds = new mapboxgl.LngLatBounds();
    extendBounds(bounds, feature.geometry.coordinates);
    if (!bounds.isEmpty()) state.map.fitBounds(bounds, { padding: 80, maxZoom: 15, duration: 760 });
  }

  function getFeatureCenter(feature) {
    const coords = [];
    collectCoordinates(feature.geometry.coordinates, coords);
    const sum = coords.reduce((acc, coord) => [acc[0] + coord[0], acc[1] + coord[1]], [0, 0]);
    return [sum[0] / coords.length, sum[1] / coords.length];
  }

  function collectCoordinates(input, output) {
    if (typeof input[0] === "number") {
      output.push(input);
      return;
    }
    input.forEach(item => collectCoordinates(item, output));
  }

  function extendBounds(bounds, coordinates) {
    if (typeof coordinates[0] === "number") {
      bounds.extend(coordinates);
      return;
    }
    coordinates.forEach(item => extendBounds(bounds, item));
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
