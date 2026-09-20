"use strict";
// hfq LV2 逐笔研究终端 —— 前端逻辑
const $ = (s) => document.querySelector(s);
const api = async (path, params) => {
  const u = new URL("/api/" + path, location.origin);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, v);
  });
  const r = await fetch(u);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
  return r.json();
};
const fmtNum = (n, d = 0) => (n == null ? "--" : Number(n).toLocaleString("en-US",
  { minimumFractionDigits: d, maximumFractionDigits: d }));
const yi = (v) => {                       // 元 -> 亿/万 缩写
  const a = Math.abs(v);
  if (a >= 1e8) return (v / 1e8).toFixed(2) + "亿";
  if (a >= 1e4) return (v / 1e4).toFixed(2) + "万";
  return v.toFixed(0);
};
const wanYuan = (w) => yi(w * 1e4);       // 输入单位为“万元”
const clsChg = (v) => (v > 0 ? "up" : v < 0 ? "down" : "flat");

const state = { code: null, basic: null, filterRecs: [], selEvent: null };

// ---------------------------------------------------------------- tabs
document.querySelectorAll("#tabs button").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("#tabs button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    const v = b.dataset.view;
    document.querySelectorAll(".view").forEach((x) => x.classList.remove("on"));
    $("#view-" + v).classList.add("on");
    if (!state.code) return;
    if (v === "map") loadMap();
    else if (v === "tick") loadTick();
    else refreshRightViewer();
  };
});

// ---------------------------------------------------------------- stock list
async function loadStocks(kw) {
  const d = await api("stocks", { kw });
  const el = $("#stockList");
  el.innerHTML = d.stocks.map((s) =>
    `<div class="stock" data-code="${s.code}">
       <span class="code">${s.code.split(".")[0]}</span>
       <span class="mkt">${s.market}</span></div>`).join("");
  el.querySelectorAll(".stock").forEach((n) => n.onclick = () => selectStock(n.dataset.code));
  markSel();
}
function markSel() {
  document.querySelectorAll(".stock").forEach((n) =>
    n.classList.toggle("sel", n.dataset.code === state.code));
}
$("#stockSearch").oninput = (e) => loadStocks(e.target.value.trim());

// ---------------------------------------------------------------- load a stock
async function selectStock(code) {
  state.code = code;
  state.filterRecs = [];
  $("#codeInput").value = code;
  $("#status").textContent = `加载 ${code} …（首次需抽取解析）`;
  markSel();
  try {
    state.basic = await api("basic", { code });
    $("#status").textContent =
      `${code} · ${state.basic.date} · ${state.basic.records.toLocaleString()} 条记录`;
    resetFilter();
    await applyFilter();
    const active = $("#tabs button.active").dataset.view;
    if (active === "map") loadMap();
    else if (active === "tick") loadTick();
  } catch (e) {
    $("#status").textContent = "加载失败：" + e.message;
  }
}
$("#loadBtn").onclick = () => {
  const c = $("#codeInput").value.trim().toUpperCase();
  if (c) selectStock(c);
};
$("#codeInput").onkeydown = (e) => { if (e.key === "Enter") $("#loadBtn").click(); };

// ---------------------------------------------------------------- filter + events
function resetFilter() {
  $("#fStart").value = ""; $("#fEnd").value = "";
  $("#fType").value = "全部"; $("#fMin").value = ""; $("#fMax").value = "";
  $("#fMinAmt").value = ""; $("#fMaxAmt").value = "";
  state.filterRecs = [];
}
$("#resetBtn").onclick = () => { resetFilter(); applyFilter(); };
$("#applyBtn").onclick = () => applyFilter(true);
$("#orderTrackBtn").onclick = () => { const v = $("#fOrder").value.trim(); if (v) trackOrder(v); };
$("#fOrder").onkeydown = (e) => { if (e.key === "Enter") $("#orderTrackBtn").click(); };
$("#jumpBtn").onclick = () => { $("#fStart").value = $("#fJump").value.trim(); applyFilter(); };
$("#fJump").onkeydown = (e) => { if (e.key === "Enter") $("#jumpBtn").click(); };

async function applyFilter(record) {
  if (!state.code) return;
  const p = {
    code: state.code, start: $("#fStart").value, end: $("#fEnd").value,
    type: $("#fType").value, min_qty: $("#fMin").value, max_qty: $("#fMax").value,
    min_amt: $("#fMinAmt").value, max_amt: $("#fMaxAmt").value,
    limit: 600,
  };
  const d = await api("events", p);
  renderEvents(d.events);
  state.lastSummary = d.summary;
  $("#viewerCount").textContent = `${d.total.toLocaleString()} 条（显示前 ${d.events.length}）`;
  if (record) {
    const qMin = $("#fMin").value, qMax = $("#fMax").value;
    const aMin = $("#fMinAmt").value, aMax = $("#fMaxAmt").value;
    const q = qMin || qMax ? ` 量[${qMin || "*"}~${qMax || "*"}股]` : "";
    const a = aMin || aMax ? ` 额[${aMin || "*"}~${aMax || "*"}万]` : "";
    state.filterRecs.push(`${$("#fType").value}${q}${a} (${d.total} 条)`);
  }
  refreshRightViewer();
}

const typeClass = (t) => t === "委托" ? "order" : t === "成交" ? "deal" : "cancel";
function renderEvents(evs) {
  const rows = evs.map((e) => `
    <tr data-buy="${e.buy_id}" data-sell="${e.sell_id}" data-side="${e.side}"
        data-time="${e.time}" data-seq="${e.seq}">
      <td>${e.seq}</td><td class="l">${e.time}</td>
      <td><span class="tag ${typeClass(e.type)}">${e.type}</span></td>
      <td class="${e.side === "买" ? "up" : "down"}">${e.side}</td>
      <td>${e.price ? e.price.toFixed(2) : "--"}</td>
      <td>${fmtNum(e.qty)}</td>
      <td>${e.amount ? e.amount.toFixed(2) : ""}</td>
      <td>${e.aseq}</td>
      <td>${e.buy_id || ""}</td><td>${e.sell_id || ""}</td>
    </tr>`).join("");
  $("#eventWrap").innerHTML = `
    <table><thead><tr>
      <th>序号</th><th class="l">时间</th><th>类型</th><th>方向</th><th>价格</th>
      <th>数量(股)</th><th>成交额(万)</th><th>序列号</th><th>买方委托号</th><th>卖方委托号</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
  $("#eventWrap").querySelectorAll("tbody tr").forEach((tr, i) => {
    tr.oncontextmenu = (ev) => {
      ev.preventDefault();
      if (!tr.classList.contains("sel")) {
        $("#eventWrap").querySelectorAll("tr.sel").forEach((x) => x.classList.remove("sel"));
        tr.classList.add("sel");
      }
      openCtx(ev, tr);
    };
    tr.onclick = (ev) => {
      const all = [...$("#eventWrap").querySelectorAll("tbody tr")];
      if (ev.shiftKey && state.lastSelIdx != null) {
        const [a, b] = [state.lastSelIdx, i].sort((x, y) => x - y);
        if (!ev.ctrlKey) all.forEach((x) => x.classList.remove("sel"));
        for (let k = a; k <= b; k++) all[k].classList.add("sel");
      } else if (ev.ctrlKey) {
        tr.classList.toggle("sel");
        state.lastSelIdx = i;
      } else {
        all.forEach((x) => x.classList.remove("sel"));
        tr.classList.add("sel");
        state.lastSelIdx = i;
      }
    };
  });
}

// ---------------------------------------------------------------- right panel
function refreshRightViewer() {
  const active = $("#tabs button.active").dataset.view;
  if (active !== "viewer") return;
  $("#rightTitle").textContent = "基本信息 / 汇总统计";
  const b = state.basic, s = state.lastSummary || {};
  if (!b) { $("#rightBody").innerHTML = ""; return; }
  const chg = b.change_pct;
  const info = [
    ["开盘价", b.open.toFixed(2)], ["昨收", b.prev_close.toFixed(2)],
    ["最新价", `<span class="${clsChg(chg)}">${b.last.toFixed(2)}</span>`],
    ["当日涨幅", `<span class="${clsChg(chg)}">${chg.toFixed(2)}%</span>`],
    ["最高", b.high.toFixed(2)], ["最低", b.low.toFixed(2)],
    ["涨停价", b.limit_up.toFixed(2)], ["跌停价", b.limit_down.toFixed(2)],
    ["换手率", b.turnover_rate == null ? "--" : b.turnover_rate.toFixed(2) + "%"],
    ["昨日涨幅", b.prev_change_pct == null ? "--" : b.prev_change_pct.toFixed(2) + "%"],
    ["流通股/市值", `${b.float_shares == null ? "--" : yi(b.float_shares)} / ${b.market_cap == null ? "--" : yi(b.market_cap)}`],
    ["是否涨停过", b.hit_limit_up ? "是" : "否"],
    ["是否跌停过", b.hit_limit_down ? "是" : "否"],
  ];
  const sm = [
    ["笔数", fmtNum(s.count)],
    ["总量/额", `${yi(s.total_vol)} / ${wanYuan(s.total_amt)}`],
    ["买入量/额", `${yi(s.buy_vol)} / ${wanYuan(s.buy_amt)}`],
    ["卖出量/额", `${yi(s.sell_vol)} / ${wanYuan(s.sell_amt)}`],
    ["买/卖额(倍)", s.buy_sell_ratio.toFixed(2)],
    ["净额(买-卖)", `<span class="${clsChg(s.net_amt)}">${wanYuan(s.net_amt)}</span>`],
    ["买占比(%)", s.buy_pct.toFixed(2)],
    ["买入均价", s.buy_avg.toFixed(2)], ["卖出均价", s.sell_avg.toFixed(2)],
  ];
  const rec = state.filterRecs.length
    ? `<h3>筛选记录</h3><div id="filterRecs">` +
      state.filterRecs.map((r, i) => `<div class="rec">${i + 1}. ${r}</div>`).join("") + `</div>`
    : "";
  $("#rightBody").innerHTML =
    `<div class="kv">${info.map((r) => kvRow(r)).join("")}</div>` +
    `<h3>汇总统计</h3><div class="kv">${sm.map((r) => kvRow(r)).join("")}</div>` + rec;
}
const kvRow = ([k, v]) => `<div class="row"><span class="k">${k}</span><span class="v">${v}</span></div>`;

// ---------------------------------------------------------------- context menu
let ctxTr = null;
function openCtx(ev, tr) {
  ctxTr = tr;
  const c = $("#ctx");
  c.style.left = ev.clientX + "px"; c.style.top = ev.clientY + "px";
  c.classList.add("on");
}
document.addEventListener("click", () => $("#ctx").classList.remove("on"));
$("#ctx").querySelectorAll("div").forEach((d) => d.onclick = () => {
  const act = d.dataset.act;
  if (!ctxTr) return;
  if (act === "track") {
    const oid = ctxTr.dataset.side === "买" ? ctxTr.dataset.buy : ctxTr.dataset.sell;
    trackOrder(oid);
  } else if (act === "book") {
    showBookAt(ctxTr.dataset.time);
  } else if (act === "region") {
    statSelectedRange();
  } else if (act === "csv") {
    exportSel("csv");
  } else if (act === "txt") {
    exportSel("txt");
  }
});

// 统计选中范围：对选中行（多选取时间跨度）做区间统计
async function statSelectedRange() {
  const sel = [...$("#eventWrap").querySelectorAll("tbody tr.sel")];
  if (!sel.length) { alert("请先选中一行或多行（Shift/Ctrl 多选）"); return; }
  const times = sel.map((tr) => tr.dataset.time).sort();
  const start = times[0], end = times[times.length - 1];
  const d = await api("region", { code: state.code, start, end });
  showRegionModal(d, start, end);
}
function showRegionModal(d, start, end) {
  $("#modalTitle").textContent = `区间统计 · ${state.code}`;
  if (!d.found) {
    $("#modalBody").innerHTML = '<div class="hint">选中范围内无成交。</div>';
    $("#modalFoot").textContent = ""; $("#modalBg").classList.add("on"); return;
  }
  const rows = [
    ["开始时间", d.start_time], ["结束时间", d.end_time],
    ["涨幅", d.change_pct.toFixed(4) + "%"],
    ["起始价", d.start_price.toFixed(2)],
    ["最高价", d.high.toFixed(2)], ["最低价", d.low.toFixed(2)],
    ["结束价", d.end_price.toFixed(2)],
    ["成交量", `${fmtNum(d.vol)} 股`],
    ["成交额", wanYuan(d.amt)],
    ["最大成交量", `${fmtNum(d.max_vol)} 股`],
    ["最大成交量方向", d.max_vol_side || "中性"],
    ["成交笔数", fmtNum(d.count)],
  ];
  $("#modalBody").innerHTML =
    `<table><thead><tr><th class="l">指标</th><th>数值</th></tr></thead><tbody>` +
    rows.map((r) => `<tr><td class="l">${r[0]}</td><td>${r[1]}</td></tr>`).join("") +
    `</tbody></table>`;
  $("#modalFoot").textContent = "";
  $("#modalBg").classList.add("on");
}

// ---------------------------------------------------------------- track order
async function trackOrder(oid) {
  if (!oid || oid === "0") { alert("该行无有效委托号"); return; }
  const d = await api("track", { code: state.code, order_id: oid });
  if (!d.found) { alert("未找到委托 " + oid); return; }
  $("#modalTitle").textContent = `追踪订单 · ${state.code} · 委托号 ${d.order_id}`;
  const rows = d.life.map((l) => `
    <tr><td class="l">${l.time}</td>
      <td><span class="tag ${typeClass(l.type)}">${l.type}</span></td>
      <td>${fmtNum(l.qty)}</td><td>${l.price ? l.price.toFixed(2) : "--"}</td>
      <td>${l.counter || "—"}</td></tr>`).join("");
  $("#modalBody").innerHTML = `
    <div style="margin-bottom:8px">方向 <b class="${d.side === "买" ? "up" : "down"}">${d.side}</b>
      · 状态 <b>${d.status}</b></div>
    <table><thead><tr><th class="l">时间</th><th>类型</th><th>数量(股)</th><th>价格</th><th>对手委托号</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
  $("#modalFoot").textContent =
    `委托 ${fmtNum(d.total_qty)}股 · 委托价 ${d.order_price.toFixed(2)}　成交 ${fmtNum(d.filled_qty)}股　撤单 ${fmtNum(d.canceled_qty)}股`;
  $("#modalBg").classList.add("on");
}
$("#modalClose").onclick = () => $("#modalBg").classList.remove("on");
$("#modalBg").onclick = (e) => { if (e.target.id === "modalBg") $("#modalBg").classList.remove("on"); };

// ---------------------------------------------------------------- export csv/txt
function exportSel(fmt) {
  const sel = [...$("#eventWrap").querySelectorAll("tbody tr.sel")];
  const trs = sel.length ? sel : [...$("#eventWrap").querySelectorAll("tbody tr")];
  const cols = ["序号", "时间", "类型", "方向", "价格", "数量", "成交额万", "序列号", "买方委托号", "卖方委托号"];
  const sep = fmt === "txt" ? "\t" : ",";
  const head = cols.join(sep);
  const lines = trs.map((tr) => [...tr.children].map((td) => td.textContent.trim()).join(sep));
  const mime = fmt === "txt" ? "text/plain" : "text/csv";
  const blob = new Blob(["\ufeff" + head + "\n" + lines.join("\n")], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${state.code}_events${sel.length ? "_selected" : ""}.${fmt}`; a.click();
}

// ---------------------------------------------------------------- order book
async function showBookAt(time) {
  const d = await api("orderbook", { code: state.code, t: time });
  renderBookPanel(d, `盘口 @ ${d.time || time}`);
}
function renderBookPanel(d, title) {
  $("#rightTitle").textContent = title || "十档盘口";
  if (!d || !d.asks) { $("#rightBody").innerHTML = '<div class="hint">无盘口数据</div>'; return; }
  const maxQ = Math.max(1, ...d.asks.map((a) => a[1]), ...d.bids.map((b) => b[1]));
  const lvl = (side, lbl, px, qy) => `
    <div class="lvl ${side}">
      <div class="bar" style="width:${(qy / maxQ * 100).toFixed(0)}%"></div>
      <span class="lb">${lbl}</span>
      <span class="px ${side === "ask" ? "down" : "up"}">${px ? px.toFixed(2) : "--"}</span>
      <span class="qy">${qy ? fmtNum(qy / 100) : ""}</span></div>`;
  let html = '<div class="ob">';
  for (let i = 9; i >= 0; i--) html += lvl("ask", "卖" + (i + 1), d.asks[i][0], d.asks[i][1]);
  const chg = state.basic ? (d.last - state.basic.prev_close) / state.basic.prev_close * 100 : 0;
  html += `<div class="last"><span class="${clsChg(chg)}">${d.last.toFixed(2)}</span>
    <span class="${clsChg(chg)}">${chg.toFixed(2)}%</span></div>`;
  for (let i = 0; i < 10; i++) html += lvl("bid", "买" + (i + 1), d.bids[i][0], d.bids[i][1]);
  html += "</div>";
  html += `<div class="kv">
    ${kvRow(["委比(%)", d.committee_ratio.toFixed(2)])}
    ${kvRow(["委差(手)", fmtNum(d.committee_diff / 100)])}
    ${kvRow(["委托买(手)", fmtNum(d.total_bid / 100)])}
    ${kvRow(["委托卖(手)", fmtNum(d.total_ask / 100)])}</div>`;
  $("#rightBody").innerHTML = html;
}

// ---------------------------------------------------------------- 委托地图
let mapChart, tickChart;
const dayMs = (t) => {                      // HHMMSSmmm -> 当日毫秒
  const h = Math.floor(t / 1e7), m = Math.floor(t / 1e5) % 100,
    s = Math.floor(t / 1e3) % 100, ms = t % 1000;
  return ((h * 60 + m) * 60 + s) * 1000 + ms;
};
async function loadMap() {
  $("#rightTitle").textContent = "十档盘口";
  const [d, lad, bk] = await Promise.all([
    api("ordermap", { code: state.code, min_qty: $("#mapMin").value, max_qty: $("#mapMax").value }),
    api("ladder", { code: state.code }),
    api("books", { code: state.code }),
  ]);
  state.ladder = lad.ladder; state.books = bk;
  if (!mapChart) mapChart = echarts.init($("#mapChart"), "dark");
  const buy = d.buy, sell = d.sell;   // 服务端已输出 [日内毫秒, 价, 量, 委托号]
  let sizeMax = 1;
  for (let i = 0; i < buy.length; i++) if (buy[i][2] > sizeMax) sizeMax = buy[i][2];
  for (let i = 0; i < sell.length; i++) if (sell[i][2] > sizeMax) sizeMax = sell[i][2];
  const sym = (v) => 4 + 22 * Math.sqrt(v[2] / sizeMax);
  mapChart.setOption({
    backgroundColor: "transparent",
    grid: { left: 55, right: 20, top: 20, bottom: 40 },
    tooltip: {
      formatter: (p) => `价格 ${p.value[1].toFixed(2)}<br>委托量 ${fmtNum(p.value[2])}股<br>委托号 ${p.value[3]}<br>${fmtHMS(p.value[0])}`,
    },
    xAxis: { type: "value", min: dayMs(91500000), max: dayMs(150000000),
      axisLabel: { formatter: fmtHMS, color: "#8196a5" }, splitLine: { show: false } },
    yAxis: { scale: true, axisLabel: { color: "#8196a5" },
      splitLine: { lineStyle: { color: "#16242f" } } },
    dataZoom: [{ type: "inside" }, { type: "inside", orient: "vertical" }],
    series: [
      { name: "委托买入", type: "scatterGL", data: buy, symbolSize: sym,
        itemStyle: { color: "#2fcf8f", opacity: .5 } },
      { name: "委托卖出", type: "scatterGL", data: sell, symbolSize: sym,
        itemStyle: { color: "#ff5f6d", opacity: .5 } },
      { name: "_cursor", type: "scatter", data: [], silent: true },
    ],
  }, true);
  mapChart.getZr().off("mousemove");
  mapChart.getZr().on("mousemove", (e) => {
    if (playTimer) return;
    const pt = mapChart.convertFromPixel({ gridIndex: 0 }, [e.offsetX, e.offsetY]);
    if (pt) { clearTimeout(mapChart._tm); mapChart._tm = setTimeout(() =>
      mapSetTime(msToHMS(pt[0]) / 1000, true), 120); }
  });
  mapSetTime(150000, false);
}
$("#mapApply").onclick = () => loadMap();

// 客户端十档快照：按毫秒时间在全天快照里二分查找
function bookObjAt(tt) {
  const B = state.books;
  if (!B || !B.t.length) return null;
  let lo = 0, hi = B.t.length - 1, idx = 0;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (B.t[m] <= tt) { idx = m; lo = m + 1; } else hi = m - 1; }
  const asks = B.ask_px[idx].map((p, k) => [p, B.ask_qty[idx][k]]);
  const bids = B.bid_px[idx].map((p, k) => [p, B.bid_qty[idx][k]]);
  const tb = bids.reduce((s, x) => s + x[1], 0), ta = asks.reduce((s, x) => s + x[1], 0);
  const den = tb + ta;
  return { t: B.t[idx], time: fmtHMS(dayMs(B.t[idx])), last: B.last[idx], asks, bids,
    total_bid: tb, total_ask: ta,
    committee_ratio: den ? (tb - ta) / den * 100 : 0, committee_diff: tb - ta };
}
const shortK = (v) => {
  if (!v) return "";
  const a = Math.abs(v);
  if (a >= 1e8) return (v / 1e8).toFixed(1) + "亿";
  if (a >= 1e4) return (v / 1e4).toFixed(1) + "万";
  return String(v);
};
// 左侧十档累积阶梯：每价位累计委托买/卖、撤单，叠加当前时刻队列
function renderLadder(bk) {
  const L = state.ladder;
  if (!L) { $("#mapLadder").innerHTML = ""; return; }
  const q = {}; const lastP = bk ? bk.last : 0;
  if (bk) {
    bk.asks.forEach((a) => { if (a[0]) q[a[0].toFixed(2)] = ["a", a[1]]; });
    bk.bids.forEach((b) => { if (b[0]) q[b[0].toFixed(2)] = ["b", b[1]]; });
  }
  const rows = L.map((r) => {
    const key = r.price.toFixed(2), cur = q[key];
    const cls = cur ? (cur[0] === "a" ? "ask" : "bid") : (lastP && r.price > lastP ? "ask" : "bid");
    const here = lastP && Math.abs(r.price - lastP) < 0.005 ? "here" : "";
    const bq = cur && cur[0] === "b" ? fmtNum(cur[1]) : "";
    const sq = cur && cur[0] === "a" ? fmtNum(cur[1]) : "";
    return `<tr class="${cls} ${here}">
      <td>${shortK(r.buy_vol)}</td><td class="cx">${shortK(r.buy_cancel)}</td>
      <td class="bq">${bq}</td><td class="px">${key}</td><td class="sq">${sq}</td>
      <td class="cx">${shortK(r.sell_cancel)}</td><td>${shortK(r.sell_vol)}</td></tr>`;
  }).join("");
  $("#mapLadder").innerHTML = `<table><thead><tr>
    <th>买累计</th><th>买撤</th><th>买盘</th><th>价格</th><th>卖盘</th><th>卖撤</th><th>卖累计</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
  const h = $("#mapLadder .here"); if (h) h.scrollIntoView({ block: "center", behavior: "instant" });
}

// 回放引擎
let playTimer = null, playT = 150000, lastTblT = 0;
const hmsToSec = (v) => Math.floor(v / 10000) * 3600 + Math.floor(v / 100) % 100 * 60 + v % 100;
const secToHms = (t) => { t = Math.max(0, Math.round(t)); return Math.floor(t / 3600) * 10000 + Math.floor(t / 60) % 60 * 100 + t % 60; };
function addSec(hms, sec) {
  let r = secToHms(hmsToSec(hms) + sec);
  if (r > 113000 && r < 130000) r = 130000;   // 跳过午休
  return r;
}
function mapSetTime(hms, fromUser) {
  playT = hms;
  $("#mapScrubT").textContent = scrubFmt(hms);
  syncLocSelects(hms);
  const tt = hms * 1000, bk = bookObjAt(tt);
  if (bk) { renderBookPanel(bk, `盘口 @ ${bk.time}`); renderLadder(bk); }
  if (mapChart) mapChart.setOption({ series: [{}, {}, { markLine: {
    silent: true, symbol: "none", label: { show: false },
    lineStyle: { color: "#f2b84b", width: 1 }, data: [{ xAxis: tt }] } }] });
  const now = Date.now();
  if (fromUser || now - lastTblT > 700) {
    lastTblT = now; const e = String(hms).padStart(6, "0") + "000";
    renderOrders("mapBuyWrap", "买", "委托买入", undefined, e);
    renderOrders("mapSellWrap", "卖", "委托卖出", undefined, e);
  }
}
function pausePlay() {
  if (playTimer) clearInterval(playTimer);
  playTimer = null; $("#mapPlay").textContent = "▶ 启动"; $("#mapPlay").classList.remove("active");
}
$("#mapPlay").onclick = () => {
  if (playTimer) { pausePlay(); return; }
  if (playT >= 150000) mapSetTime(91500, true);
  $("#mapPlay").textContent = "⏸ 暂停"; $("#mapPlay").classList.add("active");
  playTimer = setInterval(() => {
    const spd = Number($("#mapSpeed").value);
    const nt = addSec(playT, spd / 10);
    if (nt >= 150000) { mapSetTime(150000); pausePlay(); return; }
    mapSetTime(nt);
  }, 100);
};
$("#mapReset").onclick = () => { pausePlay(); mapSetTime(91500, true); };

// 委托明细表（委托时间/编号/数量/已成交/已撤单）
async function renderOrders(wrapId, side, title, start, end) {
  const d = await api("orders", { code: state.code, side, start, end, limit: 500 });
  const rows = d.orders.map((o) => `
    <tr><td class="l">${o.time}</td><td>${o.order_id}</td><td>${fmtNum(o.qty)}</td>
      <td>${fmtNum(o.filled)}</td><td>${fmtNum(o.canceled)}</td></tr>`).join("");
  $("#" + wrapId).innerHTML = `<h4>${title}（${d.total.toLocaleString()}）</h4>
    <table><thead><tr><th class="l">委托时间</th><th>委托编号</th><th>委托数量</th>
    <th>已成交</th><th>已撤单</th></tr></thead><tbody>${rows}</tbody></table>`;
}
const scrubFmt = (v) => {
  const h = Math.floor(v / 10000), m = Math.floor(v / 100) % 100, s = v % 100;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.000`;
};
// 定位下拉：时(9-15) / 分 / 秒
function fillSelect(sel, from, to, pad) {
  let o = "";
  for (let i = from; i <= to; i++) o += `<option value="${i}">${String(i).padStart(pad, "0")}</option>`;
  sel.innerHTML = o;
}
fillSelect($("#mapLocH"), 9, 15, 2);
fillSelect($("#mapLocM"), 0, 59, 2);
fillSelect($("#mapLocS"), 0, 59, 2);
let locSyncing = false;
function syncLocSelects(hms) {
  locSyncing = true;
  $("#mapLocH").value = Math.floor(hms / 10000);
  $("#mapLocM").value = Math.floor(hms / 100) % 100;
  $("#mapLocS").value = hms % 100;
  locSyncing = false;
}
$("#mapLocBtn").onclick = () => {
  pausePlay();
  const h = Number($("#mapLocH").value), m = Number($("#mapLocM").value), s = Number($("#mapLocS").value);
  mapSetTime(h * 10000 + m * 100 + s, true);
};
const fmtHMS = (ms) => {
  const s = Math.floor(ms / 1000); const h = Math.floor(s / 3600),
    m = Math.floor(s / 60) % 60, ss = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
};
const msToHMS = (ms) => {                   // -> HHMMSSmmm 供后端
  const s = Math.floor(ms / 1000); const h = Math.floor(s / 3600),
    m = Math.floor(s / 60) % 60, ss = s % 60;
  return h * 1e7 + m * 1e5 + ss * 1e3;
};

// ---------------------------------------------------------------- 逐笔 / 分时
async function loadTick() {
  $("#rightTitle").textContent = "十档盘口";
  const d = await api("intraday", { code: state.code });
  if (!tickChart) tickChart = echarts.init($("#tickChart"), "dark");
  const times = d.points.map((p) => p.time.slice(0, 8));
  const price = d.points.map((p) => p.price);
  const avg = d.points.map((p) => p.avg);
  const vol = d.points.map((p) => p.vol);
  tickChart.setOption({
    backgroundColor: "transparent",
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    tooltip: { trigger: "axis" },
    grid: [{ left: 55, right: 20, top: 15, height: "60%" },
           { left: 55, right: 20, top: "72%", height: "18%" }],
    xAxis: [
      { type: "category", data: times, axisLabel: { color: "#8196a5" } },
      { type: "category", data: times, gridIndex: 1, axisLabel: { show: false } }],
    yAxis: [
      { scale: true, axisLabel: { color: "#8196a5" }, splitLine: { lineStyle: { color: "#16242f" } } },
      { gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } }],
    dataZoom: [{ type: "inside", xAxisIndex: [0, 1] },
               { type: "slider", xAxisIndex: [0, 1], bottom: 0, height: 16 }],
    series: [
      { name: "价格", type: "line", data: price, showSymbol: false,
        lineStyle: { color: "#e7d27a", width: 1 } },
      { name: "均价", type: "line", data: avg, showSymbol: false,
        lineStyle: { color: "#27c7b8", width: 1 } },
      { name: "成交量", type: "bar", data: vol, xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: { color: "#3a6b82" } },
    ],
  }, true);
  loadTrades();
  showBookAt("150000000");
}
async function loadTrades(start, end) {
  const d = await api("trades", { code: state.code, start, end, limit: 800 });
  const rows = d.trades.map((e) => `
    <tr><td class="l">${e.time}</td>
      <td class="${e.side === "买" ? "up" : "down"}">${e.side}</td>
      <td>${e.price.toFixed(2)}</td><td>${fmtNum(e.qty)}</td>
      <td>${e.amount.toFixed(2)}</td></tr>`).join("");
  $("#tradeWrap").innerHTML = `<h4>成交（${d.total.toLocaleString()}）</h4>
    <table><thead><tr>
    <th class="l">时间</th><th>方向</th><th>价格</th><th>数量(股)</th><th>成交额(万)</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
  renderOrders("tbuyWrap", "买", "委托买入", start, end);
  renderOrders("tsellWrap", "卖", "委托卖出", start, end);
}
$("#regionBtn").onclick = async () => {
  if (!tickChart || !state.code) return;
  const opt = tickChart.getOption();
  const dz = opt.dataZoom[0];
  const cats = opt.xAxis[0].data;
  const n = cats.length;
  const s = cats[Math.floor((dz.startValue != null ? dz.startValue : (dz.start / 100) * (n - 1)))];
  const e = cats[Math.floor((dz.endValue != null ? dz.endValue : (dz.end / 100) * (n - 1)))];
  const d = await api("region", { code: state.code, start: s, end: e });
  if (!d.found) { alert("该区间无成交"); return; }
  $("#modalTitle").textContent = `区间统计 · ${state.code}`;
  const rows = [
    ["开始时间", d.start_time], ["结束时间", d.end_time],
    ["涨幅", `<span class="${clsChg(d.change_pct)}">${d.change_pct.toFixed(2)}%</span>`],
    ["起始价", d.start_price.toFixed(2)], ["最高价", d.high.toFixed(2)],
    ["最低价", d.low.toFixed(2)], ["结束价", d.end_price.toFixed(2)],
    ["成交量", yi(d.vol) + "股"], ["成交额", wanYuan(d.amt)],
    ["最大单笔", fmtNum(d.max_vol) + "股"], ["最大单方向", d.max_vol_side],
    ["成交笔数", fmtNum(d.count)],
  ];
  $("#modalBody").innerHTML = `<div class="kv">${rows.map(kvRow).join("")}</div>`;
  $("#modalFoot").textContent = "区间由分时图当前可视范围决定";
  $("#modalBg").classList.add("on");
  loadTrades(s, e);
};

// ---------------------------------------------------------------- init
window.addEventListener("resize", () => { mapChart && mapChart.resize(); tickChart && tickChart.resize(); });
loadStocks("");
