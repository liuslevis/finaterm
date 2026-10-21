"""验证 manifest 热重载：后台追加交易日时，运行中的进程无需重启即可用上新数据。

做法：把 `_parity_ds` 复制到临时目录，先把 manifest 里某个交易日「摘掉」，
再把它放回去，检查 `Store.dates` 与 `data` 的读取路径是否自动跟上。
"""
from __future__ import annotations

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

SRC = os.path.join(HFQ, "cache", "_parity_ds")
DST = os.path.join(HFQ, "cache", "_reload_test")
DATE = "20260918"
CODE = "001301.SZ"

shutil.rmtree(DST, ignore_errors=True)
shutil.copytree(SRC, DST)
mpath = os.path.join(DST, "_meta", "manifest.json")
full = json.load(open(mpath, encoding="utf-8"))
assert DATE in full["dates"], f"测试前提不满足: {DATE} 不在数据集里"
print(f"数据集交易日 {len(full['dates'])} 个（含 {DATE}）")

# 1) 先写一个「不含该交易日」的 manifest，模拟转换尚未完成
partial = json.loads(json.dumps(full))
partial["dates"].pop(DATE)
json.dump(partial, open(mpath, "w", encoding="utf-8"), ensure_ascii=False)

os.environ["HFQ_PARQUET_DIR"] = DST
from app import data  # noqa: E402

print(f"启动时 _PQ.dates = {data._PQ.dates}")
assert DATE not in data._PQ.dates
print(f"  该日走 7z 回退: load_stock 会 KeyError? ", end="")
try:
    data._PQ.load_stock(CODE, DATE)
    print("否（意外）")
except KeyError:
    print("是（符合预期）")

# 2) 把交易日放回去（等价于后台转换完成写了一次 manifest）
json.dump(full, open(mpath, "w", encoding="utf-8"), ensure_ascii=False)
os.utime(mpath, None)

# 3) 触发刷新（节流窗口内用 0 立即生效）
reloaded = data._PQ.maybe_reload(0)
data.refresh_dates()
print(f"maybe_reload -> {reloaded}")
print(f"刷新后 _PQ.dates = {data._PQ.dates}")

ok1 = reloaded and DATE in data._PQ.dates
# 4) 读取路径确实改用 Parquet
sd = data.get_stock(CODE, DATE)
used_pq = DATE in data._PQ.dates
print(f"get_stock({CODE},{DATE}) -> events={len(sd.events)} 命中 Parquet={used_pq}")

# 5) DATES 仍应覆盖全部 59 个归档交易日
print(f"DATES={len(data.DATES)} 个（应为 59）")
ok = ok1 and used_pq and len(data.DATES) == 59
print(f"\n=== 结论 === 热重载生效: {ok}")

shutil.rmtree(DST, ignore_errors=True)
print(f"明细: reloaded={reloaded} date_present={DATE in data._PQ.dates} "
      f"dates_count={len(data.DATES)}")
sys.exit(0 if ok else 1)
