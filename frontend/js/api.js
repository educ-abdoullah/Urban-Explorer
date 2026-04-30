const Api = (() => {
  const levelCache = new Map();

  async function request(path, params = {}) {
    const url = new URL(`${API_BASE_URL}${path}`);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Erreur API ${response.status} sur ${url.pathname}`);
    }
    return response.json();
  }

  function health() {
    return request("/health");
  }

  function getLevels() {
    return request("/levels");
  }

  function getFields(level) {
    return request("/fields", { level });
  }

  async function getAreas(level, includeGeometry = true) {
    const cacheKey = `${level}:${includeGeometry}`;
    if (levelCache.has(cacheKey)) {
      return levelCache.get(cacheKey);
    }

    const pageSize = 1000;
    let skip = 0;
    const allDocs = [];

    while (true) {
      const docs = await request("/areas", {
        level,
        include_geometry: includeGeometry,
        limit: pageSize,
        skip
      });
      allDocs.push(...docs.map(normalizeDoc));
      if (docs.length < pageSize) break;
      skip += pageSize;
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    levelCache.set(cacheKey, allDocs);
    return allDocs;
  }

  function getArea(level, areaId) {
    return request(`/areas/${encodeURIComponent(level)}/${encodeURIComponent(areaId)}`, {
      include_geometry: true
    });
  }

  function getAreaProperties(level, areaId) {
    return request(`/areas/${encodeURIComponent(level)}/${encodeURIComponent(areaId)}/properties`);
  }

  function getIndicator(fieldName, level, includeGeometry = false) {
    return request(`/indicators/${encodeURIComponent(fieldName)}`, {
      level,
      include_geometry: includeGeometry
    });
  }

  function getRanking(fieldName, level, top = 10) {
    return request(`/indicators/${encodeURIComponent(fieldName)}/ranking`, { level, top });
  }

  function searchByName(query, level) {
    if (!query || query.trim().length < 2) return Promise.resolve([]);
    return request("/search/by-name", { q: query.trim(), level, limit: 20 });
  }

  function normalizeDoc(doc) {
    const demographicFields = ["profil_ideal", "score_senior", "score_actifs", "score_jeune_adulte", "score_junior"];
    const properties = { ...(doc.properties || {}) };
    demographicFields.forEach(field => {
      if (properties[field] === undefined && doc[field] !== undefined) {
        properties[field] = doc[field];
      }
    });
    return { ...doc, properties };
  }

  return {
    health,
    getLevels,
    getFields,
    getAreas,
    getArea,
    getAreaProperties,
    getIndicator,
    getRanking,
    searchByName
  };
})();


