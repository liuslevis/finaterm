// 一次性诊断脚本（用完即删）
const path = require("node:path");
const puppeteer = require(path.join(__dirname, "../lightweight-charts/node_modules/puppeteer"));

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe"
  });
  const errors = [];
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1500, height: 1000 });
    page.on("console", message => {
      const text = message.text();
      if (/yahoo|macro|futu|IXIC|CNY|BTC|GC=F|tradingview/i.test(text)) errors.push(text.slice(0, 200));
    });
    await page.goto(`http://127.0.0.1:${process.argv[2] || "8799"}/`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction("window.state && !state.loading && Object.keys(state.series).length > 0", { timeout: 180000 });
    await new Promise(resolve => setTimeout(resolve, 6000));

    const info = await page.evaluate(() => ({
      banner: document.getElementById("errorBanner")?.textContent,
      status: document.getElementById("statusText")?.textContent || document.body.innerText.match(/部分数据不可用[^\n]*/)?.[0],
      tickers: [...state.tickers],
      selected: [...state.selected],
      futuErrors: [...(state.futuErrors || new Map()).entries()],
      emptySeries: Object.entries(state.series).filter(([, rows]) => !rows?.length).map(([key]) => key),
      nonEmpty: Object.entries(state.series).filter(([, rows]) => rows?.length).map(([key, rows]) => `${key}:${rows.length}`)
    }));

    // 复跑一次 loadSeries，抓每个资产的失败原因
    const failures = await page.evaluate(async () => {
      const keys = new Set([...state.tickers, ...state.selected]);
      const results = await loadSeries(state.range, {}, true, keys);
      return results.filter(item => !item.ok).map(item => `${ASSETS[item.key]?.name || item.key} :: ${item.error}`);
    });
    console.log("BANNER", info.banner);
    console.log("STATUS", info.status);
    console.log("TICKERS", JSON.stringify(info.tickers));
    console.log("SELECTED", JSON.stringify(info.selected));
    console.log("FUTU_ERRORS", JSON.stringify(info.futuErrors));
    console.log("EMPTY", JSON.stringify(info.emptySeries));
    console.log("NONEMPTY", JSON.stringify(info.nonEmpty));
    console.log("FAILURES", JSON.stringify(failures, null, 1));
  } finally {
    await browser.close();
  }
  console.log("CONSOLE", JSON.stringify([...new Set(errors)].slice(0, 12), null, 1));
})();
