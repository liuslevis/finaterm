const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const puppeteer = require("../lightweight-charts/node_modules/puppeteer");

test("calendar dates and viewport stay fixed across assets and history updates", async () => {
  const browser = await puppeteer.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1600, height: 1000 });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setRequestInterception(true);
    page.on("request", request => request.abort());
    const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
    const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    const script = scripts.find(match => match[1].includes("const ASSETS ="))[1];
    await page.setContent(html.replace(/<script(?:\s[^>]*)?>[\s\S]*?<\/script>/g, ""));
    await page.addScriptTag({ path: path.join(__dirname, "vendor", "lightweight-charts.js") });
    // Run the real UI and chart code, but not the network-dependent startup.
    await page.addScriptTag({ content: script.slice(0, script.lastIndexOf("\n    updateClock();")) });
    await page.evaluate(() => {
      preloadMarketHistory = async () => {};
      const day = 86400000;
      const today = klineBucketTime(Date.now(), "day");
      const row = (time, value, volume) => ({
        time, open: value, high: value + 2, low: value - 2, close: value + 1,
        ...(volume === undefined ? {} : { volume })
      });
      const dates = Array.from({ length: 90 }, (_, index) => today - (89 - index) * day);
      state.series = {
        qqq: dates.filter(time => ![0, 6].includes(new Date(time).getUTCDay()))
          .map((time, index) => row(time + 14.5 * 3600000, 500 + index, 1000 + index)),
        btc: dates.map((time, index) => row(time, 100000 + index)),
        usCpi: [dates[0], dates[30], dates[60]].map((time, index) => row(time, 2 + index))
      };
      state.macroAll = { usCpi: state.series.usCpi };
      state.tickers = ["qqq", "btc", "usCpi"];
      state.selected = new Set(state.tickers);
      state.active = "qqq";
      renderMarketCharts();
      renderTickers();
      window.initialWindows = [captureMarketRange(charts.market), captureMarketRange(charts.marketCompare)];
      window.axisSnapshot = () => {
        const chart = charts.market;
        const scale = chart.api.timeScale();
        return {
          range: captureMarketRange(chart),
          coordinates: dates.slice(25, 65).map(time => scale.timeToCoordinate(chartTime(time))),
          width: chart.api.priceScale("right").width(),
          calendarLength: (chart.calendar.to - chart.calendar.from) / CALENDAR_DAY + 1,
          data: chart.series[0].data()
        };
      };
      window.setTestWindow = () => {
        restoreMarketRange(charts.market, {
          from: chartTime(dates[20]) + .25 * CALENDAR_DAY,
          to: chartTime(dates[70]) + .75 * CALENDAR_DAY
        });
      };
      window.setTestWindow();
    });
    const settle = () => page.evaluate(() => new Promise(resolve =>
      requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await settle();
    const initialWindows = await page.evaluate(() => window.initialWindows);
    assert.deepEqual(initialWindows[0], initialWindows[1], "shared initial calendar window");
    const baseline = await page.evaluate(() => window.axisSnapshot());
    const assertStable = async label => {
      await settle();
      const actual = await page.evaluate(() => window.axisSnapshot());
      assert.ok(Math.abs(actual.range.from - baseline.range.from) < .001, `${label}: start`);
      assert.ok(Math.abs(actual.range.to - baseline.range.to) < .001, `${label}: end`);
      assert.equal(actual.width, baseline.width, `${label}: price axis width`);
      actual.coordinates.forEach((coordinate, index) => {
        assert.equal(typeof coordinate, "number", `${label}: missing calendar date`);
        assert.ok(Math.abs(coordinate - baseline.coordinates[index]) < .1,
          `${label}: date ${index} drifted by ${coordinate - baseline.coordinates[index]}px`);
      });
      return actual;
    };
    for (const key of ["btc", "usCpi", "qqq"]) {
      await page.click(`.ticker[data-key="${key}"]`);
      const snapshot = await assertStable(key);
      if (key === "usCpi") assert.equal(snapshot.data.length, 3, "no synthetic macro observations");
      if (key === "qqq") assert.ok(snapshot.data.length < 90, "no synthetic weekend candles");
    }
    for (const period of ["week", "month", "quarter", "half-year", "year", "day"]) {
      await page.click(`[data-kline-period="${period}"]`);
      await assertStable(period);
    }
    await page.evaluate(() => {
      state.macroAll.usCpi = [state.series.usCpi[0]];
    });
    await page.click('.ticker[data-key="usCpi"]');
    const sparse = await assertStable("no observations in visible window");
    assert.equal(sparse.data.length, 1);
    await page.click('.ticker[data-key="qqq"]');
    await assertStable("switch back from empty window");
    await page.evaluate(() => {
      state.macroAll.usCpi = state.series.usCpi;
    });
    await page.evaluate(() => {
      const oldest = Date.UTC(1990, 0, 3, 14, 30);
      state.marketAll.qqq = [
        { time: oldest, open: 10, high: 12, low: 9, close: 11, volume: 500 },
        ...state.series.qqq
      ];
      renderMarketCandleChart();
    });
    const extended = await assertStable("history preload");
    assert.ok(extended.calendarLength > baseline.calendarLength, "history extends calendar");
    await page.evaluate(() => {
      state.series.qqq = [...state.series.qqq];
      state.marketAll.qqq = [...state.marketAll.qqq];
      renderMarketCharts();
    });
    await assertStable("refresh");
    await page.evaluate(() => {
      const chart = charts.marketCompare;
      restoreMarketRange(chart, captureMarketRange(charts.market));
      window.compareBefore = captureMarketRange(chart);
      window.compareCoordinates = chart.api.timeScale().timeToCoordinate(
        chartTime(klineBucketTime(Date.now() - 40 * 86400000, "day")));
      state.selected = new Set(["usCpi"]);
      renderMarketCompareChart();
    });
    await settle();
    const comparison = await page.evaluate(() => ({
      before: window.compareBefore,
      after: captureMarketRange(charts.marketCompare),
      coordinateBefore: window.compareCoordinates,
      coordinateAfter: charts.marketCompare.api.timeScale().timeToCoordinate(
        chartTime(klineBucketTime(Date.now() - 40 * 86400000, "day"))),
      observations: charts.marketCompare.series[0].data().length
    }));
    assert.deepEqual(comparison.after, comparison.before, "comparison preserves viewport");
    assert.ok(Math.abs(comparison.coordinateAfter - comparison.coordinateBefore) < .1,
      "comparison date positions remain fixed");
    assert.equal(comparison.observations, 3);
    const aggregation = await page.evaluate(() => {
      const time = Date.UTC(2026, 8, 1);
      return aggregateKlineRows([
        { time: time + 3600000, open: 10, high: 12, low: 9, close: 11, volume: 100 },
        { time: time + 7200000, open: 11, high: 14, low: 8, close: 13, volume: 200 }
      ], "day");
    });
    assert.deepEqual(aggregation, [{
      time: Date.UTC(2026, 8, 1), open: 10, high: 14, low: 8, close: 13, volume: 300
    }]);
    assert.deepEqual(errors, [], "no browser errors");
  } finally {
    await browser.close();
  }
});
