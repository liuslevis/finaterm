# bb_qqq — 用 Bloomberg Surveillance 每日节目做 QQQ 方向的 LLM 因子

## Idea

Bloomberg Surveillance 每个交易日美东 06:00–10:00 直播。节目里会反复给出当天的
宏观叙事：联储官员措辞、油价与霍尔木兹、10Y 与期限溢价、盈利修正、AI 资本开支、
消费者数据、地缘冲击。这些东西在开盘前就已经被交易员消化过一轮。

问题：**每天早上这场 2.5 小时的对话，对 QQQ 接下来的 1/3/7 个交易日有没有方向信息？**
能不能把它做成一个可复用的量化因子（而不是"看新闻感觉"）？

做法：把每家节目的完整转写丢给 LLM，让它输出 QQQ 上涨概率（1/3/7 日）、
-2..+2 情绪分、以及"节目当时在描述的开盘前走势"。然后拿这些分数去和
QQQ 的实际远期收益做 IC / 胜率 / 多空价差，并和动量、隔夜缺口、朴素词袋情绪
这些 baseline 对比。

## 数据

| 环节 | 来源 | 工具 |
|---|---|---|
| 节目枚举 | `space.bilibili.com/670833898`（阿狸听英语） | `opencli bilibili user-videos`，翻页到 2026-08-28 |
| 视频 | 同名 B 站投稿，720p | `opencli bilibili download` |
| 转写 | Qwen3-ASR-1.7B，CUDA，300s 分段 | `deepfind-rag ingest --type bili` |
| 每日总结 | `text/<BVID>.md`（DeepSeek 走 deepfind-rag 的 formatter 模板） | `deepfind-rag` formatter |
| QQQ 日线 | 前复权日线，2001-01-02 起 | `akshare stock_us_daily` |

样本：**上传日期 2026-09-01 至 2026-10-31 的全部 Surveillance 节目**（标题含
`Surveillance` 的都算，含 `1st Hour` / `Hour1` / 中英双语版本）。
节目落盘在 `C:\Users\david\dev\deepfind-rag\video\bili\<BVID>\`。

上游目录约定（与 `BV1dyE86bENz` 一致）：

```
<BVID>/video/<BVID>.mp4
<BVID>/audio/<BVID>.wav
<BVID>/text/<BVID>.txt      # 带 [HH:MM:SS - HH:MM:SS] 的原样转写
<BVID>/text/<BVID>.md       # DeepSeek 生成的结构化总结
```

## 时间轴（这是整个设计里最重要的东西）

全部为纽约时间：

```
d 06:00-10:00   节目直播
d 10:30         转写存在 → 信号可用（t0）
d 16:00         建仓：QQQ 当日收盘          （entry）
d+h 16:00       标签：h 个交易日后的收盘     （label）
```

`r_h = close(d+h) / close(d) - 1`。

也就是说：**特征在 d 日 10:30 就已知，用 d 日收盘价建仓，预测 d+h 收盘。**
这里刻意用收盘对收盘，而不是"开盘对开盘"：d 日盘中 10:00–16:00 的走势是节目
播出后才发生的，用收盘建仓等于把这段让掉，宁可低估因子也不高估。

`h` 是**交易日**偏移（按价格表里的行号），不是自然日。

## 防特征穿越（look-ahead）的四道检查

1. **提示词里没有任何价格。** LLM 只拿到转写文本 + 节目日期，拿不到 QQQ 任何
   价格、收益、标签。`llm_score.py` 里没有任何价格变量进入 prompt。
2. **入场时点不早于信息时点。** 信号 10:30 可用、16:00 建仓，中间隔了 5.5 小时。
   如果改成"用 d 日收盘价买入、预测 d 日收盘"，那才是穿越。
3. **日期遮盖对照（blind run）。** 把 prompt 里所有"9 月 3 日""October"之类的
   绝对日期替换成 `[DATE]`/`[MONTH]`，让模型无法靠"我记得 2026 年 9 月发生过什么"
   来作弊。`llm_score.py --blind` 跑一遍，比较 blind IC 与正常 IC。
   如果模型在背答案，遮掉日期后 IC 应该明显掉下来。
4. **Placebo：明天的分数 vs 今天的收益。** 如果 `score(t+1)` 也能"预测" `r(t)`，
   说明分数只是慢变量（动量/趋势），不是当日信息。

另外两个诊断字段（**不作为特征**）：

- `ret_0` = d 日收盘 / d-1 日收盘 − 1：节目确实会描述当天盘前的走势，
  所以分数和它相关是正常的、也是预期的（说明模型读懂了文本）。
  只要它**没有**强到把 `r_h` 全部解释掉。
- `gap` = d 日开盘 / d-1 日收盘 − 1：盘前跳空，10:30 时已知，是公平 baseline。

## 因子定义

LLM 每题输出：

| 字段 | 范围 | 用途 |
|---|---|---|
| `p_up_1d` / `p_up_3d` / `p_up_7d` | 0.05–0.95 | 主因子 `score_h = 2·p_up_h − 1` |
| `sentiment` | −2..+2 | 第二个因子，序数 |
| `confidence` | 0–100 | 条件权重（可选） |
| `preopen_move` | sharply_up..sharply_down | 映射到 −2..+2，作 baseline |
| `drivers` / `rationale` | 文本 | 只用来人工核查，不进因子 |

`score_h` 与 `logit(p)` 两种变换都测（单调变换不改变 Pearson 的符号，但会改变
线性拟合的斜率和 NW t）。

同一天有两条节目时（例如 9/17 的 `Fed Decision` 和中英双语版），按算术平均合成
一条日频分数。

## Baseline（必须打败才有意义）

| baseline | 含义 |
|---|---|
| `momentum_5d` / `momentum_20d` | 截至 d-1 收盘的 5/20 日动量（10:30 时可得） |
| `overnight_gap` | d 日开盘 / d-1 收盘 − 1（10:30 时可得） |
| `preopen_tape` | LLM 读出的"节目在描述盘前涨还是跌"，−2..+2 |
| `lexicon_net` | 财经情绪词袋：(bull − bear)/(bull + bear + 1) |

如果 `lexicon_net` 和 LLM 因子 IC 差不多，说明 LLM 没带来额外信息。

## 指标

- **IC**：时序上 `corr(score_t, r_{t+h})`。这是单资产，不是横截面因子，
  所以 IC 就是"分数与远期收益的相关系数"。
- **Rank IC**：Spearman。
- **NW t**：重叠收益（h 天前向窗口）让残差强自相关，普通 OLS t 值会虚高，
  用 Newey-West（lag = h−1）修正。
- **Block bootstrap CI**：按长度 5 的循环块重采样，保留自相关结构。
- **Block permutation p**：打乱块顺序构造零分布，而不是独立同分布洗牌。
- **胜率**：`score>0` 判涨的命中率，Wilson CI，对比"永远看涨"的基准。
- **Top/Bottom 半区收益**：按分数中位数分组的前向收益差（多空价差，pp）。
- **IC 衰减**：1..10 日前向收益分别算 IC，看信号活多久。
- **Partial IC**：控制 `mom5` 和 `preopen_tape` 之后的偏相关。

## 怎么跑

```powershell
cd C:\Users\david\dev\finance\predictor\bb_qqq

# 1. 价格
python fetch_prices.py

# 2. 口径（哪些节目已经有转写了）
python build_universe.py

# 3. 日总结（stage 1，最贵的一步，按集缓存）
python make_brief.py

# 4. LLM 打分（stage 2；--repeats 2 = 每集独立调 2 次取均值，压采样噪声）
python llm_score.py --input brief --repeats 2
python llm_score.py --input brief --blind --repeats 2   # 日期遮盖对照
python llm_score.py --input full                        # 全转写对照
python llm_score.py --input full --blind

# 5. 词袋 baseline
python baseline.py

# 6. 拼面板（价格 + 分数 + 标签）
python build_panel.py --scores data/llm_scores_deepseek_brief_r2.csv --out data/panel_brief.csv

# 7. 评估
python evaluate.py --panel data/panel_brief.csv --out reports/metrics_brief.json
python report.py

# 8. 质量检查
python incremental_test.py                                     # 增量检验：控制动量后还剩什么
python selftest.py --panel data/panel_brief.csv --reps 200   # 推断自检：噪声分数下 p 值应均匀
python llm_noise_test.py --episodes 6                        # LLM 采样噪声 vs 跨集离散度
```

`run_pipeline.ps1` 把 1–7 串起来（带缓存，重跑只算新增的集）。

依赖：`pandas numpy scipy requests akshare`（miniconda 的 `python` 即可）。
LLM key 从 `deepfind-cli/.env` / `deepfind-rag/.env` 读（`DEEPSEEK_*`）。

产物：

```
data/qqq_daily.csv            价格
data/episodes.csv             节目口径（show_date, bvid, transcript）
data/briefs/<BVID>.{json,md}  stage 1 的日总结
data/llm_scores_*.csv         LLM 打分（按输入模式/遮盖/重复次数分文件）
data/llm_cache/               每次调用的原始 JSON（含 usage、prompt_sha）
data/lexicon.csv              词袋 baseline
data/panel_*.csv              面板（特征 + r1/r3/r7 + 诊断列）
data/llm_noise.csv            噪声测试明细
reports/metrics_*.json        全部指标
reports/ic_table_*.md         IC 汇总表
reports/RESULTS.md            自动生成的汇总
```

## 结果

见 [`CORR.md`](CORR.md)。一句话：**方向类信号不能用** —— 控制 20 日动量后 IC 从 −0.28 掉到 −0.05，
LLM 相对动量没有增量（`incremental_test.py`）；7 日通道跨集 sd 只有 0.043，先天噪声大。
方法本身（时间轴 / blind / placebo / 自检 / 残差化）是干净的，可复用到别的信号源。

