# -*- coding: utf-8 -*-
"""Quarterly layoff vs QQQ analysis + charts."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

BASE = Path(__file__).parent
OUT = BASE / "out"

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

quarters = ["2025Q4", "2026Q1", "2026Q2", "2026Q3", "2026Q4*"]
layoffs = [17.0, 38.6, 31.95, 5.8, 61.0]        # thousands, announced (Q4* includes MSFT offer)
qqq = [2.45, -5.93, 27.73, -3.76, -4.0]          # quarterly % return, Q4* estimate

# correlation excluding the incomplete Q4*
x = np.array(layoffs[:4])
y = np.array(qqq[:4])
r = float(np.corrcoef(x, y)[0, 1])

# cumulative QQQ path
cum = [100.0]
for q in qqq:
    cum.append(cum[-1] * (1 + q / 100))

events = [
    ("2026-01-28", "亚马逊 1.6 万", 4),
    ("2026-02-26", "Block 4,000", 4),
    ("2026-03-11", "Atlassian 1,600", 4),
    ("2026-04-16", "Snap 1,000", 4),
    ("2026-05-05", "PayPal 4,760", 4),
    ("2026-05-14", "思科 4,000", 4),
    ("2026-05-20", "Meta 8,000", 4),
    ("2026-06-03", "GitLab 350", 4),
    ("2026-07", "微软 4,800", 5),
    ("2026-10-26", "微软 6 万窗口", 6),
]

event_study = [
    ("Block", "2026-02-26", 4000, "-40%~50%", "+24%（盘后）", "裁员近半 + 费用节省 + 加密/AI 叙事"),
    ("思科", "2026-05-14", 4000, "<5%", "+13.4%（当日）", "财报超预期 + 上调指引 + 裁员 <5%"),
    ("Snap", "2026-04-16", 1000, "16%", "+8%（当日）", "AI 生成 65% 新代码 + 5 亿美元节省"),
    ("Atlassian", "2026-03-11", 1600, "10%", "+2%（当日）", "裁员 + 转向 AI/企业销售"),
    ("PayPal", "2026-05-05", 4760, "20%（2-3 年）", "-8%（当日）", "裁员 + 下调季度指引"),
]

summary = dict(quarters=quarters, layoffs=layoffs, qqq=qqq, corr=r, cum=cum,
               event_study=event_study)
(OUT / "quarterly.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")


def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b0b8c0")
    ax.spines["bottom"].set_color("#b0b8c0")
    ax.tick_params(colors="#4a5560", labelsize=9)
    ax.grid(axis="y", color="#e6ebf0", linewidth=0.8)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- fig 7
fig, ax1 = plt.subplots(figsize=(9.2, 4.6))
bars = ax1.bar(quarters[:4], layoffs[:4], color="#dfe6ee", edgecolor=NAVY, linewidth=0.8, width=0.58,
               label="大厂公告裁员（千人，左轴）")
ax1.set_ylabel("公告裁员（千人）", fontsize=10, color=NAVY)
ax1.set_ylim(0, 56)
style(ax1)
for b, v in zip(bars, layoffs[:4]):
    ax1.text(b.get_x() + b.get_width() / 2, v / 2, f"{v:.0f}", ha="center", fontsize=9,
             color=NAVY, fontweight="bold")
ax2 = ax1.twinx()
ax2.plot(quarters[:4], qqq[:4], color=RED, marker="o", markersize=6, linewidth=2.4, label="QQQ 当季回报（右轴）")
ax2.axhline(0, color=GRAY, linewidth=0.7, linestyle=":", alpha=0.5)
ax2.set_ylabel("QQQ 当季回报（%）", fontsize=10, color=RED)
ax2.set_ylim(-12, 34)
ax2.spines["top"].set_visible(False)
ax2.tick_params(colors="#4a5560", labelsize=9)
offsets = [(0, 12), (0, -26), (14, 2), (14, -6)]
for i, v in enumerate(qqq[:4]):
    ax2.annotate(f"{v:+.1f}%", (i, v), textcoords="offset points", xytext=offsets[i],
                 ha="center" if offsets[i][0] == 0 else "left", fontsize=9, color=RED, fontweight="bold")
ax1.annotate("伊朗战争 / 油价 +79%", xy=(1, 51), fontsize=8, color="#5a6672", ha="center")
ax1.annotate("AI 财报大超预期", xy=(2, 51), fontsize=8, color="#5a6672", ha="center")
ax1.annotate("资本开支焦虑", xy=(3, 51), fontsize=8, color="#5a6672", ha="center")

ax1.set_title("图7  裁员最猛的季度，不一定是 QQQ 最差的季度", fontsize=12.5, color="#1a202c", pad=12, loc="left")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False, fontsize=8.3)
fig.tight_layout()
fig.savefig(OUT / "fig7_layoffs_vs_qqq.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- fig 8
fig, ax = plt.subplots(figsize=(9.2, 4.6))
labels = ["2025-09", "2025-12", "2026-03", "2026-06", "2026-09", "2026-10"]
ax.plot(labels, cum, color=NAVY, marker="o", markersize=6, linewidth=2.6)
ax.fill_between(labels, 100, cum, color=NAVY, alpha=0.06)
for i, v in enumerate(cum):
    ax.annotate(f"{v:.0f}", (i, v), textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=9, color=NAVY, fontweight="bold")
ax.axhline(100, color=GRAY, linestyle=":", linewidth=1)
ax.set_ylabel("QQQ 累计净值（2025-09-30 = 100）", fontsize=9.5)
ax.set_ylim(88, 132)
style(ax)
ax.annotate("亚马逊 1.4 万", xy=(0.15, 104.2), fontsize=8, color=TEAL)
ax.annotate("亚马逊 1.6 万\nBlock 4,000", xy=(2.0, 92.5), fontsize=8, color=TEAL, ha="center")
ax.annotate("Meta 8,000\n思科 4,000", xy=(3.05, 126.5), fontsize=8, color=TEAL, ha="center")
ax.annotate("微软 4,800", xy=(4.15, 121.0), fontsize=8, color=TEAL)
ax.annotate("微软 6 万窗口 / eBay 9%", xy=(4.98, 110.4), fontsize=8, color=TEAL, ha="right")
ax.set_title("图8  一年 +18%，裁员没有阻止 QQQ 上涨，也没有阻止回撤", fontsize=12.5,
             color="#1a202c", pad=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / "fig8_qqq_cum.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

print("corr", round(r, 3), "cum", [round(c, 1) for c in cum])
print("charts written")
