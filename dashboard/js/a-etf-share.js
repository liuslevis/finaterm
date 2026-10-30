// 国家队ETF tab (/api/a-etf-share).

const aesState = { data: null, loading: false, metric: "ratio", flowMode: "w", charts: {} };
const AES_SIGNED = new Set(["ratio_chg", "aum_ret", "shares_chg", "flow", "flow_pct_aum", "csi300_ret"]);
const AES_KEY = new Set(["ratio", "flow"]);

function aesTime(day) {
  return Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10)) / 1000;
}

function aesNum(value, digits = 0) {
  if (!Number.isFinite(value)) return "--";
  return value.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function aesSigned(value, digits = 0, suffix = "") {
  if (!Number.isFinite(value)) return "--";
  return `${value > 0 ? "+" : ""}${aesNum(value, digits)}${suffix}`;
}

function formatAesValue(column, value) {
  if (value === null || value === undefined) return "--";
  if (column.key === "ratio" || column.key === "ratio_chg") return value.toFixed(2);
  if (column.unit === "%" || column.unit === "pp" || column.unit === "亿份") return value.toFixed(1);
  if (column.unit === "亿") return aesNum(value, 0);
  return value.toFixed(1);
}

function aesKpiCards(data) {
  const kpi = data.kpi;
  const tone = value => (value < 0 ? "neg" : value > 0 ? "pos" : "");
  return [
    { label: "当前占比", value: `${kpi.ratio.toFixed(2)}%`, sub: `${kpi.as_of} · 距峰值 ${aesSigned(kpi.drawdown, 2, "pp")}`, tone: "" },
    { label: "窗口内变动", value: aesSigned(kpi.ratio_chg, 2, "pp"), sub: `相对 ${aesSigned(kpi.ratio_chg_pct, 1, "%")}（首日 ${kpi.ratio_first.toFixed(2)}%）`, tone: tone(kpi.ratio_chg) },
    { label: "区间峰值 / 谷值", value: `${kpi.peak.toFixed(2)}%`, sub: `${kpi.peak_date} · 谷值 ${kpi.trough.toFixed(2)}%（${kpi.trough_date}）`, tone: "" },
    { label: "四只ETF合计市值", value: `${aesNum(kpi.aum, 0)} 亿`, sub: `窗口内 ${aesSigned(kpi.aum_chg, 0, " 亿")}（${aesSigned(kpi.aum_chg_pct, 1, "%")}）`, tone: tone(kpi.aum_chg) },
    { label: "合计份额", value: `${aesNum(kpi.shares, 0)} 亿份`, sub: `窗口内 ${aesSigned(kpi.shares_chg, 0, " 亿份")}（${aesSigned(kpi.shares_chg_pct, 1, "%")}）`, tone: tone(kpi.shares_chg) },
    { label: "估算累计净申赎", value: `${aesSigned(kpi.flow, 0, " 亿")}`, sub: `近 20 日 ${aesSigned(kpi.flow_20d, 0, " 亿")}`, tone: tone(kpi.flow) },
    { label: "沪深300流通市值", value: `${aesNum(kpi.float_mcap / 1e4, 2)} 万亿`, sub: `CSI300 ${aesNum(kpi.csi300, 1)} · ${aesSigned(kpi.csi300_chg_pct, 1, "%")}`, tone: "" }
  ];
}

function renderAesMain() {
  const data = aesState.data;
  const chart = aesState.charts.main;
  const daily = data.daily;
  const isRatio = aesState.metric === "ratio";
  const primary = daily.filter(row => Number.isFinite(row[isRatio ? "ratio" : "aum"])).map(row => ({
    time: aesTime(row.d),
    value: row[isRatio ? "ratio" : "aum"]
  }));
  const csi = daily.filter(row => Number.isFinite(row.csi300)).map(row => ({ time: aesTime(row.d), value: row.csi300 }));

  clearChart(chart);
  const primarySeries = chart.api.addSeries(LightweightCharts.LineSeries, {
    color: isRatio ? "#38d7c5" : "#54a4ff",
    lineWidth: 2,
    priceFormat: isRatio ? { type: "price", precision: 2, minMove: .01 } : { type: "price", precision: 0, minMove: 1 },
    priceLineStyle: 2,
    priceLineWidth: 1
  });
  primarySeries.setData(primary);
  if (isRatio && Number.isFinite(data.kpi.peak)) {
    primarySeries.createPriceLine({
      price: data.kpi.peak, color: "rgba(245,189,89,.55)", lineWidth: 1, lineStyle: 2,
      axisLabelVisible: true, title: "区间峰值"
    });
  }
  const csiSeries = chart.api.addSeries(LightweightCharts.LineSeries, {
    color: "rgba(130,151,167,.85)",
    lineWidth: 1,
    priceScaleId: "left",
    priceFormat: { type: "price", precision: 0, minMove: 1 },
    priceLineVisible: false,
    crosshairMarkerVisible: false,
    lastValueVisible: false
  });
  csiSeries.setData(csi);
  chart.series = [primarySeries, csiSeries];
  setChartLegend(chart, [
    {
      label: isRatio ? "四只ETF市值 / 沪深300流通市值（%，右轴）" : "四只ETF合计市值（亿元，右轴）",
      color: isRatio ? "#38d7c5" : "#54a4ff",
      series: primarySeries,
      data: primary,
      formatter: point => (isRatio ? `${point.value.toFixed(2)}%` : `${aesNum(point.value, 0)} 亿`)
    },
    {
      label: "沪深300 收盘（左轴）",
      color: "#8297a7",
      series: csiSeries,
      data: csi,
      formatter: point => aesNum(point.value, 1)
    }
  ]);
  if (!primary.length) showChartEmpty(chart, "暂无数据");
  chart.api.timeScale().fitContent();
}

function renderAesFlow() {
  const data = aesState.data;
  const chart = aesState.charts.flow;
  const mode = aesState.flowMode;
  const buckets = new Map();
  data.daily.forEach(row => {
    if (!Number.isFinite(row.flow)) return;
    const time = aesTime(row.d);
    let bucket;
    if (mode === "d") bucket = time;
    else if (mode === "w") bucket = time - ((new Date(time * 1000).getUTCDay() + 6) % 7) * 86400;
    else bucket = Date.UTC(+row.d.slice(0, 4), +row.d.slice(5, 7) - 1, 1) / 1000;
    buckets.set(bucket, (buckets.get(bucket) || 0) + row.flow);
  });
  const ordered = [...buckets.entries()].sort((left, right) => left[0] - right[0]);
  const bars = ordered.map(([time, value]) => ({
    time,
    value,
    color: value >= 0 ? "rgba(50,212,154,.75)" : "rgba(255,101,119,.75)"
  }));
  let running = 0;
  const cumulative = ordered.map(([time, value]) => {
    running += value;
    return { time, value: running };
  });

  clearChart(chart);
  const barSeries = chart.api.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: "price", precision: 0, minMove: 1 },
    priceLineVisible: false,
    lastValueVisible: false
  });
  barSeries.setData(bars);
  const cumSeries = chart.api.addSeries(LightweightCharts.LineSeries, {
    color: "#f5bd59",
    lineWidth: 2,
    priceScaleId: "left",
    priceFormat: { type: "price", precision: 0, minMove: 1 },
    priceLineVisible: false,
    crosshairMarkerVisible: false,
    lastValueVisible: false
  });
  cumSeries.setData(cumulative);
  chart.series = [barSeries, cumSeries];
  setChartLegend(chart, [
    { label: "期间净申赎（亿元，右轴）", color: "#32d49a", series: barSeries, data: bars, formatter: point => `${aesSigned(point.value, 0, " 亿")}` },
    { label: "累计净申赎（亿元，左轴）", color: "#f5bd59", series: cumSeries, data: cumulative, formatter: point => `${aesNum(point.value, 0)} 亿` }
  ]);
  if (!bars.length) showChartEmpty(chart, "暂无申赎数据");
  chart.api.timeScale().fitContent();
}

function renderAesShares() {
  const data = aesState.data;
  const chart = aesState.charts.shares;
  clearChart(chart);
  const series = [];
  const legend = [];
  data.etfs.forEach(etf => {
    const points = data.daily
      .filter(row => Number.isFinite(row[`s_${etf.code}`]))
      .map(row => ({ time: aesTime(row.d), value: row[`s_${etf.code}`] }));
    const line = chart.api.addSeries(LightweightCharts.LineSeries, {
      color: etf.color,
      lineWidth: 2,
      priceFormat: { type: "price", precision: 0, minMove: 1 },
      priceLineVisible: false
    });
    line.setData(points);
    series.push(line);
    legend.push({
      label: etf.short,
      color: etf.color,
      series: line,
      data: points,
      formatter: point => `${aesNum(point.value, 1)} 亿份`
    });
  });
  chart.series = series;
  setChartLegend(chart, legend);
  if (!legend.some(item => item.data.length)) showChartEmpty(chart, "暂无份额数据");
  chart.api.timeScale().fitContent();
}

function renderAesTable() {
  const data = aesState.data;
  const columns = data.columns;
  const groups = [];
  columns.forEach(column => {
    const previous = groups[groups.length - 1];
    if (previous && previous.name === column.group) previous.span += 1;
    else groups.push({ name: column.group, span: 1 });
  });
  document.getElementById("aesHead").innerHTML =
    `<tr class="asd-groups"><th></th>${groups.map(group => `<th colspan="${group.span}">${escapeHtml(group.name)}</th>`).join("")}</tr>` +
    `<tr><th>月份</th>${columns.map(column =>
      `<th>${escapeHtml(column.label)}${column.unit ? `<small>${escapeHtml(column.unit)}</small>` : ""}</th>`).join("")}</tr>`;
  document.getElementById("aesTable").innerHTML = [...data.monthly].reverse().map(row =>
    `<tr><td>${escapeHtml(row.month)}</td>${columns.map(column => {
      const value = row[column.key];
      const tone = AES_SIGNED.has(column.key) && value ? (value > 0 ? "pos" : "neg") : "";
      const key = AES_KEY.has(column.key) ? "asd-key" : "";
      return `<td class="${tone} ${key}">${formatAesValue(column, value)}</td>`;
    }).join("")}</tr>`).join("");
}

function renderAes() {
  const data = aesState.data;
  if (!data) return;
  const kpi = data.kpi;
  document.getElementById("aesNote").textContent =
    `${data.display[0]} ~ ${data.display[1]} · 四只ETF合计 ${aesNum(kpi.aum, 0)} 亿元 ÷ 沪深300流通市值 ` +
    `${aesNum(kpi.float_mcap / 1e4, 2)} 万亿 = ${kpi.ratio.toFixed(2)}% · ${kpi.as_of} · 生成于 ${data.generated_at.replace("T", " ")}`;

  document.getElementById("aesKpis").innerHTML = aesKpiCards(data).map(card =>
    `<article class="aes-kpi ${card.tone}"><div class="aes-kpi-label">${escapeHtml(card.label)}</div>` +
    `<div class="aes-kpi-value">${escapeHtml(card.value)}</div>` +
    `<div class="aes-kpi-sub">${escapeHtml(card.sub)}</div></article>`).join("");

  if (!aesState.charts.main) {
    aesState.charts.main = createFinancialChart(document.getElementById("aesChart"));
    aesState.charts.main.api.priceScale("left").applyOptions({ visible: true });
    aesState.charts.flow = createFinancialChart(document.getElementById("aesFlowChart"));
    aesState.charts.flow.api.priceScale("left").applyOptions({ visible: true });
    aesState.charts.shares = createFinancialChart(document.getElementById("aesSharesChart"));
  }
  renderAesMain();
  renderAesFlow();
  renderAesShares();
  renderAesTable();

  document.getElementById("aesSource").innerHTML =
    `${escapeHtml(data.formula)}。数据来源：${escapeHtml(data.source)}。` +
    `<ul>${data.caveats.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>` +
    `刷新：<code>cd dashboard; uv run python tab/a-etf-share/build_panel.py --refresh</code>` +
    `（设计说明见 tab/a-etf-share/SKILL.md）`;
}

async function loadAes() {
  if (aesState.loading) return;
  if (aesState.data) return renderAes();
  aesState.loading = true;
  document.getElementById("aesNote").textContent = "正在加载国家队ETF占比面板...";
  try {
    const response = await fetch("/api/a-etf-share", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    aesState.data = payload;
    renderAes();
  } catch (error) {
    console.error("a-etf-share", error);
    document.getElementById("aesNote").textContent = `国家队ETF占比数据暂不可用：${error.message}`;
  } finally {
    aesState.loading = false;
  }
}

document.querySelectorAll("[data-aes-metric]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-aes-metric]").forEach(item => item.classList.toggle("active", item === button));
    aesState.metric = button.dataset.aesMetric;
    if (aesState.data) renderAesMain();
  });
});
document.querySelectorAll("[data-aes-flow]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-aes-flow]").forEach(item => item.classList.toggle("active", item === button));
    aesState.flowMode = button.dataset.aesFlow;
    if (aesState.data) renderAesFlow();
  });
});
