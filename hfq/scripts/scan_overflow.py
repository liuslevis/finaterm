"""定位 CSV 中超出 int64 范围的数值：解压一天归档并逐文件精确扫描。

输出受影响文件、列、原始字面量与出现次数，用于确定与原始解析器一致的处置方式。
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import py7zr  # noqa: E402

ARCHIVE = os.path.join(HFQ, "data-lv2", (sys.argv[1] if len(sys.argv) > 1 else "20260901") + ".7z")
TEMP = os.path.abspath(os.path.join(HFQ, "cache", "_scan"))
DATE = os.path.basename(ARCHIVE)[:-3]
I64_MAX = 2**63 - 1
TOKEN = re.compile(rb"\d{19,}")

FILES = {"逐笔委托.csv": 11, "逐笔成交.csv": 13, "行情.csv": 67}

if not os.path.isdir(os.path.join(TEMP, DATE)):
    shutil.rmtree(TEMP, ignore_errors=True)
    os.makedirs(TEMP, exist_ok=True)
    print(f"解压 {ARCHIVE} ...", flush=True)
    with py7zr.SevenZipFile(ARCHIVE, "r") as a:
        a.extractall(path=TEMP)

base = os.path.join(TEMP, DATE)
if not os.path.isdir(base):
    base = TEMP
codes = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
print(f"目录 {base}  标的 {len(codes)}")

hits: dict[str, list] = defaultdict(list)
per_col: Counter = Counter()
n_files_hit = 0
for i, code in enumerate(codes, 1):
    for fname, width in FILES.items():
        p = os.path.join(base, code, fname)
        if not os.path.exists(p):
            continue
        with open(p, "rb") as fh:
            raw = fh.read()
        j = raw.find(b"\n")
        body = raw[j + 1:] if j >= 0 else b""
        found = set(TOKEN.findall(body))
        if not found:
            continue
        n_files_hit += 1
        # 定位到具体列
        for tok in list(found)[:3]:
            k = body.find(tok)
            line_start = body.rfind(b"\n", 0, k) + 1
            line_end = body.find(b"\n", k)
            line = body[line_start:line_end].decode("ascii", "replace")
            cells = line.split(",")
            col = next((ci for ci, c in enumerate(cells) if c.strip() == tok.decode()), -1)
            hits[fname].append({"code": code, "col": col, "value": tok.decode(),
                                "line": line[:180]})
            per_col[(fname, col)] += 1
    if i % 1000 == 0:
        print(f"  扫描 {i}/{len(codes)}  命中文件 {n_files_hit}", flush=True)

print(f"\n=== 结果 ===\n受影响文件数 {n_files_hit}")
for fname, recs in hits.items():
    print(f"\n{fname}: {len(recs)} 处")
    for r in recs[:6]:
        print(f"  {r['code']} 列#{r['col']} = {r['value']}")
        print(f"     {r['line']}")
print("\n按 (文件, 列) 统计:", dict(per_col))

allvals = [int(r["value"]) for recs in hits.values() for r in recs]
if allvals:
    print(f"\n值范围: {min(allvals)} .. {max(allvals)}  (2^63-1 = {I64_MAX}, 2^64 = {2**64})")
    print(f"超过 2^64 的: {sum(1 for v in allvals if v >= 2**64)}")
    print(f"落在 int64 内的: {sum(1 for v in allvals if v <= I64_MAX)}")
