// Usage (repo root, dashboard server already running):
//   node dashboard/skill/dashboard-tab/scripts/screenshot_tab.cjs <port> <tab> <outDir> [readyExpr] ["selector,selector" ...]
// Example:
//   node dashboard/skill/dashboard-tab/scripts/screenshot_tab.cjs 8799 ipo $env:TEMP "ipoState.data[ipoState.market]" "[data-ipo-market=hk],[data-ipo-period=day]"
// One screenshot after opening the tab, then one per click group. Exit code 1 on any JS page error.
const path = require("node:path");
const puppeteer = require(path.join(__dirname, "../../../../lightweight-charts/node_modules/puppeteer"));

const [port = "8765", tab, outDir = ".", readyExpr = "true", ...clickGroups] = process.argv.slice(2);
if (!tab) throw new Error("tab name (data-workspace-tab) required");

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe"
  });
  const errors = [];
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1500, height: 1000 });
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "domcontentloaded" });
    await page.click(`[data-workspace-tab="${tab}"]`);
    for (const [index, group] of [[], ...clickGroups.map(g => g.split(","))].entries()) {
      for (const selector of group) await page.click(selector);
      await page.waitForFunction(readyExpr, { timeout: 180000 });
      await new Promise(resolve => setTimeout(resolve, 800));
      const file = path.join(outDir, `${tab}-${index}.png`);
      await page.screenshot({ path: file });
      console.log("screenshot", file);
    }
  } finally {
    await browser.close();
  }
  console.log("errors", errors);
  process.exitCode = errors.length ? 1 : 0;
})();
