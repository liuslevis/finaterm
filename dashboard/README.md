# Global Finance Dashboard

A local financial dashboard for monitoring global markets, macro trends, semiconductor cycles, and QQQ downside risk.

## Screenshots

| Semiconductor Cycle | Macro & Correlation |
|---|---|
| ![Semiconductor cycle dashboard](img/1.jpg) | ![Macro and correlation dashboard](img/2.jpg) |

| Global Markets | QQQ Downside Factors |
|---|---|
| ![Global markets dashboard](img/3.jpg) | ![QQQ downside factors dashboard](img/4.jpg) |

## Run

### Electron desktop app

Requires Node.js, Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/).

```powershell
cd dashboard
npm install
npm start
```

On Windows, you can also double-click `打开金融仪表盘 Electron.cmd`. The
Electron process starts the local Python API on an available random port and
stops it when the desktop app exits. The launcher keeps a runtime copy under
`%LOCALAPPDATA%\FinanceDashboard` so the Windows Electron sandbox can access
its binaries even when the repository has restricted development-folder ACLs.

### Browser

```powershell
uv run python dashboard/dashboard_server.py
```

The dashboard opens automatically at `http://localhost:8765`.

## 全球市场 selection

The 全球市场 asset cards and 宏观指标 list (add / remove / drag order) are saved by the server
to `tab/markets/selection.json` via `GET/PUT /api/markets-selection`. Commit this file to share
the same lists across machines; on load it overrides the browser's localStorage copy.

## IPO calendar

The `IPO 日历` tab shows the last 5 years of IPO proceeds for A-shares
(AKShare `stock_xgsglb_em`), Hong Kong (Eastmoney `hk.eastmoney.com/ipolist`)
and the US (Nasdaq IPO calendar API), aggregated by day or month in local
currency (亿). `/api/ipo?market=a|hk|us` caches each market for 6 hours.

## A股供需

The `A股供需` tab compares monthly net equity supply (IPO + placements + rights +
convertibles + insider selling − buybacks − dividends − insider buying) against
incremental funds (new equity funds + margin financing change + SSE equity ETF net
creations), with the gap scaled by market cap, a 6-month z-score and the CSI300
monthly return. `/api/a-supply-demand` only reads the offline file
`tab/a-supply-demand/panel.json`; refresh it with
`uv run python tab/a-supply-demand/build_panel.py --refresh` (≈5 min). Methodology and
refresh notes are in `tab/a-supply-demand/SKILL.md`.

## 美股供需

The `美股供需` tab applies the same framework to US equities: IPO + follow-ons +
converts + insider selling − buybacks − dividends − insider buying versus US
equity ETF flows + margin debt change, scaled by Wilshire 5000 market cap, with
z-scores, the S&P 500 monthly return and IPO sentiment. Auto sources (Nasdaq,
openinsider, Yahoo, FINRA) are combined with AI-maintained `manual.json`.
Refresh with `uv run python tab/us-supply-demand/build_panel.py --refresh`; see
`tab/us-supply-demand/SKILL.md`.

## 国家队ETF

The `国家队ETF` tab tracks the "national team" (Central Huijin and friends) by the
share-count route: the combined market value of the four largest CSI 300 ETFs
(510300 华泰柏瑞, 510330 华夏, 159919 嘉实, 510310 易方达) divided by the CSI 300
free-float market cap, plus each ETF's shares outstanding and an estimated net
creation/redemption series (Δ shares × close). A rising ratio means the head ETFs
are being bought, a falling one means net redemptions. The sample covers only four
ETFs, so the level sits below the all-fund total — read the trend, not the level.
`/api/a-etf-share` only reads the offline file `tab/a-etf-share/panel.json`;
refresh it with `uv run python tab/a-etf-share/build_panel.py --refresh` (≈2 min,
one SSE request per trading day). Methodology and caveats are in
`tab/a-etf-share/SKILL.md`.

## Market time axis

Market and multi-asset comparison charts use an equally spaced UTC calendar-day
axis, including weekends, holidays, and dates without macro releases. Missing
dates contain no synthetic prices. Daily observations are grouped by UTC date;
weekly and longer candles retain the same daily axis.

Switching assets or candle periods, refreshing data, and loading additional
history preserve the current zoom and pan window, including fractional-day
positions. The initial window is the last calendar year, independent of the
selected asset's data coverage.

The offline browser regression test uses Puppeteer from the `lightweight-charts`
development dependencies. With a system Chrome installation on Windows:

```powershell
$env:PUPPETEER_EXECUTABLE_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
node --test .\dashboard\test_market_time_axis.cjs
```
