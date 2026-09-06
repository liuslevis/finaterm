import json
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from dashboard_server import DashboardHandler, SERVER_ID, ThreadingHTTPServer
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
        assert page.count('data-range="1y" class="active"') == 2
        assert page.count('data-range="20y"') == 2
        assert '<section id="tickerGrid" class="ticker-grid"></section>' in page
        assert ".asset-chip { display: block; }" in page
        assert "min-height: 34px;" in page
        assert 'id="tickerCategoryFilters"' in page
        assert "flex-wrap: wrap" in page
        assert 'class="macro-dialog ticker-dialog"' in page
        assert 'class="ticker-option-source">${tickerDataSource(asset)}</span>' in page
        assert 'if (asset.futu) return "Futu / Yahoo"' in page
        assert '["stocks", "Stocks"]' in page
        assert '["bonds", "Bonds"]' in page
        assert '["economy", "Economy"]' in page
        assert '["options", "Options"]' in page
        assert 'async function loadAssetSeries' in page
        assert 'data-module-id="market"' in page
        assert 'data-module-id="correlation"' in page
        assert "setupMovablePanels" in page
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
        assert 'class="ticker ${state.view' in page
        assert 'aria-label="${escapeHtml(asset.name)}" draggable="true"' in page
        assert "＋ 添加指标" in page
        assert "subscribeVisibleLogicalRangeChange" in page
        assert "state.resetMarketRange = true" in page
        assert "const marketRenderCache = {" in page
        assert "if (unchanged && !state.resetMarketRange) return;" in page
        assert 'priceScaleId: useDualPriceScales && index === 0 ? "left" : "right"' in page
        assert "selectedKeys.length > 2" in page
        assert "hasZeroBaseline" in page
        assert 'state.selected = new Set([...state.selected].slice(0, 2))' in page
        assert 'state.view === "compare" && state.selected.has(key)' in page
        assert "const correlationState = {" in page
        assert "correlationState.selected.add(input.value)" in page
        assert "changesByPeriod(key, correlationState.series[key], monthly)" in page
        assert 'setActiveRangeButton("market", nextRange)' in page
        assert 'moduleId === "correlation"' in page
        assert "function formatDisplayDate(value)" in page
        assert "timeFormatter: formatDisplayDate" in page
        assert "tickMarkFormatter: formatDisplayDate" in page
        assert "event?.date ? formatDisplayDate(event.date)" in page
        with urllib.request.urlopen(
            f"{base}/vendor/lightweight-charts.js", timeout=30
        ) as response:
            assert response.headers.get_content_type() == "text/javascript"
            chart_library = response.read()
            assert b"LightweightCharts" in chart_library
        print(f"PASS page and health on port {server.server_port}")

        for asset in ("qqq", "btc"):
            payload = json.loads(get(f"{base}/api/futu?asset={asset}&range=1mo"))
            rows = payload.get("rows") or []
            assert payload.get("provider") == "futu-opend"
            assert rows and all(row.get("close") is not None for row in rows)
            print(f"PASS Futu OpenD {asset}")

        for name in ("RMBUSD", "GOLD", "CSI300", "NASDAQ"):
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

        usdata = json.loads(get(f"{base}/api/usdata"))
        assert usdata.get("provider") == "usdata-mcp"
        expected = {
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
