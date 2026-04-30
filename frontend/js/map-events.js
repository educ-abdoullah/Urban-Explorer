const MapEvents = (() => {
  let hoveredId = null;
  let hoverPopup;

  function bind(map, handlers) {
    hoverPopup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
      maxWidth: "260px",
      className: "hover-popup"
    });

    map.on("mousemove", MapLayers.FILL_LAYER, event => {
      map.getCanvas().style.cursor = "pointer";
      if (!event.features.length) return;

      const feature = event.features[0];
      const id = feature.properties.id;
      if (hoveredId !== null && hoveredId !== id) {
        map.setFeatureState({ source: MapLayers.SOURCE_ID, id: hoveredId }, { hover: false });
      }
      hoveredId = id;
      map.setFeatureState({ source: MapLayers.SOURCE_ID, id }, { hover: true });

      hoverPopup
        .setLngLat(event.lngLat)
        .setHTML(UI.buildHoverPopupHTML(feature.properties, handlers.getHoverFields?.()))
        .addTo(map);
    });

    map.on("mouseleave", MapLayers.FILL_LAYER, () => {
      map.getCanvas().style.cursor = "";
      if (hoveredId !== null) {
        map.setFeatureState({ source: MapLayers.SOURCE_ID, id: hoveredId }, { hover: false });
      }
      hoveredId = null;
      hoverPopup.remove();
    });

    map.on("click", MapLayers.FILL_LAYER, event => {
      if (!event.features.length) return;
      hoverPopup.remove();
      handlers.onFeatureSelect(event.features[0], event.lngLat);
    });
  }

  function showPopup() {
    return null;
  }

  return { bind, showPopup };
})();
