// 美股供需 tab (/api/us-supply-demand).

const ussdState = { data: null, chart: null, mode: "gap", loading: false };
const USSD_KEY_COLUMNS = new Set(["net_supply", "demand", "gap", "gap_ex_div", "spx_ret"]);
const USSD_SIGNED_COLUMNS = new Set(["net_supply", "demand", "gap", "gap_bp", "gap_z3", "gap_z6", "gap_ex_div", "gap_ex_div_bp",
  "gap_ex_div_z6", "spx_ret", "etf_us_equity", "mf_domestic_equity", "margin", "free_credit", "first_day_median"]);

function formatUssdValue(column, value) {
  if (value === null || value === undefined) return "--";
  if (column.unit === "") return value.toFixed(2);
  if (column.unit === "家") return String(Math.round(value));
  return value.toFixed(1);
}

function renderUssd() {
  const data = ussdState.data;
  if (!data) return;
  const mode = ussdState.mode;
  const label = mode === "gap" ? "供需差" : "供需差(扣分红)";
  const last = data.rows[data.rows.length - 1];
  document.getElementById("ussdNote").textContent =
    `${data.display[0]} ~ ${data.display[1]} · 单位 ${data.unit} · 生成于 ${data.generated_at.replace("T", " ")}` +
    (last ? ` · ${last.month} ${label} ${formatUssdValue({ unit: "$B" }, last[mode])}，z6 ${formatUssdValue({ unit: "" }, last[`${mode}_z6`])}` : "");
  const commentary = document.getElementById("ussdCommentary");
  commentary.hidden = !data.commentary;
  if (data.commentary) commentary.innerHTML = `<b>${escapeHtml(data.commentary.as_of)} 结论</b> ${escapeHtml(data.commentary.text)}`;

  if (!ussdState.chart) {
    ussdState.chart = createFinancialChart(document.getElementById("ussdChart"));
    ussdState.chart.api.priceScale("left").applyOptions({ visible: true });
  }
  const chart = ussdState.chart;
  clearChart(chart);
  const toTime = month => Date.UTC(+month.slice(0, 4), +month.slice(5, 7) - 1, 1) / 1000;
  const gapData = data.rows.filter(row => row[`${mode}_bp`] !== null).map(row => ({
    time: toTime(row.month),
    value: row[`${mode}_bp`],
    color: row[`${mode}_bp`] >= 0 ? "rgba(50,212,154,.75)" : "rgba(255,101,119,.75)"
  }));
  const spxData = data.rows.filter(row => row.spx_ret !== null).map(row => ({ time: toTime(row.month), value: row.spx_ret }));
  const gapSeries = chart.api.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: "price", precision: 1, minMove: .1 },
    priceLineVisible: false
  });
  gapSeries.setData(gapData);
  const spxSeries = chart.api.addSeries(LightweightCharts.LineSeries, {
    color: "#f5bd59",
    lineWidth: 2,
    priceScaleId: "left",
    pointMarkersVisible: true,
    priceFormat: { type: "price", precision: 1, minMove: .1 },
    priceLineVisible: false
  });
  spxSeries.setData(spxData);
  chart.series = [gapSeries, spxSeries];
  setChartLegend(chart, [
    { label: `${label}/美股总市值 (bp，右轴)`, color: "#32d49a", series: gapSeries, data: gapData, formatter: point => `${point.value.toFixed(1)} bp` },
    { label: "S&P500 月涨幅 (%，左轴)", color: "#f5bd59", series: spxSeries, data: spxData, formatter: point => `${point.value.toFixed(1)}%` }
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
  document.getElementById("ussdHead").innerHTML =
    `<tr class="asd-groups"><th></th>${groups.map(group => `<th colspan="${group.span}">${escapeHtml(group.name)}</th>`).join("")}</tr>` +
    `<tr><th>月份</th>${columns.map(column =>
      `<th>${escapeHtml(column.label)}${column.unit ? `<small>${escapeHtml(column.unit)}</small>` : ""}</th>`).join("")}</tr>`;
  document.getElementById("ussdTable").innerHTML = data.rows.map(row => `<tr><td>${escapeHtml(row.month)}</td>${columns.map(column => {
    const value = row[column.key];
    const tone = USSD_SIGNED_COLUMNS.has(column.key) && value ? (value > 0 ? "pos" : "neg") : "";
    const key = USSD_KEY_COLUMNS.has(column.key) ? "asd-key" : "";
    return `<td class="${tone} ${key}">${formatUssdValue(column, value)}</td>`;
  }).join("")}</tr>`).join("");
  document.getElementById("ussdSource").innerHTML =
    `${escapeHtml(data.formula)}。数据来源：${escapeHtml(data.source)}。` +
    `<ul>${data.caveats.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>` +
    `刷新：<code>cd dashboard; uv run python tab/us-supply-demand/build_panel.py --refresh</code>（设计说明见 tab/us-supply-demand/SKILL.md）`;
}

async function loadUssd() {
  if (ussdState.loading) return;
  if (ussdState.data) return renderUssd();
  ussdState.loading = true;
  document.getElementById("ussdNote").textContent = "正在加载美股供需面板...";
  try {
    const response = await fetch("/api/us-supply-demand", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    ussdState.data = payload;
    renderUssd();
  } catch (error) {
    console.error("us-supply-demand", error);
    document.getElementById("ussdNote").textContent = `美股供需数据暂不可用：${error.message}`;
  } finally {
    ussdState.loading = false;
  }
}

document.querySelectorAll("[data-ussd-mode]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-ussd-mode]").forEach(item => item.classList.toggle("active", item === button));
    ussdState.mode = button.dataset.ussdMode;
    renderUssd();
  });
});
