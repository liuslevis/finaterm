"""跑齐全部迁移校验，产出 `snapshot/REPORT.md`。

依次执行：
  1. 重建快照口径的校验数据集（7 个交易日 × 快照里的标的）
  2. compare_snapshot  逐字段指纹（33 探针）
  3. compare_sweep     大样本逐字段比对
  4. verify_sentinel   市价委托哨兵价格差异性质
  5. verify_daily_kline 跨日日 K
  6. bench_compare     A/B 性能与磁盘
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

from app.paths import parquet_default  # noqa: E402

PY = sys.executable
SNAP = os.path.join(HFQ, "snapshot")
PARITY_DS = os.path.join(HFQ, "cache", "_parity_ds")
MAIN_DS = os.environ.get("HFQ_MAIN_DS") or parquet_default()
BASELINE = os.path.join(SNAP, "baseline-v1")

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def run(label, args, timeout=3600):
    print(f"\n{'='*70}\n>>> {label}\n{'='*70}", flush=True)
    t0 = time.perf_counter()
    p = subprocess.run([PY] + args, cwd=HFQ, env=ENV, text=True,
                       encoding="utf-8", errors="replace",
                       capture_output=True, timeout=timeout)
    dt = time.perf_counter() - t0
    out = (p.stdout or "") + (p.stderr or "")
    print(out[-4000:], flush=True)
    print(f"<<< {label} exit={p.returncode} {dt:.1f}s", flush=True)
    return p.returncode, out, dt


def main():
    os.makedirs(SNAP, exist_ok=True)
    results = {}

    # 1) 快照口径的一致性数据集
    codes = ["000001.SZ", "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ",
             "000010.SZ", "000011.SZ", "001301.SZ", "001317.SZ", "001323.SZ",
             "001332.SZ", "003039.SZ", "600967.SH"]
    dates = ["20260901", "20260902", "20260903", "20260904",
             "20260916", "20260917", "20260918"]
    rc, out, _ = run("build parity dataset",
                     ["scripts/build_parquet.py", "--root", PARITY_DS, "--force",
                      "--temp", os.path.join(HFQ, "cache", "_build_pq"),
                      "--dates"] + dates + ["--codes"] + codes)
    results["parity_build_rc"] = rc

    # 2) 逐字段指纹
    rc, out, _ = run("compare_snapshot", [
        "scripts/compare_snapshot.py", "--root", PARITY_DS,
        "--snapshot", BASELINE,
        "--json-out", os.path.join(SNAP, "compare_parity.json")])
    results["compare_snapshot_rc"] = rc

    # 3) 大样本扫描（主数据集上的全量交易日）
    m = json.load(open(os.path.join(MAIN_DS, "_meta", "manifest.json"), encoding="utf-8"))
    day = sorted(m["dates"])[-1]
    # 3a) 全日期全列越界扫描
    rc, out, _ = run("scan_anomalies (全日期)", [
        "scripts/scan_anomalies.py", "--root", MAIN_DS,
        "--json-out", os.path.join(SNAP, "anomalies.json")], timeout=7200)
    results["scan_anomalies_rc"] = rc

    rc, out, _ = run("compare_sweep", [
        "scripts/compare_sweep.py", "--date", day, "--root", MAIN_DS, "--n", "120",
        "--json-out", os.path.join(SNAP, "compare_sweep.json")])
    results["compare_sweep_rc"] = rc
    results["sweep_date"] = day

    # 4) 哨兵价格
    sentinel_day = "20260731" if "20260731" in m["dates"] else day
    rc, out, _ = run("verify_sentinel", [
        "scripts/verify_sentinel.py", "--date", sentinel_day, "--root", MAIN_DS])
    results["verify_sentinel_rc"] = rc

    # 5) 日 K
    rc, out, _ = run("verify_daily_kline", [
        "scripts/verify_daily_kline.py", "--root", MAIN_DS,
        "--codes", "000001.SZ", "001301.SZ", "600000.SH"],
        timeout=7200)
    results["verify_daily_kline_rc"] = rc

    # 6) A/B
    rc, out, _ = run("bench_compare", [
        "scripts/bench_compare.py", "--date", day, "--root", MAIN_DS])
    results["bench_compare_rc"] = rc

    with open(os.path.join(SNAP, "checks_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
