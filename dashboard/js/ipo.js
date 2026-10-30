// IPO 日历 tab (/api/ipo).

const IPO_MARKETS = {
  a: { label: "A股", dateNote: "上市日（未上市取申购日）" },
  hk: { label: "港股", dateNote: "上市日" },
  us: { label: "美股", dateNote: "定价日" }
};
const ipoState = { market: "a", period: "month", data: {}, chart: null, selected: null };

function aggregateIpoRows(rows, period) {
  const buckets = new Map();
  rows.forEach(row => {
    const key = period === "month" ? row.date.slice(0, 7) : row.date;
    const bucket = buckets.get(key) || { key, count: 0, amount: 0, upcoming: false, rows: [] };
    bucket.count += 1;
    bucket.amount += row.amount || 0;
    bucket.upcoming ||= row.upcoming;
    bucket.rows.push(row);
    buckets.set(key, bucket);
  });
  return [...buckets.values()].sort((a, b) => a.key.localeCompare(b.key));
}

function renderIpoCalendar() {
  const payload = ipoState.data[ipoState.market];
  if (!payload) return;
  const market = IPO_MARKETS[ipoState.market];
  const unit = `亿${payload.currency}`;
  const buckets = aggregateIpoRows(payload.rows, ipoState.period);
  const total = buckets.reduce((sum, bucket) => sum + bucket.amount, 0);
  document.getElementById("ipoNote").textContent =
    `近 5 年 · ${payload.rows.length} 家 · ${total.toFixed(0)} ${unit} · 日期=${market.dateNote}`;
  document.getElementById("ipoSource").textContent =
    `数据来源：${payload.source}。募资额单位 ${unit}；黄色为未上市/待定价，缺失发行价的计入家数不计金额。`;

  if (!ipoState.chart) {
    ipoState.chart = createFinancialChart(document.getElementById("ipoChart"));
    ipoState.chart.api.subscribeClick(param => {
      if (typeof param.time !== "number") return;
      const iso = new Date(param.time * 1000).toISOString();
      selectIpoBucket(ipoState.period === "month" ? iso.slice(0, 7) : iso.slice(0, 10));
    });
  }
  const chart = ipoState.chart;
  clearChart(chart);
  const data = buckets.map(bucket => ({
    time: Date.UTC(+bucket.key.slice(0, 4), +bucket.key.slice(5, 7) - 1, +(bucket.key.slice(8, 10) || 1)) / 1000,
    value: bucket.amount,
    color: bucket.upcoming ? "#f5bd59" : "#38d7c5"
  }));
  const series = chart.api.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: "price", precision: 1, minMove: .1 },
    priceLineVisible: false
  });
  series.setData(data);
  chart.series = [series];
  setChartLegend(chart, [{
    label: `${market.label} IPO 募资`,
    color: "#38d7c5",
    series,
    data,
    formatter: point => `${point.value.toFixed(2)} ${unit}`
  }]);
  if (!data.length) showChartEmpty(chart, "暂无 IPO 数据");
  chart.api.timeScale().fitContent();

  document.getElementById("ipoTable").innerHTML = buckets.slice().reverse().map(bucket => {
    const top = bucket.rows.slice().sort((a, b) => (b.amount || 0) - (a.amount || 0));
    const label = row => `${row.name}${row.amount ? ` ${row.amount.toFixed(1)}` : ""}`;
    const names = top.slice(0, 4).map(label).join("、") + (top.length > 4 ? ` 等${top.length}家` : "");
    const detail = top.map(row =>
      `<span>${escapeHtml(row.code)} ${escapeHtml(label(row))}${row.upcoming ? " · 待上市" : ""}${ipoState.period === "month" ? ` · ${row.date.slice(5)}` : ""}</span>`
    ).join("");
    return `<tr class="${bucket.upcoming ? "upcoming" : ""}" data-ipo-key="${bucket.key}">
      <td>${bucket.key}</td><td>${bucket.count}</td><td>${bucket.amount.toFixed(2)}</td>
      <td><div class="ipo-names">${escapeHtml(names)}</div><div class="ipo-detail">${detail}</div></td>
    </tr>`;
  }).join("");
  if (ipoState.selected) selectIpoBucket(ipoState.selected, false);
}

function selectIpoBucket(key, scroll = true) {
  ipoState.selected = key;
  let target = null;
  document.querySelectorAll("#ipoTable tr").forEach(row => {
    const match = row.dataset.ipoKey === key;
    row.classList.toggle("selected", match);
    if (match) target = row;
  });
  if (target && scroll) {
    const wrap = target.closest(".ipo-table-wrap");
    wrap.scrollTo({ top: target.offsetTop - wrap.clientHeight / 3, behavior: "smooth" });
  }
}

async function loadIpoCalendar() {
  const market = ipoState.market;
  if (ipoState.data[market]) return renderIpoCalendar();
  document.getElementById("ipoNote").textContent = `正在加载${IPO_MARKETS[market].label} IPO 数据...`;
  try {
    const response = await fetch(`/api/ipo?market=${market}`, { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    ipoState.data[market] = payload;
    if (ipoState.market === market) renderIpoCalendar();
  } catch (error) {
    console.error("ipo calendar", error);
    if (ipoState.market === market) {
      document.getElementById("ipoNote").textContent = `IPO 数据暂不可用：${error.message}`;
    }
  }
}

document.querySelectorAll("[data-ipo-market], [data-ipo-period]").forEach(button => {
  button.addEventListener("click", () => {
    const attribute = button.dataset.ipoMarket ? "ipoMarket" : "ipoPeriod";
    document.querySelectorAll(attribute === "ipoMarket" ? "[data-ipo-market]" : "[data-ipo-period]")
      .forEach(item => item.classList.toggle("active", item === button));
    if (attribute === "ipoMarket") ipoState.market = button.dataset.ipoMarket;
    else ipoState.period = button.dataset.ipoPeriod;
    ipoState.selected = null;
    loadIpoCalendar();
  });
});
document.getElementById("ipoTable").addEventListener("click", event => {
  const row = event.target.closest("tr[data-ipo-key]");
  if (row) selectIpoBucket(row.dataset.ipoKey, false);
});
