import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


HEADERS = {
    "Accept": "application/json,text/csv,text/plain,*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinanceDashboard/2.0",
}

YAHOO_SYMBOLS = {
    "RMBUSD": "CNY=X",
    "BTC": "BTC-USD",
    "GOLD": "GC=F",
    "QQQ": "QQQ",
    "CSI300": "000300.SS",
    "NASDAQ": "^IXIC",
}

MACRO_TARGETS = {
    "US NFP": ("US", "Nonfarm Payrolls Private"),
    "US CPI": ("US", "Inflation Rate YoY"),
    "US PPI": ("US", "PPI YoY"),
    "CN CPI": ("CN", "Inflation Rate YoY"),
    "CN PPI": ("CN", "PPI YoY"),
}


def fetch(url: str, *, timeout: int = 45, headers: dict[str, str] | None = None) -> bytes:
    request_headers = dict(HEADERS)
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise AssertionError(f"HTTP {response.status}: {url}")
        return response.read()


def test_yahoo() -> list[str]:
    results = []
    for name, symbol in YAHOO_SYMBOLS.items():
        encoded_symbol = urllib.parse.quote(symbol, safe="")
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}"
            "?range=1mo&interval=1d&includePrePost=false&events=div%2Csplits"
        )
        payload = json.loads(fetch(url))
        chart = payload.get("chart", {})
        assert not chart.get("error"), f"{name}: {chart['error']}"
        result = (chart.get("result") or [None])[0]
        assert result, f"{name}: missing chart result"
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [None])[0]
        closes = [value for value in (quote or {}).get("close", []) if value is not None]
        assert timestamps and closes, f"{name}: empty timestamps or closes"
        results.append(f"{name}: {len(closes)} points")
    return results


def test_macro_calendar() -> list[str]:
    now = datetime.now(timezone.utc)
    query = urllib.parse.urlencode(
        {
            "from": (now - timedelta(days=180)).isoformat(),
            "to": (now + timedelta(days=45)).isoformat(),
            "countries": "US,CN",
        }
    )
    url = f"https://economic-calendar.tradingview.com/events?{query}"
    payload = json.loads(fetch(url, headers={"Origin": "https://www.tradingview.com"}))
    events = payload.get("result")
    assert isinstance(events, list) and events, "calendar: empty result"

    results = []
    for name, (country, title) in MACRO_TARGETS.items():
        matches = [
            event
            for event in events
            if event.get("country") == country and event.get("title") == title
        ]
        with_values = [
            event
            for event in matches
            if event.get("actual") is not None and event.get("forecast") is not None
        ]
        assert with_values, f"{name}: no event containing actual and forecast"
        latest = max(with_values, key=lambda event: event["date"])
        results.append(
            f"{name}: actual={latest['actual']} forecast={latest['forecast']} date={latest['date']}"
        )
    return results


def main() -> int:
    suites = [
        ("Yahoo markets", test_yahoo),
        ("TradingView macro", test_macro_calendar),
    ]
    failures = []
    for label, test in suites:
        try:
            details = test()
            print(f"PASS {label}")
            for detail in details:
                print(f"  {detail}")
        except Exception as error:
            failures.append((label, error))
            print(f"FAIL {label}: {error}", file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} interface group(s) failed.", file=sys.stderr)
        return 1
    print("\nAll upstream interfaces passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
