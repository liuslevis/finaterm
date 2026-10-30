// 全球市场: candle/compare charts, K-line aggregation and fixed calendar time axis.

const charts = {
  market: createFinancialChart(document.getElementById("marketChart")),
  marketCompare: createFinancialChart(document.getElementById("marketCompareChart")),
  macro: createFinancialChart(document.getElementById("macroChart"))
};

function klineBucketTime(timestamp, period) {
  const date = new Date(timestamp);
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth();
  const day = date.getUTCDate();
  if (period === "day") return Date.UTC(year, month, day);
  if (period === "week") {
    const daysSinceMonday = (date.getUTCDay() + 6) % 7;
    return Date.UTC(year, month, day - daysSinceMonday);
  }
  if (period === "month") return Date.UTC(year, month, 1);
  if (period === "quarter") return Date.UTC(year, Math.floor(month / 3) * 3, 1);
  if (period === "half-year") return Date.UTC(year, month < 6 ? 0 : 6, 1);
  return Date.UTC(year, 0, 1);
}

function aggregateKlineRows(rows, period = state.klinePeriod) {
  let periodCache = klineAggregationCache.get(rows);
  if (!periodCache) {
    periodCache = new Map();
    klineAggregationCache.set(rows, periodCache);
  }
  const cached = periodCache.get(period);
  if (cached) return cached;
  const buckets = new Map();
  rows.forEach(row => {
    if (![row.open, row.high, row.low, row.close].every(Number.isFinite)) return;
    const time = klineBucketTime(row.time, period);
    const current = buckets.get(time);
    if (!current) {
      buckets.set(time, {
        time,
        open: row.open,
        high: row.high,
        low: row.low,
        close: row.close,
        ...(Number.isFinite(row.volume) ? { volume: row.volume } : {})
      });
      return;
    }
    current.high = Math.max(current.high, row.high);
    current.low = Math.min(current.low, row.low);
    current.close = row.close;
    if (Number.isFinite(row.volume)) current.volume = (current.volume || 0) + row.volume;
  });
  const aggregated = [...buckets.values()];
  periodCache.set(period, aggregated);
  return aggregated;
}

const CALENDAR_DAY = 86400;

function captureMarketRange(chart) {
  const range = chart.api.timeScale().getVisibleLogicalRange();
  if (!range || !chart.calendar) return null;
  return {
    from: chart.calendar.from + range.from * CALENDAR_DAY,
    to: chart.calendar.from + range.to * CALENDAR_DAY
  };
}

function ensureMarketCalendar(chart, visibleRange) {
  const today = chartTime(klineBucketTime(Date.now(), "day"));
  let from = chartTime(new Date(`${rangeStart("20y")}T00:00:00Z`).getTime());
  let to = today;
  new Set([...state.tickers, ...state.selected, state.active]).forEach(key => {
    const rows = marketChartRows(key);
    if (!rows?.length) return;
    from = Math.min(from, chartTime(klineBucketTime(rows[0].time, "day")));
    from = Math.min(from, chartTime(klineBucketTime(rows[0].time, state.klinePeriod)));
    to = Math.max(to, chartTime(klineBucketTime(rows[rows.length - 1].time, "day")));
  });
  if (visibleRange) {
    from = Math.min(from, Math.floor(visibleRange.from / CALENDAR_DAY) * CALENDAR_DAY);
    to = Math.max(to, Math.ceil(visibleRange.to / CALENDAR_DAY) * CALENDAR_DAY);
  }
  if (chart.calendar) {
    from = Math.min(from, chart.calendar.from);
    to = Math.max(to, chart.calendar.to);
    if (from === chart.calendar.from && to === chart.calendar.to) return;
  } else {
    // A hidden endpoint anchors scrolling even beyond the last real observation.
    chart.calendar = {
      series: chart.api.addSeries(LightweightCharts.LineSeries, {
        priceScaleId: "calendar",
        visible: false,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      })
    };
    chart.api.applyOptions({ rightPriceScale: { minimumWidth: 104 } });
  }
  const dates = [];
  for (let time = from; time <= to; time += CALENDAR_DAY) dates.push({ time });
  dates[dates.length - 1] = { time: to, value: 0 };
  chart.calendar.series.setData(dates);
  chart.calendar.from = from;
  chart.calendar.to = to;
}

function restoreMarketRange(chart, visibleRange) {
  const range = visibleRange || {
    from: chartTime(new Date(`${rangeStart()}T00:00:00Z`).getTime()),
    to: chartTime(klineBucketTime(Date.now(), "day"))
  };
  chart.api.timeScale().setVisibleLogicalRange({
    from: (range.from - chart.calendar.from) / CALENDAR_DAY,
    to: (range.to - chart.calendar.from) / CALENDAR_DAY
  });
}

function ohlcChartRows(rows) {
  return rows.map(row => ({
    time: chartTime(Number(row.time)),
    open: Number(row.open),
    high: Number(row.high),
    low: Number(row.low),
    close: Number(row.close)
  })).filter(row =>
    Number.isFinite(row.time) &&
    [row.open, row.high, row.low, row.close].every(Number.isFinite) &&
    row.high >= Math.max(row.open, row.close) &&
    row.low <= Math.min(row.open, row.close)
  );
}

function volumeChartRows(rows) {
  return rows.map(row => ({
    time: chartTime(Number(row.time)),
    value: Number(row.volume),
    color: Number(row.close) >= Number(row.open) ? "#ff657780" : "#32d49a80"
  })).filter(row => Number.isFinite(row.time) && Number.isFinite(row.value));
}

function formatVolume(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "";
  if (Math.abs(amount) >= 1e9) return `${(amount / 1e9).toFixed(2)}B`;
  if (Math.abs(amount) >= 1e6) return `${(amount / 1e6).toFixed(2)}M`;
  if (Math.abs(amount) >= 1e3) return `${(amount / 1e3).toFixed(2)}K`;
  return amount.toFixed(0);
}

function renderMarketCandleChart() {
  const selectedKeys = [...state.selected].filter(key => state.series[key]?.length);
  const activeKey = state.series[state.active]?.length ? state.active : selectedKeys[0];
  const sourceRows = activeKey ? marketChartRows(activeKey) : null;
  const renderKeys = [activeKey].filter(Boolean);
  const renderKey = `${activeKey || ""}:${state.klinePeriod}`;
  const cache = marketRenderCache.candle;
  const unchanged = cache.key === renderKey &&
    renderKeys.every(key => cache.series.get(key) === sourceRows);
  if (unchanged && !state.resetMarketRange) return;
  cache.key = renderKey;
  cache.series = new Map(renderKeys.map(key => [key, sourceRows]));

  const timeScale = charts.market.api.timeScale();
  const visibleRange = state.resetMarketRange ? null : captureMarketRange(charts.market);
  state.marketRangeChangeBlockedUntil = performance.now() + 300;
  ensureMarketCalendar(charts.market, visibleRange);
  charts.market.api.applyOptions({ leftPriceScale: { visible: false } });
  if (!activeKey) {
    showChartEmpty(charts.market, "暂无市场数据");
    return;
  }
  clearChart(charts.market);
  state.active = activeKey;
  const asset = ASSETS[activeKey];
  document.getElementById("chartTitle").textContent =
    `${asset.name} · ${asset.kind === "macro" ? "历史走势" : KLINE_PERIODS[state.klinePeriod].label}`;
  const rows = aggregateKlineRows(sourceRows);
  const useCandlesticks = asset.chartType === "candlestick" || asset.kind !== "macro";
  const volumeData = useCandlesticks ? volumeChartRows(rows) : [];
  const series = !useCandlesticks
    ? charts.market.api.addSeries(LightweightCharts.AreaSeries, {
        lineColor: asset.color,
        topColor: `${asset.color}30`,
        bottomColor: `${asset.color}03`,
        lineWidth: 2,
        priceFormat: priceFormat(activeKey)
      })
    : charts.market.api.addSeries(LightweightCharts.CandlestickSeries, {
        upColor: "#ff6577",
        downColor: "#32d49a",
        borderVisible: false,
        wickUpColor: "#ff6577",
        wickDownColor: "#32d49a",
        priceFormat: priceFormat(activeKey)
      });
  series.setData(useCandlesticks
    ? ohlcChartRows(rows)
    : rows.map(row => ({ time: chartTime(row.time), value: row.close })));
  charts.market.series.push(series);
  const legendItems = [{
    label: asset.name,
    color: asset.color,
    series,
    formatter: data => "value" in data
      ? formatValue(activeKey, data.value)
      : `O ${formatValue(activeKey, data.open)}  H ${formatValue(activeKey, data.high)}  L ${formatValue(activeKey, data.low)}  C ${formatValue(activeKey, data.close)}`
  }];
  if (volumeData.length) {
    series.priceScale().applyOptions({ scaleMargins: { top: .08, bottom: .28 } });
    const volumeSeries = charts.market.api.addSeries(LightweightCharts.HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      priceLineVisible: false,
      lastValueVisible: false
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: .78, bottom: 0 }
    });
    volumeSeries.setData(volumeData);
    charts.market.series.push(volumeSeries);
    legendItems.push({
      label: "成交量",
      color: "#718796",
      series: volumeSeries,
      formatter: data => formatVolume(data.value)
    });
  }
  setChartLegend(charts.market, legendItems);
  state.marketRangeChangeBlockedUntil = performance.now() + 300;
  restoreMarketRange(charts.market, visibleRange);
  state.marketLogicalRange = timeScale.getVisibleLogicalRange();
}

function renderMarketCompareChart() {
  const selectedKeys = [...state.selected].filter(key => state.series[key]?.length);
  const renderKey = selectedKeys.join(",");
  const rowsByKey = new Map(selectedKeys.map(key => [key, marketChartRows(key)]));
  const cache = marketRenderCache.compare;
  const unchanged = cache.key === renderKey &&
    selectedKeys.every(key => cache.series.get(key) === rowsByKey.get(key));
  if (unchanged && !state.resetMarketRange) return;
  cache.key = renderKey;
  cache.series = rowsByKey;

  const chart = charts.marketCompare;
  const visibleRange = state.resetMarketRange ? null : captureMarketRange(chart);
  ensureMarketCalendar(chart, visibleRange);
  const useDualPriceScales = selectedKeys.length === 2;
  const hasZeroBaseline = selectedKeys.some(key =>
    rowsByKey.get(key).find(row => Number.isFinite(row.close))?.close === 0
  );
  const useZScore = selectedKeys.length > 2 ||
    selectedKeys.some(key => ASSETS[key].kind === "macro") ||
    hasZeroBaseline;
  chart.api.applyOptions({ leftPriceScale: { visible: useDualPriceScales } });
  document.getElementById("compareChartTitle").textContent = useZScore
    ? "多资产标准化对比 · Z-score"
    : "多资产归一化对比 · 起点 = 100";
  if (!selectedKeys.length) {
    showChartEmpty(chart, "请选择要对比的资产");
    return;
  }

  clearChart(chart);
  const legendItems = [];
  selectedKeys.forEach((key, index) => {
    const rows = aggregateKlineRows(rowsByKey.get(key), "day");
    const values = rows.map(x => x.close).filter(Number.isFinite);
    const first = values[0];
    if (!useZScore && first === 0) return;
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
    const deviation = Math.sqrt(variance) || 1;
    const series = chart.api.addSeries(LightweightCharts.LineSeries, {
      color: ASSETS[key].color,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      priceScaleId: useDualPriceScales && index === 0 ? "left" : "right",
      priceFormat: {
        type: "custom",
        minMove: useZScore ? .1 : 1,
        formatter: value => useZScore ? value.toFixed(1) : value.toFixed(0)
      }
    });
    const normalizedData = rows.map(row => ({
      time: chartTime(row.time),
      value: useZScore
        ? +((row.close - mean) / deviation).toFixed(3)
        : +(row.close / first * 100).toFixed(3)
    }));
    series.setData(normalizedData);
    chart.series.push(series);
    legendItems.push({
      label: useDualPriceScales
        ? `${ASSETS[key].short} · ${index === 0 ? "左轴" : "右轴"}`
        : ASSETS[key].short,
      color: ASSETS[key].color,
      series,
      data: normalizedData,
      carryForward: true,
      formatter: data => useZScore ? data.value.toFixed(2) : data.value.toFixed(1)
    });
  });
  setChartLegend(chart, legendItems);
  restoreMarketRange(chart, visibleRange);
}

function renderMarketCharts() {
  renderMarketCandleChart();
  renderMarketCompareChart();
  state.resetMarketRange = false;
}

function setActiveRangeButton(moduleId, range) {
  document.querySelectorAll(`[data-module-id="${moduleId}"] [data-range]`).forEach(button => {
    button.classList.toggle("active", button.dataset.range === range);
  });
}

async function loadMoreOnZoomOut() {
  const activeKey = state.active;
  if (!activeKey || state.marketAll[activeKey]?.length || state.lazyRangeLoading) return;
  state.lazyRangeLoading = true;
  try {
    await preloadMarketHistory(activeKey);
  } finally {
    state.lazyRangeLoading = false;
  }
}

function handleMarketVisibleLogicalRangeChange(range) {
  if (!range || performance.now() < state.marketRangeChangeBlockedUntil) return;
  const previous = state.marketLogicalRange;
  state.marketLogicalRange = range;
  if (!previous) return;
  const previousSpan = previous.to - previous.from;
  const span = range.to - range.from;
  const zoomedOut = span > previousSpan * 1.02;
  if (zoomedOut && range.from < 30) loadMoreOnZoomOut();
}

charts.market.api.timeScale().subscribeVisibleLogicalRangeChange(
  handleMarketVisibleLogicalRangeChange
);
