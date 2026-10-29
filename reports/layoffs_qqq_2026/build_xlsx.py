# -*- coding: utf-8 -*-
"""Build the Excel model workbook."""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.worksheet.datavalidation import DataValidation

BASE = Path(__file__).parent
OUT = BASE / "out"
data = json.loads((OUT / "model_results.json").read_text(encoding="utf-8"))
qqq = json.loads((OUT / "qqq_scenarios.json").read_text(encoding="utf-8"))

NAVY = "1F3A5F"
RED = "C0392B"
LIGHT = "EEF2F7"
GOLD = "B8860B"
GRAY = "8A949E"
WHITE = "FFFFFF"

thin = Side(style="thin", color="C9D2DC")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

TITLE_FONT = Font(name="微软雅黑", size=15, bold=True, color=NAVY)
SUB_FONT = Font(name="微软雅黑", size=9, color="5A6672")
HDR_FONT = Font(name="微软雅黑", size=10, bold=True, color=WHITE)
BODY_FONT = Font(name="微软雅黑", size=9, color="1A202C")
INPUT_FONT = Font(name="微软雅黑", size=9, bold=True, color="1F4E9C")
NOTE_FONT = Font(name="微软雅黑", size=8, italic=True, color=GRAY)
BOLD_FONT = Font(name="微软雅黑", size=9, bold=True, color="1A202C")

HDR_FILL = PatternFill("solid", fgColor=NAVY)
LIGHT_FILL = PatternFill("solid", fgColor=LIGHT)
INPUT_FILL = PatternFill("solid", fgColor="FFF7E6")
ACCENT_FILL = PatternFill("solid", fgColor="F3F6FA")


def title(ws, text, sub=None, width=9):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    c = ws.cell(row=1, column=1, value=text)
    c.font = TITLE_FONT
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    if sub:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
        c2 = ws.cell(row=2, column=1, value=sub)
        c2.font = SUB_FONT
        c2.alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = 28


def header_row(ws, row, values, start_col=1):
    for j, v in enumerate(values):
        c = ws.cell(row=row, column=start_col + j, value=v)
        c.font = HDR_FONT
        c.fill = HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[row].height = 30


def body(ws, row, values, start_col=1, bold=False, fill=None, fmt=None, input_row=False):
    for j, v in enumerate(values):
        c = ws.cell(row=row, column=start_col + j, value=v)
        c.font = INPUT_FONT if (input_row and j > 0) else (BOLD_FONT if bold else BODY_FONT)
        c.border = BORDER
        c.alignment = Alignment(horizontal="center" if j > 0 else "left", vertical="center")
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        if fmt and j > 0:
            c.number_format = fmt


def note(ws, row, text, width=9):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    c = ws.cell(row=row, column=1, value=text)
    c.font = NOTE_FONT
    c.alignment = Alignment(vertical="center", wrap_text=True)


wb = Workbook()

# =====================================================================  说明
ws = wb.active
ws.title = "说明"
ws.sheet_view.showGridLines = False
title(ws, "大厂裁员与 QQQ 模型  |  Big Tech Layoff Model", width=9)
lines = [
    ("用途", "本工作簿配合《大厂裁员与QQQ_深度研究_2026Q4.docx》使用，用于复算与情景调整。"),
    ("基线", "八家公司（MSFT、GOOGL、AMZN、META、AAPL、NVDA、AVGO、TSLA）日历化 FY2026E 合并口径，美元十亿。"),
    ("工作表", "假设：可调参数；推演：单情景五年公式模型；情景对比：不裁员/10%/20% 三情景结果；敏感性：EPS 增速矩阵；QQQ：指数情景与概率加权。"),
    ("使用方法", "修改“假设”页蓝字单元格和“推演”页的增速/资本开支，表格会自动重算。情景对比与敏感性为模型输出值，不随假设联动。"),
    ("口径提醒", "人力成本为全成本估算（含股权激励）；亚马逊仅计入企业岗位；折旧按 8 年混合年限简化。"),
    ("重要提示", "所有情景均为假设推演，不构成投资建议。"),
]
r = 4
for k, v in lines:
    ws.cell(row=r, column=1, value=k).font = BOLD_FONT
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=9)
    c = ws.cell(row=r, column=2, value=v)
    c.font = BODY_FONT
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 48
    r += 1
ws.column_dimensions["A"].width = 12
for col in "BCDEFGHI":
    ws.column_dimensions[col].width = 14

# =====================================================================  假设
ws = wb.create_sheet("假设")
ws.sheet_view.showGridLines = False
title(ws, "核心假设", "蓝字单元格可修改；修改后“推演”页自动重算。", width=4)
header_row(ws, 4, ["参数", "取值", "单位", "说明"])
params = [
    ("每年裁员比例", 0.10, "%", "作用于企业/专业岗位，每年复利"),
    ("人均薪酬增速", 0.05, "%", "含股权激励，反映 AI 人才溢价"),
    ("AI 替代成本率", 0.20, "%", "被裁员工薪酬中用于推理/工具的比例"),
    ("留存员工 token 预算", 0.08, "%", "占人力成本"),
    ("其他费用收入弹性", 0.75, "指数", "其他费用 = 基期 × (收入/基期收入)^弹性"),
    ("折旧年限", 8, "年", "服务器 5-6 年、建筑 15-20 年的混合"),
    ("实际税率", 0.18, "%", "—"),
    ("股权激励", 0.025, "% 收入", "加回 FCF"),
    ("营运资金变动", 0.02, "% 收入增量", "—"),
    ("回购比例", 0.60, "% FCF", "上限为净利润的 90%"),
    ("回购估值倍数", 25, "x EPS", "用于把回购金额换算成股数"),
    ("基期收入", 2936.8, "十亿美元", "2026E 八家合计"),
    ("基期人力成本", 328.2, "十亿美元", "—"),
    ("基期其他费用", 1488.6, "十亿美元", "收入 - 人力 - 折旧 - EBIT"),
    ("基期折旧", 190.0, "十亿美元", "—"),
    ("基期资本开支", 715.0, "十亿美元", "—"),
    ("基期员工数", 1189, "千人", "企业/专业岗位"),
    ("基期净利润", 763.4, "十亿美元", "EBIT × (1-税率)"),
    ("基期股本", 78.2, "十亿股", "八家合计"),
    ("基期 EPS", 9.57, "美元", "净利润/股本"),
    ("收入拖累系数", 0.05, "百分点/10%裁员", "每裁 10%，收入增速下降 0.5 个百分点"),
]
for i, (name, val, unit, desc) in enumerate(params, start=5):
    ws.cell(row=i, column=1, value=name).font = BODY_FONT
    c = ws.cell(row=i, column=2, value=val)
    c.font = INPUT_FONT
    c.fill = INPUT_FILL
    c.border = BORDER
    c.alignment = Alignment(horizontal="center")
    if isinstance(val, float) and unit == "%":
        c.number_format = "0.0%"
    elif isinstance(val, float):
        c.number_format = "0.00"
    ws.cell(row=i, column=3, value=unit).font = BODY_FONT
    ws.cell(row=i, column=3).alignment = Alignment(horizontal="center")
    ws.cell(row=i, column=4, value=desc).font = BODY_FONT
    for j in range(1, 5):
        ws.cell(row=i, column=j).border = BORDER
ws.column_dimensions["A"].width = 22
ws.column_dimensions["B"].width = 12
ws.column_dimensions["C"].width = 12
ws.column_dimensions["D"].width = 60

# named references (direct cell refs)
P = "假设!"
CUT = f"{P}$B$5"
COMP_G = f"{P}$B$6"
AI_R = f"{P}$B$7"
TOKEN = f"{P}$B$8"
ELAS = f"{P}$B$9"
LIFE = f"{P}$B$10"
TAX = f"{P}$B$11"
SBC = f"{P}$B$12"
WC = f"{P}$B$13"
BB = f"{P}$B$14"
BBM = f"{P}$B$15"
REV0 = f"{P}$B$16"
COMP0 = f"{P}$B$17"
OTH0 = f"{P}$B$18"
DA0 = f"{P}$B$19"
CAP0 = f"{P}$B$20"
HC0 = f"{P}$B$21"
NI0 = f"{P}$B$22"
SH0 = f"{P}$B$23"
EPS0 = f"{P}$B$24"
DRAG = f"{P}$B$25"

# =====================================================================  推演
ws = wb.create_sheet("推演")
ws.sheet_view.showGridLines = False
title(ws, "单情景五年推演（公式联动）", "修改 C5:G5 的收入增速和 C14:G14 的资本开支，整张表自动重算。", width=7)
header_row(ws, 4, ["项目（十亿美元）", "2026A", "2027E", "2028E", "2029E", "2030E", "2031E"])
years = [2026, 2027, 2028, 2029, 2030, 2031]
cols = ["B", "C", "D", "E", "F", "G"]

rows = {}
r = 5
labels = [
    ("revenue_growth", "收入增速（假设）", "0.0%"),
    ("revenue", "收入", "#,##0.0"),
    ("hc", "员工数（千人）", "#,##0"),
    ("comp_ph", "人均薪酬（百万美元）", "0.00"),
    ("comp", "人力成本", "#,##0.0"),
    ("gap", "相对基准累计减员（千人）", "#,##0"),
    ("ai", "AI 推理/工具成本", "#,##0.0"),
    ("other", "其他费用", "#,##0.0"),
    ("da", "折旧", "#,##0.0"),
    ("capex", "资本开支（假设）", "#,##0.0"),
    ("ebit", "经营利润 EBIT", "#,##0.0"),
    ("ebit_m", "EBIT 利润率", "0.0%"),
    ("ni", "净利润", "#,##0.0"),
    ("shares", "股本（十亿股）", "0.00"),
    ("eps", "EPS（美元）", "0.00"),
    ("fcf", "自由现金流", "#,##0.0"),
    ("capex_rev", "资本开支/收入", "0.0%"),
    ("da_rev", "折旧/收入", "0.0%"),
]
for key, label, fmt in labels:
    rows[key] = r
    c = ws.cell(row=r, column=1, value=label)
    c.font = BOLD_FONT if key in ("ebit", "eps", "fcf") else BODY_FONT
    c.border = BORDER
    for j in range(2, 8):
        cell = ws.cell(row=r, column=j)
        cell.border = BORDER
        cell.font = BODY_FONT
        cell.number_format = fmt
        cell.alignment = Alignment(horizontal="center")
    r += 1

# 2026 base values
base = {
    "revenue": REV0, "hc": HC0, "comp": COMP0, "da": DA0, "capex": CAP0,
    "ni": NI0, "shares": SH0, "eps": EPS0,
}
for k, ref in base.items():
    ws[f"B{rows[k]}"] = f"={ref}"
ws[f"B{rows['comp_ph']}"] = f"={COMP0}/{HC0}"        # 百万美元/人
ws[f"B{rows['gap']}"] = 0
ws[f"B{rows['ai']}"] = 0
ws[f"B{rows['other']}"] = f"={OTH0}"
ws[f"B{rows['ebit']}"] = f"=B{rows['revenue']}-B{rows['comp']}-B{rows['ai']}-B{rows['other']}-B{rows['da']}"
ws[f"B{rows['ebit_m']}"] = f"=B{rows['ebit']}/B{rows['revenue']}"
ws[f"B{rows['fcf']}"] = f"=B{rows['ni']}+B{rows['da']}+B{rows['revenue']}*{SBC}-B{rows['capex']}"
ws[f"B{rows['capex_rev']}"] = f"=B{rows['capex']}/B{rows['revenue']}"
ws[f"B{rows['da_rev']}"] = f"=B{rows['da']}/B{rows['revenue']}"

# assumptions for 2027-2031
growth = [0.12, 0.10, 0.08, 0.07, 0.06]
capex_future = [900, 1020, 1100, 1120, 1100]
for j, col in enumerate(cols[1:]):
    ws[f"{col}{rows['revenue_growth']}"] = growth[j]
    ws[f"{col}{rows['revenue_growth']}"].fill = INPUT_FILL
    ws[f"{col}{rows['revenue_growth']}"].font = INPUT_FONT
    ws[f"{col}{rows['capex']}"] = capex_future[j]
    ws[f"{col}{rows['capex']}"].fill = INPUT_FILL
    ws[f"{col}{rows['capex']}"].font = INPUT_FONT

for j, col in enumerate(cols[1:], start=1):
    prev = cols[j - 1]
    yr = 2027 + j - 1
    ws[f"{col}{rows['revenue']}"] = f"={prev}{rows['revenue']}*(1+{col}{rows['revenue_growth']}-{DRAG}*{CUT})"
    ws[f"{col}{rows['hc']}"] = f"=MAX({prev}{rows['hc']}*(1-{CUT}),{HC0}*0.35)"
    ws[f"{col}{rows['comp_ph']}"] = f"={prev}{rows['comp_ph']}*(1+{COMP_G})"
    ws[f"{col}{rows['comp']}"] = f"=ROUND({col}{rows['hc']}*{col}{rows['comp_ph']},1)"
    ws[f"{col}{rows['gap']}"] = f"={HC0}-{col}{rows['hc']}"
    ws[f"{col}{rows['ai']}"] = f"=ROUND({col}{rows['gap']}*{COMP0}/{HC0}*{AI_R}+{col}{rows['comp']}*{TOKEN},1)"
    ws[f"{col}{rows['other']}"] = f"=ROUND({OTH0}*({col}{rows['revenue']}/{REV0})^{ELAS},1)"
    ws[f"{col}{rows['da']}"] = (f"=ROUND(AVERAGEIFS($B$28:$B$40,$A$28:$A$40,\">=\"&{yr - 8},"
                                f"$A$28:$A$40,\"<\"&{yr}),1)")
    ws[f"{col}{rows['ebit']}"] = f"={col}{rows['revenue']}-{col}{rows['comp']}-{col}{rows['ai']}-{col}{rows['other']}-{col}{rows['da']}"
    ws[f"{col}{rows['ebit_m']}"] = f"={col}{rows['ebit']}/{col}{rows['revenue']}"
    ws[f"{col}{rows['ni']}"] = f"={col}{rows['ebit']}*(1-{TAX})"
    ws[f"{col}{rows['shares']}"] = (f"={prev}{rows['shares']}-MIN({col}{rows['fcf'] if j > 1 else 'B'+str(rows['fcf'])}*{BB},{col}{rows['ni']}*0.9)/({BBM}*{prev}{rows['eps']})")
    ws[f"{col}{rows['eps']}"] = f"={col}{rows['ni']}/{col}{rows['shares']}"
    ws[f"{col}{rows['fcf']}"] = f"={col}{rows['ni']}+{col}{rows['da']}+{col}{rows['revenue']}*{SBC}-{col}{rows['capex']}-{WC}*({col}{rows['revenue']}-{prev}{rows['revenue']})"
    ws[f"{col}{rows['capex_rev']}"] = f"={col}{rows['capex']}/{col}{rows['revenue']}"
    ws[f"{col}{rows['da_rev']}"] = f"={col}{rows['da']}/{col}{rows['revenue']}"

# fix shares formula: use current-year FCF (defined after shares -> circular). Use prior-year FCF instead.
for j, col in enumerate(cols[1:], start=1):
    prev = cols[j - 1]
    ws[f"{col}{rows['shares']}"] = (f"={prev}{rows['shares']}-MIN({prev}{rows['fcf']}*{BB},{col}{rows['ni']}*0.9)/({BBM}*{prev}{rows['eps']})")

# ---------------------------------------------------- capex vintage helper
r0 = 27
ws.cell(row=r0, column=1, value="资本开支年度（折旧计算用）").font = Font(name="微软雅黑", size=10, bold=True, color=NAVY)
ws.cell(row=r0, column=2, value="十亿美元").font = NOTE_FONT
hist_capex = {2019: 80, 2020: 95, 2021: 130, 2022: 160, 2023: 150, 2024: 230, 2025: 380, 2026: 715}
for i, yr in enumerate(range(2019, 2032), start=1):
    r = r0 + i
    ws.cell(row=r, column=1, value=yr).font = BODY_FONT
    ws.cell(row=r, column=1).border = BORDER
    c = ws.cell(row=r, column=2)
    c.border = BORDER
    c.number_format = "#,##0"
    if yr <= 2026:
        c.value = hist_capex[yr]
        c.font = BODY_FONT
    else:
        col = cols[yr - 2026]
        c.value = f"={col}{rows['capex']}"
        c.font = BODY_FONT

# note
note(ws, rows["da_rev"] + 2,
     "说明：折旧按 2019-2031 年资本开支的 8 年滚动平均计算（与报告口径一致）；股本按上年 FCF 的 60% 回购、25 倍 EPS 估值折算。"
     "由于回购采用上年 FCF，EPS 与报告存在 1%-2% 的差异。", width=7)

ws.column_dimensions["A"].width = 30
for col in "BCDEFG":
    ws.column_dimensions[col].width = 13
ws.freeze_panes = "B5"

# =====================================================================  情景对比
ws = wb.create_sheet("情景对比")
ws.sheet_view.showGridLines = False
title(ws, "三情景对比（模型输出）", "来自 Python 完整模型：vintage 折旧、FCF 当年回购、8 家公司逐家加总。", width=7)
header_row(ws, 4, ["指标", "2026A", "2031 不裁员", "2031 每年裁 10%", "2031 每年裁 20%", "10% 相对不裁", "20% 相对不裁"])
flat = data["flat_base"]["agg"]
c10 = data["cut10_base"]["agg"]
c20 = data["cut20_base"]["agg"]
metrics = [
    ("收入", "rev", "#,##0.0", "ratio"),
    ("经营利润 EBIT", "ebit", "#,##0.0", "ratio"),
    ("EBIT 利润率", "ebit_margin", "0.0%", "pt"),
    ("净利润", "ni", "#,##0.0", "ratio"),
    ("EPS（美元）", "eps", "0.00", "ratio"),
    ("自由现金流", "fcf", "#,##0.0", "ratio"),
    ("员工数（千人）", "hc", "#,##0", "ratio"),
    ("资本开支", "capex", "#,##0.0", "ratio"),
    ("折旧", "da", "#,##0.0", "ratio"),
    ("折旧/收入", "da_rev", "0.0%", "pt"),
]
r = 5
for label, key, fmt, mode in metrics:
    ws.cell(row=r, column=1, value=label).font = BOLD_FONT if key in ("eps", "fcf") else BODY_FONT
    ws.cell(row=r, column=2, value=flat[key][0]).number_format = fmt
    ws.cell(row=r, column=3, value=flat[key][-1]).number_format = fmt
    ws.cell(row=r, column=4, value=c10[key][-1]).number_format = fmt
    ws.cell(row=r, column=5, value=c20[key][-1]).number_format = fmt
    if mode == "ratio":
        ws.cell(row=r, column=6, value=f"=D{r}/C{r}-1").number_format = "0.0%"
        ws.cell(row=r, column=7, value=f"=E{r}/C{r}-1").number_format = "0.0%"
    else:
        ws.cell(row=r, column=6, value=f"=D{r}-C{r}").number_format = "0.0%"
        ws.cell(row=r, column=7, value=f"=E{r}-C{r}").number_format = "0.0%"
    for j in range(1, 8):
        cell = ws.cell(row=r, column=j)
        cell.border = BORDER
        if j > 1:
            cell.alignment = Alignment(horizontal="center")
        if cell.font is None or cell.font.name != "微软雅黑":
            cell.font = BODY_FONT
    r += 1
note(ws, r + 1, "注：EPS 为八家公司合计净利润/合计股本，指数化处理；比例为相对“不裁员”基准的差额。", width=7)

# yearly EPS / FCF
r = 18
ws.cell(row=r, column=1, value="逐年路径").font = Font(name="微软雅黑", size=11, bold=True, color=NAVY)
r += 1
header_row(ws, r, ["EPS（美元）", "2026", "2027", "2028", "2029", "2030", "2031"])
eps_hdr = r
for name, key, label in [("flat_base", "eps", "不裁员"), ("cut10_base", "eps", "每年裁 10%"), ("cut20_base", "eps", "每年裁 20%")]:
    r += 1
    ws.cell(row=r, column=1, value=label).font = BODY_FONT
    for j, v in enumerate(data[name]["agg"]["eps"]):
        c = ws.cell(row=r, column=2 + j, value=v)
        c.number_format = "0.00"
        c.font = BODY_FONT
        c.border = BORDER
        c.alignment = Alignment(horizontal="center")
r += 2
header_row(ws, r, ["FCF（十亿美元）", "2026", "2027", "2028", "2029", "2030", "2031"])
fcf_hdr = r
for name, label in [("flat_base", "不裁员"), ("cut10_base", "每年裁 10%"), ("cut20_base", "每年裁 20%")]:
    r += 1
    ws.cell(row=r, column=1, value=label).font = BODY_FONT
    for j, v in enumerate(data[name]["agg"]["fcf"]):
        c = ws.cell(row=r, column=2 + j, value=round(v, 0))
        c.number_format = "#,##0"
        c.font = BODY_FONT
        c.border = BORDER
        c.alignment = Alignment(horizontal="center")

ws.column_dimensions["A"].width = 22
for col in "BCDEFG":
    ws.column_dimensions[col].width = 15

# charts
ch = LineChart()
ch.title = "EPS 路径：裁员只能小幅抬高 EPS"
ch.y_axis.title = "EPS（美元）"
ch.x_axis.title = "年份"
ch.add_data(Reference(ws, min_col=1, max_col=7, min_row=eps_hdr + 1, max_row=eps_hdr + 3), from_rows=True, titles_from_data=True)
ch.set_categories(Reference(ws, min_col=2, max_col=7, min_row=eps_hdr))
ch.height = 8
ch.width = 15
ws.add_chart(ch, "I4")

ch2 = LineChart()
ch2.title = "自由现金流路径"
ch2.y_axis.title = "十亿美元"
ch2.add_data(Reference(ws, min_col=1, max_col=7, min_row=fcf_hdr + 1, max_row=fcf_hdr + 3), from_rows=True, titles_from_data=True)
ch2.set_categories(Reference(ws, min_col=2, max_col=7, min_row=fcf_hdr))
ch2.height = 8
ch2.width = 15
ws.add_chart(ch2, "I22")

# =====================================================================  敏感性
ws = wb.create_sheet("敏感性")
ws.sheet_view.showGridLines = False
title(ws, "敏感性：2026-2031 年 EPS 复合增速", "行：每年裁员速度；列：收入增速相对基准的偏移。", width=7)
header_row(ws, 4, ["裁员速度 \\ 收入偏移", "-4pt", "-2pt", "基准", "+2pt", "+4pt"])
sens = data["sensitivity"]
cuts = sorted(set(round(s["cut"], 4) for s in sens))
for i, cut in enumerate(cuts, start=5):
    ws.cell(row=i, column=1, value=cut).number_format = "0%"
    ws.cell(row=i, column=1).font = BOLD_FONT
    ws.cell(row=i, column=1).border = BORDER
    ws.cell(row=i, column=1).alignment = Alignment(horizontal="center")
    for j, shift in enumerate([-0.04, -0.02, 0.0, 0.02, 0.04], start=2):
        v = next(s for s in sens if abs(s["cut"] - cut) < 1e-9 and abs(s["shift"] - shift) < 1e-9)
        c = ws.cell(row=i, column=j, value=round(v["eps_cagr"], 4))
        c.number_format = "0.0%"
        c.font = BODY_FONT
        c.border = BORDER
        c.alignment = Alignment(horizontal="center")
        if shift == 0.0:
            c.fill = ACCENT_FILL
for j in range(1, 7):
    ws.cell(row=4, column=j).fill = HDR_FILL
ws.column_dimensions["A"].width = 22
for col in "BCDEF":
    ws.column_dimensions[col].width = 13

# =====================================================================  QQQ
ws = wb.create_sheet("QQQ")
ws.sheet_view.showGridLines = False
title(ws, "QQQ 情景与概率加权", "指数 EPS 增速 = 65% × 八家公司 + 35% × 其余成分股；年化回报含 0.6% 股息率。", width=9)
header_row(ws, 4, ["情景", "假设", "指数 EPS 增速", "期末 PE", "2031 点位", "年化回报", "概率", "加权回报"])
rows_q = [
    ("牛市：AI 收入兑现", "收入 +16% 起步，裁员 10%，云维持 40%+"),
    ("基准：增长放缓、估值回归", "收入 +12% 起步，裁员 10%，云降到 25%"),
    ("熊市：资本开支反噬", "收入 +7% 起步，裁员 10%，折旧超预期"),
    ("深度衰退：20% 裁员+需求破坏", "收入零增长，裁员 20%，估值 14x"),
]
r = 5
for i, (name, assume) in enumerate(rows_q):
    q = qqq["rows"][i]
    ws.cell(row=r, column=1, value=name).font = BOLD_FONT
    ws.cell(row=r, column=2, value=assume).font = BODY_FONT
    ws.cell(row=r, column=3, value=round(q["idx_cagr"], 4)).number_format = "0.0%"
    ws.cell(row=r, column=4, value=int(q["pe_end"])).number_format = "0"
    ws.cell(row=r, column=5, value=round(q["lvl31"], 0)).number_format = "#,##0"
    ws.cell(row=r, column=6, value=round(q["total"], 4)).number_format = "0.0%"
    ws.cell(row=r, column=7, value=q["prob"]).number_format = "0%"
    ws.cell(row=r, column=8, value=f"=F{r}*G{r}").number_format = "0.0%"
    for j in range(1, 9):
        cell = ws.cell(row=r, column=j)
        cell.border = BORDER
        if j > 2:
            cell.font = BODY_FONT
            cell.alignment = Alignment(horizontal="center")
    r += 1
ws.cell(row=r, column=1, value="概率加权").font = Font(name="微软雅黑", size=10, bold=True, color=RED)
ws.cell(row=r, column=5, value=f"=SUMPRODUCT(E5:E8,G5:G8)").number_format = "#,##0"
ws.cell(row=r, column=5).font = Font(name="微软雅黑", size=10, bold=True, color=RED)
ws.cell(row=r, column=6, value=f"=SUMPRODUCT(F5:F8,G5:G8)").number_format = "0.0%"
ws.cell(row=r, column=6).font = Font(name="微软雅黑", size=10, bold=True, color=RED)
ws.cell(row=r, column=7, value="=SUM(G5:G8)").number_format = "0%"
ws.cell(row=r, column=7).font = Font(name="微软雅黑", size=10, bold=True, color=RED)
for j in range(1, 9):
    ws.cell(row=r, column=j).border = BORDER

# index path table for chart
r += 3
ws.cell(row=r, column=1, value="指数点位路径").font = Font(name="微软雅黑", size=11, bold=True, color=NAVY)
r += 1
header_row(ws, r, ["情景", "2026", "2027", "2028", "2029", "2030", "2031"])
NDX0, PE0 = 29651.441, 25.0
for i, (name, _) in enumerate(rows_q):
    q = qqq["rows"][i]
    r += 1
    ws.cell(row=r, column=1, value=name).font = BODY_FONT
    eps0 = NDX0 / PE0
    for t in range(6):
        pe = PE0 + (q["pe_end"] - PE0) * min(t / 2, 1)
        lvl = NDX0 if t == 0 else eps0 * (1 + q["idx_cagr"]) ** t * pe
        c = ws.cell(row=r, column=2 + t, value=round(lvl, 0))
        c.number_format = "#,##0"
        c.font = BODY_FONT
        c.border = BORDER
        c.alignment = Alignment(horizontal="center")

chart = LineChart()
chart.title = "QQQ 情景路径（纳斯达克100 点位）"
chart.y_axis.title = "点位"
chart.height = 8
chart.width = 17
chart.add_data(Reference(ws, min_col=1, max_col=7, min_row=r - 3, max_row=r), from_rows=True, titles_from_data=True)
chart.set_categories(Reference(ws, min_col=2, max_col=7, min_row=r - 4))
ws.add_chart(chart, "J4")

ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 44
for col in "CDEFGH":
    ws.column_dimensions[col].width = 12

# =====================================================================  季度跟踪
ws = wb.create_sheet("季度跟踪")
ws.sheet_view.showGridLines = False
title(ws, "过去四个季度：裁员、财报与 QQQ", "公告口径，单位：千人；QQQ 为纳斯达克100 季度回报。Q4* 为 9/30-10/28 估计。", width=8)
header_row(ws, 4, ["季度", "公告裁员（千人）", "QQQ 当季回报", "代表性事件", "宏观/财报主线"])
q_rows = [
    ["2025Q4", 17.0, 0.0245, "亚马逊 1.4 万、IBM 约 3,000", "AI 资本开支扩张，财报稳健"],
    ["2026Q1", 38.6, -0.0593, "亚马逊 1.6 万、戴尔 1.1 万、Block 4,000、Atlassian 1,600", "伊朗战争，油价 +79%"],
    ["2026Q2", 32.0, 0.2773, "Meta 8,000、思科 4,000、PayPal 4,760、Intuit 3,000", "AI 财报大超预期"],
    ["2026Q3", 5.8, -0.0376, "微软 4,800、谷歌滚动优化", "资本开支焦虑，Meta FCF -91%"],
    ["2026Q4*", 61.0, -0.0400, "微软 6 万窗口、eBay 9%", "12 月加息概率 78.4%"],
]
r = 5
for row in q_rows:
    for j, v in enumerate(row, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BORDER
        c.font = BODY_FONT
        if j == 2:
            c.number_format = "#,##0.0"
        if j == 3:
            c.number_format = "+0.00%;-0.00%"
        if j == 1:
            c.alignment = Alignment(horizontal="left")
        else:
            c.alignment = Alignment(horizontal="center", wrap_text=(j >= 4))
    ws.row_dimensions[r].height = 48
    r += 1

r += 1
ws.cell(row=r, column=1, value="事件窗口：五个“纯裁员”公告的股价反应").font = Font(name="微软雅黑", size=11, bold=True, color=NAVY)
r += 1
header_row(ws, r, ["公司", "公告日", "裁员规模", "占员工", "股价反应", "关键变量"])
events = [
    ["Block", "2026-02-26", 4000, "约 50%", "+24%（盘后）", "裁员近半 + 费用节省 + AI 叙事"],
    ["思科", "2026-05-14", 4000, "<5%", "+13.4%（当日）", "财报超预期 + 上调指引"],
    ["Snap", "2026-04-16", 1000, "16%", "+8%（当日）", "AI 生成 65% 新代码"],
    ["Atlassian", "2026-03-11", 1600, "10%", "+2%（当日）", "转向 AI/企业销售"],
    ["PayPal", "2026-05-05", 4760, "20%（2-3 年）", "-8%（当日）", "裁员 + 下调季度指引"],
]
for ev in events:
    r += 1
    for j, v in enumerate(ev, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BORDER
        c.font = BODY_FONT
        c.alignment = Alignment(horizontal="center" if j > 1 else "left", wrap_text=(j == 6))

ws.column_dimensions["A"].width = 14
ws.column_dimensions["B"].width = 17
ws.column_dimensions["C"].width = 14
ws.column_dimensions["D"].width = 28
ws.column_dimensions["E"].width = 26
ws.column_dimensions["F"].width = 30

# combo chart: bars = layoffs, line = QQQ return (secondary axis)
bar = BarChart()
bar.title = "裁员公告 vs QQQ 当季回报"
bar.y_axis.title = "公告裁员（千人）"
bar.height = 8
bar.width = 15
bar.add_data(Reference(ws, min_col=2, min_row=4, max_row=8), titles_from_data=True)
bar.set_categories(Reference(ws, min_col=1, min_row=5, max_row=8))

line = LineChart()
line.add_data(Reference(ws, min_col=3, min_row=4, max_row=8), titles_from_data=True)
line.y_axis.axId = 200
line.y_axis.title = "QQQ 当季回报"
line.y_axis.crosses = "max"
line.series[0].graphicalProperties.line.width = 28000
line.series[0].smooth = False
bar.series[0].smooth = False
bar.y_axis.crosses = "autoZero"
bar += line
ws.add_chart(bar, "G4")

# save
out = BASE / "大厂裁员_QQQ_模型.xlsx"
wb.save(out)
print("saved", out)




