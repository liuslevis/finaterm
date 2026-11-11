// 模拟盘 tab (/api/paper-trading)：多策略，账本来自 git 跟踪的 paper-trading/state/。

const ptState = { data: null, loading: false, selected: null, chart: null };
const PT_STRATEGY_COLOR = "#38d7c5";
const PT_BENCH_COLORS = { SHY: "#8297a7", sh000300: "#ff6577", QQQ: "#54a4ff", SPY: "#f5bd59" };

function ptTime(day) {
  return Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10)) / 1000;
}

function ptPct(value, digits = 2) {
  if (!Number.isFinite(value)) return "--";
  return `${value > 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
}

function ptUsd(value, digits = 2) {
  if (!Number.isFinite(value)) return "--";
  return `${value < 0 ? "−" : ""}$${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

function ptTone(value) {
  return value > 0 ? "pos" : value < 0 ? "neg" : "";
}

function ptSummary(strategy) {
  const nav = strategy.nav.map(row => ({ ...row, nav: +row.nav, invested: +row.invested, twr: +row.twr, cash: +row.cash }));
  const last = nav[nav.length - 1];
  if (!last) return null;
  let peak = -Infinity;
  let maxDd = 0;
  nav.forEach(row => {
    peak = Math.max(peak, row.twr);
    maxDd = Math.min(maxDd, row.twr / peak - 1);
  });
  const prev = nav[nav.length - 2];
  return {
    nav, last,
    twr: last.twr - 1,
    day: prev ? last.twr / prev.twr - 1 : 0,
    pnl: last.nav - last.invested,
    maxDd,
    holdings: last.holdings ? last.holdings.split(";").map(item => item.split("=")) : []
  };
}

function renderPtPicker() {
  document.getElementById("ptPicker").innerHTML = ptState.data.strategies.map(strategy => {
    const summary = ptSummary(strategy);
    const ret = summary ? summary.twr : NaN;
    return `<button type="button" data-pt-strategy="${escapeHtml(strategy.id)}" class="${strategy.id === ptState.selected ? "active" : ""}">` +
      `${escapeHtml(strategy.name)}<span class="${ptTone(ret)}">${ptPct(ret, 1)}</span></button>`;
  }).join("");
  document.querySelectorAll("[data-pt-strategy]").forEach(button => {
    button.addEventListener("click", () => {
      ptState.selected = button.dataset.ptStrategy;
      renderPt();
    });
  });
}

function renderPtStats(strategy, summary) {
  const { last } = summary;
  const value = summary.holdings.length
    ? summary.holdings.map(([symbol, shares]) => `${symbol} ${(+shares).toLocaleString("en-US", { maximumFractionDigits: 4 })}`).join(" · ")
    : "空仓";
  const stats = [
    ["市值", ptUsd(last.nav), ""],
    ["累计收益（时间加权）", ptPct(summary.twr), ptTone(summary.twr)],
    ["最近一日", ptPct(summary.day), ptTone(summary.day)],
    ["投入", ptUsd(last.invested, 0), ""],
    ["盈亏", ptUsd(summary.pnl), ptTone(summary.pnl)],
    ["最大回撤", ptPct(summary.maxDd), summary.maxDd < 0 ? "neg" : ""],
    ["持仓", value, ""],
    ["现金", ptUsd(last.cash), ""]
  ];
  document.getElementById("ptStats").innerHTML = stats.map(([label, text, tone]) =>
    `<div class="pt-stat"><span>${escapeHtml(label)}</span><b class="${tone}">${escapeHtml(text)}</b></div>`).join("");
}

function renderPtChart(strategy, summary) {
  if (!ptState.chart) ptState.chart = createFinancialChart(document.getElementById("ptChart"));
  const chart = ptState.chart;
  clearChart(chart);
  const start = summary.nav[0].date;
  const percent = { type: "custom", minMove: .01, formatter: value => `${value.toFixed(2)}%` };
  const lines = [{
    label: strategy.name,
    color: PT_STRATEGY_COLOR,
    width: 2,
    data: summary.nav.map(row => ({ time: ptTime(row.date), value: (row.twr - 1) * 100 }))
  }];
  const { labels, series } = ptState.data.benchmarks;
  Object.entries(labels).forEach(([symbol, label]) => {
    const rows = series[symbol] || [];
    const base = [...rows].reverse().find(([day]) => day <= start) || rows.find(([day]) => day >= start);
    if (!base) return;
    lines.push({
      label,
      color: PT_BENCH_COLORS[symbol] || "#8297a7",
      width: 1,
      data: rows.filter(([day]) => day >= base[0]).map(([day, close]) => ({
        time: ptTime(day < start ? start : day), value: (close / base[1] - 1) * 100
      })).filter((point, index, all) => index === all.length - 1 || point.time !== all[index + 1].time)
    });
  });
  const legend = lines.map(line => {
    const item = chart.api.addSeries(LightweightCharts.LineSeries, {
      color: line.color,
      lineWidth: line.width,
      priceFormat: percent,
      priceLineVisible: false,
      lastValueVisible: line.width > 1
    });
    item.setData(line.data);
    chart.series.push(item);
    return { label: line.label, color: line.color, series: item, data: line.data, carryForward: true,
      formatter: point => `${point.value > 0 ? "+" : ""}${point.value.toFixed(2)}%` };
  });
  setChartLegend(chart, legend);
  chart.api.timeScale().fitContent();
}

function renderPtTrades(strategy) {
  const pending = (strategy.account.pending || []).map(order => ({
    pending: true,
    date: "下一开盘",
    side: order.side,
    symbol: order.symbol,
    shares: order.shares === "all" ? "全部" : "",
    price: "",
    amount: order.amount ? ptUsd(order.amount) : order.weight ? `净值×${(order.weight * 100).toFixed(1)}%` : "",
    reason: `${order.reason}（${order.signal_date} 收盘信号）`
  }));
  const filled = [...strategy.trades].reverse().map(trade => ({
    date: trade.date,
    side: trade.side,
    symbol: trade.symbol,
    shares: (+trade.shares).toLocaleString("en-US", { maximumFractionDigits: 4 }),
    price: ptUsd(+trade.price),
    amount: ptUsd(+trade.amount),
    reason: trade.reason
  }));
  const rows = [...pending, ...filled];
  const action = row => `${row.pending ? "待" : ""}${row.side === "buy" ? "买入" : "卖出"}`;
  document.getElementById("ptTrades").innerHTML = rows.length
    ? rows.map(row => `<tr class="${row.pending ? "pending" : ""}"><td>${escapeHtml(row.date)}</td>` +
      `<td class="${row.pending ? "" : row.side === "buy" ? "pos" : "neg"}">${action(row)}</td><td>${escapeHtml(row.symbol)}</td>` +
      `<td class="num">${escapeHtml(row.shares)}</td><td class="num">${escapeHtml(row.price)}</td>` +
      `<td class="num">${escapeHtml(row.amount)}</td><td class="reason">${escapeHtml(row.reason)}</td></tr>`).join("")
    : `<tr><td colspan="7" class="reason">暂无调仓</td></tr>`;
  document.getElementById("ptTradesNote").textContent =
    `${strategy.trades.length} 笔成交${pending.length ? ` · ${pending.length} 笔待成交` : ""} · 收盘出信号，次日开盘价成交`;
}

function formatPtSupport(field, raw) {
  if (raw === undefined || raw === null || raw === "") return { text: "--", cls: "" };
  const value = +raw;
  switch (field.fmt) {
    case "bool": return value ? { text: "触发 · 空仓", cls: "on" } : { text: "未触发", cls: "off" };
    case "usd": return { text: ptUsd(value), cls: "" };
    case "pct1": return { text: `${(value * 100).toFixed(1)}%`, cls: "" };
    case "pct2": return { text: ptPct(value), cls: ptTone(value) };
    case "num2": return { text: value.toFixed(2), cls: "" };
    case "num4": return { text: value.toFixed(4), cls: "" };
    case "int": return { text: String(Math.round(value)), cls: "" };
    default: return { text: String(raw), cls: "text" };
  }
}

function renderPtSupport(strategy) {
  const latest = strategy.latest || {};
  document.getElementById("ptSupport").innerHTML = (strategy.support || []).map(field => {
    const { text, cls } = formatPtSupport(field, latest[field.key]);
    return `<dt>${escapeHtml(field.label)}</dt><dd class="${cls}">${escapeHtml(text)}</dd>`;
  }).join("");
  document.getElementById("ptSupportNote").textContent = latest.date ? `${latest.date} 收盘快照` : "暂无数据";
}

function renderPt() {
  const data = ptState.data;
  if (!data) return;
  if (!data.strategies.some(item => item.id === ptState.selected)) ptState.selected = data.strategies[0]?.id;
  renderPtPicker();
  const strategy = data.strategies.find(item => item.id === ptState.selected);
  const summary = strategy && ptSummary(strategy);
  if (!summary) {
    document.getElementById("ptNote").textContent = "该策略尚无已收盘交易日";
    return;
  }
  const run = data.run || {};
  const runText = run.finished_at
    ? `上次运行 ${run.finished_at.replace("T", " ").slice(5, 16)}${run.ok ? "" : ` 失败：${run.error || "见 paper-trading/.cache/run.log"}`}`
    : "本机尚未运行";
  document.getElementById("ptTitle").textContent = `模拟盘 · ${strategy.name}`;
  document.getElementById("ptNote").textContent =
    `${strategy.desc} · ${summary.nav[0].date} 起 · 截至 ${summary.last.date}（${summary.nav.length} 个交易日）· ${runText}`;
  renderPtStats(strategy, summary);
  renderPtChart(strategy, summary);
  renderPtTrades(strategy);
  renderPtSupport(strategy);
  document.getElementById("ptSource").textContent =
    "收益率为时间加权（剔除入金），基准从策略首日归零：2Y国债用 SHY（1-3 年期美债 ETF，含利息）代表，沪深300 为人民币价格指数，QQQ / SPY 为含分红总收益。" +
    "dashboard 每 2 小时运行 paper-trading/run_daily.py，账本存于 paper-trading/state/ 并经 git 在多台电脑间同步。";
}

async function loadPt() {
  if (ptState.loading) return;
  if (ptState.data) return renderPt();
  ptState.loading = true;
  document.getElementById("ptNote").textContent = "正在加载模拟盘...";
  try {
    const response = await fetch("/api/paper-trading", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    ptState.data = payload;
    renderPt();
  } catch (error) {
    console.error("paper-trading", error);
    document.getElementById("ptNote").textContent = `模拟盘数据暂不可用：${error.message}`;
  } finally {
    ptState.loading = false;
  }
}
