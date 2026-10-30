---
name: a-etf-share
description: 刷新或修改 dashboard「国家队ETF」tab（头部四只沪深300ETF 市值占沪深300流通市值、份额、估算净申赎）。用户提到国家队、中央汇金、ETF 占比、ETF 份额、万亿清仓、刷新 ETF 面板时使用。
---

# 「国家队」ETF 占比面板：设计与刷新手册

## 核心思路

中央汇金等「国家队」资金入市，主要路径是申购头部宽基 ETF（沪深300ETF 体量最大、流动性最好）。
ETF 份额只在申购/赎回时变化，所以「头部沪深300ETF 市值 ÷ 沪深300流通市值」是一个可以间接观察
国家队进出的高频代理指标：

```
四只ETF市值 = Σ(ETF 份额 × 收盘价)            # 510300 + 510330 + 159919 + 510310
占比       = 四只ETF市值 ÷ 沪深300流通市值 × 100%
估算净申赎 = Σ(ETF 份额变化 × 当日收盘价)      # 亿元，正=净申购，负=净赎回
```

- 占比抬升 → 头部 ETF 获净申购，通常对应国家队买入护盘；占比回落 → 净赎回或资金撤离。
- 样本只有 4 只 ETF（覆盖头部，但不是全口径）：**看趋势，不把绝对值当全市场国家队持仓**。
- 单独看市值会被行情带偏（指数涨也涨），所以主指标用「占流通市值比例」，并用份额曲线做交叉验证。

## 文件

| 文件 | 说明 |
|---|---|
| `build_panel.py` | 下载数据 → 计算 → 输出。`--refresh` 重新下载；`--start/--end YYYY-MM-DD` 控制展示区间（默认结束日往前一年） |
| `raw/*.csv` | 原始数据缓存（上交所份额逐日约 260 个交易日 = 260 次请求，深交所份额按月段翻页），不进 git |
| `panel.csv` | 逐日全量中间列（含窗口前的预热期），用于人工核对 |
| `panel.json` | 前端数据：`kpi`、`daily`、`monthly`、`columns`、`formula`、`caveats`、`source`、`anchor` |

## 刷新步骤

```powershell
cd dashboard
$env:PYTHONIOENCODING="utf-8"
uv run python tab/a-etf-share/build_panel.py --refresh                    # 约 2 分钟，上交所逐日请求最慢
uv run python tab/a-etf-share/build_panel.py --start 2025-10-27 --end 2026-10-23   # 只重算，不下载
```

注意事项：
- 必须在 `dashboard/` 下运行（仓库根目录的 `akshare/` 源码目录会遮蔽 pip 版的 akshare）。
- 后端 `/api/a-etf-share`（`dashboard_server.py` 的 `fetch_a_etf_share`）不缓存，每次直接读 `panel.json`，
  刷新后重新进入 tab 或点「清除缓存」即可，不用重启服务。
- 当天收盘前上交所还没有当日份额（接口返回空），所以默认 `--end` 是昨天；想看最新一天就把 `--end` 往后调并重跑。
- 缺失的交易日会被跳过；`panel.csv` 的 `coverage` 列记录当天有原始披露的 ETF 只数，正常应恒为 4。
- 刷新后做合理性检查：`aum` 不应整段为 0（说明接口失效）；单日 `flow` 超过 ±1000 亿要追到具体 ETF
  （2026-01-15 ~ 01-30 的连续大额赎回是真实事件，逐日 -300 ~ -975 亿）。

## 数据源与口径

| 列 | 来源 | 口径 |
|---|---|---|
| 份额（510300/510330/510310） | 上交所 `query.sse.com.cn` `COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L`，`STAT_DATE=YYYY-MM-DD` | `TOT_VOL` 单位**万份** ×1e4 = 份；一次只能查一天，脚本 4 线程并发抓 |
| 份额（159919） | 深交所 `fund.szse.cn/api/report/ShowReport/data`，`CATALOGID=fund_jjgm&txtDm=159919` | `current_size` 单位**万份** ×1e4 = 份；单次查询跨度上限约 183 天，脚本按 175 天切段并翻页 |
| ETF 收盘价 | 新浪 `fund_etf_hist_sina("sh510300"/"sz159919"/…)` | 元/份，与份额同日匹配 |
| 沪深300 收盘 | 新浪 `stock_zh_index_daily("sh000300")` | 也用作交易日历 |
| 沪深300 流通市值 | 东财 `push2.eastmoney.com/api/qt/stock/get?secid=1.000300` → `f117`（流通市值）、`f116`（总市值）、`f43`（点位） | 只有实时快照，所以按 `f117 × 收盘 ÷ 快照点位` 等比回溯出日序列 |

## 口径与已知缺口

- **绝对水平与视频/其他工具不一致**：按「沪深300流通市值」（≈48.9 万亿）算，2026-10 的占比约 0.65%；
  视频给的 0.45%~0.5% 若反推分母是 65~70 万亿，更像**全 A 流通市值**口径。整体量级差 1.5~2 倍，
  形状接近但不完全一致（对方可能用季度规模或不同分母）。本 tab 严格按「沪深300流通市值」口径，
  不为了对齐视频而改分母；要换算只能整体乘一个系数，趋势判断不受影响。
- **流通市值回溯的误差**：等比回溯忽略了指数成分股调整（6 月/12 月），量级 1%~2%；`--refresh` 会重新取快照，
  建议至少每月刷新一次。
- **份额≠申赎现金流**：份额变动还包含拆分、分红再投、转托管等非申赎原因；估算净申赎用当日收盘价近似成交净值，
  实际按 T 日净值或篮子折溢价成交。
- **只覆盖 4 只 ETF**：其他沪深300ETF（如 510360、159925 等）与 300增强、A500 等未纳入；占比低于全口径。
- **深交所接口稳定性**：`fund_jjgm` 是网页报表接口，跨度超限或参数变化会静默返回空表；脚本对空结果会继续按段抓，
  但没有数据时会报「窗口起始日缺少 ETF 份额数据」，据此排查即可。

## 前端（index.html 工作区 + `js/a-etf-share.js` + `css/a-etf-share.css`）

- tab：`data-workspace-tab="a-etf-share"`，工作区 `#aesWorkspace`，CSS 前缀 `.aes-`。
- JS：`aesState`、`loadAes()`（只请求一次，「清除缓存」会重新加载）、`renderAes()`（分发到
  `renderAesMain/renderAesFlow/renderAesShares/renderAesTable`）。
- 主图：`data-aes-metric` 切「占比（右轴 %）/ 市值（右轴 亿元）」，左轴固定叠沪深300收盘，并用虚线标注区间峰值。
- 净申赎图：`data-aes-flow` 切「日/周/月」聚合（默认周，日频 240 根柱子太密），柱子上色 绿正红负，
  左轴叠累计净申赎线。
- 份额图：四只 ETF 各一条线（亿份），颜色取自 `panel.json.etfs[].color`。
- 表：行是月份（倒序），列由 `panel.json.columns` 动态生成，首行按 `group` 合并表头；新增指标只要改
  `build_panel.py` 的 `COLUMNS`，前端不用动。
- 截图验证：
  `node dashboard/skill/dashboard-tab/scripts/screenshot_tab.cjs 8797 a-etf-share $env:TEMP "aesState.data" "[data-aes-metric=aum],[data-aes-flow=m]"`
