// A股供需 tab (/api/a-supply-demand).

const asdState = { data: null, chart: null, mode: "gap", loading: false };
const ASD_KEY_COLUMNS = new Set(["net_supply", "demand", "gap", "gap_ex_div", "csi300_ret"]);
const ASD_SIGNED_COLUMNS = new Set(["gap", "gap_bp", "gap_z6", "gap_ex_div", "gap_ex_div_bp", "gap_ex_div_z6", "csi300_ret", "demand", "margin", "etf"]);

function formatAsdValue(column, value) {
  if (value === null || value === undefined) return "--";
  if (column.unit === "" || column.key.endsWith("_z6")) return value.toFixed(2);
  if (column.unit === "%" || column.unit === "bp") return value.toFixed(1);
  return Math.round(value).toLocaleString("zh-CN");
}

function renderAsd() {
  const data = asdState.data;
  if (!data) return;
  const mode = asdState.mode;
  const label = mode === "gap" ? "供需差" : "供需差(扣分红)";
  const last = data.rows[data.rows.length - 1];
  document.getElementById("asdNote").textContent =
    `${data.display[0]} ~ ${data.display[1]} · 单位 ${data.unit} · 生成于 ${data.generated_at.replace("T", " ")}` +
    (last ? ` · ${last.month} ${label} ${formatAsdValue({ unit: "亿", key: "" }, last[mode])} 亿，z6 ${formatAsdValue({ unit: "", key: "" }, last[`${mode}_z6`])}` : "");

  if (!asdState.chart) {
    asdState.chart = createFinancialChart(document.getElementById("asdChart"));
    asdState.chart.api.priceScale("left").applyOptions({ visible: true });
  }
  const chart = asdState.chart;
  clearChart(chart);
  const toTime = month => Date.UTC(+month.slice(0, 4), +month.slice(5, 7) - 1, 1) / 1000;
  const gapData = data.rows.filter(row => row[`${mode}_bp`] !== null).map(row => ({
    time: toTime(row.month),
    value: row[`${mode}_bp`],
    color: row[`${mode}_bp`] >= 0 ? "rgba(50,212,154,.75)" : "rgba(255,101,119,.75)"
  }));
  const csiData = data.rows.filter(row => row.csi300_ret !== null).map(row => ({ time: toTime(row.month), value: row.csi300_ret }));
  const gapSeries = chart.api.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: "price", precision: 1, minMove: .1 },
    priceLineVisible: false
  });
  gapSeries.setData(gapData);
  const csiSeries = chart.api.addSeries(LightweightCharts.LineSeries, {
    color: "#f5bd59",
    lineWidth: 2,
    priceScaleId: "left",
    pointMarkersVisible: true,
    priceFormat: { type: "price", precision: 1, minMove: .1 },
    priceLineVisible: false
  });
  csiSeries.setData(csiData);
  chart.series = [gapSeries, csiSeries];
  setChartLegend(chart, [
    { label: `${label}/沪深总市值 (bp，右轴)`, color: "#32d49a", series: gapSeries, data: gapData, formatter: point => `${point.value.toFixed(1)} bp` },
    { label: "CSI300 月涨幅 (%，左轴)", color: "#f5bd59", series: csiSeries, data: csiData, formatter: point => `${point.value.toFixed(1)}%` }
  ]);
  if (!gapData.length) showChartEmpty(chart, "暂无供需数据");
  chart.api.timeScale().fitContent();

  const columns = data.columns;
  const groups = [];
  columns.forEach(column => {
    const prev = groups[groups.length - 1];
    if (prev && prev.name === column.group) prev.span += 1;
    else groups.push({ name: column.group, span: 1 });
  });
  document.getElementById("asdHead").innerHTML =
    `<tr class="asd-groups"><th></th>${groups.map(group => `<th colspan="${group.span}">${escapeHtml(group.name)}</th>`).join("")}</tr>` +
    `<tr><th>月份</th>${columns.map(column =>
      `<th>${escapeHtml(column.label)}${column.unit ? `<small>${escapeHtml(column.unit)}</small>` : ""}</th>`).join("")}</tr>`;
  document.getElementById("asdTable").innerHTML = data.rows.map(row => `<tr><td>${escapeHtml(row.month)}</td>${columns.map(column => {
    const value = row[column.key];
    const tone = ASD_SIGNED_COLUMNS.has(column.key) && value ? (value > 0 ? "pos" : "neg") : "";
    const key = ASD_KEY_COLUMNS.has(column.key) ? "asd-key" : "";
    return `<td class="${tone} ${key}">${formatAsdValue(column, value)}</td>`;
  }).join("")}</tr>`).join("");
  document.getElementById("asdSource").innerHTML =
    `${escapeHtml(data.formula)}。数据来源：${escapeHtml(data.source)}。` +
    `<ul>${data.caveats.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>` +
    `刷新：<code>cd dashboard; uv run python tab/a-supply-demand/build_panel.py --refresh</code>（设计说明见 tab/a-supply-demand/SKILL.md）`;
}

async function loadAsd() {
  if (asdState.loading) return;
  if (asdState.data) return renderAsd();
  asdState.loading = true;
  document.getElementById("asdNote").textContent = "正在加载 A股供需面板...";
  try {
    const response = await fetch("/api/a-supply-demand", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    asdState.data = payload;
    renderAsd();
  } catch (error) {
    console.error("a-supply-demand", error);
    document.getElementById("asdNote").textContent = `A股供需数据暂不可用：${error.message}`;
  } finally {
    asdState.loading = false;
  }
}

document.querySelectorAll("[data-asd-mode]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-asd-mode]").forEach(item => item.classList.toggle("active", item === button));
    asdState.mode = button.dataset.asdMode;
    renderAsd();
  });
});
