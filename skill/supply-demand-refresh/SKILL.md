---
name: supply-demand-refresh
description: 刷新并校验 finance dashboard 的「美股供需」和「A股供需」月度表格。用户提到刷新供需表、更新美股/A股供需、净股权供给、增量资金或供需差时使用。
---

# 美股/A股供需刷新

工作目录是 `dashboard/`。目标月份通常为上一个完整月；先确认系统日期，不纳入未结束月份。

## 刷新顺序

1. 读 `tab/us-supply-demand/SKILL.md` 和 `tab/a-supply-demand/SKILL.md` 了解口径。
2. 刷新美股 `manual.json`，再运行美股脚本。
3. 运行 A 股脚本。
4. 校验输出、变更和页面；不要只看脚本退出码。

## 美股

文件：

- `tab/us-supply-demand/manual.json`：人工源、来源、估算说明、结论。
- `tab/us-supply-demand/build_panel.py`：自动源下载与计算。
- `tab/us-supply-demand/panel.csv|json`：输出。

月初 8–12 日先查 First Trust 当月版 Asset Flows Monitor，把上月 `U.S. equity ETFs` 流量写到
`monthly.etf_us_equity`，并把页面 URL 写到 `sources.etf_us_equity`。同时记录总 Equity ETF 流量到
`sources.etf_all_equity` 的来源；供需公式只使用美国股票 ETF。

ICI `Domestic equity` 共同基金实际月值通常月底发布。未发布时不要混入 ETF，也不要用
Active and Index Investing（该表包含 ETF）；脚本会用此前 3 个月实际值均值估算并在 caveats 标注。

FINRA 融资余额通常次月第三周发布。未发布时脚本用此前 3 个月月度变化均值估算；实际值发布后重跑会替换。
季度结束后再查 ICR 的 follow-on/convertible 和 S&P DJI 的 buyback/dividend；缺失季度沿用上一季度并标注估算。

更新 `manual.json.updated`、每个实际值的 `sources`，然后运行：

```bash
uv run python tab/us-supply-demand/build_panel.py
```

缓存必须实际覆盖目标月。脚本会检查 Nasdaq 与 openinsider 的目标月 key；若自动源抓取失败，不得把含空
`insider_sell`、`net_supply`、`gap` 的目标月提交为完成。

完成计算后，把 `manual.json.commentary` 更新为最近 3 个月的中文结论，再重跑一次。至少说明：

- gap / gap_ex_div、bp、z6 的方向；
- ETF、共同基金、融资余额的主要驱动；
- IPO 和内部人交易情绪；
- 哪些列是估算。

## A 股

运行：

```bash
uv run python tab/a-supply-demand/build_panel.py
```

脚本依赖东方财富、上交所、深交所和新浪。DNS/接口失败时保留旧 `panel.json`，不要用半成品覆盖；稍后重试。
在月中沪深总市值未发布前，目标月 bp/z6 可能为空，脚本每 12 小时重试。

## 校验

- 两个 `panel.json.display[1]` 都应是目标月份，`generated_at` 是本次时间。
- 目标月核心列 `net_supply`、`demand`、`gap` 不能为 null；供给/需求分项不能无故整月为 0。
- 美股输出的 `demand parts` 应包含 ETF、共同基金和 margin；检查 `estimated` 与 caveats 一致。
- A 股检查异常尖峰；确认分红季优先解读 `gap_ex_div`。
- 用 `git diff --check`，并审阅 `manual.json`、`panel.csv`、`panel.json` 的 diff。

可选页面验证：

```bash
uv run python dashboard_server.py --port 8799 --no-browser
node ../skill/dashboard/scripts/screenshot_tab.cjs 8799 us-supply-demand "$TMPDIR" "ussdState.data" "[data-ussd-mode=gap_ex_div]"
node ../skill/dashboard/scripts/screenshot_tab.cjs 8799 a-supply-demand "$TMPDIR" "asdState.data" "[data-asd-mode=gap_ex_div]"
```

最终报告每张表的最新月份、核心读数、估算项，以及任何数据源阻塞。
