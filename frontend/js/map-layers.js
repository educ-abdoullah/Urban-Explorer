const MapLayers = (() => {
  const SOURCE_ID = "urban-areas";
  const CENTROID_SOURCE_ID = "urban-area-centroids";
  const FILL_LAYER = "urban-areas-fill";
  const LINE_LAYER = "urban-areas-line";
  const CIRCLE_LAYER = "urban-areas-circles";
  const LABEL_LAYER = "urban-arrondissement-labels";
  const SELECTED_LAYER = "urban-areas-selected";

  function documentsToFeatureCollection(docs) {
    return {
      type: "FeatureCollection",
      features: docs
        .filter(doc => doc.geometry)
        .map(doc => ({
          type: "Feature",
          geometry: doc.geometry,
          properties: {
            id: doc.area_id,
            name: doc.area_name,
            level: doc.level,
            year: doc.year ?? doc.properties?.annee,
            profil_ideal: doc.profil_ideal ?? doc.properties?.profil_ideal,
            score_senior: doc.score_senior ?? doc.properties?.score_senior,
            score_actifs: doc.score_actifs ?? doc.properties?.score_actifs,
            score_jeune_adulte: doc.score_jeune_adulte ?? doc.properties?.score_jeune_adulte,
            score_junior: doc.score_junior ?? doc.properties?.score_junior,
            ...doc.properties,
            nb_logements_familiaux: toNumber(doc.properties?.nb_4_pieces) + toNumber(doc.properties?.nb_5_pieces_plus),
            densite_population: safeDensity(doc.properties?.population, doc.properties?.surface)
          }
        }))
    };
  }

  function toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function safeDensity(population, surface) {
    const pop = Number(population);
    const area = Number(surface);
    if (!Number.isFinite(pop) || !Number.isFinite(area) || area <= 0) return null;
    return pop / (area / 1000000);
  }

  function getNumericValues(featureCollection, field) {
    return featureCollection.features
      .map(feature => Number(feature.properties[field]))
      .filter(Number.isFinite);
  }

  function getDomain(featureCollection, field) {
    const values = getNumericValues(featureCollection, field);
    if (!values.length) return { min: 0, mid: 50, max: 100 };
    const min = Math.min(...values);
    const max = Math.max(...values);
    return { min, mid: min + (max - min) / 2, max: max === min ? min + 1 : max };
  }

  function addLayers(map) {
    if (map.getSource(SOURCE_ID)) return;

    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
      promoteId: "id"
    });

    map.addSource(CENTROID_SOURCE_ID, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
      promoteId: "id"
    });

    map.addLayer({
      id: FILL_LAYER,
      type: "fill",
      source: SOURCE_ID,
      paint: {
        "fill-color": "#dbeafe",
        "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.86, 0.68]
      }
    });

    map.addLayer({
      id: LINE_LAYER,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "#ffffff",
        "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 2.4, 1.1]
      }
    });

    map.addLayer({
      id: SELECTED_LAYER,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "#1e3a8a",
        "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 4, 0]
      }
    });

    map.addLayer({
      id: CIRCLE_LAYER,
      type: "circle",
      source: CENTROID_SOURCE_ID,
      paint: {
        "circle-color": "#10b981",
        "circle-opacity": 0,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.5,
        "circle-radius": 0
      }
    });

    map.addLayer({
      id: LABEL_LAYER,
      type: "symbol",
      source: CENTROID_SOURCE_ID,
      layout: {
        "text-field": ["to-string", ["coalesce", ["get", "arrondissement"], ["slice", ["get", "id"], 3, 5]]],
        "text-size": ["interpolate", ["linear"], ["zoom"], 10, 12, 13, 18],
        "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
        "text-allow-overlap": false,
        "visibility": "visible"
      },
      paint: {
        "text-color": "#0f172a",
        "text-halo-color": "#ffffff",
        "text-halo-width": 2,
        "text-opacity": 0.92
      }
    });
  }

  function updateData(map, featureCollection) {
    map.getSource(SOURCE_ID).setData(featureCollection);
    map.getSource(CENTROID_SOURCE_ID).setData(toCentroidFeatureCollection(featureCollection));
  }

  function toCentroidFeatureCollection(featureCollection) {
    return {
      type: "FeatureCollection",
      features: featureCollection.features.map(feature => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: getFeatureCenter(feature.geometry.coordinates)
        },
        properties: feature.properties
      }))
    };
  }

  function getFeatureCenter(coordinates) {
    const points = [];
    collectCoordinates(coordinates, points);
    if (!points.length) return PARIS_VIEW.center;
    const sum = points.reduce((acc, point) => [acc[0] + point[0], acc[1] + point[1]], [0, 0]);
    return [sum[0] / points.length, sum[1] / points.length];
  }

  function collectCoordinates(input, output) {
    if (typeof input[0] === "number") {
      output.push(input);
      return;
    }
    input.forEach(item => collectCoordinates(item, output));
  }

  function updateFillColor(map, featureCollection, field, palette = POLYGON_PALETTES.blue.colors) {
    const domain = getDomain(featureCollection, field);
    map.setPaintProperty(FILL_LAYER, "fill-color", [
      "case",
      ["has", field],
      ["interpolate", ["linear"], ["to-number", ["get", field], domain.min], domain.min, palette[0], domain.mid, palette[1], domain.max, palette[2]],
      "#e2e8f0"
    ]);
    return domain;
  }

  function updateCircles(map, featureCollection, field, color = CIRCLE_COLORS.green.value) {
    if (!field || field === "none") {
      map.setPaintProperty(CIRCLE_LAYER, "circle-opacity", 0);
      map.setPaintProperty(CIRCLE_LAYER, "circle-radius", 0);
      return null;
    }

    const domain = getDomain(featureCollection, field);
    map.setPaintProperty(CIRCLE_LAYER, "circle-color", color);
    map.setPaintProperty(CIRCLE_LAYER, "circle-opacity", 0.62);
    map.setPaintProperty(CIRCLE_LAYER, "circle-radius", [
      "case",
      ["has", field],
      ["interpolate", ["linear"], ["to-number", ["get", field], domain.min], domain.min, 4, domain.max, 24],
      0
    ]);
    return domain;
  }

  function updateLabelVisibility(map, level) {
    if (!map.getLayer(LABEL_LAYER)) return;
    map.setLayoutProperty(LABEL_LAYER, "visibility", level === "arrondissement" ? "visible" : "none");
  }

  function fitToFeatures(map, featureCollection) {
    const bounds = new mapboxgl.LngLatBounds();
    featureCollection.features.forEach(feature => extendBounds(bounds, feature.geometry.coordinates));
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 42, maxZoom: 13.8, duration: 800 });
    }
  }

  function extendBounds(bounds, coordinates) {
    if (typeof coordinates[0] === "number") {
      bounds.extend(coordinates);
      return;
    }
    coordinates.forEach(item => extendBounds(bounds, item));
  }

  function setSelected(map, previousId, nextId) {
    if (previousId !== null && previousId !== undefined) {
      map.setFeatureState({ source: SOURCE_ID, id: previousId }, { selected: false });
    }
    if (nextId !== null && nextId !== undefined) {
      map.setFeatureState({ source: SOURCE_ID, id: nextId }, { selected: true });
    }
  }

  return {
    SOURCE_ID,
    CENTROID_SOURCE_ID,
    FILL_LAYER,
    CIRCLE_LAYER,
    LABEL_LAYER,
    documentsToFeatureCollection,
    addLayers,
    updateData,
    updateFillColor,
    updateCircles,
    updateLabelVisibility,
    fitToFeatures,
    setSelected,
    getDomain
  };
})();


