// 半导体周期 tab.

let semiChart = null;
const SEMI_MARKET_KEYS = ["soxx", "smh", "nvda", "tsm", "avgo", "mu", "amd", "asml", "amat", "lrcx", "klac", "intc", "txn"];
const SEMI_DEFAULT_KEYS = ["soxx", "nvda", "tsm", "mu", "asml"];
const SEMI_SIGNAL_KEY = "finance-dashboard-semiconductor-signals-v1";
const SEMI_OPINION_KEY = "finance-dashboard-semiconductor-opinions-v1";

const SEMI_OPINION_DEFAULTS = [
  {
    id: "research-2026-09-11",
    date: "2026-09-11",
    confidence: "中",
    source: "research",
    text: "全球半导体仍处于高景气，但已经进入盈利暴涨、估值收缩的后周期阶段。最可能的顶部窗口为2026年Q4至2027年Q2；若DRAM/NAND现货连续四周下跌、合约价降至0–5%，并伴随云厂商资本开支下修，应视为周期下行确认。2027年下半年至2028年需重点防范新增产能集中释放。"
  }
];
const CLOUD_CAPEX = {
  quarters: ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"],
  companies: [
    { key: "MSFT", name: "Microsoft", color: "#54a4ff", values: [16.745, 17.079, 19.394, 29.876, 30.876, 35.802], yoy: 109.6, qoq: 16.0 },
    { key: "GOOGL", name: "Alphabet", color: "#f5bd59", values: [17.197, 22.446, 23.953, 27.851, 35.674, 44.924], yoy: 100.1, qoq: 25.9 },
    { key: "AMZN", name: "Amazon", color: "#ff8a65", values: [25.019, 32.183, 35.095, 39.522, 44.203, 54.208], yoy: 68.4, qoq: 22.6 },
    { key: "META", name: "Meta", color: "#a889ff", values: [12.941, 16.538, 18.829, 21.383, 18.997, 30.116], yoy: 82.1, qoq: 58.5 }
  ],
  totals: [71.902, 88.246, 97.271, 118.632, 129.750, 165.050],
  totalYoy: 87.0,
  totalQoq: 27.2,
  oracle: { quarter: "FY27Q1", period: "2026-06-01 至 2026-08-31", value: 28.499, yoy: 235.2, qoq: 72.8 }
};
const SEMI_SIGNALS = [
  { key: "spotTrend", name: "DRAM/NAND现货趋势", type: "select", value: "flat", options: [["up", "上涨"], ["flat", "横盘"], ["down4w", "连续4周下跌"]], threshold: "连续4周下跌 = +2风险", score: value => value === "down4w" ? 2 : value === "flat" ? 1 : 0 },
  { key: "dramQoq", name: "DRAM合约价 QoQ", type: "number", value: 15.5, suffix: "%", threshold: "≤5% = +2风险", score: value => Number(value) <= 5 ? 2 : Number(value) <= 10 ? 1 : 0 },
  { key: "nandQoq", name: "NAND合约价 QoQ", type: "number", value: 12.5, suffix: "%", threshold: "≤5% = +1风险", score: value => Number(value) <= 5 ? 1 : 0 },
  { key: "tsmcYoy", name: "台积电月营收 YoY", type: "number", value: 53.3, suffix: "%", threshold: "<30% = +1风险", score: value => Number(value) < 30 ? 1 : 0 },
  { key: "koreaExportYoy", name: "韩国芯片出口 YoY", type: "number", value: 209, suffix: "%", threshold: "<50% = +1风险", score: value => Number(value) < 50 ? 1 : 0 },
  { key: "us10y", name: "美国10年期收益率", type: "number", value: 4.8, suffix: "%", threshold: ">5% = +1风险", score: value => Number(value) > 5 ? 1 : 0 },
  { key: "capex", name: "云厂商资本开支指引", type: "select", value: "stable", options: [["up", "上调"], ["stable", "稳定"], ["cut", "下调/消化"]], threshold: "下调/消化 = +2风险", score: value => value === "cut" ? 2 : value === "stable" ? 1 : 0 },
  { key: "earningsBreadth", name: "盈利修正广度", type: "select", value: "balanced", options: [["up", "上调占优"], ["balanced", "接近平衡"], ["down", "下调占优"]], threshold: "下调占优 = +1风险", score: value => value === "down" ? 1 : value === "balanced" ? 1 : 0 }
];
const semiState = {
  range: "1y",
  selected: new Set(SEMI_DEFAULT_KEYS),
  series: {},
  signals: loadSemiSignals(),
  opinions: loadSemiOpinions(),
  animateKey: null,
  loaded: false,
  loading: false
};

function loadSemiSignals() {
  const defaults = Object.fromEntries(SEMI_SIGNALS.map(signal => [signal.key, signal.value]));
  try {
    const saved = JSON.parse(localStorage.getItem(SEMI_SIGNAL_KEY));
    return saved && typeof saved === "object" ? { ...defaults, ...saved } : defaults;
  } catch (error) {
    console.warn("semiconductor signals", error);
    return defaults;
  }
}

function saveSemiSignals() {
  try {
    localStorage.setItem(SEMI_SIGNAL_KEY, JSON.stringify(semiState.signals));
  } catch (error) {
    console.warn("semiconductor signals save", error);
  }
}

function loadSemiOpinions() {
  try {
    const saved = JSON.parse(localStorage.getItem(SEMI_OPINION_KEY));
    const merged = new Map(SEMI_OPINION_DEFAULTS.map(item => [item.id, item]));
    if (Array.isArray(saved)) saved.forEach(item => {
      if (item?.id && item?.date && item?.text) merged.set(item.id, item);
    });
    return [...merged.values()];
  } catch (error) {
    console.warn("semiconductor opinions", error);
    return [...SEMI_OPINION_DEFAULTS];
  }
}

function saveSemiOpinions() {
  try {
    localStorage.setItem(SEMI_OPINION_KEY, JSON.stringify(semiState.opinions));
  } catch (error) {
    console.warn("semiconductor opinions save", error);
  }
}

function renderSemiOpinions() {
  const host = document.getElementById("opinionTimeline");
  const opinions = [...semiState.opinions].sort((a, b) => b.date.localeCompare(a.date));
  host.innerHTML = opinions.length ? opinions.map(item => `
    <article class="opinion-entry" data-opinion-id="${escapeHtml(item.id)}">
      <div>
        <div class="opinion-date">${escapeHtml(item.date)}</div>
        <div class="opinion-confidence">${escapeHtml(item.confidence)}置信度${item.source === "research" ? " · 研究基线" : " · 手工记录"}</div>
      </div>
      <div>
        <div class="opinion-title">${escapeHtml(item.text.split(/[。！？\n]/)[0] || "半导体周期观点")}</div>
        <div class="opinion-body">${escapeHtml(item.text)}</div>
      </div>
      <div class="opinion-actions">
        <button type="button" class="opinion-action" data-opinion-edit="${escapeHtml(item.id)}">编辑</button>
        ${item.source === "research" ? "" : `<button type="button" class="opinion-action" data-opinion-delete="${escapeHtml(item.id)}">删除</button>`}
      </div>
    </article>
  `).join("") : '<div class="opinion-empty">尚未记录观点</div>';

  host.querySelectorAll("[data-opinion-edit]").forEach(button => {
    button.addEventListener("click", () => {
      const item = semiState.opinions.find(opinion => opinion.id === button.dataset.opinionEdit);
      if (!item) return;
      document.getElementById("opinionDate").value = item.date;
      document.getElementById("opinionConfidence").value = item.confidence;
      document.getElementById("opinionText").value = item.text;
      document.getElementById("opinionText").focus();
    });
  });
  host.querySelectorAll("[data-opinion-delete]").forEach(button => {
    button.addEventListener("click", () => {
      semiState.opinions = semiState.opinions.filter(item => item.id !== button.dataset.opinionDelete);
      saveSemiOpinions();
      renderSemiOpinions();
    });
  });
}

function saveCurrentOpinion() {
  const date = document.getElementById("opinionDate").value;
  const confidence = document.getElementById("opinionConfidence").value;
  const text = document.getElementById("opinionText").value.trim();
  if (!date || !text) {
    document.getElementById("opinionText").focus();
    return;
  }
  const existing = semiState.opinions.find(item => item.date === date);
  const next = {
    id: existing?.id || `manual-${date}`,
    date,
    confidence,
    source: existing?.source || "manual",
    text
  };
  semiState.opinions = [...semiState.opinions.filter(item => item.id !== next.id), next];
  saveSemiOpinions();
  renderSemiOpinions();
  document.getElementById("opinionText").value = "";
}

function renderCloudCapex() {
  const chart = document.getElementById("cloudCapexChart");
  const width = 900;
  const height = 340;
  const margin = { top: 28, right: 24, bottom: 45, left: 48 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maxValue = 180;
  const band = plotWidth / CLOUD_CAPEX.quarters.length;
  const barWidth = Math.min(72, band * .56);
  const y = value => margin.top + plotHeight - value / maxValue * plotHeight;
  const gridValues = [0, 50, 100, 150];
  const grid = gridValues.map(value => `
    <line x1="${margin.left}" y1="${y(value)}" x2="${width - margin.right}" y2="${y(value)}" stroke="rgba(151,180,202,.12)" />
    <text x="${margin.left - 9}" y="${y(value) + 4}" text-anchor="end" fill="#718796" font-size="10">${value}</text>
  `).join("");
  const bars = CLOUD_CAPEX.quarters.map((quarter, quarterIndex) => {
    const x = margin.left + band * quarterIndex + (band - barWidth) / 2;
    let cumulative = 0;
    const segments = CLOUD_CAPEX.companies.map(company => {
      const value = company.values[quarterIndex];
      const segmentHeight = value / maxValue * plotHeight;
      const rectY = y(cumulative + value);
      cumulative += value;
      return `<rect x="${x}" y="${rectY}" width="${barWidth}" height="${segmentHeight}" fill="${company.color}" rx="2"><title>${company.name} ${quarter}: $${value.toFixed(1)}B</title></rect>`;
    }).join("");
    return `
      ${segments}
      <text x="${x + barWidth / 2}" y="${y(cumulative) - 8}" text-anchor="middle" fill="#eaf4fa" font-size="10" font-weight="700">$${cumulative.toFixed(1)}B</text>
      <text x="${x + barWidth / 2}" y="${height - 18}" text-anchor="middle" fill="#8297a7" font-size="10">${quarter}</text>
    `;
  }).join("");
  chart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="四大云厂商季度资本开支堆叠图">
      ${grid}
      ${bars}
      <text x="12" y="17" fill="#8297a7" font-size="9">USD bn</text>
    </svg>
  `;

  document.getElementById("cloudCapexLatest").innerHTML = CLOUD_CAPEX.companies.map(company => {
    const latest = company.values.at(-1);
    return `
      <div class="capex-company">
        <span class="capex-company-name">${escapeHtml(company.name)}</span>
        <span class="capex-company-value">$${latest.toFixed(1)}B</span>
        <span class="capex-company-growth">+${company.yoy.toFixed(1)}%</span>
      </div>
    `;
  }).join("");

  const rows = [
    ...CLOUD_CAPEX.companies.map(company => ({
      name: company.name,
      values: company.values,
      total: false
    })),
    { name: "四大合计", values: CLOUD_CAPEX.totals, total: true }
  ];
  document.getElementById("cloudCapexTable").innerHTML = rows.map(row => `
    <tr class="${row.total ? "capex-total" : ""}">
      <td>${escapeHtml(row.name)}</td>
      ${row.values.map(value => `<td>${value.toFixed(1)}</td>`).join("")}
      <td>待披露</td>
    </tr>
  `).join("");
}

function semiRiskScore() {
  return SEMI_SIGNALS.reduce((sum, signal) => sum + signal.score(semiState.signals[signal.key]), 0);
}

function semiRiskProfile(score = semiRiskScore()) {
  if (score >= 6) return { label: "周期转向", state: "risk", headline: "领先指标确认转弱 · 下行风险占优" };
  if (score >= 3) return { label: "高位预警", state: "watch", headline: "高景气 · 后周期 · 等待转向确认" };
  return { label: "景气延续", state: "safe", headline: "高景气延续 · 尚未形成下行确认" };
}

function renderSemiSignals() {
  const host = document.getElementById("semiSignalList");
  host.innerHTML = SEMI_SIGNALS.map(signal => {
    const value = semiState.signals[signal.key];
    const points = signal.score(value);
    const state = points >= 2 ? "risk" : points === 1 ? "watch" : "safe";
    const label = points >= 2 ? `风险 +${points}` : points === 1 ? "观察 +1" : "正常";
    const control = signal.type === "select"
      ? `<select class="signal-input" data-semi-signal="${signal.key}">${signal.options.map(([key, text]) => `<option value="${key}" ${value === key ? "selected" : ""}>${text}</option>`).join("")}</select>`
      : `<input class="signal-input" data-semi-signal="${signal.key}" type="number" step="0.1" value="${escapeHtml(value)}" aria-label="${escapeHtml(signal.name)}">`;
    return `
      <div class="signal-row">
        <div><div class="signal-name">${escapeHtml(signal.name)}</div><div class="signal-threshold">${escapeHtml(signal.threshold)}</div></div>
        ${control}
        <span class="signal-state ${state}">${label}</span>
      </div>
    `;
  }).join("");
  host.querySelectorAll("[data-semi-signal]").forEach(input => {
    input.addEventListener("change", () => {
      semiState.signals[input.dataset.semiSignal] = input.type === "number" ? Number(input.value) : input.value;
      saveSemiSignals();
      renderSemiSignals();
      renderSemiRisk();
    });
  });
  renderSemiRisk();
}

function renderSemiRisk() {
  const score = semiRiskScore();
  const profile = semiRiskProfile(score);
  document.getElementById("cycleScore").textContent = `${score}/11`;
  document.getElementById("cycleScore").style.color = profile.state === "risk" ? "var(--red)" : profile.state === "watch" ? "var(--amber)" : "var(--green)";
  document.getElementById("cycleLabel").textContent = profile.label;
  document.getElementById("cycleDetail").textContent = score >= 6
    ? "至少三类领先指标已显著恶化，应按周期下行管理风险"
    : score >= 3
      ? "边际风险正在累积，等待价格、资本开支和盈利修正共同确认"
      : "主要领先指标仍支持景气延续";
  document.getElementById("semiHeadline").textContent = profile.headline;
  document.getElementById("semiRiskState").textContent = profile.label;
  document.getElementById("semiRiskState").style.color = profile.state === "risk" ? "var(--red)" : profile.state === "watch" ? "var(--amber)" : "var(--green)";
}

function renderSemiAssetChips() {
  const host = document.getElementById("semiAssetChips");
  host.innerHTML = SEMI_MARKET_KEYS.map(key => `
    <button type="button" class="semi-chip ${semiState.selected.has(key) ? "active" : ""}" data-semi-asset="${key}">
      ${escapeHtml(ASSETS[key].short)}
    </button>
  `).join("");
  host.querySelectorAll("[data-semi-asset]").forEach(button => {
    button.addEventListener("click", async () => {
      const key = button.dataset.semiAsset;
      if (semiState.selected.has(key) && semiState.selected.size > 1) semiState.selected.delete(key);
      else {
        semiState.selected.add(key);
        semiState.animateKey = key;
        if (!semiState.series[key]?.length) {
          button.textContent = "读取中";
          try {
            semiState.series[key] = await fetchYahoo(key, ASSETS[key], semiState.range);
          } catch (error) {
            console.warn(`semiconductor ${key}`, error);
          }
        }
      }
      renderSemiAssetChips();
      renderSemiMarketChart();
    });
  });
}

function periodReturn(rows, days) {
  const valid = rows?.filter(row => Number.isFinite(row.close)) || [];
  if (valid.length < 2) return NaN;
  const cutoff = valid.at(-1).time - days * 86400000;
  const first = valid.find(row => row.time >= cutoff) || valid[0];
  const last = valid.at(-1);
  return first.close ? (last.close / first.close - 1) * 100 : NaN;
}

function formatPct(value) {
  return Number.isFinite(value) ? `${value >= 0 ? "+" : ""}${value.toFixed(1)}%` : "暂无";
}

function animateLineSeries(series, rows, duration = 500) {
  if (!rows.length) return;
  const startedAt = performance.now();
  let renderedCount = 0;
  const draw = now => {
    const progress = Math.min(1, (now - startedAt) / duration);
    const eased = 1 - (1 - progress) ** 3;
    const nextCount = Math.max(1, Math.ceil(rows.length * eased));
    if (nextCount !== renderedCount) {
      series.setData(rows.slice(0, nextCount));
      renderedCount = nextCount;
    }
    if (progress < 1) requestAnimationFrame(draw);
  };
  requestAnimationFrame(draw);
}

function renderSemiStats() {
  const soxx1m = periodReturn(semiState.series.soxx, 30);
  const soxx3m = periodReturn(semiState.series.soxx, 91);
  const spy3m = periodReturn(semiState.series.spy, 91);
  const relative = Number.isFinite(soxx3m) && Number.isFinite(spy3m) ? soxx3m - spy3m : NaN;
  const yieldRow = semiState.series.us10y?.at(-1);
  const yieldValue = Number.isFinite(yieldRow?.close) ? yieldRow.close / 10 : NaN;
  document.getElementById("semiSoxx1m").textContent = formatPct(soxx1m);
  document.getElementById("semiSoxx1m").className = `semi-stat-value ${soxx1m >= 0 ? "up" : "down"}`;
  document.getElementById("semiRelative3m").textContent = formatPct(relative);
  document.getElementById("semiRelative3m").className = `semi-stat-value ${relative >= 0 ? "up" : "down"}`;
  document.getElementById("semiUs10y").textContent = Number.isFinite(yieldValue) ? `${yieldValue.toFixed(2)}%` : "暂无";
  if (Number.isFinite(yieldValue)) {
    semiState.signals.us10y = +yieldValue.toFixed(2);
    saveSemiSignals();
    renderSemiSignals();
  }
  document.getElementById("semiUpdatedAt").textContent = `行情更新 ${new Date().toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" })}`;
}

function renderSemiMarketChart() {
  if (!semiChart) semiChart = createFinancialChart(document.getElementById("semiMarketChart"));
  clearChart(semiChart);
  const keys = [...semiState.selected].filter(key => semiState.series[key]?.length);
  if (!keys.length) {
    showChartEmpty(semiChart, "半导体行情暂不可用");
    return;
  }
  const legendItems = [];
  keys.forEach(key => {
    const rows = semiState.series[key];
    const first = rows.find(row => Number.isFinite(row.close))?.close;
    if (!first) return;
    const series = semiChart.api.addSeries(LightweightCharts.LineSeries, {
      color: ASSETS[key].color,
      lineWidth: key === "soxx" ? 3 : 2,
      priceLineVisible: false,
      lastValueVisible: false,
      priceFormat: { type: "custom", minMove: .1, formatter: value => value.toFixed(1) }
    });
    const normalizedRows = rows.map(row => ({
      time: chartTime(row.time),
      value: +(row.close / first * 100).toFixed(3)
    }));
    if (key === semiState.animateKey) animateLineSeries(series, normalizedRows, 500);
    else series.setData(normalizedRows);
    semiChart.series.push(series);
    legendItems.push({ label: ASSETS[key].short, color: ASSETS[key].color, series, formatter: data => data.value.toFixed(1) });
  });
  setChartLegend(semiChart, legendItems);
  semiChart.api.timeScale().fitContent();
  if (semiState.animateKey) {
    const animatedButton = document.querySelector(`[data-semi-asset="${semiState.animateKey}"]`);
    animatedButton?.classList.add("drawing");
    setTimeout(() => animatedButton?.classList.remove("drawing"), 500);
    semiState.animateKey = null;
  }
}

async function loadSemiDashboard() {
  if (semiState.loading) return;
  semiState.loading = true;
  const button = document.getElementById("refreshSemiBtn");
  button.textContent = "更新中";
  button.disabled = true;
  try {
    const keys = [...new Set([...semiState.selected, "soxx", "spy", "us10y"])];
    const results = await Promise.all(keys.map(async key => {
      try {
        semiState.series[key] = await fetchYahoo(key, ASSETS[key], semiState.range);
        return true;
      } catch (error) {
        console.warn(`semiconductor ${key}`, error);
        return false;
      }
    }));
    semiState.loaded = results.some(Boolean);
    renderSemiMarketChart();
    renderSemiStats();
  } finally {
    semiState.loading = false;
    button.textContent = "刷新";
    button.disabled = false;
  }
}

document.querySelectorAll("[data-semi-range]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-semi-range]").forEach(item => item.classList.toggle("active", item === button));
    semiState.range = button.dataset.semiRange;
    semiState.series = {};
    loadSemiDashboard();
  });
});
document.getElementById("refreshSemiBtn").addEventListener("click", loadSemiDashboard);

document.getElementById("saveOpinionBtn").addEventListener("click", saveCurrentOpinion);
