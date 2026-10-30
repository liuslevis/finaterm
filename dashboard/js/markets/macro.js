// 全球市场: macro calendar indicators and macro history chart.

const MACRO_INDICATOR_LABELS = {
  "US:Nonfarm Payrolls Private": "美国非农就业",
  "US:Non Farm Payrolls": "美国非农就业人数",
  "US:Unemployment Rate": "美国失业率",
  "US:Inflation Rate YoY": "美国 CPI",
  "US:Core Inflation Rate YoY": "美国核心 CPI",
  "US:PPI YoY": "美国 PPI",
  "US:Core PPI YoY": "美国核心 PPI",
  "US:Core PCE Price Index MoM": "美国核心 PCE 环比",
  "US:Average Hourly Earnings MoM": "美国平均时薪环比",
  "US:Retail Sales MoM": "美国零售销售",
  "US:GDP Growth Rate QoQ": "美国 GDP 环比",
  "US:ISM Manufacturing PMI": "美国 ISM 制造业 PMI",
  "US:ISM Manufacturing New Orders": "美国 ISM 制造业新订单",
  "US:ISM Manufacturing Prices": "美国 ISM 制造业支付价格",
  "US:ISM Services PMI": "美国 ISM 服务业 PMI",
  "US:Fed Interest Rate Decision": "美联储利率决议",
  "US:Initial Jobless Claims": "美国初请失业金人数",
  "US:JOLTs Job Openings": "美国 JOLTS 职位空缺",
  "US:Consumer Confidence": "美国消费者信心",
  "US:Michigan Consumer Sentiment": "美国密歇根消费者信心",
  "CN:Inflation Rate YoY": "中国 CPI",
  "CN:PPI YoY": "中国 PPI",
  "CN:GDP Growth Rate YoY": "中国 GDP 同比",
  "CN:Industrial Production YoY": "中国规模以上工业增加值",
  "CN:Retail Sales YoY": "中国社会消费品零售总额",
  "CN:Unemployment Rate": "中国失业率",
  "CN:NBS Manufacturing PMI": "中国官方制造业 PMI",
  "CN:Non Manufacturing PMI": "中国官方非制造业 PMI",
  "CN:Caixin Manufacturing PMI": "中国财新制造业 PMI",
  "CN:Caixin Services PMI": "中国财新服务业 PMI",
  "CN:Balance of Trade": "中国贸易差额",
  "CN:Exports YoY": "中国出口同比",
  "CN:Imports YoY": "中国进口同比",
  "CN:New Yuan Loans": "中国新增人民币贷款",
  "CN:Loan Growth YoY": "中国贷款余额同比",
  "CN:Total Social Financing": "中国社会融资规模",
  "CN:M2 Money Supply YoY": "中国 M2 货币供应同比",
  "CN:PBoC Interest Rate Decision": "中国央行利率决议"
};
const BASE_MACRO_INDICATORS = [
  "US:Nonfarm Payrolls Private",
  "US:Inflation Rate YoY",
  "US:PPI YoY",
  "CN:Inflation Rate YoY",
  "CN:PPI YoY"
];
const NEW_DEFAULT_MACRO_INDICATORS = [
  "US:Core PCE Price Index MoM",
  "US:Average Hourly Earnings MoM",
  "US:Initial Jobless Claims",
  "US:ISM Manufacturing New Orders",
  "US:ISM Manufacturing Prices",
  "US:Fed Interest Rate Decision",
  "CN:Total Social Financing",
  "CN:M2 Money Supply YoY"
];
const DEFAULT_MACRO_INDICATORS = [
  ...BASE_MACRO_INDICATORS,
  ...NEW_DEFAULT_MACRO_INDICATORS
];
const MACRO_TRADING_VALUES = {
  "US:Nonfarm Payrolls Private": "衡量就业增量，显著偏离预期会迅速改变降息预期并影响指数风格。",
  "US:Inflation Rate YoY": "通胀主线指标，超预期通常推高利率并压制高估值成长股。",
  "US:PPI YoY": "观察上游成本与企业利润压力，也是消费通胀的潜在线索。",
  "US:Core PCE Price Index MoM": "美联储偏好的核心通胀指标，对利率路径和成长股估值影响很大。",
  "US:Average Hourly Earnings MoM": "工资增速反映服务通胀黏性，偏强可能推迟降息。",
  "US:Initial Jobless Claims": "高频就业拐点指标，持续上升通常意味着增长和盈利预期走弱。",
  "US:ISM Manufacturing New Orders": "制造业领先分项，可提前观察需求、库存和周期股盈利方向。",
  "US:ISM Manufacturing Prices": "制造业通胀领先分项，超预期上升通常推高利率并压制估值。",
  "US:Fed Interest Rate Decision": "直接决定政策利率，需结合声明、点阵图和新闻发布会判断。",
  "CN:Inflation Rate YoY": "反映内需与价格环境，对消费、利率敏感板块和政策预期重要。",
  "CN:PPI YoY": "反映工业品价格与中上游盈利周期，对周期股和工业企业利润敏感。",
  "CN:Total Social Financing": "衡量实体融资扩张，超预期通常改善A股、港股和周期品风险偏好。",
  "CN:M2 Money Supply YoY": "观察货币供给宽松程度，需结合社融和M1判断资金是否进入实体经济。",
  "US:Unemployment Rate": "就业松紧度核心指标，上升过快会强化衰退与宽松交易。",
  "US:Core Inflation Rate YoY": "剔除食品能源后观察通胀黏性，对利率敏感资产影响更直接。",
  "US:Core PPI YoY": "剔除波动项后观察生产成本压力，有助于判断利润率和核心通胀。",
  "US:Retail Sales MoM": "衡量消费动能，超预期利好增长但也可能推高利率预期。",
  "US:GDP Growth Rate QoQ": "确认经济增长状态，但发布较滞后，交易重点通常是与预期的偏差。",
  "US:ISM Manufacturing PMI": "判断制造业扩张或收缩，周期股通常对新趋势更敏感。",
  "US:ISM Services PMI": "覆盖美国经济主体，价格和就业分项对通胀、利率尤其重要。",
  "US:JOLTs Job Openings": "衡量劳动力需求，职位空缺下降通常意味着工资压力缓解。",
  "US:Consumer Confidence": "反映消费意愿，对可选消费与经济增长预期有参考价值。",
  "US:Michigan Consumer Sentiment": "观察居民信心及通胀预期，影响消费和美联储预期。",
  "CN:GDP Growth Rate YoY": "确认中国增长强弱，对指数整体盈利预期有方向性影响。",
  "CN:Industrial Production YoY": "反映工业景气，对原材料、制造业和周期板块较敏感。",
  "CN:Retail Sales YoY": "衡量消费修复，对消费、互联网和可选消费板块重要。",
  "CN:Unemployment Rate": "观察就业与居民收入压力，是消费持续性的辅助指标。",
  "CN:NBS Manufacturing PMI": "官方制造业景气指标，新订单变化对周期行情更具领先性。",
  "CN:Non Manufacturing PMI": "观察服务业和建筑业景气，对内需及基建链有参考价值。",
  "CN:Caixin Manufacturing PMI": "更偏中小型及出口企业，可补充官方制造业 PMI。",
  "CN:Caixin Services PMI": "观察民营服务业景气，对消费和就业预期有参考价值。",
  "CN:Balance of Trade": "反映外需和进口需求，对出口链、人民币及商品价格有影响。",
  "CN:Exports YoY": "衡量外需强弱，对出口制造、航运和人民币预期较敏感。",
  "CN:Imports YoY": "反映国内需求及大宗商品采购，对周期品交易有参考价值。",
  "CN:New Yuan Loans": "观察银行信贷投放，但需结合社融结构判断资金去向。",
  "CN:Loan Growth YoY": "衡量信贷存量扩张速度，可辅助判断信用周期方向。",
  "CN:PBoC Interest Rate Decision": "影响人民币利率和估值环境，重点观察是否超出市场预期。"
};
const MACRO_SELECTION_KEY = "finance-dashboard-macro-indicators";
const MACRO_DEFAULTS_VERSION_KEY = "finance-dashboard-macro-defaults-version";
const MACRO_DEFAULTS_VERSION = 2;
const macroCalendarState = {
  events: [],
  available: new Map(
    Object.keys(MACRO_INDICATOR_LABELS).map(key => {
      const [country, ...titleParts] = key.split(":");
      const title = titleParts.join(":");
      return [key, { key, country, title, name: MACRO_INDICATOR_LABELS[key] }];
    })
  ),
  selected: loadMacroSelection()
};

function loadMacroSelection() {
  try {
    const saved = JSON.parse(localStorage.getItem(MACRO_SELECTION_KEY));
    let selected = Array.isArray(saved) && saved.every(key => typeof key === "string")
      ? saved
      : [...DEFAULT_MACRO_INDICATORS];
    const version = Number(localStorage.getItem(MACRO_DEFAULTS_VERSION_KEY) || 0);
    if (version < MACRO_DEFAULTS_VERSION) {
      selected = [...new Set([...selected, ...NEW_DEFAULT_MACRO_INDICATORS])];
      localStorage.setItem(MACRO_SELECTION_KEY, JSON.stringify(selected));
      localStorage.setItem(MACRO_DEFAULTS_VERSION_KEY, String(MACRO_DEFAULTS_VERSION));
    }
    return selected;
  } catch (error) {
    console.warn("macro indicator selection", error);
  }
  return [...DEFAULT_MACRO_INDICATORS];
}

function saveMacroSelection() {
  try {
    localStorage.setItem(MACRO_SELECTION_KEY, JSON.stringify(macroCalendarState.selected));
  } catch (error) {
    console.warn("macro indicator selection save", error);
  }
  persistMarketsSelection({ macroIndicators: macroCalendarState.selected });
}

function macroIndicatorKey(country, title) {
  return `${String(country).toUpperCase()}:${String(title)}`;
}

function macroIndicatorName(country, title) {
  const key = macroIndicatorKey(country, title);
  return MACRO_INDICATOR_LABELS[key] || `${country === "US" ? "美国" : "中国"} · ${title}`;
}

function macroTradingValue(indicator) {
  return MACRO_TRADING_VALUES[indicator.key]
    || "重点观察实际值与预测值的偏差，以及是否改变增长、通胀或政策预期。";
}

function selectedMacroIndicators() {
  return macroCalendarState.selected.map(key => macroCalendarState.available.get(key) || (() => {
    const [country, ...titleParts] = key.split(":");
    const title = titleParts.join(":");
    return { key, country, title, name: macroIndicatorName(country, title) };
  })());
}

function latestMacroEvent(indicator) {
  const matches = macroCalendarState.events.filter(event =>
    String(event.country).toUpperCase() === indicator.country &&
    String(event.title).toLowerCase() === indicator.title.toLowerCase()
  ).sort((a, b) => new Date(b.date) - new Date(a.date));
  return matches.find(event => event.actual !== null && event.actual !== undefined) || matches[0];
}

function macroRowsHtml(statusText = "") {
  const rows = selectedMacroIndicators().map(indicator => {
    const event = latestMacroEvent(indicator);
    const tradingValue = macroTradingValue(indicator);
    const date = statusText || (event?.date ? formatDisplayDate(event.date) : "暂无公开数据");
    return `
      <div class="macro-row" data-indicator-key="${escapeHtml(indicator.key)}">
        <div><div class="macro-name" draggable="true" title="拖动排序或移到垃圾桶删除">${escapeHtml(indicator.name)}</div><div class="macro-date">${escapeHtml(date)}</div></div>
        <div class="macro-number"><small>实际值</small><strong>${statusText ? "—" : escapeHtml(event?.actual ?? "—")}</strong></div>
        <div class="macro-number"><small>预测值</small><strong>${statusText ? "—" : escapeHtml(event?.forecast ?? "—")}</strong></div>
        <div class="macro-trading-value"><small>交易价值</small><span title="${escapeHtml(tradingValue)}">${escapeHtml(tradingValue)}</span></div>
      </div>
    `;
  }).join("");
  return `${rows}<button type="button" class="macro-add-row" id="addMacroIndicator">＋ 添加指标</button>`;
}

function setupMacroRows() {
  const host = document.getElementById("macroList");
  let draggedRow = null;
  let droppedInTrash = false;
  host.querySelectorAll(".macro-row").forEach(row => {
    row.querySelector(".macro-name").addEventListener("dragstart", event => {
      draggedRow = row;
      droppedInTrash = false;
      row.classList.add("row-dragging");
      showDragTrash(() => {
        if (!draggedRow) return;
        droppedInTrash = true;
        macroCalendarState.selected = macroCalendarState.selected
          .filter(key => key !== draggedRow.dataset.indicatorKey);
        saveMacroSelection();
        draggedRow.remove();
      });
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", row.dataset.indicatorKey);
    });
    row.querySelector(".macro-name").addEventListener("dragend", () => {
      row.classList.remove("row-dragging");
      hideDragTrash();
      draggedRow = null;
      if (!droppedInTrash) {
        macroCalendarState.selected = [...host.querySelectorAll(".macro-row[data-indicator-key]")]
          .map(item => item.dataset.indicatorKey);
        saveMacroSelection();
      }
    });
  });
  host.ondragover = event => {
    if (!draggedRow) return;
    event.preventDefault();
    const nextRow = [...host.querySelectorAll(".macro-row:not(.row-dragging)")]
      .find(row => event.clientY < row.getBoundingClientRect().top + row.offsetHeight / 2);
    host.insertBefore(draggedRow, nextRow || document.getElementById("addMacroIndicator"));
  };
  document.getElementById("addMacroIndicator").addEventListener("click", openMacroIndicatorDialog);
}

function renderMacroRows(statusText = "") {
  document.getElementById("macroList").innerHTML = macroRowsHtml(statusText);
  setupMacroRows();
}

function renderMacroIndicatorOptions() {
  const query = document.getElementById("macroIndicatorSearch").value.trim().toLowerCase();
  const selected = new Set(macroCalendarState.selected);
  const groups = ["US", "CN"].map(country => {
    const options = [...macroCalendarState.available.values()]
      .filter(item => item.country === country)
      .filter(item => !query || `${item.name} ${item.title} ${country === "US" ? "美国" : "中国"}`.toLowerCase().includes(query))
      .sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
    if (!options.length) return "";
    return `
      <div class="macro-country">${country === "US" ? "美国" : "中国"}</div>
      ${options.map(item => `
        <label class="macro-option">
          <input type="checkbox" data-indicator-key="${escapeHtml(item.key)}" ${selected.has(item.key) ? "checked" : ""}>
          <span>${escapeHtml(item.name)}</span>
          <span class="macro-option-source">${escapeHtml(item.title)}</span>
        </label>
      `).join("")}
    `;
  }).join("");
  const host = document.getElementById("macroIndicatorOptions");
  host.innerHTML = groups || '<div class="macro-options-empty">没有匹配的指标</div>';
  host.querySelectorAll("input[data-indicator-key]").forEach(input => {
    input.addEventListener("change", () => {
      const key = input.dataset.indicatorKey;
      if (input.checked) {
        if (!macroCalendarState.selected.includes(key)) macroCalendarState.selected.push(key);
      } else {
        macroCalendarState.selected = macroCalendarState.selected.filter(item => item !== key);
      }
      saveMacroSelection();
      renderMacroRows();
    });
  });
}

function openMacroIndicatorDialog() {
  const dialog = document.getElementById("macroIndicatorDialog");
  document.getElementById("macroIndicatorSearch").value = "";
  renderMacroIndicatorOptions();
  dialog.showModal();
  requestAnimationFrame(() => document.getElementById("macroIndicatorSearch").focus());
}

async function loadMacroCalendar() {
  document.getElementById("macroLoading").style.display = "block";
  renderMacroRows("读取中...");
  try {
    const end = new Date();
    end.setDate(end.getDate() + 45);
    const start = new Date();
    start.setDate(start.getDate() - 120);
    const from = start.toISOString();
    const to = end.toISOString();
    const url = `https://economic-calendar.tradingview.com/events?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&countries=US,CN`;
    const response = await fetchWithFallback(url);
    const payload = await response.json();
    const events = payload.result;
    if (!Array.isArray(events)) throw new Error("宏观接口返回格式错误");
    macroCalendarState.events = events;
    events.filter(event => ["US", "CN"].includes(String(event.country).toUpperCase()) && event.title).forEach(event => {
      const country = String(event.country).toUpperCase();
      const title = String(event.title);
      const key = macroIndicatorKey(country, title);
      macroCalendarState.available.set(key, {
        key,
        country,
        title,
        name: macroIndicatorName(country, title)
      });
    });
    renderMacroRows();
  } catch (error) {
    console.error("macro calendar", error);
    renderMacroRows("数据源暂不可用");
  } finally {
    document.getElementById("macroLoading").style.display = "none";
  }
}

async function loadMacroHistory() {
  try {
    const keys = ["usCpi", "usPpi", "usRate", "cnCpi", "cnPpi", "cnRate"];
    if (keys.some(key => !state.macroAll[key]?.length)) throw new Error("宏观历史序列尚未载入");
    const cutoff = new Date();
    cutoff.setFullYear(cutoff.getFullYear() - 3);
    const rowsByKey = Object.fromEntries(keys.map(key => [
      key,
      state.macroAll[key].filter(row => row.time >= cutoff.getTime())
    ]));
    clearChart(charts.macro);
    keys.forEach(key => {
      const data = rowsByKey[key].map(row => ({
        time: chartTime(row.time),
        value: row.close
      }));
      const series = charts.macro.api.addSeries(LightweightCharts.LineSeries, {
        color: ASSETS[key].color,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        priceFormat: { type: "custom", minMove: .01, formatter: value => `${value.toFixed(1)}%` }
      });
      series.setData(data);
      charts.macro.series.push(series);
      charts.macro.legendItems.push({
        label: ASSETS[key].short,
        color: ASSETS[key].color,
        series,
        data,
        carryForward: true,
        formatter: point => `${point.value.toFixed(2)}%`
      });
    });
    renderChartLegend(charts.macro);
    charts.macro.api.timeScale().fitContent();
  } catch (error) {
    console.error("macro history", error);
    showChartEmpty(charts.macro, "宏观历史数据暂不可用");
  }
}
