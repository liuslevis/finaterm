---
name: dashboard-tab
description: 在 dashboard（全球金融数据终端）中新增或修改工作区 tab，包括后端 /api 数据路由、index.html 页面/样式/JS、测试与截图验证。用户提到 dashboard、仪表盘、tab、工作区、新面板、IPO 日历、更新 tab 数据源时使用。
---

# Dashboard tab 新增 / 更新手册

单页应用：`dashboard/index.html`（HTML + CSS + JS 全在一个 ~200KB 文件，用 grep 定位，view_range 读）
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

## 2. 前端：新增 tab（index.html）

按顺序修改以下锚点（grep 搜索引号内文本）：

| 位置 | 锚点 | 改动 |
|---|---|---|
| tab 按钮 | `data-workspace-tab="qqq-risk"` | 其后追加 `<button type="button" class="workspace-tab" data-workspace-tab="xxx">名称</button>` |
| 工作区 | `<div class="attribution">` | 其前插入 `<section id="xxxWorkspace" class="workspace" data-workspace="xxx">…</section>` |
| CSS | `.workspace.active { display: block; }` | 其后追加本 tab 样式（用 `#id` / `.xxx-` 前缀避免冲突） |
| JS 逻辑 | `function activateWorkspace(name) {` | 其前插入 state + `loadXxx()` + `renderXxx()` |
| 懒加载 | `activateWorkspace` 末尾 | `if (name === "xxx") requestAnimationFrame(loadXxx);`（隐藏容器里建图会 0 尺寸，必须激活后再建图） |
| 事件 | `getElementById("refreshSemiBtn").addEventListener` | 其后绑定本 tab 按钮 |
| 清缓存 | `clearDataCache` 中 `if (semiState.loaded) reloads.push(` | 其后清空本 tab state，已加载过则重新 load |

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

- `dashboard/test_dashboard_integration.py`（联网集成测试）：在 `row.value === null ...` 断言后加页面字符串断言；
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
| 全球市场 | markets | Yahoo proxy / Futu / AKShare / usdata / TradingView 日历 | `loadMarkets`, `loadCorrelationData` |
| 半导体周期 | semiconductor | Yahoo | `loadSemiDashboard` |
| QQQ 决策 | qqq-decision | 静态研究结论 `QQQ_DECISIONS` | `renderQqqDecisions` |
| QQQ 下跌因子 | qqq-risk | 静态 `QQQ_RISK_CONDITIONS` | `renderQqqRiskDashboard` |
| IPO 日历 | ipo | `/api/ipo?market=a\|hk\|us`（6h 缓存） | `loadIpoCalendar`, `renderIpoCalendar`, `aggregateIpoRows`, `selectIpoBucket`（点柱子 `subscribeClick` → 表格滚动高亮并展开全部公司） |

### IPO 日历数据源（更新时参考）

| 市场 | 源 | 函数 | 要点 |
|---|---|---|---|
| A股 | akshare `stock_xgsglb_em(symbol="全部股票")` | `fetch_ipo_a` | 募资 = 发行总数(万股)×发行价格/1e4 亿元；日期=上市日期，空则申购日期并标 upcoming |
| 港股 | `https://hk.eastmoney.com/ipolist[_N].html` HTML（每页 50 条，倒序） | `fetch_ipo_hk` | 正则 `HK_IPO_ROW` 解析；募资 "30.59亿"/"万" → `parse_cn_amount`；仅已上市。`stock_ipo_hk_ths` 已失效（返回 A 股） |
| 美股 | `https://api.nasdaq.com/api/ipo/calendar?date=YYYY-MM`（需 UA） | `fetch_ipo_us` | 逐月并发；priced + upcoming 按 dealID 去重；含 SPAC |
| 港/美待上市（备选） | `FutuOpenD/skills/futuapi/scripts/quote/get_ipo_list.py HK --json` | — | 只有当前管道，无募资额、无历史 |

窗口长度改 `IPO_YEARS`，缓存改 `IPO_TTL`。
