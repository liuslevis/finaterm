# 底部主力进场识别

从非 ST 躺平股中筛选当日触达涨停的股票，再用逐笔委托与成交数据计算 LV2 排名。

## 运行

```powershell
python .\predictor\ambush\strategy.py --date 20260901
python .\predictor\ambush\optimize_score.py --train-through 20260914 --end-date 20260916
```

- 训练：2026-09-01 至 2026-09-14。
- 预测：2026-09-16，不参与训练或调参；09-15 无有效样本。
- 样本：`launch_detected=True` 且 `data_quality_valid=True`。
- 目标：`0.4 × 3D 收益日内排名 + 0.6 × 1W 收益日内排名`。
- 因子按交易日转为百分位，避免跨日量级差异。

## 分数

| 字段 | 方法 |
|---|---|
| `lv2_score` | 预设方向与权重的 LV2 百分位分数 |
| `lv2_score_v2_baseline` | 固定 7 因子方向的基线分数 |
| `lv2_score_v3` | 训练期按 Spearman 相关性筛选因子方向 |
| `lv2_score_v4` | 23 因子 Ridge；正则强度仅在训练期按日期交叉验证选择 |

最终分数：

```text
score = 0.45 × dormancy_score + 0.20 × trigger_score + 0.35 × LV2 score
```

预测期同时输出四种 LV2 分数用于比较；未来收益只用于评估，不参与分数计算。

## 回测收益

预测期按分数分为上下半组：

| 分数 | 3D Spearman | 3D 上半组 | 3D 下半组 |
|---|---:|---:|---:|
| `lv2_score` | -0.700 | -1.59% | +10.28% |
| `lv2_score_v2_baseline` | +0.533 | +6.91% | -0.35% |
| `lv2_score_v3` | +0.067 | +6.26% | +0.46% |
| `lv2_score_v4` | +0.350 | **+7.37%** | **-0.92%** |

留出集有 9 个 3D 标签，收益均为非年化平均收益；1W 尚未到期。

## 输出

- `ambush_results_YYYYMMDD.csv`：单日候选与分数。
- `ambush_lv2_training_panel_20260901_20260916.csv`：训练与预测面板。
- `ambush_lv2_optimization_20260916.csv`：预测期分数评估。
- `lv2_score_model.json`：v4 模型参数与训练边界。

逐笔数据不能识别账户身份，结果仅用于研究，不构成投资建议。
