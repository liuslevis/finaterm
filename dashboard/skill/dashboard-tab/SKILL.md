---
name: dashboard-tab
description: 在 dashboard（全球金融数据终端）中新增或修改工作区 tab，包括后端 /api 数据路由、index.html 页面/样式/JS、测试与截图验证。用户提到 dashboard、仪表盘、tab、工作区、新面板、IPO 日历、更新 tab 数据源时使用。
---

# Dashboard tab 新增 / 更新手册

单页应用：`dashboard/index.html`（只含 HTML 骨架与各 tab 的工作区标记）+ `css/`（样式）+ `js/`（脚本）
+ 本地 Python 服务 `dashboard/dashboard_server.py`（`http.server`，无框架）。图表库 TradingView
Lightweight Charts v5（`vendor/lightweight-charts.js`，全局 `LightweightCharts`）。

## 1. 后端：新增数据路由（dashboard_server.py）

1. 写 `fetch_xxx(...) -> dict`：放在 `class DashboardHandler` 之前。返回可 JSON 序列化的 dict，
   失败直接 raise（`ValueError` → 400，其余 → 502/504）。
2. 在 `do_GET` 中加 `if request.path == "/api/xxx": self.handle_xxx(request); return`
   （放在 `/api/usdata` 分支之后、静态文件分支之前）。
3. `handle_xxx` 模板（照抄 `handle_ipo`）：
   ```python
   body = cached_json(f"xxx:{param}", TTL_SECONDS, lambda: fetch_xxx(param))
   self.send_body(200, body, "application/json; charset=utf-8")
   ```
   `cached_json` 是全局内存缓存；前端「清除缓存」按钮调用 `DELETE /api/cache` 清空。
4. 参数必须白名单校验（如 `IPO_MARKETS` dict），不要把用户输入拼进 URL。
5. 浏览器直连外部 URL 只能走 `/api/proxy`，且 host 必须在 `ALLOWED_HOSTS`；需要解析/聚合的数据
   优先在后端写专用路由。
6. 慢源（逐月请求等）用 `ThreadPoolExecutor(max_workers≈6)` 并发 + 重试，见 `fetch_ipo_us`。
7. tab 专属的离线脚本、数据和说明统一放在 `dashboard/tab/<data-workspace>/`（`build_panel.py`、
   `panel.json`、`SKILL.md`、`raw/`），后端用 `ROOT / "tab" / "<name>" / ...` 读取，不要放在 dashboard 根目录。

## 2. 前端：新增 tab（index.html + css/ + js/）

### 文件布局

所有脚本都是普通 `<script src>`（非 ES module），共享全局作用域，按 `index.html` 中的顺序加载：

| 文件 | 内容 |
|---|---|
| `css/base.css` | 变量、布局、面板、按钮/分段、图表 legend、拖拽回收站、workspace tab |
| `css/<tab>.css` | 各 tab 专属样式（`markets`、`semiconductor`、`qqq`、`ipo`、`a-supply-demand` …） |
| `css/responsive.css` | 全部 `@media` 断点，必须最后加载（覆盖前面同优先级规则） |
| `js/core.js` | 共享工具：`fmt`、`escapeHtml`、`formatDisplayDate`、`createFinancialChart`、`clearChart`、`showChartEmpty`、`setChartLegend`、`chartTime`、`priceFormat`、`setStatus`、`showError`、拖拽回收站 |
| `js/markets/*.js` | 全球市场：`state.js`（ASSETS/state/缓存）、`charts.js`、`tickers.js`、`data.js`、`correlation.js`、`macro.js`、`rates-term.js`、`index.js`（`renderAll` + 事件） |
| `js/<tab>.js` | 各 tab 的 state、load/render 与本 tab 事件绑定 |
| `js/app.js` | `activateWorkspace`、`clearDataCache`、缩放、全局事件、可拖动面板、时钟 |
| `js/main.js` | 启动流程（必须最后加载；`test_market_time_axis.cjs` 会加载除它以外的全部脚本） |

加载顺序规则：顶层**立即执行**的代码（如 `const xxxState = { a: loadXxx() }`、`createFinancialChart(...)`）
只能依赖本文件或更早加载的文件；只在事件/调用时才用到的函数可以跨文件引用。新 tab 的
`<script src="js/xxx.js">` 放在 `js/app.js` 之前，`<link href="css/xxx.css">` 放在 `css/responsive.css` 之前。

### 新增 tab 步骤

| 位置 | 文件 / 锚点 | 改动 |
|---|---|---|
| tab 按钮 | `index.html`：`data-workspace-tab="a-etf-share"` | 其后追加 `<button type="button" class="workspace-tab" data-workspace-tab="xxx">名称</button>` |
| 工作区 | `index.html`：`<div class="attribution">` | 其前插入 `<section id="xxxWorkspace" class="workspace" data-workspace="xxx">…</section>` |
| CSS | 新建 `css/xxx.css`，在 `index.html` 中 `css/responsive.css` 前引入 | 本 tab 样式（用 `#id` / `.xxx-` 前缀避免冲突）；窄屏规则加到 `css/responsive.css` |
| JS 逻辑 | 新建 `js/xxx.js`，在 `index.html` 中 `js/app.js` 前引入 | state + `loadXxx()` + `renderXxx()`，文件末尾绑定本 tab 按钮事件 |
| 懒加载 | `js/app.js`：`activateWorkspace` 末尾 | `if (name === "xxx") requestAnimationFrame(loadXxx);`（隐藏容器里建图会 0 尺寸，必须激活后再建图） |
| 清缓存 | `js/app.js`：`clearDataCache` 中 `if (aesLoaded) reloads.push(` | 其后清空本 tab state，已加载过则重新 load |

### 可复用 UI 组件（极简风格优先复用）

- 面板：`<section class="panel">` + `.panel-head`（左：`.panel-title` + `.panel-note`；右：`.panel-actions`）+ `.source-note` 页脚。
- 分段切换按钮：`<div class="range"><button data-xxx="a" class="active">…</button></div>`。
  **不要用 `data-range` 属性**（全局已绑定到行情模块），自定义 `data-xxx-*`。
- 图表：`createFinancialChart(hostEl)` → `{ api, series, legend, empty, ... }`；
  `clearChart(chart)`、`showChartEmpty(chart, msg)`、
  `setChartLegend(chart, [{ label, color, series, data, formatter }])`。
  加序列：`chart.api.addSeries(LightweightCharts.HistogramSeries | LineSeries, opts)`，然后 `chart.series = [series]`。
  时间用 UTC 秒：`Date.UTC(y, m - 1, d) / 1000`，严格递增、不能重复。
- 表格样式参考 `.ipo-table` / `.capex-table`（数字列等宽字体、表头 sticky）。
- HTML 拼接文本必须 `escapeHtml(...)`。
- 配色变量：`--cyan`（主色）、`--amber`（预告/警示）、`--red`、`--green`、`--muted`。

## 3. 测试

- `dashboard/test_dashboard_integration.py`（联网集成测试）：在 `row.value === null ...` 断言后加页面字符串断言（`page` 已拼接 index.html 引用的全部 css/js）；
  在 `PASS usdata MCP series` 后加 `/api/xxx` 校验。
  运行：`cd dashboard; uv run python test_dashboard_integration.py`
  - 注意：截至 2026-10 该测试会先在 `"fred.stlouisfed.org" not in page` 处失败（QQQ 下跌因子 tab 的既有链接），
    与新 tab 无关；需要时用一次性脚本启动 `ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)` 单独验证新路由。
- 快速验证 fetcher：`cd dashboard; uv run python -c "import dashboard_server as s; print(s.fetch_xxx(...))"`。

## 4. 截图验证（必做，检查 JS 报错与布局）

```powershell
# 终端 A（async）：启动服务
cd dashboard; uv run python dashboard_server.py --port 8799 --no-browser
# 终端 B：截图（repo 根目录）
node dashboard/skill/dashboard-tab/scripts/screenshot_tab.cjs 8799 ipo $env:TEMP "ipoState.data[ipoState.market]" "[data-ipo-market=hk],[data-ipo-period=day]"
```
参数：端口、tab 名、输出目录、就绪 JS 表达式、若干组逗号分隔的点击选择器（每组后截一张图）。
脚本输出 `errors []` 才算通过；用 view 工具查看 PNG。完成后停止服务。
- 停止 async 的 `uv run` 不一定会结束子进程 python。若新启动的服务立刻退出码 0，说明端口上已有旧服务（`find_or_create_server` 复用它）。
  用 `Get-NetTCPConnection -LocalPort 8799 -State Listen` 查 PID，再 `Stop-Process -Id <PID>`。

## 5. 环境陷阱

- 仓库根有 `akshare/` 源码目录，会遮蔽 pip 版 akshare（变成空 namespace 包）。不要在 repo 根运行
  `import akshare`；在 `dashboard/` 下用 `uv run` 或在 `%TEMP%` 下运行。
- Windows 控制台中文乱码：`$env:PYTHONIOENCODING="utf-8"`。
- Futu 数据需本机 FutuOpenD 运行，并使用 `FutuOpenD/.venv` 子进程（见 `fetch_futu`）；不要让 tab 硬依赖它。
- 改完同步更新 `dashboard/README.md` 对应章节。

## 6. 现有 tab 速查

| tab | data-workspace | 数据 | 关键 JS |
|---|---|---|---|
| 全球市场 | markets | Yahoo proxy / Futu / AKShare / usdata / TradingView 日历 | `loadMarkets`, `loadCorrelationData`, `updateRatesTerm`（底部「术语解释 · 10Y-2Y 曲线交易」，静态文案 + 用 usdata 的 10Y/2Y/利差判定熊牛平陡） |
| 半导体周期 | semiconductor | Yahoo | `loadSemiDashboard` |
| QQQ 决策 | qqq-decision | 静态研究结论 `QQQ_DECISIONS` | `renderQqqDecisions` |
| QQQ 下跌因子 | qqq-risk | 静态 `QQQ_RISK_CONDITIONS` | `renderQqqRiskDashboard` |
| QQQ 定投框架 | qqq-dca | 纯静态 HTML（复用 qqq-risk 样式类） | 无 |
| IPO 日历 | ipo | `/api/ipo?market=a\|hk\|us`（6h 缓存） | `loadIpoCalendar`, `renderIpoCalendar`, `aggregateIpoRows`, `selectIpoBucket`（点柱子 `subscribeClick` → 表格滚动高亮并展开全部公司） |
| A股供需 | a-supply-demand | `/api/a-supply-demand` 只读离线文件 `tab/a-supply-demand/panel.json`（由 `build_panel.py` 生成，方法论见 `dashboard/tab/a-supply-demand/SKILL.md`） | `loadAsd`, `renderAsd`（`data-asd-mode` 切换原口径/扣分红） |
| 美股供需 | us-supply-demand | `/api/us-supply-demand` 只读离线文件 `tab/us-supply-demand/panel.json`（`build_panel.py` + AI 维护的 `manual.json`，见 `dashboard/tab/us-supply-demand/SKILL.md`） | `loadUssd`, `renderUssd`（`data-ussd-mode`） |
| 国家队ETF | a-etf-share | `/api/a-etf-share` 只读离线文件 `tab/a-etf-share/panel.json`（四只头部沪深300ETF 市值/沪深300流通市值，见 `dashboard/tab/a-etf-share/SKILL.md`） | `loadAes`, `renderAes`（`data-aes-metric` 切占比/市值，`data-aes-flow` 切日/周/月） |
### IPO 日历数据源（更新时参考）

| 市场 | 源 | 函数 | 要点 |
|---|---|---|---|
| A股 | akshare `stock_xgsglb_em(symbol="全部股票")` | `fetch_ipo_a` | 募资 = 发行总数(万股)×发行价格/1e4 亿元；日期=上市日期，空则申购日期并标 upcoming |
| 港股 | `https://hk.eastmoney.com/ipolist[_N].html` HTML（每页 50 条，倒序） | `fetch_ipo_hk` | 正则 `HK_IPO_ROW` 解析；募资 "30.59亿"/"万" → `parse_cn_amount`；仅已上市。`stock_ipo_hk_ths` 已失效（返回 A 股） |
| 美股 | `https://api.nasdaq.com/api/ipo/calendar?date=YYYY-MM`（需 UA） | `fetch_ipo_us` | 逐月并发；priced + upcoming 按 dealID 去重；含 SPAC |
| 港/美待上市（备选） | `FutuOpenD/skills/futuapi/scripts/quote/get_ipo_list.py HK --json` | — | 只有当前管道，无募资额、无历史 |

窗口长度改 `IPO_YEARS`，缓存改 `IPO_TTL`。

### 国家队ETF：刷新与历史重建

详细数据口径见 `dashboard/tab/a-etf-share/SKILL.md`。后端只读
`tab/a-etf-share/panel.json`，清缓存不会下载新数据，必须先离线重建。

**普通窗口刷新**（以下命令在 `dashboard/` 运行，不要在仓库根运行 akshare）：

```bash
uv run python tab/a-etf-share/build_panel.py --refresh --start 2025-10-27
```

`--end YYYY-MM-DD` 指定结束日，默认昨天；省略 `--refresh` 复用原始缓存。
上交所份额按交易日逐日请求，十年历史可能耗时一小时以上；不要用 `| tail`
遮住进度，也不要因为暂时没有输出反复重启下载。

**2016 起的长历史**：2026-10-27 实测嘉实 159919 份额最早返回
2016-10-28，故四只 ETF 的共同窗口从该日开始，不代表 2016 年初已有完整数据。
脚本会额外取起始日前 45 天作预热，而 `compute()` 要求输入首日四只份额齐全；
直接 `--start 2016-10-28` 仍可能报「窗口起始日缺少 ETF 份额数据」。
不能把缺失份额填零或向过去回填，也不要删除已经下载的缓存重来。

以下用临时计算输入裁掉共同窗口之前的指数日期，保留完整原始缓存，调用原有
`compute/monthly/to_json` 生成面板，无需修改计算口径：

```bash
uv run python - <<'PY'
import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

spec = importlib.util.spec_from_file_location("etf_panel", "tab/a-etf-share/build_panel.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
start = "2016-10-28"
end = pd.Timestamp((datetime.now() - timedelta(days=1)).date())
refresh = False  # 更新到最新交易日时改为 True；已有完整下载时保持 False
m.ensure_raw(pd.Timestamp(start), end, refresh)
raw = m.RAW
csi = m.load("csi300")
end = min(end, csi.date.max()).strftime("%Y-%m-%d")
with TemporaryDirectory(prefix="etf-rebuild-") as tmp:
    m.RAW = Path(tmp)
    for path in raw.iterdir():
        if path.is_file() and path.name != "csi300.csv":
            (m.RAW / path.name).symlink_to(path)
    csi.loc[csi.date.between(start, end)].to_csv(m.RAW / "csi300.csv", index=False)
    panel, anchor = m.compute()
    payload = m.to_json(panel, m.monthly(panel), anchor, start, end)
    assert payload["daily"][0]["d"] == start
    assert payload["daily"][-1]["d"] == end
    assert panel.aum.gt(0).all()
    assert panel[[f"shares_{code}" for code in m.CODES]].gt(0).all().all()
    encoded = json.dumps(payload, ensure_ascii=False, indent=1, allow_nan=False)
    panel.round(4).to_csv(m.HERE / "panel.csv", encoding="utf-8-sig")
    (m.HERE / "panel.json").write_text(encoded, encoding="utf-8")
    print(payload["display"], len(payload["daily"]), "个交易日")
    print("沿用前值的交易日：", int(panel.coverage.lt(4).sum()))
PY
```

若刷新后数据源不再提供指定起始日的四只份额，应停止并确认可用区间，不要自动缩短历史。
共同窗口首日没有前一天嘉实份额，首日净申赎按现有逻辑为零，不代表实际没有申赎。
区间内缺失份额按现有逻辑前向填充，检查 `panel.csv` 的 `coverage`（完整为 4）；
流通市值是当前快照按指数等比回溯，十年历史的绝对占比不能视为精确值，
不能套用短窗口文档中的「1%～2%」误差说明。

**验证与提交**：

- 运行 `uv run python -c "import dashboard_server as s; d=s.fetch_a_etf_share(); print(d['display'], len(d['daily']))"`，
  确认起止日期与行数；按上文截图步骤检查 `a-etf-share`，就绪表达式为 `aesState.data`。
- 重新进入 tab 或点「清除缓存」重新请求面板，不用重启服务。
- 提交 `panel.csv`、`panel.json`，以及需要归档的 `raw/csi300.csv`、
  `raw/prices.csv`、`raw/sse_shares.csv`、`raw/szse_shares.csv`、`raw/float_mcap.json`。
  原始缓存若被忽略，仅对这些明确的数据文件使用 `git add -f`，不要强制加入整个目录。
