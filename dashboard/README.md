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
`a-supply-demand/panel.json`; refresh it with
`uv run python a-supply-demand/build_panel.py --refresh` (≈5 min). Methodology and
refresh notes are in `a-supply-demand/SKILL.md`.

## 美股供需

The `美股供需` tab applies the same framework to US equities: IPO + follow-ons +
converts + insider selling − buybacks − dividends − insider buying versus US
equity ETF flows + margin debt change, scaled by Wilshire 5000 market cap, with
z-scores, the S&P 500 monthly return and IPO sentiment. Auto sources (Nasdaq,
openinsider, Yahoo, FINRA) are combined with AI-maintained `manual.json`.
Refresh with `uv run python tab/us-supply-demand/build_panel.py --refresh`; see
`tab/us-supply-demand/SKILL.md`.

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
