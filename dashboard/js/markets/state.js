// 全球市场: asset catalogue, ticker selection persistence, shared market state and data-point cache.

const ASSETS = {
  fedFunds: { name: "美国有效联邦基金利率", short: "FED FUNDS", category: "bonds", unit: "%", source: "usdata", usdataId: "fed_funds_rate", kind: "rate", digits: 2, color: "#ffb74d" },
  treasury2y: { name: "美国 2 年期国债收益率", short: "US 2Y", category: "bonds", unit: "%", source: "usdata", usdataId: "treasury_2y", kind: "rate", digits: 2, color: "#26a69a" },
  treasury10y: { name: "美国 10 年期国债收益率", short: "US 10Y", category: "bonds", unit: "%", source: "usdata", usdataId: "treasury_10y", kind: "rate", digits: 2, color: "#4db6ac" },
  spread: { name: "美债 10Y-2Y", short: "10Y-2Y", category: "bonds", unit: " bp", source: "usdata", usdataId: "treasury_10y_2y_spread", multiplier: 100, kind: "rate", digits: 1, color: "#38d7c5" },
  qqq: { name: "纳指 100 ETF", short: "QQQ", category: "stocks", symbol: "QQQ", futu: true, digits: 2, prefix: "$", color: "#54a4ff" },
  spy: { name: "标普 500 ETF", short: "SPY", category: "stocks", symbol: "SPY", digits: 2, prefix: "$", color: "#56b4e9" },
  dia: { name: "道琼斯 ETF", short: "DIA", category: "stocks", symbol: "DIA", digits: 2, prefix: "$", color: "#6fa8dc" },
  iwm: { name: "罗素 2000 ETF", short: "IWM", category: "stocks", symbol: "IWM", digits: 2, prefix: "$", color: "#76b7b2" },
  aapl: { name: "苹果", short: "AAPL", category: "stocks", symbol: "AAPL", digits: 2, prefix: "$", color: "#a7b1ba" },
  msft: { name: "微软", short: "MSFT", category: "stocks", symbol: "MSFT", digits: 2, prefix: "$", color: "#65a9e8" },
  nvda: { name: "英伟达", short: "NVDA", category: "stocks", symbol: "NVDA", digits: 2, prefix: "$", color: "#76b947" },
  tsla: { name: "特斯拉", short: "TSLA", category: "stocks", symbol: "TSLA", digits: 2, prefix: "$", color: "#e95d5d" },
  meta: { name: "Meta", short: "META", category: "stocks", symbol: "META", digits: 2, prefix: "$", color: "#5b8def" },
  amzn: { name: "亚马逊", short: "AMZN", category: "stocks", symbol: "AMZN", digits: 2, prefix: "$", color: "#f3a847" },
  googl: { name: "Alphabet", short: "GOOGL", category: "stocks", symbol: "GOOGL", digits: 2, prefix: "$", color: "#4285f4" },
  soxl: { name: "半导体 3 倍做多 ETF", short: "SOXL", category: "stocks", symbol: "SOXL", digits: 2, prefix: "$", color: "#ff8f3f" },
  csi300: { name: "沪深 300", short: "CSI300", category: "stocks", symbol: "000300.SS", akshareSymbol: "sh000300", chartType: "candlestick", digits: 2, color: "#ff6577" },
  nasdaq: { name: "纳斯达克综指", short: "NASDAQ", category: "stocks", symbol: "^IXIC", digits: 2, color: "#a889ff" },
  sp500: { name: "标普 500 指数", short: "S&P 500", category: "stocks", symbol: "^GSPC", digits: 2, color: "#4fc3f7" },
  dow: { name: "道琼斯工业指数", short: "DJIA", category: "stocks", symbol: "^DJI", digits: 2, color: "#42a5f5" },
  hsi: { name: "恒生指数", short: "HSI", category: "stocks", symbol: "^HSI", digits: 2, color: "#ef6c70" },
  nikkei: { name: "日经 225", short: "NIKKEI", category: "stocks", symbol: "^N225", digits: 2, color: "#ef5350" },
  tlt: { name: "美国长期国债 ETF", short: "TLT", category: "bonds", symbol: "TLT", digits: 2, prefix: "$", color: "#4db6ac" },
  ief: { name: "美国 7-10 年国债 ETF", short: "IEF", category: "bonds", symbol: "IEF", digits: 2, prefix: "$", color: "#26a69a" },
  shy: { name: "美国 1-3 年国债 ETF", short: "SHY", category: "bonds", symbol: "SHY", digits: 2, prefix: "$", color: "#80cbc4" },
  tip: { name: "美国通胀保值债券 ETF", short: "TIP", category: "bonds", symbol: "TIP", digits: 2, prefix: "$", color: "#00897b" },
  lqd: { name: "投资级公司债 ETF", short: "LQD", category: "bonds", symbol: "LQD", digits: 2, prefix: "$", color: "#26c6da" },
  hyg: { name: "高收益公司债 ETF", short: "HYG", category: "bonds", symbol: "HYG", digits: 2, prefix: "$", color: "#00acc1" },
  bnd: { name: "美国综合债券 ETF", short: "BND", category: "bonds", symbol: "BND", digits: 2, prefix: "$", color: "#4dd0e1" },
  usNfp: { name: "美国非农就业", short: "US NFP", category: "economy", kind: "macro", usdataId: "nonfarm_payrolls", transform: "diff", digits: 0, unit: "K", color: "#ff8a65" },
  usCpi: { name: "美国 CPI 同比", short: "US CPI", category: "economy", kind: "macro", usdataId: "cpi", transform: "yoy", digits: 2, unit: "%", color: "#2563eb" },
  usPpi: { name: "美国 PPI 同比", short: "US PPI", category: "economy", kind: "macro", usdataId: "ppi_final_demand", transform: "yoy", digits: 2, unit: "%", color: "#4f46e5" },
  usRate: { name: "美国有效联邦基金利率", short: "US RATE", category: "economy", kind: "macro", usdataId: "fed_funds_rate", digits: 2, unit: "%", color: "#0e7490" },
  cnCpi: { name: "中国 CPI 同比", short: "CN CPI", category: "economy", kind: "macro", source: "calendar-history", calendarTitle: "Inflation Rate YoY", digits: 2, unit: "%", color: "#ef4444" },
  cnPpi: { name: "中国 PPI 同比", short: "CN PPI", category: "economy", kind: "macro", source: "calendar-history", calendarTitle: "PPI YoY", digits: 2, unit: "%", color: "#f97316" },
  cnRate: { name: "中国 1 年期 LPR", short: "CN 1Y LPR", category: "economy", kind: "macro", source: "calendar-history", calendarTitle: "Loan Prime Rate 1Y", digits: 2, unit: "%", color: "#eab308" },
  vix: { name: "标普 500 波动率指数", short: "VIX", category: "options", symbol: "^VIX", digits: 2, color: "#ff7043" },
  vix3m: { name: "3 月波动率指数", short: "VIX3M", category: "options", symbol: "^VIX3M", digits: 2, color: "#ff8a65" },
  vvix: { name: "VIX 波动率指数", short: "VVIX", category: "options", symbol: "^VVIX", digits: 2, color: "#ffab91" },
  skew: { name: "标普 500 偏度指数", short: "SKEW", category: "options", symbol: "^SKEW", digits: 2, color: "#ffb74d" },
  cny: { name: "美元/人民币", short: "USD/CNY", category: "fx", symbol: "CNY=X", digits: 4, color: "#f5bd59" },
  eurusd: { name: "欧元/美元", short: "EUR/USD", category: "fx", symbol: "EURUSD=X", digits: 4, color: "#64b5f6" },
  usdjpy: { name: "美元/日元", short: "USD/JPY", category: "fx", symbol: "JPY=X", digits: 2, color: "#ef9a9a" },
  gbpusd: { name: "英镑/美元", short: "GBP/USD", category: "fx", symbol: "GBPUSD=X", digits: 4, color: "#7986cb" },
  dxy: { name: "美元指数", short: "DXY", category: "fx", symbol: "DX-Y.NYB", digits: 2, color: "#ffee58" },
  btc: { name: "比特币", short: "BTC", category: "crypto", symbol: "BTC-USD", digits: 0, prefix: "$", color: "#f7931a" },
  eth: { name: "以太坊", short: "ETH", category: "crypto", symbol: "ETH-USD", digits: 1, prefix: "$", color: "#8c9eff" },
  sol: { name: "Solana", short: "SOL", category: "crypto", symbol: "SOL-USD", digits: 2, prefix: "$", color: "#14f195" },
  gold: { name: "黄金期货", short: "GOLD", category: "commodities", symbol: "GC=F", digits: 1, prefix: "$", color: "#ffd166" },
  silver: { name: "白银期货", short: "SILVER", category: "commodities", symbol: "SI=F", digits: 2, prefix: "$", color: "#b0bec5" },
  crude: { name: "WTI 原油期货", short: "WTI", category: "commodities", symbol: "CL=F", digits: 2, prefix: "$", color: "#8d6e63" },
  brent: { name: "布伦特原油期货", short: "BRENT", category: "commodities", symbol: "BZ=F", digits: 2, prefix: "$", color: "#a1887f" },
  copper: { name: "铜期货", short: "COPPER", category: "commodities", symbol: "HG=F", digits: 2, prefix: "$", color: "#d07c4c" },
  natgas: { name: "天然气期货", short: "NATGAS", category: "commodities", symbol: "NG=F", digits: 2, prefix: "$", color: "#90caf9" },
  soxx: { name: "iShares 半导体 ETF", short: "SOXX", category: "stocks", symbol: "SOXX", digits: 2, prefix: "$", color: "#38d7c5" },
  smh: { name: "VanEck 半导体 ETF", short: "SMH", category: "stocks", symbol: "SMH", digits: 2, prefix: "$", color: "#54a4ff" },
  tsm: { name: "台积电 ADR", short: "TSM", category: "stocks", symbol: "TSM", digits: 2, prefix: "$", color: "#ff6577" },
  amd: { name: "AMD", short: "AMD", category: "stocks", symbol: "AMD", digits: 2, prefix: "$", color: "#f5bd59" },
  avgo: { name: "博通", short: "AVGO", category: "stocks", symbol: "AVGO", digits: 2, prefix: "$", color: "#a889ff" },
  mu: { name: "美光科技", short: "MU", category: "stocks", symbol: "MU", digits: 2, prefix: "$", color: "#ef6c70" },
  asml: { name: "阿斯麦 ADR", short: "ASML", category: "stocks", symbol: "ASML", digits: 2, prefix: "$", color: "#42a5f5" },
  amat: { name: "应用材料", short: "AMAT", category: "stocks", symbol: "AMAT", digits: 2, prefix: "$", color: "#4db6ac" },
  lrcx: { name: "泛林集团", short: "LRCX", category: "stocks", symbol: "LRCX", digits: 2, prefix: "$", color: "#76b7b2" },
  klac: { name: "科磊", short: "KLAC", category: "stocks", symbol: "KLAC", digits: 2, prefix: "$", color: "#ff8a65" },
  intc: { name: "英特尔", short: "INTC", category: "stocks", symbol: "INTC", digits: 2, prefix: "$", color: "#7e57c2" },
  txn: { name: "德州仪器", short: "TXN", category: "stocks", symbol: "TXN", digits: 2, prefix: "$", color: "#ab47bc" },
  us10y: { name: "美国10年期国债收益率", short: "US10Y", category: "bonds", symbol: "^TNX", digits: 2, unit: "%", color: "#f5bd59" }
};

const TICKER_CATEGORIES = [
  ["all", "All"],
  ["stocks", "Stocks"],
  ["bonds", "Bonds"],
  ["economy", "Economy"],
  ["options", "Options"],
  ["fx", "FX"],
  ["crypto", "Crypto"],
  ["commodities", "Commodities"]
];

const RANGE_OPTIONS = {
  "1d": { range: "1d", interval: "5m", label: "1D" },
  "1mo": { range: "1mo", interval: "1d", label: "1M" },
  "6mo": { range: "6mo", interval: "1d", label: "6M" },
  "1y": { range: "1y", interval: "1d", label: "1Y" },
  "5y": { range: "5y", interval: "1d", label: "5Y" },
  "10y": { range: "10y", interval: "1d", label: "10Y" },
  "20y": { range: "max", interval: "1d", label: "20Y" }
};

const KLINE_PERIODS = {
  day: { label: "日K" },
  week: { label: "周K" },
  month: { label: "月K" },
  quarter: { label: "季K" },
  "half-year": { label: "半年K" },
  year: { label: "年K" }
};
const LEGACY_DEFAULT_TICKERS = ["spread", "cny", "btc", "gold", "qqq"];
const PREVIOUS_DEFAULT_TICKERS = [
  "spread", "cny", "btc", "gold", "qqq", "csi300", "nasdaq",
  "usNfp", "usCpi", "usPpi", "cnCpi", "cnPpi"
];
const DEFAULT_TICKERS = [
  "fedFunds", "treasury2y", "treasury10y", "spread",
  "cny", "btc", "gold", "qqq", "csi300", "nasdaq",
  "usNfp", "usCpi", "usPpi", "cnCpi", "cnPpi"
];
const TICKER_SELECTION_KEY = "finance-dashboard-tickers";
let tickerCategory = "all";

function loadTickerSelection() {
  try {
    const saved = JSON.parse(localStorage.getItem(TICKER_SELECTION_KEY));
    if (Array.isArray(saved) && saved.length && saved.every(key => ASSETS[key])) {
      const isDefaultSelection = [LEGACY_DEFAULT_TICKERS, PREVIOUS_DEFAULT_TICKERS]
        .some(defaults => saved.length === defaults.length &&
          saved.every((key, index) => key === defaults[index]));
      return isDefaultSelection ? [...DEFAULT_TICKERS] : saved;
    }
  } catch (error) {
    console.warn("ticker selection", error);
  }
  return [...DEFAULT_TICKERS];
}

function saveTickerSelection() {
  try {
    localStorage.setItem(TICKER_SELECTION_KEY, JSON.stringify(state.tickers));
  } catch (error) {
    console.warn("ticker selection save", error);
  }
  persistMarketsSelection({ tickers: state.tickers });
}

// Shared selection lives in dashboard/tab/markets/selection.json (git-tracked) so it survives git pull.
const MARKETS_SELECTION_URL = "/api/markets-selection";

function persistMarketsSelection(patch) {
  fetch(MARKETS_SELECTION_URL, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch)
  }).catch(error => console.warn("markets selection persist", error));
}

async function applySharedMarketsSelection() {
  let shared;
  try {
    const response = await fetch(MARKETS_SELECTION_URL, { cache: "no-store" });
    if (!response.ok) return;
    shared = await response.json();
  } catch (error) {
    console.warn("markets selection load", error);
    return;
  }
  const seed = {};
  const tickers = Array.isArray(shared.tickers) ? shared.tickers.filter(key => ASSETS[key]) : [];
  if (tickers.length) {
    state.tickers = tickers;
    if (!tickers.includes(state.active)) state.active = tickers.includes("qqq") ? "qqq" : tickers[0];
    try { localStorage.setItem(TICKER_SELECTION_KEY, JSON.stringify(tickers)); } catch {}
  } else {
    seed.tickers = state.tickers;
  }
  if (Array.isArray(shared.macroIndicators) && shared.macroIndicators.every(key => typeof key === "string")) {
    macroCalendarState.selected = [...shared.macroIndicators];
    try { localStorage.setItem(MACRO_SELECTION_KEY, JSON.stringify(macroCalendarState.selected)); } catch {}
  } else {
    seed.macroIndicators = macroCalendarState.selected;
  }
  if (Object.keys(seed).length) persistMarketsSelection(seed);
  renderSelectors();
  renderTickers();
}

const initialTickerSelection = loadTickerSelection();
const state = {
  selected: new Set(["spread", "cny", "btc", "gold", "qqq"]),
  active: initialTickerSelection.includes("qqq") ? "qqq" : initialTickerSelection[0],
  tickers: initialTickerSelection,
  range: "1y",
  klinePeriod: "day",
  series: {},
  macroAll: {},
  usdataPromise: null,
  futuErrors: new Map(),
  loading: false,
  resetMarketRange: false,
  lazyRangeLoading: false,
  marketAll: {},
  marketLogicalRange: null,
  marketRangeChangeBlockedUntil: 0
};
const correlationState = {
  selected: new Set(["spread", "cny", "btc", "gold", "qqq"]),
  range: "1y",
  series: {},
  loading: false,
  requestId: 0
};
const marketRenderCache = {
  candle: { key: "", series: new Map() },
  compare: { key: "", series: new Map() }
};
const DATA_POINT_CACHE_TTL = 60_000;
const dataPointCache = new Map();
const marketHistoryPromises = new Map();
const klineAggregationCache = new WeakMap();

function cachedDataPoints(key, loader, ttl = DATA_POINT_CACHE_TTL) {
  const cached = dataPointCache.get(key);
  if (cached?.value && cached.expiresAt > Date.now()) return Promise.resolve(cached.value);
  if (cached?.promise) return cached.promise;

  const promise = loader().then(value => {
    dataPointCache.set(key, { value, expiresAt: Date.now() + ttl });
    return value;
  }).catch(error => {
    if (dataPointCache.get(key)?.promise === promise) dataPointCache.delete(key);
    throw error;
  });
  dataPointCache.set(key, { promise });
  return promise;
}
