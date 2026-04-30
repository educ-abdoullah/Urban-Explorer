const Filters = (() => {
  function bind(handlers) {
    document.querySelectorAll("[data-level]").forEach(button => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-level]").forEach(item => item.classList.remove("is-active"));
        button.classList.add("is-active");
        handlers.onLevelChange(button.dataset.level);
      });
    });

    document.getElementById("year-slider").addEventListener("input", event => {
      handlers.onYearChange(Number(event.target.value));
    });

    document.getElementById("color-indicator").addEventListener("change", event => {
      handlers.onColorChange(event.target.value);
    });

    document.getElementById("circle-indicator").addEventListener("change", event => {
      handlers.onCircleChange(event.target.value);
    });

    document.getElementById("analysis-preset").addEventListener("change", event => {
      handlers.onPresetChange(event.target.value);
    });

    document.querySelectorAll("[data-swatch-type]").forEach(button => {
      button.addEventListener("click", () => {
        const type = button.dataset.swatchType;
        const value = button.dataset.swatchValue;
        UI.setActiveSwatch(type, value);
        if (type === "map") handlers.onMapStyleChange(value);
        if (type === "palette") handlers.onPaletteChange(value);
        if (type === "circle") handlers.onCircleColorChange(value);
      });
    });

    document.getElementById("fit-paris").addEventListener("click", handlers.onFitParis);
    document.getElementById("toggle-details").addEventListener("click", () => UI.toggleDetails(true));
    document.getElementById("set-zone-a").addEventListener("click", handlers.onSetZoneA);
    document.getElementById("set-zone-b").addEventListener("click", handlers.onSetZoneB);
    document.getElementById("clear-comparison").addEventListener("click", handlers.onClearComparison);
  }

  return { bind };
})();



