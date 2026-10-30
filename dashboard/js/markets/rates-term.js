// 全球市场: 术语解释 · 10Y-2Y 曲线交易 regime panel.

const RATES_TERM_LOOKBACK = 20;
const RATES_TERM_REGIMES = {
  "bear-steep": { name: "熊陡", tone: "bear", curve: "利差走阔", equity: "杀估值 · 成长股最不利", detail: "长端主导上行，贴现率抬升" },
  "bear-flat": { name: "熊平", tone: "bear", curve: "利差收窄", equity: "紧缩压制 · 高位震荡", detail: "短端主导上行，政策利率牵引" },
  "bull-steep": { name: "牛陡", tone: "bull", curve: "利差走阔", equity: "流动性友好 · 小盘成长弹性", detail: "短端主导下行，降息预期升温" },
  "bull-flat": { name: "牛平", tone: "bull", curve: "利差收窄", equity: "盈利转弱 · 防御占优", detail: "长端主导下行，增长与避险驱动" },
  range: { name: "震荡", tone: "range", curve: "方向不明", equity: "信号不足，按区间对待", detail: "短端与利差的变动均小于 5bp" }
};

function ratesTermPoint(key) {
  const rows = (state.series[key] || []).filter(row => Number.isFinite(row.close));
  if (!rows.length) return null;
  const last = rows.at(-1);
  const lookback = Math.min(RATES_TERM_LOOKBACK, rows.length - 1);
  const base = rows[rows.length - 1 - lookback] || last;
  return { value: last.close, delta: (last.close - base.close) * (key === "spread" ? 1 : 100), lookback };
}

function ratesTermSnapshot() {
  const ten = ratesTermPoint("treasury10y");
  const two = ratesTermPoint("treasury2y");
  const spread = ratesTermPoint("spread");
  const curve = spread ? spread.delta : (ten && two ? ten.delta - two.delta : null);
  let regime = null;
  if (two && Number.isFinite(curve)) {
    const quiet = Math.abs(two.delta) < 5 && Math.abs(curve) < 5;
    const key = quiet
      ? "range"
      : two.delta >= 0
        ? (curve >= 0 ? "bear-steep" : "bear-flat")
        : (curve >= 0 ? "bull-steep" : "bull-flat");
    regime = RATES_TERM_REGIMES[key];
  }
  return { ten, two, spread, regime };
}

function updateRatesTerm() {
  const tenHost = document.getElementById("ratesTerm10y");
  if (!tenHost) return;
  const snapshot = ratesTermSnapshot();
  const rateText = point => point ? `${point.value.toFixed(2)}%` : "—";
  const bpText = value => Number.isFinite(value) ? `${value > 0 ? "+" : ""}${value.toFixed(0)}bp` : "—";
  tenHost.textContent = rateText(snapshot.ten);
  document.getElementById("ratesTerm2y").textContent = rateText(snapshot.two);
  const spreadHost = document.getElementById("ratesTermSpread");
  spreadHost.textContent = snapshot.spread ? bpText(snapshot.spread.value) : "—";
  spreadHost.classList.toggle("inverted", Boolean(snapshot.spread) && snapshot.spread.value < 0);

  const lookbacks = [snapshot.ten, snapshot.two].filter(Boolean).map(point => point.lookback);
  const lookback = lookbacks.length ? Math.min(...lookbacks) : RATES_TERM_LOOKBACK;
  document.getElementById("ratesTermDeltaLabel").textContent = `近 ${lookback} 个交易日变化`;
  document.getElementById("ratesTermDelta").textContent = snapshot.ten && snapshot.two
    ? `10Y ${bpText(snapshot.ten.delta)} · 2Y ${bpText(snapshot.two.delta)}`
    : "—";

  const stateHost = document.getElementById("ratesTermState");
  stateHost.classList.remove("bear", "bull", "range");
  if (!snapshot.regime) {
    document.getElementById("ratesTermStateName").textContent = "等待数据";
    document.getElementById("ratesTermStateNote").textContent = "需要 10Y / 2Y / 利差三张市场卡片";
    return;
  }
  stateHost.classList.add(snapshot.regime.tone);
  document.getElementById("ratesTermStateName").textContent = snapshot.regime.name;
  document.getElementById("ratesTermStateNote").textContent =
    `${snapshot.regime.detail} · ${snapshot.regime.equity}`;
}
