# 救市量化：周频 ETF 监测

本目录把“国家队救市”拆成可复核的周频代理变量。核心结论见 [CORR.md](CORR.md)，数据见
[`rescue_weekly.csv`](rescue_weekly.csv)，逐 ETF 原始份额截面见
[`rescue_weekly_shares.csv`](rescue_weekly_shares.csv)，官方消息明细见
[`rescue_events.csv`](rescue_events.csv)。事件匹配资产后的结果见
[`rescue_event_performance.csv`](rescue_event_performance.csv) 和
[`rescue_event_asset_performance.csv`](rescue_event_asset_performance.csv)，复现入口为
[`research.py`](research.py)。

## 研究问题

1. 核心宽基 ETF 的**净申购估算**和**成交额异常**，是否与当周沪深 300 探底、止跌有关？
2. 这些周末才完整的数据，是否对**下一周**收益有稳定相关性？
3. 代理信号能否覆盖中央汇金公开宣布增持 ETF 的周？

观察单元从月改为 **week（周）**。一周按周五结束；遇节假日，使用该周最后一个共同交易日。
样本从 2023 年开始，覆盖中央汇金三次公开 ETF 增持公告及其前后的市场状态。

## ETF 篮子

| 代码 | 代表指数 | 用途 |
|---|---|---|
| 510050 | 上证 50 | 大盘权重 |
| 510300 | 沪深 300 | 核心市场标签 |
| 510500 | 中证 500 | 中盘对照 |
| 512100 | 中证 1000 | 小盘对照 |
| 588000 | 科创 50 | 成长对照 |

全部为上交所 ETF，因此历史份额口径一致。未纳入深交所同类 ETF，避免把“上交所可按日期回溯”
与“深交所接口只给当前截面”混在同一序列。

## 事件研究原则：救什么，看什么

周频大盘标签仍使用 510300，但事件表现不再统一套用沪深 300：

| 公告对象 | 观察标的 | 映射质量 |
|---|---|---|
| 汇金明确增持四大行 | 601398、601288、601988、601939 等权篮子 | `exact` |
| 国新增持央企科技类指数基金 | 560170；或同指数 560170/562380/563050 | `exact_secondary` / `exact_family` |
| 汇金未披露明细的 ETF 增持 | 510050/510300/510500/512100/588000 | `proxy` |
| 诚通/国新泛称央企、科技股票及 ETF | 510060、560170、561790、588000 等对应主题代理 | `proxy` |
| 全市场流动性或融券措施 | 510300 | `proxy` |

`exact_secondary` 表示官方确认资产类别、具体代码来自公开成交报道；`proxy` 表示公告没有披露
证券明细，只能观察代表性指数产品。代理标的表现不能解释为官方实际持仓收益。

`rescue_event_performance.csv` 每个事件簇一行，对该事件关联标的做等权平均；
`rescue_event_asset_performance.csv` 保留逐证券结果。两者均包含事件周收益，并提供相对
510300 的 `forward_1w_*`、`forward_2w_*`、`forward_1m_*`、`forward_2m_*`、
`forward_3m_*`、`forward_6m_*` 前瞻标签。期限固定为 **1、2、4、8、13、26 个交易周**，
不是自然月末。

## 字段

| 列 | 含义 | 时间可得性 |
|---|---|---|
| `week_end` | 当周最后共同交易日 | 当周收盘后 |
| `hs300_return_pct` | 510300 周收益（%） | 同期标签 |
| `panic_drawdown_pct` | 510300 周内最低价 / 上周收盘 − 1（%） | 同期状态 |
| `close_rebound_pct` | 510300 周收盘 / 周内最低价 − 1（%） | 同期止跌代理 |
| `largecap_relative_pct` | 50/300 平均周收益 − 500/1000/科创 50 平均周收益（百分点） | 同期风格 |
| `basket_turnover_bn` | 五只 ETF 当周成交额合计（十亿元） | 同期交易 |
| `turnover_ratio_20w` | 当周成交额 / **此前** 20 周中位数 | 同期异常 |
| `share_flow_bn` | Σ(本周份额 − 上周份额) × 本周收盘价（十亿元） | 收盘后估算 |
| `share_flow_pct` | 上述估算 / 上周份额按本周收盘价估值（%） | 收盘后估算 |
| `official_announcement` | 该周是否有国家队已买入或明确承诺买入 | 核心消息标签 |
| `official_message_count` | 当周权威原始消息条数 | 明细量，不直接用于推断强度 |
| `core_purchase_cluster_count` | 当周核心买入事件簇数 | 同一轮多机构行动去重 |
| `broad_rescue_cluster_count` | 买入、流动性工具和监管维稳事件簇数 | 扩展消息标签 |
| `confirmed_purchase` / `committed_purchase` | 已实施买入 / 明确承诺买入 | 买入状态分层 |
| `liquidity_facility` | 互换便利或回购增持再贷款 | 提供资金能力，不等于已经买入 |
| `regulatory_stabilization` | 暂停限售股出借、转融券等逆周期监管 | 制度措施，不等于资金流入 |
| `rescue_proxy` | 净申购估算 ≥200 亿元、成交额 ≥前 20 周中位数 1.5 倍、周内跌幅 ≤−2% | 疑似托底标签 |
| `next_week_return_pct` | 从本周收盘到下一周收盘的 510300 累计收益（1W） | 预测检验目标 |
| `next_2w_return_pct` | 从本周收盘到第 2 个交易周收盘的累计收益（2W） | 预测检验目标 |
| `next_1m_return_pct` | 从本周收盘到第 4 个交易周收盘的累计收益（1M） | 预测检验目标 |
| `next_2m_return_pct` | 从本周收盘到第 8 个交易周收盘的累计收益（2M） | 中期检验目标 |
| `next_3m_return_pct` | 从本周收盘到第 13 个交易周收盘的累计收益（3M） | 中期检验目标 |
| `next_6m_return_pct` | 从本周收盘到第 26 个交易周收盘的累计收益（6M） | 中期检验目标 |

`rescue_proxy` 的三个固定阈值分别代表显著申购、异常放量和恐慌环境，不使用未来样本分位数。
200 亿元只针对本研究的五只 ETF 篮子，不是全市场阈值。`share_flow_bn` 是用收盘价把份额变化换算为金额的近似，不等于基金公司公布的精确净流入；
申赎发生价、分红和份额拆分都会造成误差。脚本保留 `share_flow_pct`，用于发现拆分等异常值。

## 信号分层

- **盘中预警**：成交额比率、周内跌幅、低点后反弹、大盘相对小盘。它们只能说明“盘面像托底”。
- **盘后确认**：交易所清算后份额变化。大额净申购比单纯放量更接近真金白银，但不能识别买方身份。
- **官方确认**：中央汇金、中国国新、中国诚通的已买入/明确增持公告。消息明细按机构保留，
  周频分析按 `cluster_id` 去重。
- **长期确认**：ETF 定期报告中的单一投资者/持有人披露。该数据为季度或半年度，不应伪装成周频列。

只有官方公告或定期报告能确认主体；任何仅由行情和份额推导的 `rescue_proxy` 都应称为“疑似托底”，
不能称为“国家队买入”。

## 复现

在仓库根目录运行：

```powershell
.\akshare\.venv\Scripts\python.exe .\predictor\rescue\research.py --refresh
```

脚本通过 AkShare 获取：

- 上交所 [ETF 规模/份额](https://www.sse.com.cn/market/funddata/volumn/etfvolumn/)（当日清算后数据）
- 东方财富 ETF 日行情（AkShare `fund_etf_hist_em`）；源不可用时自动回退新浪
  `fund_etf_hist_sina`

`--refresh` 会逐周请求上交所历史截面，耗时较长；份额截面会断点写入
`rescue_weekly_shares.csv`。不加参数时直接分析已提交的 CSV。
东方财富路径请求前复权行情；新浪回退路径为原始收盘价。当前事件窗口只有一至两周，
仍应检查除权除息日，尤其是个股事件，避免把现金分红误记为价格下跌。

## 官方消息数据

`rescue_events.csv` 目前有 16 条权威消息、10 个去重事件簇，其中 7 个核心买入事件簇。
类别定义：

- `confirmed_purchase`：原文明确“已增持”“今日增持”或披露已经使用的增持资金。
- `committed_purchase`：原文明确“将增持”，但没有把计划伪装成已成交。
- `liquidity_facility`：资本市场互换便利、股票回购增持再贷款。
- `regulatory_stabilization`：直接以逆周期调节或维护稳定为目的的交易制度措施。

同一天、同一轮稳定市场行动使用相同 `cluster_id`。例如 2025-04-07 至 04-08 的汇金、
中国诚通、中国国新消息有四条，但周频只计一个事件簇，防止人为放大样本。

### 代表性原始来源

- [2023-10-23：中央汇金买入 ETF，并将在未来继续增持](https://www.huijin-inv.cn/huijin-inv/c100074/2023-10/1002226.shtml)
- [2024-02-06：扩大 ETF 增持范围并持续加大力度](https://www.huijin-inv.cn/huijin-inv/c100077/2024-02/1002262.shtml)
- [2025-04-07：再次增持 ETF，并将在未来继续增持](https://www.huijin-inv.cn/huijin-inv/SC20252/2025-04/1002841.shtml)
- [2024-02-06：证监会支持中央汇金持续加大增持](https://www.csrc.gov.cn/csrc/c100028/c7462111/content.shtml)
- [2023-12-01：中国国新增持央企科技类指数基金](https://www.crhc.cn/qygg/2023/12/a97c8ecf60774265a5cd119045dfa2c8.htm)
- [2024-09-13：中国国新再次增持央企科技类指数基金](https://www.crhc.cn/qygg/2024/9/4eb5837c20ca422f8bb3c799c364c40d.htm)
- [2024-10-17：设立股票回购增持再贷款](https://www.gov.cn/zhengce/zhengceku/202410/content_6981220.htm)
- [2025-04-07：中国诚通增持 ETF 和央企股票](https://www.cctgroup.com.cn/cctgroup/2025-04/07/article_2025052219311019648.html)

## 使用边界

- 相关不等于买方身份确认，也不等于因果。
- 固定阈值并非根据收益最优化，但仍只是假设；应做滚动样本外验证后才可用于交易。
- 当周变量与当周收益存在同期信息；只有 `next_week_return_pct` 检验具有预测含义。
- 研究篮子只覆盖五只代表性上交所 ETF，不等于国家队全部 ETF 持仓。
- 末行没有下一周标签，分析时会自动剔除。
