r"""修改后对比快照：用 Parquet 路径重跑同一批行为探针，逐字段比对指纹。

基线来自 ``hfq/scripts/snapshot.py`` 生成的 ``snapshot/<tag>/behavior/*.json``；
探针函数直接复用 snapshot.py 里的 ``probe_behavior``，因此计算口径完全一致。

用法：
    python hfq/scripts/compare_snapshot.py --root D:\data-parquet \
        --snapshot hfq/snapshot/baseline-v1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Parquet 数据集根目录")
    ap.add_argument("--snapshot", required=True, help="基线快照目录")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    os.environ["HFQ_PARQUET_DIR"] = os.path.abspath(args.root)

    import snapshot as snap  # noqa: E402  复用同一探针实现

    from app import data  # noqa: E402

    if not data.PARQUET_ENABLED:
        raise SystemExit(f"Parquet 数据集不可用: {args.root}")
    print(f"Parquet 路径已启用: {args.root}")
    print(f"  分区频率 {data._PQ.manifest()['freq']}  "
          f"交易日 {len(data.DATES)} 个  universe {len(data._PQ.manifest()['universe'])} 只")

    bdir = os.path.join(args.snapshot, "behavior")
    files = sorted(os.listdir(bdir))
    print(f"基线探针 {len(files)} 个\n")

    results = []
    t_total = 0.0
    t_load_total = 0.0
    for fn in files:
        with open(os.path.join(bdir, fn), encoding="utf-8") as fh:
            base = json.load(fh)
        date, code = base["date"], base["code"]
        t0 = time.perf_counter()
        try:
            new = snap.probe_behavior(date, code)
            err = None
        except Exception as e:  # noqa: BLE001
            new, err = None, f"{type(e).__name__}: {e}"
        dt = time.perf_counter() - t0
        t_total += dt
        new_load = (new or {}).get("load_seconds")
        if new_load:
            t_load_total += new_load

        rec = {"date": date, "code": code,
               "probe_seconds": round(dt, 4),
               "load_seconds": new_load,
               "status": "?", "diffs": []}
        if err:
            rec["status"] = "ERROR"
            rec["error"] = err
        elif "error" in base:
            rec["status"] = "SKIP(base error)"
        else:
            diffs = []
            if base["counts"] != new["counts"]:
                for k in sorted(set(base["counts"]) | set(new["counts"])):
                    if base["counts"].get(k) != new["counts"].get(k):
                        diffs.append(f"counts.{k}: {base['counts'].get(k)} -> "
                                     f"{new['counts'].get(k)}")
            for k in sorted(set(base["fingerprints"]) | set(new["fingerprints"])):
                if base["fingerprints"].get(k) != new["fingerprints"].get(k):
                    diffs.append(f"fp.{k}: {base['fingerprints'].get(k)} -> "
                                 f"{new['fingerprints'].get(k)}")
            rec["diffs"] = diffs
            rec["status"] = "PASS" if not diffs else "FAIL"
        rec["baseline_seconds"] = base.get("load_seconds")
        results.append(rec)

        mark = {"PASS": "OK  ", "FAIL": "FAIL", "ERROR": "ERR ", "SKIP(base error)": "SKIP"}[
            rec["status"]]
        print(f"  [{mark}] {date}/{code:<12} load={new_load or 0:.3f}s "
              f"(base {base.get('load_seconds')}s)  probe={dt:.3f}s")
        if rec["diffs"]:
            for d in rec["diffs"][:12]:
                print(f"        {d}")
            if len(rec["diffs"]) > 12:
                print(f"        ... 共 {len(rec['diffs'])} 处差异")

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_err = sum(1 for r in results if r["status"] == "ERROR")
    n_skip = sum(1 for r in results if r["status"].startswith("SKIP"))
    n = max(len(results), 1)
    base_sum = sum(r["baseline_seconds"] or 0 for r in results)
    print(f"\n=== 一致性结论 ===")
    print(f"  PASS {n_pass}   FAIL {n_fail}   ERROR {n_err}   SKIP {n_skip}")
    print(f"  get_stock 加载  新 {t_load_total:.3f}s (均 {t_load_total/n*1000:.1f} ms)  "
          f"基线 {base_sum:.3f}s (均 {base_sum/n*1000:.1f} ms)")
    print(f"  全探针耗时      新 {t_total:.3f}s (均 {t_total/n*1000:.1f} ms)")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"root": os.path.abspath(args.root),
                       "snapshot": os.path.abspath(args.snapshot),
                       "results": results,
                       "summary": {"pass": n_pass, "fail": n_fail,
                                   "error": n_err, "skip": n_skip,
                                   "new_load_seconds": round(t_load_total, 4),
                                   "new_probe_seconds": round(t_total, 4),
                                   "baseline_seconds": round(base_sum, 4)}},
                      fh, indent=2, ensure_ascii=False)
        print(f"  明细 -> {args.json_out}")

    return 0 if (n_fail == 0 and n_err == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
