import json
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from dashboard_server import CACHE, CACHE_LOCK, DashboardHandler, SERVER_ID, ThreadingHTTPServer
from test_upstreams import MACRO_TARGETS, YAHOO_SYMBOLS


def get(url: str, timeout: int = 90) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        assert response.status == 200, f"HTTP {response.status}: {url}"
        return response.read()


def proxy_url(base: str, upstream: str) -> str:
    return f"{base}/api/proxy?{urllib.parse.urlencode({'url': upstream})}"


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    try:
        assert get(f"{base}/__finance_dashboard_health").decode() == SERVER_ID
        page = get(f"{base}/").decode("utf-8")
        assert "全球金融数据终端" in page
        assert "vendor/lightweight-charts.js" in page
        assert "echarts" not in page.lower()
        assert page.count('data-range="1y" class="active"') == 1
        assert page.count('data-range="20y"') == 1
        assert 'data-kline-period="day" class="active">日K' in page
        assert 'data-kline-period="week">周K' in page
        assert 'data-kline-period="month">月K' in page
        assert 'data-kline-period="quarter">季K' in page
        assert 'data-kline-period="half-year">半年K' in page
        assert 'data-kline-period="year">年K' in page
        assert "function aggregateKlineRows(" in page
        assert "const klineAggregationCache = new WeakMap();" in page
        assert "const minRange = KLINE_PERIODS[period].minRange;" not in page
        assert '<section id="tickerGrid" class="ticker-grid"></section>' in page
        assert ".asset-chip { display: block; }" in page
        assert "min-height: 34px;" in page
        assert 'id="tickerCategoryFilters"' in page
        assert "flex-wrap: wrap" in page
        assert 'class="macro-dialog ticker-dialog"' in page
        assert 'class="ticker-option-source">${tickerDataSource(asset)}</span>' in page
        assert 'if (asset.futu) return "Futu / Yahoo"' in page
        assert "function connectedDataSources(results)" in page
        assert '`实时数据已连接 [${connectedSources}]`' in page
        assert 'btc: { name: "比特币", short: "BTC", category: "crypto", symbol: "BTC-USD", digits: 0' in page
        assert '["stocks", "Stocks"]' in page
        assert '["bonds", "Bonds"]' in page
        assert 'usdataId: "fed_funds_rate"' in page
        assert 'usdataId: "treasury_2y"' in page
        assert 'usdataId: "treasury_10y"' in page
        assert 'usRate: { name: "美国有效联邦基金利率"' in page
        assert 'cnRate: { name: "中国 1 年期 LPR"' in page
        assert 'const keys = ["usCpi", "usPpi", "usRate", "cnCpi", "cnPpi", "cnRate"]' in page
        assert "async function fetchUsdataRate(asset" in page
        assert '["economy", "Economy"]' in page
        assert '["options", "Options"]' in page
        assert 'async function loadAssetSeries' in page
        assert 'akshareSymbol: "sh000300"' in page
        assert 'chartType: "candlestick"' in page
        assert "async function fetchAkshareMarket(asset, range)" in page
        assert "if (state.active !== key) state.resetMarketRange = true;" in page
        assert "function fitMarketRange(timeScale, keys)" in page
        assert "else fitMarketRange(timeScale, [activeKey]);" in page
        assert 'data-module-id="market"' in page
        assert 'data-module-id="correlation"' in page
        assert 'data-module-id="market-compare"' in page
        assert page.index('data-module-id="correlation"') < page.index('data-module-id="market-compare"')
        assert 'id="marketCompareChart"' in page
        assert 'id="compareAssetSelector"' in page
        assert "setupMovablePanels" in page
        assert 'data-workspace-tab="semiconductor"' in page
        assert 'id="semiconductorWorkspace"' in page
        assert 'data-workspace-tab="qqq-decision"' in page
        assert 'id="qqqDecisionWorkspace"' in page
        assert 'id="qqqDecisionGrid"' in page
        assert "QQQ_DECISIONS" in page
        assert "function renderQqqDecisions()" in page
        assert 'data-workspace-tab="qqq-risk"' in page
        assert 'id="qqqRiskWorkspace"' in page
        assert 'id="qqqRiskBlocks"' in page
        assert 'id="qqqFactorToggles"' in page
        assert "QQQ_RISK_CONDITIONS" in page
        assert "QQQ_CONDITION_OUTCOMES" in page
        assert "function renderQqqRiskDashboard()" in page
        assert "renderQqqRiskDashboard();" in page
        assert page.count('date: "2026-09-11"') >= 10
        assert "研究基线 · 2026-09-11" in page
        assert 'id="semiMarketChart"' in page
        assert "SEMI_SIGNALS" in page
        assert "function semiRiskScore()" in page
        assert "function loadSemiDashboard()" in page
        assert 'id="semiOpinionPanel"' in page
        assert 'id="opinionTimeline"' in page
        assert "SEMI_OPINION_DEFAULTS" in page
        assert "function saveCurrentOpinion()" in page
        assert "function animateLineSeries(" in page
        assert "animateLineSeries(series, normalizedRows, 500)" in page
        assert 'id="cloudCapexPanel"' in page
        assert 'id="cloudCapexChart"' in page
        assert "const CLOUD_CAPEX =" in page
        assert "function renderCloudCapex()" in page
        assert "165.050" in page
        assert '"soxx"' in page
        assert 'symbol: "^TNX"' in page
        assert "fred.stlouisfed.org" not in page.lower()
        assert 'id="macroIndicatorDialog"' in page
        assert 'id="macroIndicatorSearch"' in page
        assert "setupMacroRows" in page
        assert 'class="macro-name" draggable="true"' in page
        assert 'class="macro-trading-value"' in page
        assert ".macro-number, .macro-trading-value {" in page
        assert "grid-template-rows: 12px 12px;" in page
        assert "NEW_DEFAULT_MACRO_INDICATORS" in page
        assert '"US:Core PCE Price Index MoM"' in page
        assert '"CN:Total Social Financing"' in page
        assert "MACRO_DEFAULTS_VERSION_KEY" in page
        assert 'id="dragTrash"' in page
        assert 'class="ticker ${state.active === key ? "active" : ""}' in page
        assert 'aria-label="${escapeHtml(asset.name)}" draggable="true"' in page
        assert "＋ 添加指标" in page
        assert "subscribeVisibleLogicalRangeChange" in page
        assert "state.resetMarketRange = true" in page
        assert "candle: { key: \"\", series: new Map() }" in page
        assert "compare: { key: \"\", series: new Map() }" in page
        assert "if (unchanged && !state.resetMarketRange) return;" in page
        assert 'priceScaleId: useDualPriceScales && index === 0 ? "left" : "right"' in page
        assert "selectedKeys.length > 2" in page
        assert "hasZeroBaseline" in page
        assert "function renderMarketCandleChart()" in page
        assert "function ohlcChartRows(rows)" in page
        assert 'const useCandlesticks = asset.chartType === "candlestick" || asset.kind !== "macro";' in page
        assert "function volumeChartRows(rows)" in page
        assert "LightweightCharts.HistogramSeries" in page
        assert 'priceScaleId: "volume"' in page
        assert 'const visibleRange = state.resetMarketRange ? null : timeScale.getVisibleRange();' in page
        assert "if (visibleRange) timeScale.setVisibleRange(visibleRange);" in page
        assert "function renderMarketCompareChart()" in page
        assert "const normalizedData = rows.map(row => ({" in page
        assert "series.setData(normalizedData);" in page
        assert "data: normalizedData," in page
        assert "const correlationState = {" in page
        assert "correlationState.selected.add(input.value)" in page
        assert "changesByPeriod(key, correlationState.series[key], monthly)" in page
        assert 'setActiveRangeButton("market", nextRange)' in page
        assert 'moduleId === "correlation"' in page
        assert "function formatDisplayDate(value)" in page
        assert "timeFormatter: formatDisplayDate" in page
        assert "tickMarkFormatter: formatDisplayDate" in page
        assert "minBarSpacing: .05" in page
        assert "function findLatestDataPoint(data, time)" in page
        assert "renderChartLegend(chart, param.seriesData, param.time)" in page
        assert "(item.carryForward ? findLatestDataPoint(item.data, time) : null)" in page
        assert "function renderCarryForwardMarkers(chart, seriesData, time)" in page
        assert "chart.api.timeScale().timeToCoordinate(data.time)" in page
        assert "item.series.priceToCoordinate(data.value)" in page
        assert "上次 ${formatDisplayDate(data.time)} (${ageDays}天前)" in page
        assert "carryForward: true" in page
        assert "event?.date ? formatDisplayDate(event.date)" in page
        assert 'id="clearCacheBtn"' in page
        assert 'fetch("/api/cache", { method: "DELETE"' in page
        assert "const dataPointCache = new Map()" in page
        assert "function cachedDataPoints(" in page
        assert "const marketHistoryPromises = new Map();" in page
        assert "async function preloadAllMarketDataPoints(keys)" in page
        assert "function marketChartRows(key)" in page
        assert "const sourceRows = activeKey ? marketChartRows(activeKey) : null;" in page
        assert "await preloadMarketHistory(activeKey);" in page
        assert "void preloadMarketHistory(key);" in page
        assert "if (state.selected.has(key)) renderMarketCompareChart();" in page
        assert "const rowsByKey = new Map(selectedKeys.map(key => [key, marketChartRows(key)]));" in page
        assert "dataPointCache.clear()" in page
        assert "futuErrors: new Map()" in page
        assert 'setStatus("error", "Futu OpenD 连接失败 · 已回退 Yahoo")' in page
        assert "state.futuErrors.set(key, error.message)" in page
        assert "state.futuErrors.clear()" in page
        assert "/无权限|权限不足|行情权限/.test(message)" in page
        assert "Futu OpenD 已连接，但账号没有" in page
        assert 'row.value === null || row.value === undefined || row.value === ""' in page
        with CACHE_LOCK:
            CACHE["integration:test"] = (0.0, b"cached", "text/plain")
        request = urllib.request.Request(f"{base}/api/cache", method="DELETE")
        with urllib.request.urlopen(request, timeout=30) as response:
            cache_result = json.loads(response.read())
            assert response.status == 200
            assert cache_result["cleared"] >= 1
        with CACHE_LOCK:
            assert not CACHE
        with urllib.request.urlopen(
            f"{base}/vendor/lightweight-charts.js", timeout=30
        ) as response:
            assert response.headers.get_content_type() == "text/javascript"
            chart_library = response.read()
            assert b"LightweightCharts" in chart_library
        print(f"PASS page and health on port {server.server_port}")

        for asset in ("qqq",):
            payload = json.loads(get(f"{base}/api/futu?asset={asset}&range=1mo"))
            rows = payload.get("rows") or []
            assert payload.get("provider") == "futu-opend"
            assert rows and all(row.get("close") is not None for row in rows)
            print(f"PASS Futu OpenD {asset}")

        for name in ("RMBUSD", "GOLD", "NASDAQ"):
            symbol = YAHOO_SYMBOLS[name]
            encoded_symbol = urllib.parse.quote(symbol, safe="")
            upstream = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}"
                "?range=1mo&interval=1d&includePrePost=false&events=div%2Csplits"
            )
            payload = json.loads(get(proxy_url(base, upstream)))
            result = (payload.get("chart", {}).get("result") or [None])[0]
            closes = (
                (((result or {}).get("indicators") or {}).get("quote") or [{}])[0].get("close")
                or []
            )
            assert any(value is not None for value in closes), f"{name}: no proxy data"
            print(f"PASS proxy {name}")

        csi300 = json.loads(get(f"{base}/api/akshare?symbol=sh000300&range=1mo"))
        assert csi300.get("provider") == "akshare"
        assert len(csi300.get("rows") or []) > 1
        assert all(row.get("close") is not None for row in csi300["rows"])
        print("PASS AKShare CSI300")

        usdata = json.loads(get(f"{base}/api/usdata"))
        assert usdata.get("provider") == "usdata-mcp"
        expected = {
            "fed_funds_rate",
            "treasury_2y",
            "treasury_10y",
            "treasury_10y_2y_spread",
            "nonfarm_payrolls",
            "cpi",
            "ppi_final_demand",
        }
        assert expected <= set(usdata.get("series", {}))
        assert all(usdata["series"][key].get("observations") for key in expected)
        print("PASS usdata MCP series")

        now = datetime.now(timezone.utc)
        query = urllib.parse.urlencode(
            {
                "from": (now - timedelta(days=180)).isoformat(),
                "to": (now + timedelta(days=45)).isoformat(),
                "countries": "US,CN",
            }
        )
        calendar_url = f"https://economic-calendar.tradingview.com/events?{query}"
        events = json.loads(get(proxy_url(base, calendar_url))).get("result") or []
        for name, (country, title) in MACRO_TARGETS.items():
            matches = [
                event
                for event in events
                if event.get("country") == country
                and event.get("title") == title
                and event.get("actual") is not None
                and event.get("forecast") is not None
            ]
            assert matches, f"{name}: no actual/forecast data through proxy"
            print(f"PASS proxy {name}")

        print("\nAll integrated dashboard routes passed.")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
