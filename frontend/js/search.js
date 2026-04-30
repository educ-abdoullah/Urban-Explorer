const Search = (() => {
  const state = {
    arrondissement: [],
    quartiers: [],
    iris: []
  };

  function bind(onSelect, getState, ensureSearchFeatures) {
    setup(onSelect, ensureSearchFeatures);
  }

  async function setup(onSelect, ensureSearchFeatures) {
    const arrondissementSelect = document.getElementById("arrondissement-select");
    const arrondissementFilter = document.getElementById("arrondissement-filter");
    const quartierSelect = document.getElementById("quartier-select");
    const quartierFilter = document.getElementById("quartier-filter");
    const irisSelect = document.getElementById("iris-select");
    const irisFilter = document.getElementById("iris-filter");
    if (!arrondissementSelect || !quartierSelect || !irisSelect) return;

    const [arrFeatures, irisFeatures] = await Promise.all([
      ensureSearchFeatures("arrondissement"),
      ensureSearchFeatures("iris")
    ]);

    state.arrondissement = arrFeatures.map(feature => toItem(feature.properties, "arrondissement")).filter(Boolean)
      .sort((a, b) => Number(a.sort) - Number(b.sort));
    state.quartiers = uniqueBy(
      irisFeatures.map(feature => toItem(feature.properties, "quartier")).filter(Boolean),
      item => normalizeSearch(item.label)
    ).sort((a, b) => a.label.localeCompare(b.label, "fr"));
    state.iris = irisFeatures.map(feature => toItem(feature.properties, "iris")).filter(Boolean)
      .sort((a, b) => a.label.localeCompare(b.label, "fr"));

    fillSelect(arrondissementSelect, state.arrondissement, "Sélectionner un arrondissement");
    fillSelect(quartierSelect, state.quartiers, "Sélectionner un quartier");
    fillSelect(irisSelect, state.iris, "Sélectionner un IRIS");

    arrondissementSelect.addEventListener("change", () => selectItem(arrondissementSelect, onSelect));
    quartierSelect.addEventListener("change", () => selectItem(quartierSelect, onSelect));
    irisSelect.addEventListener("change", () => selectItem(irisSelect, onSelect));

    arrondissementFilter.addEventListener("input", () => {
      fillSelect(arrondissementSelect, filterItems(state.arrondissement, arrondissementFilter.value), "Sélectionner un arrondissement");
    });
    quartierFilter.addEventListener("input", () => {
      fillSelect(quartierSelect, filterItems(state.quartiers, quartierFilter.value), "Sélectionner un quartier");
    });
    irisFilter.addEventListener("input", () => {
      fillSelect(irisSelect, filterItems(state.iris, irisFilter.value), "Sélectionner un IRIS");
    });
  }

  function toItem(props, type) {
    if (type === "arrondissement") {
      const arr = Number(props.arrondissement ?? props.c_ar ?? props.id);
      return {
        id: props.id,
        level: "arrondissement",
        label: props.name || `${arr}e arrondissement`,
        meta: props.code_commune || `Paris ${arr}`,
        sort: arr
      };
    }

    if (type === "quartier") {
      if (!props.nom_quartier) return null;
      return {
        id: props.id,
        level: "iris",
        label: props.nom_quartier,
        meta: props.arrondissement ? `Paris ${props.arrondissement}` : ""
      };
    }

    return {
      id: props.id,
      level: "iris",
      label: props.nom_iris || props.name,
      meta: props.code_iris || props.nom_quartier || ""
    };
  }

  function fillSelect(select, items, placeholder) {
    select.innerHTML = `<option value="">${placeholder}</option>` + items.map(item => (
      `<option value="${escapeHtml(item.id)}" data-level="${escapeHtml(item.level)}">${escapeHtml(item.label)}${item.meta ? ` · ${escapeHtml(item.meta)}` : ""}</option>`
    )).join("");
  }

  function selectItem(select, onSelect) {
    const option = select.selectedOptions[0];
    if (!option.value) return;
    onSelect(option.dataset.level, option.value);
  }

  function filterItems(items, query) {
    const normalized = normalizeSearch(query);
    if (!normalized) return items;
    return items.filter(item => normalizeSearch(`${item.label} ${item.meta} ${item.id}`).includes(normalized));
  }

  function uniqueBy(items, keyFn) {
    const map = new Map();
    items.forEach(item => {
      const key = keyFn(item);
      if (!map.has(key)) map.set(key, item);
    });
    return [...map.values()];
  }

  function normalizeSearch(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  return { bind };
})();


