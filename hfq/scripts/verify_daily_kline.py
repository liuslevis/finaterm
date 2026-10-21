"""校验 daily_kline：旧实现（纯 7z/二进制缓存） vs 新实现（catalog + 回退混用）。

旧实现直接从快照副本 ``snapshot/<tag>/code/app/data.py`` 导入，保证对比的是
改动前的真实代码，而不是重新实现的近似版本。
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

OLDAPP = os.path.join(HFQ, "cache", "_oldapp")


def load_old_module(snapshot: str):
    """把快照里的原始 data.py 装成独立包 app_old。"""
    src = os.path.join(snapshot, "code", "app", "data.py")
    if not os.path.exists(src):
        raise SystemExit(f"快照缺少原始源码: {src}")
    dst_dir = os.path.join(OLDAPP, "app_old")
    shutil.rmtree(OLDAPP, ignore_errors=True)
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dst_dir, "data.py"))
    with open(os.path.join(dst_dir, "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write("")
    sys.path.insert(0, OLDAPP)
    mod = importlib.import_module("app_old.data")
    # 指向真实数据目录，但缓存独立，避免污染
    # 归档可能已挪到别的盘（本机在 D:\data-lv2），统一走 app.paths
    sys.path.insert(0, HFQ)
    from app.paths import archive_dir
    mod.DATA_DIR = archive_dir()
    mod.CACHE_DIR = os.path.join(HFQ, "cache", "_ab_old")
    os.makedirs(mod.CACHE_DIR, exist_ok=True)
    mod.DATES = mod.list_dates()
    mod.DEFAULT_DATE = mod.DATES[-1] if mod.DATES else "20260918"

    # 旧实现的 ensure_extracted 直接调 py7zr 选择性解压，偶发 Bad7zFile。
    # 这里只包一层「清缓存 + 重试」，被测的是解析/派生逻辑，不是 py7zr 的可靠性。
    _orig_ensure = mod.ensure_extracted

    def robust_ensure(code: str, date: str) -> str:
        last = None
        for attempt in range(4):
            try:
                return _orig_ensure(code, date)
            except Exception as e:  # noqa: BLE001
                last = e
                shutil.rmtree(os.path.join(mod.CACHE_DIR, date, "_stage"),
                              ignore_errors=True)
                shutil.rmtree(os.path.join(mod.CACHE_DIR, date, code),
                              ignore_errors=True)
        raise last  # type: ignore[misc]

    mod.ensure_extracted = robust_ensure
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=os.path.join(HFQ, "snapshot", "baseline-v1"))
    ap.add_argument("--root", default=os.path.join(HFQ, "data-parquet"))
    ap.add_argument("--codes", nargs="*",
                    default=["000001.SZ", "001301.SZ", "600000.SH", "300750.SZ"])
    args = ap.parse_args()

    os.environ["HFQ_PARQUET_DIR"] = os.path.abspath(args.root)
    from app import data as new

    if not new.PARQUET_ENABLED:
        raise SystemExit("Parquet 数据集不可用")
    m = new._PQ.manifest()
    complete = sorted(d for d in new._PQ.dates if not new._PQ.is_partial(d))
    print(f"数据集 {args.root}")
    print(f"  已全量转换交易日 {len(complete)} 个: {complete}")
    print(f"  总交易日 {len(new.DATES)} 个（其余走 7z 回退）")

    old = load_old_module(args.snapshot)
    print(f"  旧实现 DATES {len(old.DATES)} 个\n")

    out = {"codes": {}}
    for code in args.codes:
        print(f"--- {code} ---")
        t0 = time.perf_counter()
        k_old = old.daily_kline(code)
        t_old = time.perf_counter() - t0
        t0 = time.perf_counter()
        k_new = new.daily_kline(code)
        t_new = time.perf_counter() - t0
        same = k_old == k_new
        print(f"  旧 {len(k_old['days'])} 天 / {t_old:.1f}s")
        print(f"  新 {len(k_new['days'])} 天 / {t_new:.3f}s  "
              f"{'一致' if same else '不一致!'}")
        diffs = []
        if not same:
            do = {d["date"]: d for d in k_old["days"]}
            dn = {d["date"]: d for d in k_new["days"]}
            for d in sorted(set(do) | set(dn)):
                if do.get(d) != dn.get(d):
                    diffs.append({"date": d, "old": do.get(d), "new": dn.get(d)})
            for x in diffs[:5]:
                print(f"    {x['date']}: {x['old']} != {x['new']}")
        out["codes"][code] = {
            "old_days": len(k_old["days"]), "new_days": len(k_new["days"]),
            "old_seconds": round(t_old, 3), "new_seconds": round(t_new, 4),
            "identical": same, "diffs": diffs[:20],
            "speedup": round(t_old / t_new, 1) if t_new else None,
        }

    ok = all(v["identical"] for v in out["codes"].values())
    print(f"\n=== 结论 === daily_kline 全部一致: {ok}")
    for c, v in out["codes"].items():
        print(f"  {c:<12} 旧 {v['old_seconds']:7.1f}s -> 新 {v['new_seconds']:6.3f}s "
              f"({v['speedup']}x)  {v['old_days']}天 {'OK' if v['identical'] else 'FAIL'}")

    path = os.path.join(HFQ, "snapshot", "compare_daily_kline.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"明细 -> {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
