function initializeMap() {
  if (!window.mapboxgl) {
    throw new Error("Mapbox GL JS n'est pas chargé.");
  }

  mapboxgl.accessToken = MAPBOX_TOKEN;

  const map = new mapboxgl.Map({
    container: "map",
    style: MAP_STYLES.warm.url,
    center: PARIS_VIEW.center,
    zoom: PARIS_VIEW.zoom,
    maxBounds: [[2.12, 48.74], [2.58, 48.96]]
  });

  map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "bottom-right");
  map.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");
  map.once("style.load", () => applyBaseMapTheme(map, "warm"));

  return map;
}

function applyBaseMapTheme(map, styleKey) {
  const style = MAP_STYLES[styleKey];
  if (!style.warm) return;

  const paintUpdates = [
    ["background", "background-color", "#f4ead8"],
    ["land", "background-color", "#f4ead8"],
    ["landuse", "fill-color", "#efe2ca"],
    ["water", "fill-color", "#dbeafe"],
    ["road-primary", "line-color", "#ffffff"],
    ["road-secondary-tertiary", "line-color", "#fffaf0"],
    ["building", "fill-color", "#eadcc5"]
  ];

  paintUpdates.forEach(([layerId, prop, value]) => {
    if (map.getLayer(layerId)) {
      try {
        map.setPaintProperty(layerId, prop, value);
      } catch (error) {
        // Certains styles Mapbox ne possèdent pas les mêmes propriétés de paint.
      }
    }
  });
}


