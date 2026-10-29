# -*- coding: utf-8 -*-
"""Charts for the Big Tech layoff / QQQ report."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.font_manager as fm

BASE = Path(__file__).parent
OUT = BASE / "out"
OUT.mkdir(exist_ok=True)

# Chinese font
for name in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]:
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 200
plt.rcParams["savefig.dpi"] = 200

NAVY = "#1f3a5f"
RED = "#c0392b"
GOLD = "#b8860b"
GRAY = "#8a949e"
TEAL = "#2c7a7b"
LIGHT = "#dfe6ee"

data = json.loads((OUT / "model_results.json").read_text(encoding="utf-8"))
hist = data["hist"]


def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b0b8c0")
    ax.spines["bottom"].set_color("#b0b8c0")
    ax.tick_params(colors="#4a5560", labelsize=9)
    ax.grid(axis="y", color="#e6ebf0", linewidth=0.8)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- fig 1
fig, ax1 = plt.subplots(figsize=(9.2, 4.6))
yrs = hist["year"]
rev = hist["rev"]
hc = [h / 1000 for h in hist["hc"]]
bars = ax1.bar(yrs, rev, color=LIGHT, edgecolor=NAVY, linewidth=0.7, width=0.62, label="合计营收（十亿美元，左轴）")
ax1.set_ylabel("营收（十亿美元）", color=NAVY, fontsize=10)
ax1.set_ylim(0, 3200)
style(ax1)
ax2 = ax1.twinx()
ax2.plot(yrs, hc, color=RED, marker="o", markersize=4.5, linewidth=2.2, label="合计员工（百万人，右轴）")
ax2.set_ylabel("员工人数（百万）", color=RED, fontsize=10)
ax2.set_ylim(0.9, 2.6)
ax2.spines["top"].set_visible(False)
ax2.tick_params(colors="#4a5560", labelsize=9)
for i, (y, h) in enumerate(zip(yrs, hc)):
    if y in (2022, 2026):
        ax2.annotate(f"{h:.2f}", (y, h), textcoords="offset points", xytext=(0, 9),
                     ha="center", fontsize=9, color=RED, fontweight="bold")
ax1.annotate("营收 2019→2026：+201%", xy=(2021.4, 2650), fontsize=10.5, color=NAVY, fontweight="bold")
ax1.annotate("员工 2022→2026：-2%", xy=(2022.35, 2130), fontsize=10.5, color=RED, fontweight="bold")
ax1.set_title("图1  六家科技巨头：营收翻倍，人头原地踏步", fontsize=12.5, color="#1a202c", pad=12, loc="left")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False, fontsize=8.5)
fig.tight_layout()
fig.savefig(OUT / "fig1_hc_vs_rev.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- fig 2
fig, ax = plt.subplots(figsize=(9.2, 4.6))
ax.plot(yrs, hist["payroll"], color=TEAL, marker="o", markersize=4.5, linewidth=2.4, label="人力成本（薪酬+福利）")
ax.plot(yrs, hist["capex"], color=RED, marker="s", markersize=4.5, linewidth=2.4, label="资本开支")
ax.fill_between(yrs, hist["payroll"], hist["capex"], where=[c > p for c, p in zip(hist["capex"], hist["payroll"])],
                color=RED, alpha=0.08, interpolate=True)
ax.annotate("2026：capex 715 vs 人力 328\n每 1 美元工资对应 2.2 美元算力", xy=(2022.9, 585),
            fontsize=10, color=RED, fontweight="bold")
ax.set_ylabel("十亿美元", fontsize=10)
ax.set_ylim(0, 800)
style(ax)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title("图2  “资本迁移”：算力支出反超并吞噬人力预算", fontsize=12.5, color="#1a202c", pad=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / "fig2_payroll_vs_capex.png", bbox_inches="tight", facecolor="white")
plt.close(fig)


# ---------------------------------------------------------------- fig 3
def series(key):
    return data[key]["agg"]


fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
specs = [("eps", "每股收益（2026=100）", "EPS"), ("fcf", "自由现金流（2026=100）", "FCF")]
for ax, (key, title, _) in zip(axes, specs):
    for name, color, label in [("flat_base", GRAY, "不裁员"), ("cut10_base", NAVY, "每年裁 10%"),
                               ("cut20_base", RED, "每年裁 20%")]:
        a = series(name)
        base = a[key][0]
        ax.plot(a["year"], [v / base * 100 for v in a[key]], color=color, marker="o", markersize=3.5,
                linewidth=2.2, label=label)
    ax.set_title(title, fontsize=11, color="#1a202c", loc="left")
    ax.set_ylim(85, 280)
    style(ax)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
axes[0].text(2029.1, 96, "2031 年相对不裁员：10%/年 +8%，20%/年 +11%", fontsize=8.5, color="#4a5560")
fig.suptitle("图3  五年裁员之后：EPS 只抬高 8-11%，FCF 改善更有限", fontsize=12.5,
             color="#1a202c", x=0.02, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT / "fig3_eps_fcf.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- fig 4 waterfall
a_flat, a10 = series("flat_base"), series("cut10_base")
i = -1
gross = a_flat["comp"][i] - a10["comp"][i]
ai = a10["ai_cost"][i] - a_flat["ai_cost"][i]
net = a10["ebit"][i] - a_flat["ebit"][i]
rev_drag = gross - ai - net
fig, ax = plt.subplots(figsize=(9.2, 4.5))
labels = ["毛节省\n（人力预算）", "AI 推理/工具\n成本", "收入拖累\n（执行摩擦）", "净节省\n（EBIT）"]
vals = [gross, -ai, -rev_drag, net]
colors = [TEAL, RED, GOLD, NAVY]
bottom = [0, gross - ai, gross - ai - rev_drag, 0]
for i2, (v, b, c) in enumerate(zip(vals, bottom, colors)):
    ax.bar(i2, abs(v), bottom=b, color=c, width=0.55, alpha=0.9)
    ax.text(i2, b + abs(v) + 3, f"{v:+.0f}", ha="center", fontsize=10.5, fontweight="bold", color=c)
ax.set_xticks(range(4))
ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("十亿美元（2031 年，相对不裁员基准）", fontsize=9.5)
ax.set_ylim(0, 205)
style(ax)
ax.set_title("图4  裁员的钱去哪了：1,700 亿毛节省，约一半被收入摩擦与 AI 成本吃掉",
             fontsize=12, color="#1a202c", pad=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / "fig4_savings_leakage.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- fig 5 QQQ scenarios
NDX0, PE0 = 29651.441, 25.0  # index level, forward P/E base
EPS0 = NDX0 / PE0
q = json.loads((OUT / "qqq_scenarios.json").read_text(encoding="utf-8"))
label_map = {"牛市": "牛市：AI 收入兑现", "基准": "基准：增长放缓、估值回归",
             "熊市": "熊市：资本开支反噬", "深度衰退": "深度衰退：20% 裁员+需求破坏"}
colors = {"牛市": TEAL, "基准": NAVY, "熊市": GOLD, "深度衰退": RED}
fig, ax = plt.subplots(figsize=(9.2, 4.8))
yrs2 = list(range(2026, 2032))
for r in q["rows"]:
    g, pe = r["idx_cagr"], r["pe_end"]
    eps = [EPS0 * (1 + g) ** t for t in range(6)]
    pe_path = [PE0 + (pe - PE0) * min(t / 2, 1) for t in range(6)]
    lvl = [NDX0 if t == 0 else eps[t] * pe_path[t] for t in range(6)]
    c = colors[r["name"]]
    ax.plot(yrs2, lvl, marker="o", markersize=3.5, linewidth=2.3, color=c,
            label=f"{label_map[r['name']]}（{r['prob']*100:.0f}%）")
    ax.annotate(f"{lvl[-1]:,.0f}", (2031, lvl[-1]), textcoords="offset points", xytext=(6, 0),
                fontsize=9, color=c, fontweight="bold", va="center")
ax.axhline(NDX0, color=GRAY, linestyle=":", linewidth=1)
ax.set_xlim(2026, 2032.4)
ax.set_ylabel("纳斯达克100 点位", fontsize=10)
style(ax)
ax.legend(loc="upper left", frameon=False, fontsize=8.3)
ax.set_title("图5  QQQ 的五年路径：盈利是慢变量，估值是快变量", fontsize=12.5, color="#1a202c", pad=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / "fig5_qqq_scenarios.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- fig 6 labor intensity
names = ["英伟达", "博通", "苹果", "谷歌", "Meta", "微软", "亚马逊", "eBay", "埃森哲"]
ratio = [7, 25, 29, 34, 37, 42, 92, 68, 776]
colors = [NAVY if r < 100 else RED for r in ratio]
fig, ax = plt.subplots(figsize=(9.2, 4.4))
bars = ax.barh(names[::-1], ratio[::-1], color=[GRAY if r < 50 else (NAVY if r < 100 else RED) for r in ratio[::-1]],
               height=0.6)
for b, r in zip(bars, ratio[::-1]):
    ax.text(b.get_width() + 8, b.get_y() + b.get_height() / 2, f"{r}%", va="center", fontsize=9.5,
            color="#1a202c", fontweight="bold")
ax.set_xlabel("人力成本 / 经营利润（EBIT，%）", fontsize=9.5)
ax.set_xlim(0, 880)
style(ax)
ax.set_title("图6  “裁员弹性”取决于人力成本占利润的比重", fontsize=12.5, color="#1a202c", pad=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / "fig6_labor_intensity.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

print("charts written to", OUT)



