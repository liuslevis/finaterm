// QQQ 决策 / QQQ 下跌因子 tabs (QQQ 定投框架 is static HTML).

const QQQ_DECISIONS = [
  {
    date: "2026-09-11",
    title: "QQQ 是集中型成长组合，不是整个纳斯达克",
    summary: "QQQ 跟踪 Nasdaq-100，主要持有 Nasdaq 上市的大型非金融公司，显著集中于超大型科技、互联网平台、半导体和成长消费股。它不是美国全市场或全球分散组合。",
    action: "把行业集中度和前十大权重纳入仓位决策，不把 QQQ 当作天然低风险的唯一核心资产。",
    sources: [["Nasdaq-100 事实表", "https://indexes.nasdaq.com/docs/FS_NDX.pdf"], ["Invesco QQQ", "https://www.invesco.com/qqq-etf/en/home.html"]]
  },
  {
    date: "2026-09-11",
    title: "短期看折现率，长期看盈利兑现",
    summary: "短期涨跌主要受实际利率、Fed 路径、风险溢价、仓位和财报意外影响；三至十年以上的回报最终取决于收入、EPS、自由现金流和资本回报率。",
    action: "不要用一次宏观数据替代长期盈利判断；季度复核盈利与现金流是否跟上价格和估值。",
    sources: [["美国财政部利率数据", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"], ["Nasdaq 盈利研究", "https://www.nasdaq.com/articles/global-indexes/nasdaq-100-outperforms-the-sp-500"]]
  },
  {
    date: "2026-09-11",
    title: "最有利的是通胀下降且增长不失速",
    summary: "通胀温和下降、经济保持增长、实际利率稳定或回落、信用利差平稳且盈利预期上修，通常是 QQQ 较有利的宏观组合。",
    action: "观察核心 PCE/CPI 的 3—6 个月趋势、实际利率和 EPS 修正是否共同改善，而不是只看是否降息。",
    sources: [["BLS CPI", "https://www.bls.gov/news.release/cpi.nr0.htm"], ["BEA PCE", "https://www.bea.gov/data/personal-consumption-expenditures-price-index"]]
  },
  {
    date: "2026-09-11",
    title: "最危险的是利率、信用与盈利同时恶化",
    summary: "实际利率上升、信用利差扩大、美元走强、就业和订单转弱，同时盈利预期下修，是比任何单一指标更值得警惕的风险组合。",
    action: "至少等待两至三类指标共同恶化再重新检查配置；风险信号增加不等于立即清仓。",
    sources: [["Fed 金融条件研究", "https://www.federalreserve.gov/econres/notes/feds-notes/financial-conditions-and-risks-to-the-economic-outlook-20240920.html"], ["Fed 美元指数", "https://www.federalreserve.gov/releases/h10/summary/"], ["BLS 就业数据", "https://www.bls.gov/news.release/empsit.nr0.htm"]]
  },
  {
    date: "2026-09-11",
    title: "AI 资本开支不是单向利好",
    summary: "AI Capex 短期推动 GPU、存储、网络和云基础设施收入，长期却必须转化为可持续收入、自由现金流和资本回报；否则折旧、电力及运维成本会反噬估值。",
    action: "每季度同时比较 Capex、AI/云收入、自由现金流和 ROIC；Capex 上升而后三项走弱是风险信号。",
    sources: [["Microsoft 投资者关系", "https://www.microsoft.com/en-us/investor"], ["Alphabet 投资者关系", "https://abc.xyz/investor/"], ["Amazon 投资者关系", "https://ir.aboutamazon.com/"]]
  },
  {
    date: "2026-09-11",
    title: "半导体需要按库存与产能周期观察",
    summary: "QQQ 对半导体权重较高，而 GPU、HBM、传统存储、汽车及工业芯片可能处于不同周期，不能只看行业总销售额。",
    action: "联合观察销售、存储价格、库存天数、交货期、代工利用率、先进封装产能和云厂商订单。",
    sources: [["WSTS", "https://www.wsts.org/"]]
  },
  {
    date: "2026-09-11",
    title: "高估值是长期回报约束，不是短期卖出信号",
    summary: "估值越高，未来回报越依赖盈利兑现，也越容易受到实际利率上升和业绩不及预期的冲击；但高估值本身不能可靠预测未来几个月走势。",
    action: "用估值决定目标权重和再平衡纪律，不设置单一市盈率清仓线，也不因创新高而停止定投。",
    sources: [["SEC 资产配置指南", "https://www.sec.gov/about/reports-publications/investorpubsassetallocationhtm"]]
  },
  {
    date: "2026-09-11",
    title: "长期定投依赖期限、现金储备与分散",
    summary: "QQQ 适合用至少 10 年、最好 15 年以上的资金承担波动；五年内明确要使用的资金不宜主要配置 QQQ。投资前应处理高息债务并建立应急储备。",
    action: "发薪后自动投入固定金额或比例，把 QQQ 放在整体资产配置中，并以能否承受约 50% 回撤检验仓位。",
    sources: [["Investor.gov 长期投资", "https://www.investor.gov/build-wealth-over-time-through-saving-and-investing"], ["Investor.gov 应急储备", "https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/save-rainy-day"]]
  },
  {
    date: "2026-09-11",
    title: "已有现金通常尽早投入，分批用于管理行为风险",
    summary: "历史研究中，一次性投入约三分之二时间优于分批投入，因为股票长期预期收益高于现金；工资按月到账则自然适合定投。",
    action: "若一次投入会导致恐慌卖出，可预先限定 3—6 个月分批完成，避免根据行情无限延期。",
    sources: [["Vanguard 定投研究", "https://externalcrewnet.vanguard.com/content/dam/corp/research/pdf/cost_averaging_invest_now_or_temporarily_hold_your_cash.pdf"]]
  },
  {
    date: "2026-09-11",
    title: "因个人目标和配置变化调整，不因新闻停投",
    summary: "临近用钱、应急金不足、高息负债、收入结构变化、风险承受力下降或 QQQ 超出目标权重，都是合理的调整原因；单次 CPI、Fed 讲话或市场下跌通常不是。",
    action: "每年检查一次，优先用新增资金再平衡；提前写好 20%、30% 和 40% 以上回撤时的执行纪律，不借款抄底。",
    sources: [["SEC 资产配置指南", "https://www.sec.gov/about/reports-publications/investorpubsassetallocationhtm"]]
  }
];
const QQQ_RISK_BLOCKS = [
  { name: "趋势", score: 39.0, color: "#54a4ff", note: "QQQ尚未进入明确趋势破坏" },
  { name: "波动率", score: 48.4, color: "#a889ff", note: "VIX期限结构未倒挂" },
  { name: "信用与金融条件", score: 39.2, color: "#32d49a", note: "整体利差仍低，低评级信用分化" },
  { name: "利率与通胀", score: 86.7, color: "#ff6577", note: "当前最主要的风险来源" },
  { name: "估值与市场宽度", score: 75.0, color: "#f5bd59", note: "半导体落后、宽度转弱" }
];
const QQQ_RISK_CONDITIONS = [
  { key: "below200d", name: "QQQ跌破200日均线", note: "趋势确认", active: false },
  { key: "realYield", name: "实际利率60日上升>30bp", note: "折现率压力", active: true },
  { key: "credit", name: "信用利差60日扩大>20bp", note: "融资环境恶化", active: false },
  { key: "cpi", name: "CPI同比>3%", note: "限制货币宽松空间", active: true },
  { key: "financial", name: "NFCI高于一年均值", note: "金融条件收紧", active: false },
  { key: "breadth", name: "市场宽度转负", note: "上涨依赖少数权重股", active: true },
  { key: "backwardation", name: "VIX期限结构倒挂", note: "短期压力进入确认", active: false },
  { key: "oil", name: "WTI同比上涨>30%", note: "再通胀风险", active: true },
  { key: "semis", name: "半导体相对标普走弱", note: "科技高Beta前哨", active: true },
  { key: "twoYear", name: "2Y收益率60日下降>40bp", note: "可能定价衰退或危机降息", active: false }
];
const QQQ_CONDITION_OUTCOMES = {
  0: { drawdown: -4.23, probability: 10.19 },
  1: { drawdown: -5.27, probability: 12.41 },
  2: { drawdown: -6.67, probability: 19.53 },
  3: { drawdown: -8.56, probability: 30.36 },
  4: { drawdown: -7.74, probability: 28.71 },
  5: { drawdown: -8.55, probability: 33.46 },
  6: { drawdown: -12.01, probability: 48.46 },
  7: { drawdown: -13.75, probability: 53.37 },
  8: { drawdown: -13.04, probability: 45.10 },
  9: { drawdown: -13.79, probability: 64.41 }
};
const QQQ_RISK_SELECTION_KEY = "finance-dashboard-qqq-risk-conditions-v1";

function renderQqqDecisions() {
  document.getElementById("qqqDecisionGrid").innerHTML = QQQ_DECISIONS.map((item, index) => `
    <article class="panel decision-card">
      <div class="decision-card-head">
        <span class="decision-index">结论 ${String(index + 1).padStart(2, "0")}</span>
        <time class="decision-date" datetime="${escapeHtml(item.date)}">${escapeHtml(item.date)}</time>
      </div>
      <h3>${escapeHtml(item.title)}</h3>
      <p class="decision-summary">${escapeHtml(item.summary)}</p>
      <div class="decision-action"><strong>决策含义：</strong>${escapeHtml(item.action)}</div>
      <div class="decision-sources">
        ${item.sources.map(([label, url]) => `<a class="decision-source" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`).join("")}
      </div>
    </article>
  `).join("");
}

function loadQqqRiskConditions() {
  const defaults = QQQ_RISK_CONDITIONS.filter(item => item.active).map(item => item.key);
  try {
    const saved = JSON.parse(localStorage.getItem(QQQ_RISK_SELECTION_KEY));
    return Array.isArray(saved) && saved.every(key => QQQ_RISK_CONDITIONS.some(item => item.key === key))
      ? new Set(saved)
      : new Set(defaults);
  } catch (error) {
    console.warn("QQQ risk conditions", error);
    return new Set(defaults);
  }
}

const qqqRiskState = { active: loadQqqRiskConditions() };

function renderQqqRiskBlocks() {
  document.getElementById("qqqRiskBlocks").innerHTML = QQQ_RISK_BLOCKS.map(block => `
    <section class="panel qqq-block-card">
      <div class="qqq-block-name">${escapeHtml(block.name)}</div>
      <div class="qqq-block-score" style="color:${block.color}">${block.score.toFixed(1)}</div>
      <div class="qqq-block-meter"><span style="width:${block.score}%;background:${block.color}"></span></div>
      <div class="qqq-block-note">${escapeHtml(block.note)}</div>
    </section>
  `).join("");
}

function renderQqqRiskConditions() {
  const host = document.getElementById("qqqFactorToggles");
  host.innerHTML = QQQ_RISK_CONDITIONS.map(item => `
    <button type="button" class="factor-toggle ${qqqRiskState.active.has(item.key) ? "active" : ""}" data-qqq-condition="${item.key}" aria-pressed="${qqqRiskState.active.has(item.key)}">
      <strong>${escapeHtml(item.name)}</strong>
      <span>${escapeHtml(item.note)}</span>
    </button>
  `).join("");
  host.querySelectorAll("[data-qqq-condition]").forEach(button => {
    button.addEventListener("click", () => {
      const key = button.dataset.qqqCondition;
      if (qqqRiskState.active.has(key)) qqqRiskState.active.delete(key);
      else qqqRiskState.active.add(key);
      try {
        localStorage.setItem(QQQ_RISK_SELECTION_KEY, JSON.stringify([...qqqRiskState.active]));
      } catch (error) {
        console.warn("QQQ risk conditions save", error);
      }
      renderQqqRiskConditions();
      renderQqqRiskOutcome();
    });
  });
}

function renderQqqRiskOutcome() {
  const count = qqqRiskState.active.size;
  const outcome = QQQ_CONDITION_OUTCOMES[count];
  document.getElementById("qqqConditionCount").textContent = `${count} / ${QQQ_RISK_CONDITIONS.length}`;
  document.getElementById("qqqConditionDrawdown").textContent = outcome ? `−${Math.abs(outcome.drawdown).toFixed(2)}%` : "样本不足";
  document.getElementById("qqqConditionProbability").textContent = outcome ? `${outcome.probability.toFixed(2)}%` : "样本不足";
  document.getElementById("qqqConditionBar").style.width = `${Math.min(100, count / QQQ_RISK_CONDITIONS.length * 100)}%`;
}

function renderQqqRiskDashboard() {
  renderQqqRiskBlocks();
  renderQqqRiskConditions();
  renderQqqRiskOutcome();
}
