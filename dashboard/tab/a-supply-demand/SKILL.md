---
name: a-supply-demand
description: 刷新或修改 dashboard「A股供需」tab（净股权供给 vs 增量资金、供需差 z-score、CSI300 月涨幅）。用户提到 A股供需、净股权供给、增量资金、供需差、刷新供需面板时使用。
---

# A股供需面板：设计与刷新手册

## 核心思路

单看 IPO 意义不大：A 股一年的 IPO 募资通常不到流通市值的 1%。所以要把全部股权供给加总，再和增量资金比较。

```
净股权供给 = IPO + 定增/增发 + 配股 + 可转债 + 重要股东减持 − 回购 − 现金分红 − 重要股东增持
增量资金   = 新发偏股基金 + 融资余额变化 + 沪市股票 ETF 净申购
供需差     = 增量资金 − 净股权供给
标准化     = 供需差 / 沪深总市值（bp），再做 3/6 个月滚动 z-score（z3/z6）
```

- **扣分红口径**（`gap_ex_div`）：分红有很强的季节性（6–7 月集中派发约 5000 亿/月），会让 6–7 月的原口径供需差虚高。判断资金趋势时，以扣分红口径为主。
- **解禁市值**：只作参考，不进公式。公式里用的是实际减持（估算）。
- **CSI300 月涨幅**：用来对照，验证供需差与市场表现是否同向或领先。
- **情绪指标**（偏同步或滞后）：新股首日平均涨幅、首日破发率、网下询价报价倍数中位数。2016 年改革后，打新冻结资金已经没有参考意义，不采用。

## 文件

| 文件 | 说明 |
|---|---|
| `build_panel.py` | 下载数据 → 计算 → 输出。`--refresh` 重新下载；`--start/--end YYYY-MM` 控制展示区间（默认当年 1 月到上一个完整月） |
| `raw/*.pkl` | 原始数据缓存（约 65 MB，不需要提交）。没有 `--refresh` 时直接复用，只重新计算 |
| `panel.csv` | 全部月份（从 `HISTORY_START=2025-01` 开始，供 z-score 回看）× 全部中间列，用于人工核对 |
| `panel.json` | 前端数据：`columns`（key/label/group/unit）、`rows`（展示区间）、`formula`、`caveats`、`source`、`generated_at` |

## 刷新步骤

```powershell
cd dashboard
$env:PYTHONIOENCODING="utf-8"
uv run python tab/a-supply-demand/build_panel.py --refresh   # 约 5 分钟，ETF 价格要逐只请求约 900 次
```

注意事项：
- 必须在 `dashboard/` 下运行。仓库根目录的 `akshare/` 源码目录会遮蔽 pip 安装的 akshare。
- 后端 `/api/a-supply-demand`（`dashboard_server.py` 里的 `fetch_a_supply_demand`）不缓存，每次请求直接读 `panel.json`。所以刷新后只需在页面里重新进入 tab 或点「清除缓存」，不用重启服务。
- 跨年后默认展示区间会自动变成新的一年。需要看去年全年时，加 `--start 2026-01 --end 2026-12`。
- 刷新后要做合理性检查：打印的表里 `net_supply/demand/gap` 不应出现整月为 0（说明接口失效）；异常尖峰要追查到个股或个券（例如 2025-06 银行定增约 5200 亿、2026-07 长鑫科技 IPO 约 579 亿、2026-07 科创芯片类 ETF 大额净申购）。

## 数据源与口径（akshare）

| 列 key | 接口 | 口径 / 归月 |
|---|---|---|
| ipo, ipo_count | `stock_xgsglb_em("全部股票")` | 发行总数(万股) × 1e4 × 发行价格，按**申购日期**归月（资金冻结时点） |
| seo | `stock_qbzf_em()` | 发行总数(股) × 发行价格，按发行日期归月（含银行注资类大额定增） |
| rights | `stock_pg_em()` | 配股数量 × 配股价，按缴款起始日期归月 |
| cb | `bond_zh_cov()` | 发行规模(亿)，按申购日期归月 |
| unlock | `stock_restricted_release_summary_em` | 实际解禁市值，按解禁日期归月（仅参考） |
| holder_sell / holder_buy | `stock_ggcg_em("全部")` | 变动数量(万股) × **最新价**（估算，没有成交价），按变动截止日期归月；先按 代码+股东+起止日+数量 去重 |
| buyback | `stock_repurchase_em()` | 已回购金额在「回购起始时间 → 最新公告日期」之间按月均摊（接口只给累计值，属估算） |
| dividend | `stock_fhps_em(date=YYYY0630/YYYY1231)` | 每 10 股现金分红 / 10 × 总股本，按除权除息日归月；按 代码+除权除息日 去重 |
| new_fund | `fund_new_found_em()` | 股票型、偏股/灵活/平衡混合、指数型-股票的募集份额（亿份 ≈ 亿元），按成立日期归月；**剔除场内 ETF**（ETF 已计入 etf 列，避免重复计算），保留联接基金 |
| margin | `macro_china_market_margin_sh/sz` | 沪深**融资**余额的月末差分（不含融券） |
| etf | `fund_etf_scale_sse(date=月末交易日)` + `fund_etf_hist_sina` | 沪市 ETF Δ份额 × 前后两个月末收盘价的均值；用名称正则 `NON_EQUITY_ETF` 剔除债券、货币、黄金、商品、跨境 ETF |
| mcap | `macro_china_stock_market_cap()` | 沪 + 深市价总值（亿），作为分母 |
| csi300_ret | `stock_zh_index_daily("sh000300")` | 月末收盘价环比（%） |
| first_day_mean, break_rate, quote_multiple | `stock_xgsglb_em` | 首日收盘价 / 发行价 − 1，按上市日期归月；报价倍数取中位数 |

## 已知缺口（后续可改进）

- **银证转账（证券保证金）、新开户数**：没有可用的公开接口。`stock_account_statistics_em` 从 2023-08 起停更。如果找到数据源，加到需求端。
- **深市 ETF**：`fund_etf_scale_szse` 解析报错（akshare 1.18.94），目前只统计沪市。沪市覆盖了大部分宽基和「国家队」ETF。
- **分母**：用总市值，不是自由流通市值。z-score 对比例缩放不敏感，但 bp 的绝对水平偏小。
- **z-score 回看**：只有 2025-01 起的历史，6 个月窗口的结果不太稳定。需要更长历史时调整 `HISTORY_START`，但 `stock_ggcg_em` / `stock_repurchase_em` 是全量快照，历史越早，估算误差越大。

## 前端（index.html）

- tab：`data-workspace-tab="a-supply-demand"`，工作区 `#asdWorkspace`，CSS 前缀 `.asd-`。
- JS：`asdState`、`loadAsd()`（只请求一次，「清除缓存」会重新加载）、`renderAsd()`。
- 图：直方图显示 `{mode}_bp`（右轴，绿正红负）；折线显示 CSI300 月涨幅（左轴，琥珀色）。
- 表：行是月份，列由 `panel.json.columns` 动态生成，第一行按 `group` 合并表头。新增指标时，只需在 `build_panel.py` 的 `COLUMNS` 里追加，前端不用改。
- `ASD_KEY_COLUMNS` 控制高亮列，`ASD_SIGNED_COLUMNS` 控制绿正红负着色。
- 截图验证：`node dashboard/skill/dashboard-tab/scripts/screenshot_tab.cjs 8799 a-supply-demand $env:TEMP "asdState.data" "[data-asd-mode=gap_ex_div]"`
