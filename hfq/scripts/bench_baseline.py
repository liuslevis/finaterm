"""基线基准：测量当前 7z 读路径的耗时构成（索引 / 抽取 / 解析 / 二进制缓存）。"""
from __future__ import annotations

import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import py7zr  # noqa: E402

from app import data  # noqa: E402

DATE = sys.argv[1] if len(sys.argv) > 1 else "20260901"
CODE = sys.argv[2] if len(sys.argv) > 2 else "000001.SZ"
ARCHIVE = os.path.join(data.DATA_DIR, f"{DATE}.7z")


def timed(label, fn):
    t0 = time.perf_counter()
    r = fn()
    dt = time.perf_counter() - t0
    print(f"  {label:<34} {dt*1000:9.1f} ms")
    return r, dt


print(f"=== baseline {DATE} / {CODE} ===")
print(f"archive: {os.path.getsize(ARCHIVE)/1024**3:.2f} GB")

# 1. 打开归档 + 列目录（索引构建成本）
def open_and_list():
    with py7zr.SevenZipFile(ARCHIVE, "r") as a:
        return [f.filename for f in a.list() if not f.is_directory]

files, _ = timed("py7zr open+list (index scan)", open_and_list)
print(f"    members: {len(files)}")

members = [f for f in files if f.split('/')[1] == CODE]

# 2. 单只股票随机抽取（solid 归档的代价）
stage = os.path.join(ROOT, "cache", "_bench_stage")
shutil.rmtree(stage, ignore_errors=True)

def extract_one():
    with py7zr.SevenZipFile(ARCHIVE, "r") as a:
        a.extract(path=stage, targets=members)

_, t_extract = timed("py7zr extract 1 stock (solid)", extract_one)
sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(stage) for f in fs)
print(f"    extracted: {sz/1024**2:.2f} MB")

# 3. CSV 解析（冷路径）
data.CACHE_DIR = os.path.join(ROOT, "cache", "_bench_cfg")
shutil.rmtree(data.CACHE_DIR, ignore_errors=True)
src = os.path.join(stage, DATE, CODE)
dst = os.path.join(data.CACHE_DIR, DATE, CODE)
os.makedirs(dst, exist_ok=True)
for n in ("行情.csv", "逐笔委托.csv", "逐笔成交.csv"):
    if os.path.exists(os.path.join(src, n)):
        shutil.copy2(os.path.join(src, n), os.path.join(dst, n))

sd, t_parse = timed("parse CSV -> StockData", lambda: data.StockData(CODE, DATE))
print(f"    events={len(sd.events)} quotes={len(sd.quotes)} orders={len(sd.orders_summary)}")

binp = os.path.join(dst, f"_cache_v{data._CACHE_VER}.bin")
print(f"    bin cache: {os.path.getsize(binp)/1024**2:.2f} MB")

# 4. 二进制缓存命中（热路径）
def load_bin():
    s = data.StockData.__new__(data.StockData)
    s.code = CODE; s.date = DATE
    return s._load_binary()

ok, t_bin = timed("load _cache_v1.bin (warm)", load_bin)
print(f"    hit={ok}")

# 5. 派生结构成本
def derive():
    s = data.StockData(CODE, DATE)
    data.build_ladder(s)
    data.all_books(s)
    data.intraday(s)
    return s

_, t_derive = timed("StockData (bin warm) + 派生结构", derive)

print()
print("=== 汇总 ===")
print(f"  冷访问(抽取+解析)      {t_extract*1000 + t_parse*1000:9.1f} ms")
print(f"  热访问(bin 缓存)       {t_bin*1000:9.1f} ms")
print(f"  含派生(热)             {t_derive*1000:9.1f} ms")

shutil.rmtree(stage, ignore_errors=True)
shutil.rmtree(data.CACHE_DIR, ignore_errors=True)
