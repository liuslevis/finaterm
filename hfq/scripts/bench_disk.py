"""对比 C: 与 D: 上的同源 Parquet 分片：顺序吞吐 + 随机过滤读延迟。

用来判断把数据集放到 D: 后随机访问性能是否可接受。
"""
from __future__ import annotations

import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import pyarrow.parquet as pq  # noqa: E402

from app.parquet_store import Store  # noqa: E402
from app.paths import parquet_default  # noqa: E402

# 2026-10-29：仓库内 C: 副本已删除，此前"C: vs D:"的迁移期对比不再可复现。
# 只保留当前数据集（HFQ_PARQUET_DIR → D:\data-parquet）作为基线测量。
ROOTS = {
    "Parquet": parquet_default(),
}
DATE = "20260901"
CODES = ["000001.SZ", "600525.SH", "159119.SZ", "300965.SZ", "900948.SH"]


def seq_read(path: str, n: int = 3) -> float:
    best = 1e9
    for _ in range(n):
        t0 = time.perf_counter()
        with open(path, "rb") as fh:
            while fh.read(1 << 22):
                pass
        best = min(best, time.perf_counter() - t0)
    return os.path.getsize(path) / 1024**2 / best


def main():
    print(f"{'root':<12}{'MB/s 顺序':>12}{'冷读 ms':>10}{'热读 ms(中位)':>16}"
          f"{'热读 ms(最差)':>16}")
    summary = {}
    for label, root in ROOTS.items():
        if not os.path.isdir(root):
            print(f"{label:<12} 不存在，跳过")
            continue
        st = Store(root).open()
        # 顺序吞吐：取最大的 trades 分片
        big = max(
            (os.path.join(dp, f) for dp, _, fs in os.walk(root) for f in fs
             if f.startswith("trades-") and f.endswith(".parquet")),
            key=os.path.getsize)
        thr = seq_read(big)

        cold, warm = [], []
        for code in CODES:
            shard, _ = st.shard_of(code)
            lat = []
            for k in range(6):
                t0 = time.perf_counter()
                pq.read_table(st.table_path(DATE, "orders", shard),
                              filters=[("code", "=", code)])
                lat.append((time.perf_counter() - t0) * 1000)
            cold.append(lat[0])
            warm.append(statistics.median(lat[1:]))
        print(f"{label:<12}{thr:>12.1f}{statistics.median(cold):>10.1f}"
              f"{statistics.median(warm):>16.1f}{max(warm):>16.1f}")
        summary[label] = {"seq_mb_s": round(thr, 1),
                          "cold_ms": round(statistics.median(cold), 1),
                          "warm_ms": round(statistics.median(warm), 1),
                          "worst_ms": round(max(warm), 1),
                          "largest_shard_mb": round(os.path.getsize(big) / 1024**2, 1)}
    print("\n结论：", summary)


if __name__ == "__main__":
    main()
