// 全球市场: data fetching (Yahoo proxy, Futu/AKShare, usdata, China macro) and load orchestration.

async function fetchWithFallback(url) {
  const servedLocally = ["localhost", "127.0.0.1"].includes(location.hostname);
  const candidates = servedLocally
    ? [`/api/proxy?url=${encodeURIComponent(url)}`]
    : [
        url,
        `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
        `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`
      ];
  let lastError;
  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("数据请求失败");
}

function transformInverted(row) {
  if (![row.open, row.high, row.low, row.close].every(Number.isFinite)) return row;
  return {
    ...row,
    open: 1 / row.open,
    high: 1 / row.low,
    low: 1 / row.high,
    close: 1 / row.close
  };
}

async function fetchAkshareMarket(asset, range) {
  const response = await fetch(
    `/api/akshare?symbol=${encodeURIComponent(asset.akshareSymbol)}&range=${encodeURIComponent(range)}`,
    { cache: "no-store" }
  );
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  if (!Array.isArray(payload.rows) || !payload.rows.length) {
    throw new Error(`${asset.name} 无 AKShare 数据`);
  }
  return payload.rows.filter(row => Number.isFinite(row.close));
}

async function fetchYahoo(key, asset, range = state.range) {
  return cachedDataPoints(`market:${key}:${range}`, async () => {
    const servedLocally = ["localhost", "127.0.0.1"].includes(location.hostname);
    if (servedLocally && asset.futu) {
      try {
        const response = await fetch(`/api/futu?asset=${encodeURIComponent(key)}&range=${encodeURIComponent(range)}`, {
          cache: "no-store"
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.error || `HTTP ${response.status}`);
        }
        const payload = await response.json();
        if (!Array.isArray(payload.rows) || !payload.rows.length) {
          throw new Error(`${asset.name} 无 OpenD 数据`);
        }
        state.futuErrors.delete(key);
        return payload.rows.filter(row => Number.isFinite(row.close));
      } catch (error) {
        console.warn(`${asset.name} OpenD fallback`, error);
        state.futuErrors.set(key, error.message);
      }
    }
    if (asset.akshareSymbol) return fetchAkshareMarket(asset, range);
    const option = RANGE_OPTIONS[range];
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(asset.symbol)}?range=${option.range}&interval=${option.interval}&includePrePost=false&events=div%2Csplits`;
    const response = await fetchWithFallback(url);
    const payload = await response.json();
    const result = payload.chart?.result?.[0];
    if (!result) throw new Error(payload.chart?.error?.description || `${asset.name} 无数据`);
    const quote = result.indicators?.quote?.[0] || {};
    const rows = (result.timestamp || []).map((timestamp, index) => {
      const row = {
        time: timestamp * 1000,
        open: quote.open?.[index],
        high: quote.high?.[index],
        low: quote.low?.[index],
        close: quote.close?.[index],
        volume: quote.volume?.[index]
      };
      return asset.invert ? transformInverted(row) : row;
    }).filter(row => Number.isFinite(row.close));
    return range === "20y" ? filterSeriesRange(rows, range) : rows;
  });
}

function rangeStart(range = state.range) {
  const now = new Date();
  if (range === "1d") now.setDate(now.getDate() - 10);
  else if (range === "1mo") now.setMonth(now.getMonth() - 2);
  else if (range === "6mo") now.setMonth(now.getMonth() - 6);
  else if (range === "1y") now.setFullYear(now.getFullYear() - 1);
  else if (range === "5y") now.setFullYear(now.getFullYear() - 5);
  else if (range === "10y") now.setFullYear(now.getFullYear() - 10);
  else now.setFullYear(now.getFullYear() - 20);
  return now.toISOString().slice(0, 10);
}

async function fetchUsdataRate(asset, range = state.range) {
  const observations = usdataObservations(
    await fetchUsdata(),
    asset.usdataId
  );
  const cutoff = new Date(`${rangeStart(range)}T00:00:00Z`).getTime();
  const rows = observations.filter(row => row.time >= cutoff).map(row => {
    const value = Number(row.value);
    const close = Number.isFinite(value) ? value * (asset.multiplier || 1) : NaN;
    return {
      time: row.time,
      open: close, high: close, low: close, close
    };
  }).filter(row => Number.isFinite(row.close));
  if (range === "1d") return rows.slice(-2);
  if (range === "1mo") return rows.slice(-23);
  return rows;
}

async function fetchUsdata() {
  if (!state.usdataPromise) {
    state.usdataPromise = fetch("/api/usdata", { cache: "no-store" }).then(async response => {
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || `HTTP ${response.status}`);
      }
      return response.json();
    });
  }
  return state.usdataPromise;
}

function usdataObservations(payload, id) {
  const observations = payload.series?.[id]?.observations;
  if (!Array.isArray(observations)) throw new Error(`usdata 缺少 ${id}`);
  return observations.map(row => ({
    time: new Date(`${row.date}T00:00:00Z`).getTime(),
    value: row.value === null || row.value === undefined || row.value === ""
      ? NaN
      : Number(row.value)
  })).filter(row => Number.isFinite(row.time));
}

function transformMacroSeries(asset, observations) {
  const values = observations.map((row, index) => {
    let value;
    if (asset.transform === "diff") {
      value = index ? row.value - observations[index - 1].value : NaN;
    } else if (asset.transform === "yoy") {
      const prior = observations[index - 12]?.value;
      value = prior ? (row.value / prior - 1) * 100 : NaN;
    } else {
      value = row.value;
    }
    return { time: row.time, open: value, high: value, low: value, close: value };
  }).filter(row => Number.isFinite(row.close));
  return values;
}

function filterSeriesRange(rows, range = state.range) {
  if (range === "1d" || range === "1mo") return rows.slice(-2);
  const cutoff = new Date(`${rangeStart(range)}T00:00:00Z`).getTime();
  return rows.filter(row => row.time >= cutoff);
}

function macroHistoryYears(range = state.range) {
  return Math.max(3, { "1d": 1, "1mo": 1, "6mo": 1, "1y": 1, "5y": 5, "10y": 10, "20y": 20 }[range] || 3);
}

async function fetchChinaMacroHistory(range = state.range, targetSeries = state.series, storeFullSeries = true) {
  const now = new Date();
  const requests = Array.from({ length: macroHistoryYears(range) }, async (_, index) => {
    const end = new Date(now);
    end.setFullYear(now.getFullYear() - index);
    const start = new Date(end);
    start.setFullYear(end.getFullYear() - 1);
    const url = `https://economic-calendar.tradingview.com/events?from=${encodeURIComponent(start.toISOString())}&to=${encodeURIComponent(end.toISOString())}&countries=CN`;
    const response = await fetchWithFallback(url);
    const payload = await response.json();
    if (!Array.isArray(payload.result)) throw new Error("中国宏观历史接口格式错误");
    return payload.result;
  });
  const events = (await Promise.all(requests)).flat();
  ["cnCpi", "cnPpi", "cnRate"].forEach(key => {
    const asset = ASSETS[key];
    const byDate = new Map();
    events.filter(event =>
      event.country === "CN" &&
      event.title === asset.calendarTitle &&
      Number.isFinite(Number(event.actual))
    ).forEach(event => {
      const time = new Date(event.date).getTime();
      const value = Number(event.actual);
      byDate.set(time, { time, open: value, high: value, low: value, close: value });
    });
    const fullSeries = [...byDate.values()].sort((a, b) => a.time - b.time);
    if (storeFullSeries) state.macroAll[key] = fullSeries;
    targetSeries[key] = filterSeriesRange(fullSeries, range);
  });
}

async function fetchMacroAssets(range = state.range, targetSeries = state.series, storeFullSeries = true) {
  const chinaHistory = fetchChinaMacroHistory(range, targetSeries, storeFullSeries);
  const payload = await fetchUsdata();
  const observationsByKey = Object.fromEntries(
    Object.entries(ASSETS)
      .filter(([, asset]) => asset.usdataId)
      .map(([key, asset]) => [key, usdataObservations(payload, asset.usdataId)])
  );
  await chinaHistory;
  Object.entries(ASSETS).filter(([, asset]) => asset.usdataId).forEach(([key, asset]) => {
    const fullSeries = transformMacroSeries(asset, observationsByKey[key]);
    if (storeFullSeries) state.macroAll[key] = fullSeries;
    targetSeries[key] = filterSeriesRange(fullSeries, range);
  });
}

async function loadAssetSeries(key, range = state.range, targetSeries = state.series) {
  const asset = ASSETS[key];
  if (!asset) throw new Error(`未知资产 ${key}`);
  if (asset.kind === "macro") {
    await fetchMacroAssets(range, targetSeries, targetSeries === state.series);
    return;
  }
  targetSeries[key] = asset.source === "usdata"
    ? await fetchUsdataRate(asset, range)
    : await fetchYahoo(key, asset, range);
}

function mergeSeriesRows(history = [], recent = []) {
  const rowsByTime = new Map(history.map(row => [row.time, row]));
  recent.forEach(row => rowsByTime.set(row.time, row));
  return [...rowsByTime.values()].sort((a, b) => a.time - b.time);
}

function marketChartRows(key) {
  return ASSETS[key]?.kind === "macro"
    ? state.macroAll[key] || state.series[key]
    : state.marketAll[key] || state.series[key];
}

function preloadMarketHistory(key) {
  const asset = ASSETS[key];
  if (!asset || asset.kind === "macro") return Promise.resolve();
  if (state.marketAll[key]?.length) return Promise.resolve(state.marketAll[key]);
  if (marketHistoryPromises.has(key)) return marketHistoryPromises.get(key);

  const promise = (asset.source === "usdata"
    ? fetchUsdataRate(asset, "20y")
    : fetchYahoo(key, asset, "20y")
  ).then(rows => {
    state.marketAll[key] = mergeSeriesRows(rows, state.series[key]);
    if (state.active === key) renderMarketCandleChart();
    if (state.selected.has(key)) renderMarketCompareChart();
    return state.marketAll[key];
  }).catch(error => {
    console.warn(`preload history ${key}`, error);
  }).finally(() => {
    marketHistoryPromises.delete(key);
  });
  marketHistoryPromises.set(key, promise);
  return promise;
}

async function preloadAllMarketDataPoints(keys) {
  const queue = [...new Set(keys)]
    .filter(key => ASSETS[key] && ASSETS[key].kind !== "macro")
    .sort((a, b) => Number(b === state.active) - Number(a === state.active));
  const workers = Array.from({ length: Math.min(4, queue.length) }, async () => {
    while (queue.length) await preloadMarketHistory(queue.shift());
  });
  await Promise.all(workers);
}

async function loadSeries(range, targetSeries, storeFullSeries = false, keys = Object.keys(ASSETS)) {
  const requested = new Set(keys);
  const assetsByPriority = Object.entries(ASSETS)
    .filter(([key, asset]) => requested.has(key) && asset.kind !== "macro")
    .sort(([, a], [, b]) => Number(Boolean(a.source)) - Number(Boolean(b.source)));
  const tasks = assetsByPriority.map(async ([key, asset]) => {
    try {
      targetSeries[key] = asset.source === "usdata"
        ? await fetchUsdataRate(asset, range)
        : await fetchYahoo(key, asset, range);
      return { key, ok: true };
    } catch (error) {
      console.error(key, error);
      targetSeries[key] = [];
      return { key, ok: false, error: error.message };
    }
  });
  const needsMacro = [...requested].some(key => ASSETS[key]?.kind === "macro") || storeFullSeries;
  if (needsMacro) tasks.push((async () => {
    try {
      await fetchMacroAssets(range, targetSeries, storeFullSeries);
      return { key: "macro", name: "宏观历史数据", ok: true };
    } catch (error) {
      console.error("macro assets", error);
      Object.entries(ASSETS).filter(([, asset]) => asset.kind === "macro").forEach(([key]) => {
        targetSeries[key] = [];
      });
      return { key: "macro", name: "宏观历史数据", ok: false, error: error.message };
    }
  })());
  return Promise.all(tasks);
}

async function loadMarkets() {
  state.loading = true;
  state.usdataPromise = null;
  setStatus("loading", "正在更新市场数据...");
  const requiredKeys = new Set([...state.tickers, ...state.selected]);
  const results = await loadSeries(state.range, state.series, true, requiredKeys);
  Object.keys(state.marketAll).forEach(key => {
    state.marketAll[key] = mergeSeriesRows(state.marketAll[key], state.series[key]);
  });
  const failures = results.filter(result => !result.ok);
  state.loading = false;
  if (failures.length === results.length) {
    setStatus("error", "市场数据连接失败");
    showError("浏览器无法连接行情数据源。可稍后刷新，或使用本地 HTTP 服务打开本页以避免浏览器的跨域限制。");
  } else {
    const unavailable = failures.map(x => x.name || ASSETS[x.key].name);
    if (state.futuErrors.size) {
      const fallbackAssets = [...state.futuErrors.keys()].map(key => ASSETS[key]?.name || key);
      const permissionErrors = [...state.futuErrors.values()].filter(message =>
        /无权限|权限不足|行情权限/.test(message)
      );
      const onlyPermissionErrors = permissionErrors.length === state.futuErrors.size;
      setStatus(
        "error",
        onlyPermissionErrors
          ? `Futu ${fallbackAssets.join("、")}行情权限不足 · 已回退 Yahoo`
          : "Futu OpenD 连接失败 · 已回退 Yahoo"
      );
      showError([
        onlyPermissionErrors
          ? `Futu OpenD 已连接，但账号没有${fallbackAssets.join("、")}行情权限；当前使用 Yahoo Finance 数据。`
          : `Futu OpenD 连接失败；${fallbackAssets.join("、")}当前使用 Yahoo Finance 数据。`,
        unavailable.length ? `暂时无法载入：${unavailable.join("、")}` : ""
      ].filter(Boolean).join(" "));
    } else {
      const connectedSources = connectedDataSources(results);
      setStatus(
        failures.length ? "error" : "live",
        failures.length
          ? `部分数据不可用 · ${failures.length} 项`
          : `实时数据已连接 [${connectedSources}]`
      );
      showError(unavailable.length ? `暂时无法载入：${unavailable.join("、")}` : "");
    }
  }
  renderAll();
}

async function loadCorrelationData() {
  const requestId = ++correlationState.requestId;
  const range = correlationState.range;
  const nextSeries = {};
  correlationState.loading = true;
  const button = document.getElementById("refreshBtn");
  button.textContent = "更新中";
  button.disabled = true;
  try {
    const results = await loadSeries(range, nextSeries, false, correlationState.selected);
    if (requestId !== correlationState.requestId) return;
    correlationState.series = nextSeries;
    if (results.every(result => !result.ok)) {
      document.getElementById("correlationChart").innerHTML =
        '<div class="empty">相关性数据加载失败，请稍后刷新</div>';
      return;
    }
    renderCorrelation();
  } finally {
    if (requestId !== correlationState.requestId) return;
    correlationState.loading = false;
    button.textContent = "刷新";
    button.disabled = false;
  }
}
